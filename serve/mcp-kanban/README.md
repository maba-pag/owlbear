# owlbear-mcp-kanban — Kanban MCP Server

MCP server that exposes `KanbanEngine` operations as tools for pipeline agents. Registered in VS Code's MCP configuration as `owlbear-kanban`. Consumed by all pipeline agents to read and write the task board.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_mcp_kanban
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json` — not invoked directly.

### Tools

The server exposes exactly 8 tools:

| Tool | Signature |
|------|-----------|
| `list_tasks` | `list_tasks(status: str \| None = None, priority: str \| None = None, tag: str \| None = None, archival_reason: str \| None = None, ids: list[int] \| None = None, unclaimed: bool = False, blocked: bool \| None = None, parent: int \| None = None, search: str \| None = None, sort: str \| None = None, reverse: bool = False, limit: int = 0)` |
| `show_task` | `show_task(id: int, section: str \| None = None)` |
| `pick_tasks` | `pick_tasks(wave_size: int \| None = None, max_waves: int = 3)` |
| `create_task` | `create_task(title: str, body: str = "", priority: str = "needed", tags: list[str] \| None = None, parent: int \| None = None, depends_on: list[int] \| None = None)` |
| `edit_task` | `edit_task(id: int, body: str \| None = None, append_body: str \| None = None, timestamp: bool = False, priority: str \| None = None, parent: int \| None = None, add_dep: list[int] \| None = None, remove_dep: list[int] \| None = None, add_tag: list[str] \| None = None, remove_tag: list[str] \| None = None, block_reason: str \| None = None, archival_reason: str \| None = None, archival_refs: list[int] \| None = None)` |
| `move_task` | `move_task(id: int, status: str, archival_reason: str \| None = None, archival_refs: list[int] \| None = None)` |
| `start_work` | `start_work(id: int)` |
| `end_work` | `end_work(id: int, outcome: str, move_to: str \| None = None, note: str \| None = None, archival_reason: str \| None = None, archival_refs: list[int] \| None = None, block_reason: str \| None = None)` |

## Data Projections and Envelopes

### TaskSummary

Returned by `list_tasks` in `tasks: list[TaskSummary]`.

- Includes `dep_status` projection and archival metadata (`archival_reason`, `archival_refs`)
- Excludes full body content

### TaskFull

Returned by `show_task` and single-task mutation/lifecycle responses.

- Extends `TaskSummary`
- Adds `created` and `body`

### DispatchEntry and Wave

Returned by `pick_tasks` in `waves: list[Wave]`.

- `Wave`: `index`, `tasks`
- `DispatchEntry`: `id`, `status`, `priority`, `title`, `tags`, `agent`

### guidance Field

Responses include `guidance: list[str]` for operational hints (for example: DR-required block guidance and forward-skip warnings). Treat as advisory metadata.

## Archival Fields

`archival_reason` supports 5 values:

- `completed`
- `deprecated`
- `dropped`
- `duplicate`
- `wontfix`

`archival_refs` rules:

- Required with `archival_reason in {deprecated, duplicate}`
- Forbidden with `archival_reason in {completed, dropped, wontfix}`

## end_work Outcomes

Documented lifecycle outcomes for agent routing:

- `success`
- `reject`
- `release`
- `block`

`block` requires `block_reason`.

`reject` uses `move_to` as the target status.

## Usage Examples

```json
{"tool":"list_tasks","arguments":{"status":"in-progress","blocked":false,"limit":20}}
```

```json
{"tool":"show_task","arguments":{"id":1094,"section":"Acceptance Criteria"}}
```

```json
{"tool":"move_task","arguments":{"id":1094,"status":"archived","archival_reason":"duplicate","archival_refs":[1001]}}
```

```json
{"tool":"end_work","arguments":{"id":1094,"outcome":"block","block_reason":"Awaiting user action"}}
```

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KANBAN_TOOLS_EXCLUDE` | _(none)_ | Comma-separated tool names to remove at startup (e.g. `create_task,move_task`) |

Board directory is resolved relative to the working directory at `.owlbear/kanban`. No override is supported at the MCP server level.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-kanban` | Kanban engine (workspace package) |
