---
name: mcp-kanban
description: "Use the owlbear-kanban MCP tools to manage the kanban board programmatically. Covers all 8 tools: list_tasks, show_task, create_task, move_task, edit_task, pick_task, start_work, end_work."
user-invocable: false
---

# MCP Kanban Skill

The `owlbear-kanban` MCP server exposes all `kanban-md` board operations as MCP tools over stdio transport.

## Server registration

The server is registered in `.vscode/mcp.json` as `owlbear-kanban`.

## Tools

| Tool | Description | Key parameters |
|------|-------------|----------------|
| `list_tasks` | List tasks with optional filters | `status`, `tag`, `priority`, `search`, `sort`, `unclaimed`, `archived`, `limit`, `reverse`, `blocked` |
| `show_task` | Show a single task by ID | `task_id` (required) |
| `create_task` | Create a new task | `title` (required), `body`, `claim`, `depends_on`, `parent` (int, 0=none), `priority`, `status`, `tags` |
| `move_task` | Move task to a new status; returns JSON task object | `task_id`, `status` (both required) |
| `edit_task` | Edit task fields | `task_id` (required), `body`, `block`, `unblock`, `tags`, `priority`, `append_body`, `claim`, `release`, `status`, `timestamp`, `add_dep`, `remove_dep`, `parent`, `title` |
| `pick_task` | Pick the next unclaimed task; returns JSON task object | `status`, `claim`, `move`, `tags` |
| `start_work` | Compound: claim a task and return full JSON details | `task_id` (required), `claim` (optional — auto-generated if omitted) |
| `end_work` | Compound: append note, optionally advance status, release claim | `task_id`, `note`, `outcome` (required); `block_reason`, `move_to` (default: `ideation`), `claim` (optional) |

## start_work details

`start_work` replaces the separate claim + `show_task` pattern with a single call:

1. If no `claim` is provided, calls `kanban-md agent-name` to generate a unique two-word name (e.g. `cedar-cloud`).
2. Claims the task at its current status (no status change — the task must already be in the correct column).
3. Returns JSON with all `show_task` fields plus an injected `claim_name` field containing the name used.

On any failure (agent-name error, already-claimed, show failure) it returns `error: {reason}`.

The `claim_name` in the response is used by agents to release their claim at `end_work` without needing to know their name in advance.

## end_work details

`end_work` is the counterpart to `start_work`. It appends a note, optionally advances the task status, and releases the claim in one call.

Supported `outcome` values:

| Outcome | Behaviour |
|---------|-----------|
| `success` | Advances task to the next status (determined from board config). If the task is already at the last status, archives it instead. |
| `fail` | Keeps current status, releases claim. Use when work failed and needs to restart. |
| `block` | Marks the task blocked with `block_reason` and releases claim. `block_reason` is required when `outcome=block`. |
| `reject` | Moves task to `move_to` status (default: `ideation`) and releases claim. Use when the task is sent back in the pipeline. |

`claim` is optional: when provided it is passed to `--claim`; when absent, the tool reads `claimed_by` from `kanban-md show --json`.

Returns JSON from the final `kanban-md edit --json` call on success, or `error: {reason}` on failure.

## Error handling

Error handling differs by tool:

- **`show_task`, `move_task`, `pick_task`** — raise `ToolError` when `kanban-md` exits with a non-zero code. The MCP client receives `isError: true` in the call result. These tools also raise `ToolError` when the JSON output cannot be validated into a `KanbanTask` (wraps `ValidationError` with details).
- **`list_tasks`, `create_task`, `edit_task`, `start_work`, `end_work`** — return `error: {message}` string on failure. Check for the `error:` prefix to detect failures.

## Binary discovery

The server resolves `kanban-md.exe` at startup using:
1. `KANBAN_BIN` environment variable (explicit override)
2. `kanban/kanban-md.exe` (convention fallback — clone-then-run default)

If the binary is not found, the server fails to start with a `FileNotFoundError`.

## Configuration

The server reads the following environment variables at startup:

| Variable | Default | Description |
|----------|---------|-------------|
| `KANBAN_BIN` | `kanban/kanban-md.exe` | Path to the `kanban-md` binary |
| `KANBAN_TOOLS_EXCLUDE` | _(unset)_ | Comma-separated list of tool names to remove from the server |

### KANBAN_TOOLS_EXCLUDE

Set this variable to hide specific tools from the MCP server. This is useful when a client
should only have access to a subset of board operations (e.g., read-only access).

**Syntax:** comma-separated tool names, whitespace around names is stripped.

```
KANBAN_TOOLS_EXCLUDE=create_task,move_task,edit_task,pick_task
```

Valid names: `list_tasks`, `show_task`, `create_task`, `move_task`, `edit_task`,
`pick_task`, `start_work`, `end_work`.

Unknown names are silently ignored. If the variable is not set or is empty, all 8 tools
are registered (backwards-compatible default).
