# Decisions

## D1 — Investment Tier
**Shared.** Multi-surface cockpit foundation. Clean engine↔GUI contract, thorough tests, demo-ready polish. Consistent with the prep brief (also Shared) that was explicitly designed as groundwork for this project. Not Production — single laptop user, no SLOs, no external release engineering.

## D2 — Core Framing
**Steering cockpit**, not "kanban viewer." Intervention verbs (move, reprioritise, block/unblock, unclaim, edit body + allowlisted YAML) are headline features. Observability is the substrate; action is the point.

## D3 — Board / Activity Weighting (v1)
**~70 % board, ~30 % activity.** Activity is a proper panel, derived from claim state (`claimed + valid_claim == running`). No process monitoring.

## D4 — Intervention Principle
**Humans may RELEASE stuck work. Only agents may CLAIM or advance work-state.** Clean invariant that explains why unclaim is in and claim/start/end/dispatch are out.

## D5 — Display Principle
Never dump raw file contents. YAML frontmatter rendered as structured controls; markdown body rendered as markdown (with editor mode).

## D6 — Staleness Budget
**2–5 s.** SSE (server-sent events) as primary transport; mtime-scan polling @ 3 s as fallback when SSE connection drops. *Amended per resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md` (Option A approved).*

## D7 — Extensibility as Shell, Not Surfaces
v1 ships the **cockpit shell** (routing, layout, engine adapter, session model, theming). v1 ships **only the kanban surface + activity panel**. Future surfaces (decision queue, knowledge search, memory curation, agent/skill/instruction editor, VS Code settings controller, DnD dispatch) are out of v1, but their shape informs the shell design.

## D8 — Project Name
**cockpit.** Working directory renamed from `draft-new` to `draft-cockpit` after M1.

## D9 — O6 conflict detection via `updated`-timestamp save-time check
On task save, the cockpit re-reads the task and compares `updated` to the snapshot taken at load. If changed (regardless of which field changed), show a refresh-or-overwrite modal. Because the engine rewrites the whole task file on every edit and bumps `updated` accordingly, this provides task-level conflict detection without needing per-field compare-and-swap engine support.

## D10 — Activity surface: "Work Sessions" model
A **single combined surface** with smart row aggregation:

- **Row model:** one row per agent-claim-cycle (claim → release/end_work). The row mutates as state changes; never three rows for one task's lifecycle.
  - Active: *"builder started work on #347 (3 min ago)"*
  - Completed: *"builder worked on #347 (4m36s) — pass"* / *"fail"* / *"rejected → todo"*
- **Default filter:** show only active (currently-claimed) sessions.
- **Filter controls:** all sessions / failed-only / failed-or-rejected — switchable inline.
- **Lives in:** sidecar tab (alongside the task Detail tab).
- **Click row:** opens task in Detail tab + adds a **History subtab** showing per-session breakdown (which agent, duration, outcome).
- Mutations (e.g. unclaim) are reachable via the Detail tab once a row is opened. No inline buttons in the activity row itself.

**Data source:** dedicated **sessions log** (new schema) maintained by the engine. Each session is a logical unit (one row, mutated as state transitions) rather than a stream of raw events. The legacy `activity.jsonl` event format may be replaced or superseded — nothing currently consumes it, so we are free to redesign. The engine gains a `list_sessions(filter=...)` helper. This is accepted engine scope, not a separate brief.

## D11 — Benchmark `list_tasks()` at reality scale
**Scale baseline: 700 tasks (current real count) with headroom to 1500.** All scale references in subsequent docs use these numbers.

Single benchmark script. **This is the planner's first gating kanban task** — it precedes all other build work because its outcome may force engine changes:
- <150 ms: ship as-is
- 150–500 ms: implement YAML-head-only parsing optimisation in engine
- \>500 ms: in-memory cache or FSEvents watcher

## D12 — Backend exposes only allowed verbs; release is unrestricted
The cockpit HTTP layer exposes only the six v1 mutations. Agent-only verbs (`claim_task`, `start_work`, `end_work`, dispatch) are not routed at all — survives XSS by absence. The `release_task` endpoint allows release unconditionally (UI confirms; backend trusts the request because it cannot meaningfully second-guess from data alone — only an active claim is ever surfaced in the UI). D4 is preserved by surface design, not by backend gating.

## D13 — Static layout mockup before committing
**Planner's second gating kanban task** (parallel with D11 acceptable). Static HTML mockup at 1440×900 with sidecar open + 700-task board. Branches:
- Columns ≥100 px wide with sidecar open: ship the planned layout
- Columns <100 px: switch sidecar to overlay/drawer pattern (collapses by default)

## D14 — Stack & system topology (panel convergence, recorded)
- **Backend:** FastAPI at `serve/cockpit/`, imports `owlbear_kanban` directly. Single process, single port, single `uv run`.
- **Frontend:** React 19 + Vite + TypeScript. Built bundle served by FastAPI static handler.
- **Design system:** Porsche DS React wrapper primary; Radix UI + Tailwind on Porsche tokens as fallback if PDS card customisation proves heavy.
- **Network:** binds `127.0.0.1` only by default. `--allow-remote` flag (deferred to future brief) would require mandatory bearer token.
- **Change detection:** SSE as primary push transport (backend emits event on tasks-dir mtime change). Mtime-scan polling @ 3 s as automatic fallback when SSE connection is lost. Skip 1 poll cycle after a local mutation. *Amended per resolved DR `.owlbear/decisions/resolved/1233-cockpit-polling-vs-sse.md` (Option A approved).*
- **Layout:** thin top status bar (traffic light + counts) · narrow left icon rail (surface selectors) · kanban workspace center · right sidecar with Detail + Activity tabs.
- **Mutation safety:** "oppose-the-flow = confirm" — backward moves, unclaim, unblock require confirmation; forward moves and reprioritise don't. Unblock surfaces the block reason before clearing.
- **Audit:** cockpit-initiated mutations write `actor: "cockpit"` to `activity.jsonl`.
- **XSS:** rehypeSanitize + strict CSP on markdown body rendering. No `dangerouslySetInnerHTML` for any task-derived field.

## D15 — Packaging
Frontend source lives only on `dev` branch. CI sync builds the SPA bundle into `main` so consumer-side users need no Node toolchain.

