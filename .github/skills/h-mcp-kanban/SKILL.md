---
name: h-mcp-kanban
description: "Handbook: owlbear-kanban MCP tool reference — 7 tools for programmatic board management"
user-invocable: false
---

# MCP Kanban Tool Reference

The `owlbear-kanban` MCP server exposes `kanban-md` board operations as MCP tools over stdio transport. Registered in `.vscode/mcp.json` as `owlbear-kanban`.

For pipeline conventions and claiming protocol, see `r-pipeline-protocol`.
For direct CLI access (deprecated, fallback only), see `h-kanban-md`.

## Tool Summary

| Tool | Description |
|------|-------------|
| `list_tasks` | List tasks with optional filters |
| `show_task` | Show full task details by ID |
| `create_task` | Create a new task |
| `move_task` | Move task to a status column, or archive it (status="archived") |
| `edit_task` | Edit task fields |
| `start_work` | Claim task and return full details |
| `end_work` | Append note, advance or resolve status, release claim |

Parameter names, types, defaults, descriptions, and allowed values are exposed via the MCP tool schema. Use `list_tools` or inspect the schema directly — do not rely on this document for parameter details.

## Compound Tools

### start_work

Claims the task and returns its full details as JSON. No status change.

On failure: returns `error: {reason}`.

### end_work

Counterpart to `start_work`. Appends a timestamped note, resolves the task based on `outcome`, and releases the claim.

| Outcome | Behaviour |
|---------|-----------|
| `success` | Advance to next status. If already at last status, archive. |
| `fail` | Keep current status, release claim. |
| `block` | Mark blocked with `block_reason` (required), release claim. |
| `reject` | Move to `move_to` status (default: `ideation`), release claim. |

On failure: returns `error: {reason}`.

## Agent Lifecycle Pattern

Every pipeline agent follows a 3-call MCP lifecycle per task:

```python
# 1. Claim + read
task = start_work(task_id="480")

# 2. Channel B (mid-task notes, repeatable)
edit_task(task_id="480", append_body="## Builder Notes\n- Files changed: ...", timestamp=True)

# 3. Advance + release
end_work(task_id="480", note="12 tests passed, ruff clean", outcome="success")
```

## Compound vs Single Tool Guidance

| Situation | Recommended Tools |
|-----------|------------------|
| Normal lifecycle (claim, work, advance) | `start_work` → `edit_task` (Channel B) → `end_work` |
| Block mid-task | `end_work(outcome="block", block_reason="...")` |
| Reject (send back in pipeline) | `end_work(outcome="reject", move_to="todo")` |
| Inspect without claiming | `show_task` only |
| Scan the board | `list_tasks` with filters |
| Partial status move | `edit_task(status="...")` |

## Error Handling

- **`list_tasks`, `show_task`, `move_task`, `edit_task`** — raise `ToolError` (MCP `isError: true`).
- **`create_task`, `start_work`, `end_work`** — return `error: {message}` string. Check for `error:` prefix.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KANBAN_BIN` | `kanban/kanban-md.exe` | Path to the `kanban-md` binary |
| `KANBAN_TOOLS_EXCLUDE` | _(unset)_ | Comma-separated tool names to remove |

## Body Content Gotchas

These affect both MCP `append_body`/`body` parameters and CLI `-a` arguments, because kanban-md parses the content internally.

- **`->` arrows** — parsed as CLI flag fragments. Use prose ("hands off to") instead.
- **`--token` patterns** — parsed as flags. Never paste raw CLI output containing `--cov`, `--tb`, etc. Describe in prose.
- **Pipe `|` characters** — safe through MCP (server handles escaping). Backtick-escape only when calling kanban-md CLI directly.

## Known Gotchas

- **Binary discovery:** The server resolves `kanban-md.exe` via `KANBAN_BIN` env var, then falls back to `kanban/kanban-md.exe`. If not found, server fails to start with `FileNotFoundError`.
