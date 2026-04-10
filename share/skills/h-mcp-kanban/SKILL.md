---
name: h-mcp-kanban
description: "Handbook: owlbear-kanban MCP tool reference — 8 tools for programmatic board management"
user-invocable: false
---

# MCP Kanban Tool Reference

The `owlbear-kanban` MCP server exposes the native kanban engine operations as MCP tools over stdio transport. Registered in `.vscode/mcp.json` as `owlbear-kanban`.

For pipeline conventions and claiming protocol, see `r-pipeline-protocol`.

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
| `pick_tasks` | Gate-filtered dispatch list, sorted by priority/status, capped at `limit` |

Parameter names, types, defaults, descriptions, and allowed values are exposed via the MCP tool schema. Use `list_tools` or inspect the schema directly — do not rely on this document for parameter details.

## Compound Tools

### start_work

Checks blocked and claim status, claims the task, and returns its full details. No status change.

On failure: raises `ToolError` (MCP `isError: true`).

### end_work

Counterpart to `start_work`. Appends a timestamped note, resolves the task based on `outcome`, and releases the claim.

| Outcome | Behaviour |
|---------|----------|
| `success` | Advance to next status. If already at last status, archive. |
| `fail` | Keep current status, release claim. |
| `block` | Mark blocked with `block_reason` (required), release claim. |
| `reject` | Move to `move_to` status (default: `research`), release claim. |

On failure: raises `ToolError` (MCP `isError: true`).

## Agent Lifecycle Pattern

Every pipeline agent follows a 2-call MCP lifecycle per task:

```python
# 1. Claim + read
task = start_work(task_id="480")

# 2. (do the actual work)

# 3. Append agent notes + advance + release — all in one call
end_work(task_id="480", note="## Builder Notes\n- Files changed: ...\n\n12 tests passed, ruff clean", outcome="success")
```

Put your full agent section (header + content + summary) into the `note` parameter of `end_work`. The note is appended to the task body with a timestamp, then the task advances and the claim is released — all atomically.

For the section header to use per agent, see `agent-common.instructions.md` — `## Per-Agent Section Mapping`.

### edit_task (advanced)

`edit_task` is available for field edits (tags, dependencies, blocking, unblocking) but is **not needed** for the standard lifecycle. The server auto-resolves claim identity when the calling agent owns the claim.

Do not use `edit_task` to append agent notes — use `end_work(note="...")` instead.

## Compound vs Single Tool Guidance

| Situation | Recommended Tools |
|-----------|------------------|
| Normal lifecycle (claim, work, advance) | `start_work` → `end_work` |
| Block mid-task | `end_work(outcome="block", block_reason="...")` |
| Reject (send back in pipeline) | `end_work(outcome="reject", move_to="todo")` |
| Inspect without claiming | `show_task` only |
| Scan the board | `list_tasks` with filters |
| Edit fields on a claimed task | `edit_task` (auto-resolves claim) |

## Error Handling

All tools raise `ToolError` (MCP `isError: true`) on failure.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KANBAN_TOOLS_EXCLUDE` | _(unset)_ | Comma-separated tool names to remove |

## Body Content Gotchas

These affect both MCP `append_body`/`body` parameters and CLI `-a` arguments, because kanban-md parses the content internally.

- **`->` arrows** — parsed as CLI flag fragments. Use prose ("hands off to") instead.
- **`--token` patterns** — parsed as flags. Never paste raw CLI output containing `--cov`, `--tb`, etc. Describe in prose.
- **Pipe `|` characters** — safe through MCP (server handles escaping). Backtick-escape only when calling kanban-md CLI directly.
