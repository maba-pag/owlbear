# Cockpit Project Landscape Scan — Research Notes

**Working Directory:** `.owlbear/briefs/draft-cockpit/`
**Tier:** Shared | **Scope:** v1 = kanban board + activity panel inside extensible cockpit shell
**Date:** 2026-04-17

---

## PART A: CODEBASE SCAN

### 1. Kanban Engine Surface (`serve/kanban/src/owlbear_kanban/`)

**Public API:**
- `KanbanEngine` — main filesystem-backed engine class
- `Task`, `TaskSummary`, `BoardConfig` — Pydantic models (canonical task representation)
- `pick_dispatchable` — dispatch selector for agent priority ranking

**Key Methods:**
- `list_tasks(status=, priority=, tag=, blocked=, ...)` → `list[TaskSummary]` (filtered, sorted by config rank)
- `show_task(task_id)` → `Task` (full object with markdown body)
- `edit_task(task_id, {fields})` → mutates in-place; slug frozen at creation
- `move_task(task_id, status)` → status transition, validates via `valid_transitions()`
- `claim_task(task_id)` → agent-only; cockpit must not expose
- `release_task(task_id)` → unclaims unconditionally (**key for cockpit unclaim use case**)
- `start_work` / `end_work` → agent lifecycle, cockpit must not expose
- `board_config()` → defensive copy of config (valid statuses, priorities, display order)
- `valid_transitions(status)` → `set[str]` of all reachable statuses
- `revision` property → per-instance counter, incremented on every write

**Concurrency:** Exclusive file locking (`fcntl.flock` / `msvcrt.locking`) + atomic writes via `os.replace`. Per-instance revision counter; cross-process detection is the GUI's responsibility.

**Activity Log:** `.owlbear/kanban/activity.jsonl` — append-only JSONL, entries `{timestamp, action, task_id, detail, actor}`. Actions: create, edit, move, claim, release, block, unblock, archive.

### 2. MCP Server Adapter Pattern

Pattern: `server.py` wraps engine with MCP tool decorators; `models.py` provides boundary models. Cockpit backend should mirror this pattern but with HTTP routes instead of MCP tools. MCP transport itself (stdio) is not reusable for a browser client.

### 3. Python Workspace

- `uv` manager; workspace members under `serve/*`
- Each package has its own `pyproject.toml`
- Tests in root `tests/`; pytest config at root
- ruff: 3.12 target, line-length 120
- Cockpit backend fits as `serve/cockpit/`

### 4. Existing Frontend

None. `serve/browser/` is a Playwright web scraper, unrelated. **Cockpit frontend is greenfield.**

---

## PART B: ECOSYSTEM SCAN

### 1. Launch Mechanism Options

| Mechanism | Idle Memory | Startup | Setup Friction | Fit |
|-----------|-------------|---------|----------------|-----|
| **FastAPI + static SPA** | 40–80 MB | 2–3 s | Low (single `uv run`) | ✅ Recommended |
| VS Code webview extension | +0 (shared VS Code process) | <1 s | Medium (extension packaging) | ⚠ Tightly couples cockpit to VS Code |
| Electron | 150–250 MB | 5–10 s | High (binary packaging) | ❌ Overkill |
| Tauri | 80–150 MB | 3–5 s | High (Rust toolchain) | ❌ Overkill |
| Static + MCP HTTP relay | 30–50 MB | 1–2 s | Medium (custom middleware) | ❌ Awkward; MCP is stdio-native |

**Recommendation:** FastAPI + static SPA. Backend imports `owlbear_kanban` directly; serves JSON over HTTP + static files. Polling the `revision` counter @ 3 s satisfies the staleness budget.

### 2. Porsche Design System

