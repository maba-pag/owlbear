---
name: mcp-kanban
description: "Use the owlbear-kanban MCP tools to manage the kanban board programmatically. Covers all 7 tools: list_tasks, show_task, create_task, move_task, edit_task, pick_task, board_context."
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
| `create_task` | Create a new task | `title` (required), `priority`, `tags`, `body`, `depends_on`, `claim` |
| `move_task` | Move task to a new status | `task_id`, `status` (both required) |
| `edit_task` | Edit task fields | `task_id` (required), `body`, `block`, `unblock`, `tags`, `priority`, `append_body`, `claim`, `release`, `status`, `timestamp` |
| `pick_task` | Pick the next unclaimed task | `status`, `claim`, `move`, `tags` |
| `board_context` | Get a board context snapshot | (no parameters) |

## Error handling

All tools return `error: {message}` when `kanban-md` exits with a non-zero code. Check for the `error:` prefix to detect failures.

## Binary discovery

The server resolves `kanban-md.exe` at startup using:
1. `KANBAN_BIN` environment variable (explicit override)
2. `kanban/kanban-md.exe` (convention fallback — clone-then-run default)

If the binary is not found, the server fails to start with a `FileNotFoundError`.
