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
| `move_task(task_id, status, *, archival_reason=None, archival_refs=None)` | Change task status; `"archived"` moves file to `archive/` — requires a valid `archival_reason` |
| `claim_task(task_id)` | Mark task claimed by this engine's `agent_name`; rejects blocked/rival claims |
| `release_task(task_id, *, note=None)` | Clear claim unconditionally; appends a timestamped note to the body when `note` is provided |
| `start_work(task_id)` | Claim the task for this agent (no status advancement) |
| `end_work(task_id, …)` | Finalise a work session: append timestamped note and apply outcome (success, fail, block, or reject) |
| `board_config()` | Defensive copy of the current `BoardConfig` |
| `agent_view()` | Return the cached `AgentView` facade for agent-facing operations |
| `cockpit_view()` | Return the cached `CockpitView` facade for cockpit-facing operations |
| `valid_transitions(status)` | Set of all statuses except the given one |
| `refresh_config()` | Reload config from disk |
| `sweep()` | Release stale claims exceeding `claim_timeout` |
| `repair_storage()` | Quarantine corrupt task files and create action-required tasks |
| `list_sessions(**kwargs)` | Derived `SessionRecord` objects from `activity.jsonl` |

### Dispatch helper

```python
from owlbear_kanban import pick_dispatchable

dispatchable = pick_dispatchable(tasks)   # returns list[TaskSummary]
```

### AgentView dispatch pipeline

```python
agent = engine.agent_view()
response = agent.pick_tasks(wave_size=3, max_waves=3)  # returns PickTasksResponse
for wave in response.waves:
    for entry in wave.tasks:   # each entry: id, status, priority, title, tags, agent
        ...
```

`AgentView.pick_tasks` runs a five-step pipeline: resolve pending Decision Requests (exceptions logged and suppressed, never blocks dispatch), filter (exclude claimed/archived/blocked/dep-blocked tasks), deterministic sort (priority ASC, age DESC, id ASC), greedy wave assembly (size cap, dep-disjointness, agent-bucket compatibility), and agent assignment from `BoardConfig.agent_map`.

### Decision Requests

Lightweight file-based decision request (DR) helpers, stored under `decisions/` with `pending/` and `resolved/` subdirectories.

```python
from pathlib import Path
from owlbear_kanban.decisions import create_dr, resolve_pending_drs

# Create a pending DR file and block the task
create_dr(
    decisions_dir=Path(".owlbear/kanban/decisions"),
    engine=engine,
    task_id=42,
    agent="architect",
    request_type="approach-selection",
    body="Should we use X or Y?",
)

# Resolve pending DRs during dispatch (one-argument form used by pick_tasks)
moved = resolve_pending_drs(engine)
```

| Function | Description |
|----------|-------------|
| `create_dr(decisions_dir, engine, *, task_id, agent, request_type, body)` | Write a 5-field YAML-frontmatter DR to `pending/` using `O_EXCL` (atomic), then block the task via `engine.edit_task`. Collision retries append `-2`, `-3`, … suffix. |
| `resolve_pending_drs(decisions_dir, engine)` | Scan `pending/` and process non-pending responses: append summary to task body, unblock (`approved`/`rejected`) or keep blocked (`needs-info`), and move file to `resolved/` using collision-safe exclusive-create (suffixes `-2`, `-3`, … on conflict). Supports single-argument form `resolve_pending_drs(engine)` (used by `pick_tasks`). |

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

After `--lane config` runs, `agent_map`, `agent_types`, and `agent_compatibility` are empty stubs that must be populated before starting the engine.

## Configuration

Board directory is passed to the `KanbanEngine` constructor. No environment variables.

## Dependencies

| Package | Purpose |
|---------|---------|
| `pydantic` | Task and config model validation |
| `ruamel.yaml` | Round-trip YAML for task file serialisation |
| `pyyaml` | YAML loading |