- v3, Apache 2.0, production-ready, actively maintained
- Tech flavours: **Web Components** (Lit-based, framework-agnostic), **React wrapper**, **Vue 3**, **Angular**, raw HTML/CSS tokens
- No hard CSS reset; custom-element scoping; light/dark built in
- Fit:
  - ✅ React + Vite (mature React wrapper)
  - ✅ SvelteKit + Web Components
  - ✅ Vue 3 (official wrapper)
  - ❌ HTMX (client-side components don't fit server-rendering paradigm)

### 3. Frontend Frameworks

| Framework | Bundle (gz) | v1 fit | Notes |
|-----------|-------------|--------|-------|
| **React + Vite** | ~100 KB | ✅ Primary | Largest ecosystem, Porsche DS mature, cockpit patterns abundant |
| SvelteKit | ~30–50 KB | ✅ Alt | Compiler-based, smaller bundle, great DX, fewer patterns |
| Vue 3 | ~50 KB | ✅ Alt | Official Porsche DS wrapper, smaller community than React |
| Solid.js | ~25 KB | ⚠ No | Emerging; risky for Shared tier |
| Lit / Web Components | ~10 KB | ⚠ No | Fewer layout patterns; Shadow DOM complexity |
| HTMX + SSR | ~15 KB | ❌ No | Polling inverted, gesture story poor, form-centric |

### 4. Optimistic UI + Short-Poll

Standard React pattern: snapshot → optimistic update → API call → rollback on error → revision-counter poll for reconciliation. Poll interval 3 s. Skip poll if a local mutation was issued within the last ~500 ms to avoid clobbering in-flight state.

### 5. Markdown + YAML Frontmatter

| Library | Use |
|---------|-----|
| **react-markdown + remark-gfm + rehypeSanitize** | Primary render |
| js-yaml | Frontmatter parse |
| DOMPurify | Extra sanitization layer if needed |

Always sanitize body output; agent-authored markdown should be treated with the same caution as user input.

### 6. Design System Alternatives

If Porsche DS doesn't fit:
- **Radix UI + Tailwind** — unstyled accessible primitives + utility CSS; high control
- **shadcn/ui** — copy-paste Radix + Tailwind; easy customization
- **Carbon DS (IBM)** — professional, technical aesthetic
- **Material 3 Web** — if Material is desired aesthetic
- Reject: Fluent UI (MS-centric), Ant Design (form-heavy)

### 7. Prior-Art Cockpit Layouts

| Tool | Layout | Pattern |
|------|--------|---------|
| Apache Airflow | L-sidebar / canvas / R-sidebar | nav \| canvas \| detail |
| Prefect | Top nav / L-section / center / R-filters | context \| discovery \| canvas \| refine |
| Temporal | Top-context / L-search / center / modals | context \| discovery \| detail \| overlays |
| Linear | L-sidebar / center / R-detail | nav \| content \| inline-detail |
| GitHub Projects | Top-nav / L-filters / canvas / inline edit | minimal chrome, inline mutations |

**Converged principles:**
1. Inline mutations > modals for quick actions (move, block, unclaim)
2. Detail panel (right or tab) > full-page for body/YAML edits
3. Status light + running count in status region
4. Sidebar/search reserved but not required in v1

---

## KEY RISKS / UNKNOWNS

1. **Markdown view + edit mode.** No single React component combines view + edit with frontmatter split; may need a custom split-pane.
2. **Board performance at ≥200 tasks.** Requires React.memo + possibly virtualized column lists.
3. **Polling + concurrent edits.** Stale poll could clobber user action; use revision-check conditional refresh and poll-skip after local mutation.
4. **Porsche DS task cards may not fit cockpit indicators.** Overrides or custom cards likely.
5. **Activity panel freshness.** `activity.jsonl` may trail engine state; poll both activity + revision and handle missing `actor` gracefully.

---

## RECOMMENDATIONS

- **Backend:** FastAPI at `serve/cockpit/` importing `owlbear_kanban` directly; mirrors MCP adapter pattern.
- **Frontend:** React + Vite; primary Porsche DS React wrapper; fall back to Radix + Tailwind if PDS card customisation proves heavy.
- **Architecture contract:** URL-routed surfaces; engine adapter as singleton; reserved sidebar + status slots; typed JSON boundary; revision polling @ 3 s with local-mutation skip window.
- **Validation early:** prototype task card with PDS + optimistic move before locking DS choice.

---

## PART C: REFERENCE-PROJECT SCAN

### Archon (coleam00/Archon)
- **What:** YAML-defined workflow engine for AI coding. Deterministic step sequencing with fresh-context-per-iteration.
- **Stack:** Bun + TypeScript backend; Next.js + React frontend; SQLite.
- **Shell:** Chat sidebar + Conversation | Mission Control dashboard | Workflow Builder (drag-drop DAG) | Execution viewer.
- **Mutations:** Visual DAG editor; executions read-only; feedback via chat.
- **Steal:** Fresh context per iteration (aligns with OwlBear D4 principle). Side-by-side workflow-def + execution view.
- **Avoid:** DAG complexity when a state machine suffices.

### Mission Control / Autensa (crshdn/mission-control)
- **What:** Autonomous product-improvement loop; research → ideation → swipe → plan → build → test → review → PR.
- **Stack:** Next.js + TS + Tailwind; Node/Express + SQLite; SSE for activity feed.
- **Shell:** Top navbar + left agent panel + center canvas (kanban / swipe / planning) + right detail pane.
- **Mutations:** Drag-drop kanban; modals for plan Q&A, settings; inline notes; cost breakdown dialogs.
- **Steal:** Per-task agent sessions (D4 alignment). Live activity feed via SSE overlaid right. Checkpoint & crash recovery. Operator-chat queue (notes/nudges to running agent).
- **Avoid:** Modal-heavy interactions for fast flows; unbounded swipe fatigue.

### OpenClaw Command Center (jontsai/openclaw-command-center)
- **What:** Real-time monitoring for OpenClaw agent fleet — sessions, costs, cron jobs, memory.
- **Stack:** Vanilla JS (no bundler) + Node/Express + SSE.
- **Shell:** Hero metrics top + multi-panel grid (Sessions / Cron / Topics / Operators / Memory / Costs) + click-to-expand modals.
- **Mutations:** Intentionally read-only. Enable/disable cron only.
- **Steal:** Localhost-only by default. Zero-config workspace auto-detection. 5-second server-side cache to prevent polling thrash. Audit logging of mutations.
- **Avoid:** Over-polling; overloading dashboard with control (they kept it monitor-only).

### Vibe Kanban (BloopAI/vibe-kanban)
- **What:** Kanban + isolated-worktree workspace runner for multi-agent coding; integrated terminal + dev server + browser preview.
- **Stack:** React + TS frontend; Rust + SQLite backend; WebSocket.
- **Shell:** Left kanban with drag-drop + center workspace (terminal / dev log / integrated browser) + right detail pane (diff review with inline comments).
- **Mutations:** Drag-drop kanban; modals for create/edit; inline diff comments; serialized merge queue.
- **Steal:** Detail pane with inline comments as feedback channel. Kanban-on-the-left layout density. Clear per-agent worktree isolation.
- **Avoid:** Integrated browser/workspace scope creep for v1; multi-agent coordination without crisp handoff semantics.

### Cross-Cutting Insights

1. **Fresh context / per-task isolation** is a recurring reliability pattern — aligns directly with OwlBear's D4 invariant.
2. **Kanban + right-panel detail beats modals** for interaction speed. Modals reserved for rare blocking actions.
3. **Revision-counter polling is simpler than SSE** for a filesystem-backed engine. Activity feed may additionally use SSE (optional for v1).
4. **Reserve multi-surface shell regions early** (sidebar / main / detail / status). All four projects converge here; v2+ rework is avoided by planning from v1.
5. **Security-first defaults** (localhost-only bind) with optional token / Tailscale / Cloudflare Access for remote deployment. Never expose secrets in UI.

