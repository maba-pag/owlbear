# owlbear-kanban — Kanban Engine

Transport-free kanban engine for the OwlBear pipeline. Provides filesystem-backed read/write operations for task files with no HTTP or CLI dependency — suitable for embedding in MCP servers, the Cockpit backend, and the orchestrator.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

No standalone launch. Import and use directly:

```python
from owlbear_kanban import KanbanEngine, Task, TaskSummary, WorkSession

engine = KanbanEngine(".owlbear/kanban")

# Read
tasks = engine.list_tasks(status="in-progress")
task  = engine.show_task(42)
cfg   = engine.board_config()

# Write
engine.create_task("My task", body="…", priority="important")
engine.move_task(42, "review")
engine.edit_task("42", add_tags=["phase-1"])
engine.claim_task(42)
engine.release_task(42)
```

### KanbanEngine methods

| Method | Description |
|--------|-------------|
| `list_tasks(**kwargs)` | List tasks with optional `status`, `priority`, `tag`, `blocked` filters |
| `show_task(task_id)` | Fetch a single full `Task` by ID |
| `create_task(title, …)` | Allocate next ID and write a new task file |
| `edit_task(task_id, …)` | Update task fields in-place (slug/filename unchanged) |
| `move_task(task_id, status, *, archival_reason=None, archival_refs=None)` | Change task status; `"archived"` moves file to `archive/` and requires a valid `archival_reason` |
| `claim_task(task_id)` | Mark task claimed by this engine's `agent_name`; rejects blocked/rival claims |
| `release_task(task_id, *, note=None)` | Clear claim unconditionally; appends a timestamped note to the body when `note` is provided |
| `start_work(task_id)` | Claim the task for this agent (no status advancement); if an existing rival claim is expired, it is reclaimed first. Returns `SingleTaskResponse` with a `guidance` list: one warning string when unresolved active dependencies are detected, empty otherwise |
| `end_work(task_id, …)` | Finalise a work session: append timestamped note and apply outcome (success, fail, block, or reject) |
| `board_config()` | Defensive copy of the current `BoardConfig` |
| `agent_view()` | Return the cached `AgentView` facade for agent-facing operations |
| `valid_transitions(status)` | Set of all statuses except the given one |
| `refresh_config()` | Reload config from disk |
| `repair_storage()` | Quarantine corrupt task files and create action-required tasks |
| `cleanup()` | User-triggered maintenance: release expired claims, move drift-archived files to `archive/`, remove tasks/ duplicates of archived records, and return a `CleanupResult` with `released_claim_ids`, `archived_task_ids`, `duplicate_removed_ids`, and `skipped_items` |
| `list_sessions(**kwargs)` | Derived `SessionRecord` objects from `activity.jsonl` |
| `create_request(task_id, kind, title, summary, agent, *, options=None, body="")` | Write a decision/action request to `decisions/pending/{uuid}.md`, block the task, and return a `RequestRecord`; rolls back the file if blocking fails |
| `get_request(request_id)` | Return a `RequestRecord` for the given UUID, searching `decisions/pending/` then `decisions/resolved/`; raises `NotFoundError` when absent, `ValidationError` on corrupt or invalid files |
| `resolve_request(request_id, selected_option_id, free_text)` | Resolve a pending structured request: validates option/kind/null constraints, writes updated file to `decisions/resolved/{request_id}.md`, deletes `decisions/pending/{request_id}.md`, appends write-back to the task body, and conditionally unblocks the task when no sibling structured requests remain pending; returns `RequestRecord` with populated resolution fields; raises `NotFoundError(ERR_NOT_FOUND)` or `ValidationError(ERR_ALREADY_RESOLVED)` |
| `list_requests(status="pending", task_id=None)` | List structured request files by status (`"pending"`, `"resolved"`, or `"all"`) with optional `task_id` filter; only UUID4-named files are returned; corrupt files are skipped with a WARNING log; results ordered by `created_at` ascending; returns `list[RequestRecord]` |
| `sweep_requests()` | Scan `decisions/pending/` for UUID4-named files where resolution fields are populated (manual edits or crash recovery); for each match in sorted filename order: sets `resolved_at`, moves to `decisions/resolved/`, deletes pending copy, appends write-back to the task body, and conditionally unblocks the task; post-move side-effect failures are logged at WARNING without interrupting the sweep; returns `list[str]` of resolved request IDs |

