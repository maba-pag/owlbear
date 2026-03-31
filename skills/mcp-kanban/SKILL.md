---
name: mcp-kanban
description: "Use the owlbear-kanban MCP tools to manage the kanban board programmatically. Covers all 6 tools: list_tasks, show_task, create_task, move_task, edit_task, pick_task."
user-invocable: false
---

# MCP Kanban Skill

The `owlbear-kanban` MCP server exposes all `kanban-md` board operations as MCP tools over stdio transport.

## Server registration

The server is registered in `.vscode/mcp.json` as `owlbear-kanban`.

## Tools

| Tool | Description | Key parameters |
|------|-------------|----------------|
| `list_tasks` | List tasks with optional filters | `status`, `tag`, `priority`, `block_filter`, `search`, `sort`, `unclaimed` |
| `show_task` | Show a single task by ID | `task_id` (required) |
| `create_task` | Create a new task | `title` (required), `body`, `claim`, `depends_on`, `parent` (int, 0=none), `priority`, `status`, `tags` |
| `move_task` | Move task to a new status | `task_id`, `status` (both required) |
| `edit_task` | Edit task fields | `task_id` (required), `body`, `block`, `unblock`, `tags`, `priority`, `append_body`, `claim`, `release`, `status`, `timestamp`, `add_dep`, `remove_dep`, `parent`, `title` |
| `pick_task` | Pick the next unclaimed task | `status`, `claim`, `move`, `tags` |

## Error handling

All tools return `error: {message}` when `kanban-md` exits with a non-zero code. Check for the `error:` prefix to detect failures.

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
`pick_task`.

Unknown names are silently ignored. If the variable is not set or is empty, all 6 tools
are registered (backwards-compatible default).
