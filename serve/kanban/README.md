# owlbear-kanban — Kanban Engine

Transport-free kanban engine for the OwlBear pipeline. Provides filesystem-backed read/write operations for task files with no HTTP or CLI dependency — suitable for embedding in MCP servers, the Cockpit backend, and the orchestrator.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

No standalone launch. Import and use directly:

```python
from owlbear_kanban import KanbanEngine, Task, TaskSummary, BoardConfig, WorkSession

engine = KanbanEngine(".owlbear/kanban")

# Read
tasks = engine.list_tasks(status="in-progress")
task  = engine.show_task(42)
cfg   = engine.board_config()

# Write
engine.create_task("My task", body="…", priority="important")
engine.move_task(42, "review")
engine.edit_task(42, tags=["phase-1"])
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
| `move_task(task_id, status)` | Change task status; `"archived"` moves file to `archive/` |
| `claim_task(task_id)` | Mark task claimed by this engine's `agent_name`; rejects blocked/rival claims |
| `release_task(task_id)` | Clear claim unconditionally |
| `start_work(task_id)` | Claim and advance to `in-progress` |
| `end_work(task_id, …)` | Append outcome note and advance or reject |
| `board_config()` | Defensive copy of the current `BoardConfig` |
| `valid_transitions(status)` | Set of all statuses except the given one |
| `refresh_config()` | Reload config from disk |
| `sweep()` | Release stale claims exceeding `claim_timeout` |
| `repair_storage()` | Quarantine corrupt task files and create action-required tasks |
| `list_sessions(**kwargs)` | Derived `WorkSession` objects from `activity.jsonl` |

### Dispatch helper

```python
from owlbear_kanban import pick_dispatchable

dispatchable = pick_dispatchable(tasks)   # returns list[TaskSummary]
```

## Configuration

Board directory is passed to the `KanbanEngine` constructor. No environment variables.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Task and config model validation |
| `ruamel.yaml` | Round-trip YAML for task file serialisation |
| `pyyaml` | YAML loading |