The `guidance` list in `SingleTaskResponse` from `start_work()` carries dependency warnings. When the task has at least one unresolved active dependency (a `depends_on` entry whose task is not archived), exactly one string is emitted: `"⚠️ This task has unresolved dependencies (IDs: {id, …}). Review and confirm with the user that starting this work is intentional."` Callers should surface this to the user before proceeding. When all dependencies are archived or the `depends_on` list is empty, `guidance` is `[]`. Dep-lookup exceptions are swallowed silently; failed lookups are excluded from the active-ID set.

### Utilities

| Function | Signature | Description |
|----------|-----------|-------------|
| `atomic_write` | `atomic_write(target: Path, content: str) -> None` | Crash-safe file write: writes content to a sibling `.tmp-*` temp file, fsyncs, then atomically renames to `target`. Removes temp on any error. |

```python
from owlbear_kanban import atomic_write
from pathlib import Path

atomic_write(Path("output.md"), "# Hello\n")
```

### Product topology (fixed)

Kanban topology is product-owned and fixed in code (not user-configured in `config.yml`).

| Topology element | Value |
|------------------|-------|
| Statuses | `research -> backlog -> todo -> in-progress -> review -> docs -> done` |
| Priorities | `someday`, `nice-to-have`, `important`, `needed`, `critical` |
| Status-to-agent routing | `research: researcher`, `backlog: architect`, `todo: test-writer`, `in-progress: builder`, `review: reviewer`, `docs: doc-writer`, `done: auditor` |
| Storage paths | `tasks/`, `archive/`, `decisions/` under `.owlbear/kanban/` |
| Archival reasons | `completed`, `deprecated`, `dropped`, `duplicate`, `wontfix` |
| Claim timeout | `1h` |
| Dispatch policy | Deterministic wave planning: priority ASC, age DESC, id ASC; dependency-disjoint wave assembly; fixed status-to-agent assignment |
| Activity logging | Enabled (`activity.jsonl` audit trail) |

### AgentView dispatch pipeline

```python
agent = engine.agent_view()
response = agent.pick_tasks(wave_size=3, max_waves=3)  # returns PickTasksResponse
for wave in response.waves:
    for entry in wave.tasks:   # each entry: id, status, priority, title, tags, agent
        ...
```

`AgentView.pick_tasks` begins with a maintenance step — `sweep_requests()` is called to flush manually-resolved structured requests before dispatch (failures are caught and logged at WARNING without interrupting the pipeline). The remaining five steps are read-only: topology validation against fixed product statuses, filter (exclude tasks with a live claim, archived/blocked tasks, and tasks whose `depends_on` entries are still active or otherwise dependency-blocked; apply TDD gate for in-progress tasks without `## Test-Writer Notes` unless tagged non-impl; apply clarity gate for active statuses without bullet/numbered AC lines; post-rehydrate archived-status guard skips tasks archived between list and show), deterministic sort (priority ASC, age DESC, id ASC), greedy wave assembly (size cap, dep-disjointness, agent-bucket compatibility), and fixed status-to-agent assignment.

Concurrency is handled via optimistic concurrency control (OCC): `write_task_if_unchanged` compares the task's `updated` timestamp before writing and raises `ConcurrencyError` on stale reads.

## Migration

To migrate an existing board from the legacy schema to the grouped canonical schema (``schema: grouped``):

```bash
uv run kanban-migrate [--dry-run] [--lane tasks|archive|config|all] [--kanban-dir PATH]
```

| Flag | Description |
|------|-------------|
| `--lane tasks` | Migrate only active task files (`tasks/`) |
| `--lane archive` | Migrate only archive files (`archive/`) |
| `--lane config` | Migrate only `config.yml` |
| `--lane all` | Run all three lanes (default) |
| `--dry-run` | Report what would change without writing any files |
| `--kanban-dir PATH` | Path to the kanban directory (default: auto-detect `.owlbear/kanban/`) |

Exit code 0 when no files failed; exit code 1 otherwise. Each failed file is reported on stderr as `FAIL {path}: {reason}`.

After `--lane config` runs, topology values (`agent_map`, `agent_types`, `agent_compatibility`, statuses, priorities, and pipeline settings) are provided by the product-topology constant and do not need to be set in `config.yml`. `pick_tasks()` works immediately after migration without any manual configuration.

## Configuration

Board directory is passed to the `KanbanEngine` constructor. No environment variables.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Task and config model validation |
| `ruamel.yaml` | Round-trip YAML for task file serialisation |
| `pyyaml` | YAML loading |
