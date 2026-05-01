# Brief: OwlBear Cockpit — v1 (Kanban + Activity)

## Summary

Build an extensible web GUI for OwlBear — the **steering cockpit** — whose v1 surface is the kanban board plus a Work Sessions activity panel. The cockpit is a *stop-and-redirect* operator console, not a read-only dashboard. It runs as a single FastAPI process serving a static React SPA, importing `owlbear_kanban` directly. The shell is structured for future surfaces (decision queue, knowledge search, memory curation, agent/skill/instruction editor, recurring-tasks panel, VS Code settings controller, DnD dispatch) without architectural rework.

## Investment Tier

**Shared.** Multi-surface foundation, clean engine↔GUI contract, thorough tests, demo-ready polish. Single laptop user + occasional shoulder-surfing demos. No SLOs, no external release engineering.

## Problem Statement

OwlBear today is steered entirely through the CLI and filesystem. The user lists tasks via MCP, reads task files by hand, opens `activity.jsonl` to infer what's running, and jumps into decision files to see what's pending. This is fine for an automated pipeline but **leaves the human operator blind and slow when intervention matters**.

The real problem is not "I can't see the board" — it is **"I can't quickly decide what needs my attention and act on it."** The board is the most acute blind spot because it aggregates the most state, but the underlying need is a steering cockpit: a single surface where the operator observes the system, spots where their judgement is required, and intervenes directly.

v1 focuses on the kanban surface because it is the highest-value beachhead. The cockpit shell must be structured for additional surfaces named as near-term extensions.

## Intervention Principle (D4)

> **Humans may RELEASE work (with confirmation). Only agents may CLAIM or advance work-state.**

The cockpit is *stop-and-redirect*, not *start-and-run*. This invariant explains why release/unclaim is in v1 and claim, `start_work`, `end_work`, dispatch, and task creation are not. The original "stuck only" framing was loosened in M4: the cockpit cannot reliably distinguish a stuck claim from an actively-running one (we only see status changes, not running processes), so the operator's confirmation is the gate, not a backend stuck-check.

## Outcomes

| # | Outcome | Success Indicator |
|---|---------|-------------------|
| O1 | **Board at a glance** | At 1440×900 with ≥700 tasks loaded, all status columns visible (horizontal scroll between columns; vertical within). "What's in review?" / "What's blocked?" answerable without clicking. Cold-load time is *not* a pass/fail criterion — post-load smoothness is. |
| O2 | **Intervene without leaving the surface** | Six v1 mutations (move, reprioritise, block/unblock, unclaim, edit body, edit allowlisted YAML — fields: `title`, `tags`, `priority`, `depends_on`, `parent`, `block_reason`) reachable from the board. Quick mutations ≤2 clicks/keystrokes. A GUI mutation is visible to a parallel MCP `list_tasks` within 5 s. Destructive mutations confirm. |
| O3 | **I know what's running, and I know my view is fresh** | (a) Work Sessions surface shows session states in human language: *running*, *stuck*, *released* (operator unclaimed), *completed-pass*, *completed-fail*, *completed-rejected*. (b) Status region traffic light (green/yellow/red) reflects engine connection health within one update cycle (sub-second via SSE; ≤3 s via polling fallback), per resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`. |
| O4a | **Extensibility: shell welcomes new surfaces** | A hello-world second surface = route + component + optional nav entry. Shell↔surface contract is documented. No shell-layout changes needed. |
| O4b | **Cockpit layout philosophy** | Top status bar · left icon rail (surface selectors) · workspace center (kanban in v1) · a sidecar panel carrying **Detail + Activity tabs**. Whether the sidecar is always-visible or behaves as an overlay/drawer is decided by the D13 mockup outcome — the panel contract (tab structure, surface reachability) is invariant. Reserved areas (project/consumer nav) present but empty. |
| O5 | **Coherent, tokenized design** | All UI uses Porsche DS primitives + tokens (or fallback DS — see D14). No hand-rolled colour hex outside tokens file. Recolouring is a token swap. |
| O6 | **Safe intervention** | Read-only fields have no interactive UI. Destructive mutations confirm. On save, `updated`-timestamp comparison detects concurrent agent edits and prompts refresh-or-overwrite. Optimistic UI rolls back on engine error. |
| O7 | **Trustworthy foundation (Shared-tier)** | (a) Adapter test coverage at Shared bar. (b) Docs page lists engine surface used. (c) Induced engine failure produces visible recoverable error state within one update cycle. |

## Solution Approach

### Phase 0 — Gating Validations (D11, D13)

These two tasks **block** Phase 1 because their outcomes may force architecture changes.

