# owlbear-mcp-kanban — Kanban MCP Server

MCP server that exposes `KanbanEngine` operations as tools for pipeline agents. Registered in VS Code's MCP configuration as `ob-kanban`. Consumed by all pipeline agents to read and write the task board.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

```bash
uv run python -m owlbear_mcp_kanban
```

Typically launched as a stdio MCP server via VS Code's `mcp.json`/`settings.json` — not invoked directly.

### Tools

The server exposes 11 tools:

| Tool | Signature |
|------|-----------|
| `list_tasks` | `list_tasks(status: str \| None = None, priority: str \| None = None, tag: str \| None = None, archival_reason: str \| None = None, ids: list[int] \| None = None, unclaimed: bool = False, blocked: bool \| None = None, parent: int \| None = None, search: str \| None = None, sort: str \| None = None, reverse: bool = False, limit: int = 0)` |
| `show_task` | `show_task(id: str \| int, section: str \| None = None)` |
| `pick_tasks` | `pick_tasks(wave_size: int \| None = None, max_waves: int = 3)` |
| `create_task` | `create_task(title: str, body: str = "", priority: str = "", tags: list[str] \| None = None, parent: int \| None = None, depends_on: list[int] \| None = None, ac: list[str] \| None = None, proof_bundle: str \| None = None)` |
| `edit_task` | `edit_task(id: str \| int, title: str \| None = None, body: str \| None = None, append_body: str \| None = None, timestamp: bool = False, priority: str \| None = None, parent: int \| None = None, ac: list[str] \| None = None, add_ac: list[str] \| None = None, remove_ac: list[str] \| None = None, proof_bundle: str \| None = None, add_dep: list[int] \| None = None, remove_dep: list[int] \| None = None, add_tag: list[str] \| None = None, remove_tag: list[str] \| None = None, block_reason: str \| None = None, archival_reason: str \| None = None, archival_refs: list[int] \| None = None)` |
| `move_task` | `move_task(id: str \| int, status: str, archival_reason: str \| None = None, archival_refs: list[int] \| None = None)` |
| `start_work` | `start_work(id: str \| int)` |
| `end_work` | `end_work(id: str \| int, outcome: str, move_to: str \| None = None, note: str \| None = None, archival_reason: str \| None = None, archival_refs: list[int] \| None = None, block_reason: str \| None = None)` |
| `create_request` | `create_request(task_id: str \| int, kind: str, title: str, summary: str, agent: str, options: list[dict] \| None = None, body: str = "")` |
| `list_requests` | `list_requests(status: str = "pending", task_id: str \| int \| None = None)` |
| `show_request` | `show_request(request_id: str)` |

### Lifecycle and dispatch semantics

- `create_task.priority`: omitted or `""` uses the product topology default priority (`important`). Pass an explicit value when a different priority is intended.

- `pick_tasks` computes dispatch waves from task state. It sweeps pending request state as part of dispatch, so it is not read-only.
- `start_work` delegates to engine claim logic. If a rival claim is still live, the call fails; if the rival claim is expired, the claim is reclaimed and the task is claimed for the caller.
- `create_request` creates a structured pending request linked to a task and returns its full payload plus a `guidance` array.
- `list_requests` returns request summaries (body excluded) filtered by status and optional task.
- `show_request` returns a single request record with full detail including body and resolution. Accepts a UUID4 `request_id`.
- Cockpit maintenance triggers cleanup via its `POST /tasks/cleanup` route, which calls engine cleanup and releases expired claims plus archives done tasks.

## Data Projections and Envelopes

### TaskSummary

Returned by `list_tasks` in `tasks: list[TaskSummary]`.

- Includes `dep_status` projection and archival metadata (`archival_reason`, `archival_refs`)
- Includes `proof_bundle` (normalized string or `null`)
- Excludes full body content

### TaskFull

Returned by `show_task` and single-task mutation/lifecycle responses.

- Extends `TaskSummary`
- Adds `created`, `body`, and `ac: list[str]` (acceptance-criteria lines)

### DispatchEntry and Wave

Returned by `pick_tasks` in `waves: list[Wave]`.

- `Wave`: `index`, `tasks`
- `DispatchEntry`: `id`, `status`, `priority`, `title`, `tags`, `proof_bundle`, `agent`

### guidance Field

Responses include `guidance: list[str]` for operational hints (for example: DR-required block guidance, forward-skip warnings, and body-newline normalization notices). Treat as advisory metadata.

### Error Envelopes

All tool errors are returned as JSON objects with two fields:

```json
{"code": "ERR_NOT_FOUND", "message": "Task '99' not found"}
```

| Code | Trigger |
|------|---------|
| `ERR_NOT_FOUND` | Task file not found (FileNotFoundError) |
| `ERR_PARAM_VALIDATION` | Invalid parameter value or Pydantic validation failure |
| `ERR_INVALID_ID` | Malformed or non-positive task ID |
| `ERR_STALE_WRITE` | Concurrent write conflict detected by the engine |

Internal file paths are never included in error messages. `move_task` and `end_work` share a single validation path for archival constraints; errors from either tool use the same codes above.

## list_tasks Filter Semantics

- `ids=[]` (explicit empty list) returns an empty task list with no `missing_ids` entry. `ids=None` (omitted) returns all tasks matching other filters.
- `archival_reason` without `status` automatically defaults to searching archived tasks.

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

- `success`: Advance to the next status (or `move_to` when provided).
- `fail`: Record a failed attempt and release claim without changing status.
- `reject`: Move to `move_to`, then release claim.
- `block`: Mark task blocked (requires `block_reason`), optionally move to `move_to`, then release claim.
- `release`: Release claim without changing status.

`block` requires `block_reason`.

`reject` uses `move_to` as the target status.

## Usage Examples

`edit_task` semantics:

- `body`: omitted or `null` means no change, `""` clears, non-empty text replaces body
- `parent`: positive ID sets parent, `0` clears parent, omitted or `null` means no change

### Body text normalization

The following text body parameters are normalized at the MCP ingress boundary before any write:
`create_task.body`, `edit_task.body`, `edit_task.append_body`, `end_work.note`, `create_request.body`.

- Literal `\n` sequences are converted to actual newlines.
- To keep a literal `\n` in the stored file, send `\\n` in JSON input.
- When normalization occurs a guidance entry is appended to the response: _"Literal \n sequences were normalized to actual newlines."_

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
| `KANBAN_DIR` | `.owlbear/kanban` | Optional board directory override. Relative values resolve from process working directory, then normalize to absolute paths. |

If `KANBAN_DIR` is unset or empty, the server uses `.owlbear/kanban` relative to the current working directory.

## Dependencies

| Package | Purpose |
|---------|---------|
| `mcp[cli]` | FastMCP server framework |
| `owlbear-kanban` | Kanban engine (workspace package) |
