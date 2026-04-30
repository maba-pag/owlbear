# owlbear-cockpit — Kanban Backend

FastAPI backend for the Cockpit kanban UI. Wraps `KanbanEngine` with an HTTP API consumed by the React frontend. For the frontend stack, entry points, and full endpoint list, see [copilot-instructions.md](../../.github/copilot-instructions.md) §3 and §4.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

See [copilot-instructions.md](../../.github/copilot-instructions.md) §4 for launch commands and environment variables (`COCKPIT_PORT`, `COCKPIT_NO_OPEN`, `KANBAN_DIR`).

## Engine Surface — Allowlist

The cockpit exposes a subset of `KanbanEngine`'s public API. All read access goes through `adapter.py`.

### Via adapter (read-only)

| Method | Purpose |
|--------|---------|
| `list_tasks(**kwargs)` | Task summaries for board columns |
| `show_task(task_id)` | Full task detail for the detail tab |
| `board_config()` | Statuses and priorities for column rendering |
| `valid_transitions(status)` | Validates move targets; also used by `move_task` route |
| `list_sessions(**kwargs)` | Work session data for the activity tab |
| `list_activity(**kwargs)` | Activity events for the audit trail tab |

### Mutation routes

All mutation routes go through the `CockpitView` facade.

#### Via CockpitView facade

| Method | Route | Notes |
|--------|-------|-------|
| `view.engine.show_task()` + `view.move_task()` | `POST /tasks/{id}/move` | OCC token precheck, then `valid_transitions` check, then move through CockpitView with `expected_updated`; `ConcurrencyError` → 409 |
| `view.show_task()` + `view.release_task()` | `POST /tasks/{id}/release` | Claimed check (409 if unclaimed), release through CockpitView with `expected_updated`; `ConcurrencyError` → 409 |
| `view.show_task()` + `view.edit_task()` | `POST /tasks/{id}/edit` | Pre-fetches task when `tags`, `depends_on`, or `block_reason` is set (for diff and D21 block:user lifecycle); diffs tags/deps, restores block:user; edit with `expected_updated`; `ConcurrencyError` → 409 |
| `view.sweep()` | `POST /tasks/sweep` | Releases expired claims; returns list of released task IDs |
| `view.scan_corruption()` | `POST /tasks/scan` | Scans all task files for corruption; returns list of `{code, detail, file_path}` items |
| `view.repair_storage()` | `POST /tasks/repair` | Repairs corrupted task files; returns list of `RepairOutcome` items |
| `view.compact_activity()` | `POST /tasks/compact-activity` | Compacts the activity log; returns `ActivityCompactionResult` |

### Excluded methods — why

| Method | Reason excluded |
|--------|----------------|
| `create_task()` | Pipeline agents create tasks, not the UI |
| `claim_task()` / `start_work()` / `end_work()` | Agent lifecycle operations |
| `refresh_config()` | Managed internally by the engine |

## Decisions API

Two endpoints handle Decision Request (DR) lifecycle. These routes use `get_decisions_dir` (a separate DI callable in `deps.py`) — not the CockpitView facade.

| Route | Behaviour |
|-------|----------|
| `GET /api/decisions/pending` | Reads `decisions/pending/*.md`, parses YAML frontmatter, returns `{count, items[{id, task_id, agent, request_type, created, title, body, body_preview}]}`. Only items with frontmatter `response == "pending"` are included. Returns `{count: 0, items: []}` when the directory is empty or missing. |
| `POST /api/decisions/{id}/resolve` | Accepts `{response: "approved"\|"needs-info"\|"rejected"\|"completed", notes?: string}`. Updates the DR file in-place (sets frontmatter `response`, appends `## Response` section). Returns 404 for unknown ids. The engine's `resolve_pending_drs` sweep (triggered by `pick_tasks`) handles the physical move to `resolved/`. |

## Work Sessions Model

`GET /api/sessions` returns derived `SessionRecord` objects built from `activity.jsonl` at read time — there is no separate sessions store.

### Derived states

| State | Derivation condition |
|-------|---------------------|
| `running` | Open claim; last activity within `claim_timeout` |
| `stuck` | Open claim; last activity exceeds `claim_timeout` |
| `completed` | `end_work` with `detail` starting `"success:"` |
| `rejected` | `end_work` with `detail` starting `"reject:"` |
| `blocked` | Any other `end_work` outcome |
| `released` | `release` action in the log |
| `expired` | `sweep-release` action in the log (expired claim auto-released) |

### Filter vocabulary

| Filter value | Included states |
|-------------|-----------------|
| `active` | `running`, `stuck` |
| `all` | all states |
| `blocked-or-rejected` | `blocked`, `rejected` |
| `failed-or-rejected` | `blocked`, `rejected` (legacy alias for `blocked-or-rejected`) |
| `released` | `released` |

Usage: `GET /api/sessions?filter=active`

## Audit Trail — `actor: "cockpit"` Convention

The engine is initialised with `agent_name="cockpit"`. Every mutation written to `activity.jsonl` carries `actor: "cockpit"`, distinguishing UI-initiated changes from agent-initiated ones (e.g. `actor: "builder"`).

## Configuration

See [copilot-instructions.md](../../.github/copilot-instructions.md) §4 for all environment variables.

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | HTTP framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response model validation |
| `owlbear-kanban` | Kanban engine (workspace package) |