| Task | Detail | Branch |
|------|--------|--------|
| **Bench `list_tasks()` at 700 / 1500 tasks** | Single benchmark script. Measure p50 / p99. | <150 ms → ship; 150–500 ms → YAML-head-only parse; >500 ms → in-memory cache or FSEvents watcher |
| **Static layout mockup (HTML + CSS, no logic)** | 1440×900, sidecar open, 700 tasks rendered. Visual readability check. | Cols ≥100 px → planned layout; <100 px → sidecar becomes overlay/drawer pattern |

### Phase 1 — Backend (`serve/cockpit/`)

| Work Item | Detail |
|-----------|--------|
| Package skeleton | New uv workspace member at `serve/cockpit/`. `pyproject.toml` deps: `owlbear-kanban`, `fastapi`, `uvicorn`, `pydantic`. |
| FastAPI app | Single `main.py` mounting routes + static handler for SPA bundle. Bind `127.0.0.1` only by default. |
| HTTP routes (six v1 mutations + reads + SSE) | `GET /api/board` (config + valid_transitions), `GET /api/tasks` (TaskSummary list + mtime), `GET /api/tasks/{id}` (full Task + `updated` snapshot), `POST /api/tasks/{id}/move`, `POST /api/tasks/{id}/edit` (allowlisted YAML fields `title`, `tags`, `priority`, `depends_on`, `parent`, `block_reason` + body, requires `updated` snapshot for D9), `POST /api/tasks/{id}/release`, `GET /api/sessions?filter=` (derived from activity log), `GET /api/events` (SSE stream — emits change events on tasks-dir mtime change), per resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`. |
| `list_sessions` engine helper | New helper that **derives** logical Work Sessions by reducing existing `activity.jsonl` events (claim / release / move / edit / block / unblock / end_work). One logical session per claim cycle; mutates as state advances; terminal states: *completed-pass*, *completed-fail*, *completed-rejected*, *released*. No new log schema — sessions are a view over the existing event stream. Legacy activity.jsonl format is preserved; cockpit writes its own entries with `actor: "cockpit"`. |
| SSE + mtime-scan fallback | Backend pushes change events via SSE on tasks-dir mtime change; falls back to polling @ 3 s when SSE disconnects. Cache invalidates on mtime change (~1 ms scan); full reload only when files changed. Authority: resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`. |
| Audit | All cockpit mutations write `actor: "cockpit"` to `activity.jsonl` via the engine's existing logging path. Sessions log is derived, not separately written. |
| Engine adapter discipline | Backend imports only allowed engine methods. Linter or boundary test prevents accidental import of `claim_task`, `start_work`, `end_work`, `pick_dispatchable`. |

### Phase 2 — Frontend (`serve/cockpit/web/`)

| Work Item | Detail |
|-----------|--------|
| Vite + React 19 + TS scaffold | Built bundle output to `serve/cockpit/dist/`. |
| Porsche DS integration | React wrapper. Tokens layer extracted to `tokens.css`. **Fallback path:** if PDS task-card customisation proves heavy in Phase 0/1, swap to Radix UI + Tailwind on PDS tokens (D14). |
| App shell | Top status bar (traffic light + counts), left icon rail (surface selectors), workspace, right sidecar with Detail/Activity tabs. CSS Grid; reserved regions present-but-empty. |
| Kanban surface | Status columns by board config order; cards by priority. Card density ~48–56 px. Indicators: priority border, block badge, running indicator. Drag-to-move with valid-target highlighting (per `valid_transitions`); context menu for long-distance moves. |
| Detail tab | YAML allowlist as structured controls; markdown body as react-markdown + remark-gfm + rehypeSanitize editor/viewer. Save-time `updated` comparison (D9). History subtab listing per-session breakdown. |
| Activity tab (Work Sessions) | Default filter: active sessions (running + stuck). Filter switch: all / failed-or-rejected / released. One row per session, mutating as state advances. Click row → opens Detail tab + History subtab. |
| SSE + polling fallback | SSE as primary push channel; mtime-aware polling @ 3 s as automatic fallback. Skip 1 poll cycle after a local mutation. Authority: resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`. |
| Optimistic UI + rollback | Per-mutation snapshot + rollback on engine error. |
| Confirmations | "Oppose-the-flow" rule: backward moves, unclaim, unblock require confirm. Unblock surfaces existing block reason. |
| Connection health | Status traffic light: green = SSE connected, yellow = SSE lost (polling fallback active), red = disconnected. Authority: resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`. |
| XSS hardening | Strict CSP. No `dangerouslySetInnerHTML` for any task-derived field. rehypeSanitize on body render. |
| Empty / error / loading states | Designed (not browser-default). White-screen forbidden. |

