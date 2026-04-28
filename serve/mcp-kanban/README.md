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

| Tool | Description |
|------|-------------|
| `list_tasks` | List tasks with optional `status`, `priority`, `tag`, `blocked`, `limit` filters |
| `show_task` | Fetch full task detail by ID |
| `create_task` | Create a new task with title, body, priority, tags, and dependencies |
| `move_task` | Move a task to a new status |
| `edit_task` | Edit task fields (body, append_body, priority, parent, tags, dependencies, block_reason, archival fields) |
| `start_work` | Claim a task and advance it to `in-progress` |
| `end_work` | Append an outcome note and apply outcome (success, fail, reject, block, or release) |
| `pick_tasks` | Select the top dispatchable tasks from the board |

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
