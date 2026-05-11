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
| `start_work(task_id)` | Claim the task for this agent (no status advancement); if an existing rival claim is expired, it is reclaimed first |
| `end_work(task_id, …)` | Finalise a work session: append timestamped note and apply outcome (success, fail, block, or reject) |
| `board_config()` | Defensive copy of the current `BoardConfig` |
| `agent_view()` | Return the cached `AgentView` facade for agent-facing operations |
| `valid_transitions(status)` | Set of all statuses except the given one |
| `refresh_config()` | Reload config from disk |
| `repair_storage()` | Quarantine corrupt task files and create action-required tasks |
| `cleanup()` | User-triggered maintenance: release expired claims, move drift-archived files to `archive/`, and return a `CleanupResult` with `released_claim_ids`, `archived_task_ids`, and `skipped_items` |
| `list_sessions(**kwargs)` | Derived `SessionRecord` objects from `activity.jsonl` |

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

`AgentView.pick_tasks` runs a five-step read-only pipeline: topology validation against fixed product statuses, filter (exclude tasks with a live claim, archived/blocked/dep-blocked tasks; apply TDD gate for in-progress tasks without `## Test-Writer Notes` unless tagged non-impl; apply clarity gate for active statuses without bullet/numbered AC lines; post-rehydrate archived-status guard skips tasks archived between list and show), deterministic sort (priority ASC, age DESC, id ASC), greedy wave assembly (size cap, dep-disjointness, agent-bucket compatibility), and fixed status-to-agent assignment.

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