### Phase 3 — Packaging & Delivery

| Work Item | Detail |
|-----------|--------|
| Launch | `uv run cockpit` starts FastAPI; auto-opens browser to `http://127.0.0.1:<port>/`. |
| Sync to main | CI build step bundles SPA into `main` branch. Consumer-side users need no Node toolchain. |
| Docs page | Engine surface used by cockpit (allow-list). Future-surface contract (route + component + adapter use). Hello-world second-surface walkthrough. |

## Out of Scope (mentioned for future Briefs)

- Task creation in cockpit (agent-only)
- Claim, `start_work`, `end_work`, archive, dispatch (agent-only)
- Editing timestamps, ids, claim fields
- Save-time per-field conflict detection (task-level via `updated` is sufficient for v1)
- WebSocket (SSE approved as primary transport per resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`; polling retained as fallback)
- Multi-user, auth, remote network binding (`--allow-remote` deferred to a future brief)
- Mobile / responsive layouts (desktop-only v1)
- Future surfaces themselves: decision queue, knowledge search, memory curation, agent/skill/instruction editor, recurring-tasks/maintenance panel, VS Code settings controller, drag-task-onto-chat dispatch (North Star)

## Constraints & Risks

| # | Item | Mitigation |
|---|------|------------|
| R1 | `list_tasks()` performance unknown at real scale (700+ tasks) | D11 benchmark gates Phase 1 |
| R2 | Sidecar-open layout may compress columns below readable width at 1440×900 | D13 mockup gates Phase 1; fallback to overlay/drawer pattern |
| R3 | Per-instance revision counter does **not** see cross-process writes | SSE push on mtime change (D14); polling @ 3 s as fallback — corrects the original research-notes assumption. Authority: resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`. |
| R4 | Concurrent same-task edits could overwrite agent changes | D9 `updated`-timestamp save-time check + traffic-light freshness signal |
| R5 | Markdown body XSS (agent-authored content) | rehypeSanitize + strict CSP (security panel: load-bearing control) |
| R6 | Porsche DS task cards may need heavy override for cockpit indicators | Validate during Phase 1; swap to Radix + Tailwind on PDS tokens if needed |
| R7 | Sessions log is new schema; engine work expands cockpit scope | Accepted; legacy activity.jsonl has no current consumers |
| R8 | SSE/polling vs in-flight mutation race | SSE suppresses push for 1 cycle after local mutation; polling fallback skips 1 cycle similarly. Authority: resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`. |

## Key Design Decisions (D-series, condensed)

| # | Decision |
|---|----------|
| D1 | Investment tier: **Shared** |
| D2 | Framing: **steering cockpit**, not kanban viewer |
| D3 | Board / activity weighting: **70 / 30** |
| D4 | **Humans RELEASE (with confirmation); agents CLAIM/advance** — cockpit cannot distinguish stuck-vs-running, so confirmation is the gate |
| D5 | YAML frontmatter and markdown body parsed and rendered separately |
| D6 | Staleness budget: **2–5 s**; SSE primary, polling fallback (amended per resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md`) |
| D7 | v1 ships shell + kanban + activity; future surfaces are out of v1 |
| D8 | Project name: **cockpit** |
| D9 | Save-time `updated`-timestamp conflict detection (refresh / overwrite modal) |
| D10 | Activity = **Work Sessions** (one row per claim cycle, mutating); engine `list_sessions` helper **derives** sessions from existing `activity.jsonl` events; no new log schema |
| D11 | Bench `list_tasks()` at 700 / 1500 tasks before Phase 1 (planner's first gating task) |
| D12 | Backend exposes only allowed verbs; release is unrestricted (UI confirms; D4 preserved by surface design and confirmation, not by backend stuck-check) |
| D13 | Static layout mockup at 1440×900 + sidecar + 700 tasks before Phase 1 (planner's second gating task) |
| D14 | Stack: FastAPI + React 19 + Vite + TypeScript + Porsche DS (Radix+Tailwind fallback). Localhost-only bind. |
| D15 | Frontend source on `dev` only; CI builds bundle into `main`. |

## Adoption Notes

- **For pipeline agents:** No behavioural change. The engine is unchanged in behaviour; only adds `list_sessions` (a derived view over existing activity events). Activity log schema is unchanged; cockpit writes new entries with `actor: "cockpit"`. MCP server unaffected.
- **For the user:** New `uv run cockpit` command starts the cockpit on `127.0.0.1`. Browser opens automatically.
- **For future-surface authors:** Follow the documented hello-world walkthrough. Register a route, drop a component, optionally surface a primary-nav entry. Use the engine adapter; do not touch shell layout.
