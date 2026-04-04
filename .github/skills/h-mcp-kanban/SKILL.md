---
name: h-mcp-kanban
description: "Handbook: owlbear-kanban MCP tool reference — 8 tools for programmatic board management"
user-invocable: false
---

# MCP Kanban Tool Reference

The `owlbear-kanban` MCP server exposes all `kanban-md` board operations as MCP tools over stdio transport. Registered in `.vscode/mcp.json` as `owlbear-kanban`.

For the CLI equivalent, see the `h-kanban-md` skill.
For pipeline conventions and claiming protocol, see `r-pipeline-protocol`.

## Tool Summary

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `list_tasks` | List tasks with optional filters | `status`, `tag`, `priority`, `search`, `sort`, `unclaimed`, `archived`, `limit`, `reverse`, `blocked` |
| `show-task` | Show a single task by ID | `task_id` (required) |
| `create_task` | Create a new task | `title` (required), `body`, `claim`, `depends_on`, `parent`, `priority`, `status`, `tags` |
| `move_task` | Move task to a new status | `task_id`, `status` (both required) |
| `edit_task` | Edit task fields | `task_id` (required), plus field flags |
| `pick_task` | Pick the next unclaimed task | `status`, `claim`, `move`, `tags` |
| `start_work` | Compound: claim + return full details | `task_id` (required), `claim` (optional) |
| `end_work` | Compound: append note + advance + release | `task_id`, `note` (required), `outcome`, `claim` |

## Compound Tools

### start_work

Replaces the separate claim + `show-task` pattern with a single call:

1. If no `claim` is provided, calls `kanban-md agent-name` to auto-generate a unique two-word name (e.g., `cedar-cloud`).
2. Claims the task at its current status (no status change).
3. Returns JSON with all `show-task` fields plus an injected `claim_name` field.

On failure: returns `error: {reason}`.

### end_work

Counterpart to `start_work`. Appends a note, optionally advances task status, and releases the claim.

| Outcome | Behaviour |
|---------|-----------|
| `success` | Advances to next status (from board config). If already at last status, archives. |
| `fail` | Keeps current status, releases claim. |
| `block` | Marks blocked with `block_reason`, releases claim. `block_reason` required. |
| `reject` | Moves to `move_to` status (default: `ideation`), releases claim. |

`claim` is optional: when provided, passed to `--claim`; when absent, reads `claimed_by` from task metadata.

On success: returns JSON from final `kanban-md edit --json`. On failure: `error: {reason}`.

## Agent Lifecycle Pattern

Every pipeline agent follows a 3-call MCP lifecycle per task:

```python
# 1. Claim + read
task = start_work(task_id="480", claim="cedar-cloud")
claim = task["claim_name"]

# 2. Channel B (mid-task notes, repeatable)
edit_task(task_id="480", append_body="## Builder Notes\n- Files changed: ...", timestamp=True, claim=claim)

# 3. Advance + release
end_work(task_id="480", note="12 tests passed, ruff clean", outcome="success", claim=claim)
```

This replaces the 4-5 CLI call pattern with 3 MCP calls.

## Per-Tool Parameter Reference

### list_tasks

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | str | `""` | Filter by status column |
| `tag` | str | `""` | Filter by tag (comma-separated for multiple) |
| `priority` | str | `""` | Filter by priority level |
| `search` | str | `""` | Full-text search in title/body |
| `sort` | str | `""` | Sort field |
| `unclaimed` | bool | `false` | Only tasks with no claim |
| `archived` | bool | `false` | Include archived tasks |
| `limit` | int | `0` (no limit) | Maximum results to return |
| `reverse` | bool | `false` | Reverse sort order |
| `blocked` | bool\|null | `null` | Filter by blocked state |

Returns: `list[TaskDict]` or `error: {msg}`.

### show-task

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_id` | str | (required) | Task ID to show |

Returns: `TaskDict`. Raises `ToolError` on failure.

### create_task

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | str | (required) | Task title |
| `body` | str | `""` | Initial body/description |
| `claim` | str | `""` | Claim name to set immediately |
| `depends_on` | str | `""` | Comma-separated dependency IDs |
| `parent` | int | `0` (none) | Parent task ID |
| `priority` | str | `""` | Priority level |
| `status` | str | `""` | Initial status (default from board config) |
| `tags` | str | `""` | Comma-separated tags |

Returns: `str` confirmation or `error: {msg}`.

### move_task

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_id` | str | (required) | Task ID to move |
| `status` | str | (required) | Target status column |

Returns: `TaskDict`. Raises `ToolError` on failure.

### edit_task

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_id` | str | (required) | Task ID to edit |
| `title` | str | `""` | New title |
| `body` | str | `""` | Replace full body |
| `append_body` | str | `""` | Append text to body |
| `timestamp` | bool | `false` | Prepend timestamp to appended content |
| `claim` | str | `""` | Set claim name |
| `release` | bool | `false` | Release current claim |
| `status` | str | `""` | Move to new status |
| `block` | str | `""` | Block the task with reason |
| `unblock` | bool | `false` | Remove block |
| `tags` | str | `""` | Replace tags |
| `priority` | str | `""` | Set priority |
| `add_dep` | int | `0` | Add dependency by task ID |
| `remove_dep` | int | `0` | Remove dependency by task ID |
| `parent` | int | `0` | Set parent task ID |

Returns: `TaskDict`. Raises `ToolError` on failure.

### pick_task

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `status` | str | `""` | Status column to pick from |
| `claim` | str | `""` | Claim name to assign |
| `move` | str | `""` | Move task to this status after picking |
| `tags` | str | `""` | Filter by tags |

Returns: `TaskDict`. Raises `ToolError` on failure.

### start_work

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_id` | str | (required) | Task ID to claim and read |
| `claim` | str | `""` | Claim name (auto-generated via `agent-name` if omitted) |

Returns: `TaskDict` with injected `claim_name`, or `error: {msg}`.

### end_work

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_id` | str | (required) | Task ID to close |
| `note` | str | (required) | Note appended to body before advancing |
| `outcome` | str | `"success"` | `success`, `fail`, `block`, or `reject` |
| `block_reason` | str | `""` | Required when `outcome=block` |
| `move_to` | str | `"ideation"` | Target status when `outcome=reject` |
| `claim` | str | `""` | Claim name (reads from `claimed_by` if omitted) |

Returns: `TaskDict` or `error: {msg}`.

## Compound vs Single Tool Guidance

| Situation | Recommended Tools |
|-----------|------------------|
| Normal lifecycle (claim, work, advance) | `start_work` → `edit_task` (Channel B) → `end_work` |
| Block mid-task | `edit_task(block="reason", release=True)` |
| Reject (send back in pipeline) | `end_work(outcome="reject", move_to="todo")` |
| Inspect without claiming | `show-task` only |
| Scan the board | `list_tasks` with filters |
| Partial status move without release | `edit_task(status="...")` |

## Error Handling

- **`show-task`, `move_task`, `pick_task`, `edit_task`** — raise `ToolError` (MCP `isError: true`). Also raise on JSON validation failure (`KanbanTask` schema mismatch).
- **`list_tasks`, `create_task`, `start_work`, `end_work`** — return `error: {message}` string. Check for `error:` prefix.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `KANBAN_BIN` | `kanban/kanban-md.exe` | Path to the `kanban-md` binary |
| `KANBAN_TOOLS_EXCLUDE` | _(unset)_ | Comma-separated tool names to remove |

`KANBAN_TOOLS_EXCLUDE` accepts: `list_tasks`, `show-task`, `create_task`, `move_task`, `edit_task`, `pick_task`, `start_work`, `end_work`. Unknown names silently ignored.

## PowerShell Escaping Gotchas

MCP tools call kanban-md internally, but agents using `edit_task(append_body=...)` can still hit PS escaping issues when content is passed through. These gotchas also apply when mixing CLI and MCP calls.

### Pipe characters in body content

Markdown tables with `|` in `append_body` strings are generally safe through MCP (the server handles escaping), but backtick-escape pipes when calling kanban-md CLI directly. See `h-kanban-md` for full details.

### `->` arrows in body text

Body text containing `->` is parsed by kanban-md as shorthand flag fragments — replace with prose (e.g., "hands off to" instead of `->`) in both MCP `append_body` and CLI `-a` arguments.

### `--token` patterns in body text

Double-dash patterns (`--cov`, `--tb`) in body text are parsed as CLI flags by kanban-md. Keep evidence summaries in prose — never paste raw CLI output containing flag-style tokens into `append_body` or `-a` arguments.

### Temp-file pattern for complex body content

For body content with tables, multi-line sections, or special characters, write to a temp file first when using the CLI path:

```powershell
[IO.File]::WriteAllText("docs/scratch/$id-notes.tmp", $body, [Text.UTF8Encoding]::new($false))
$content = Get-Content "docs/scratch/$id-notes.tmp" -Raw
kanban\kanban-md.exe edit $id -a $content -t
Remove-Item "docs/scratch/$id-notes.tmp"
```

For MCP: prefer `edit_task(append_body=...)` which handles most escaping internally.

## Known Gotchas

- **Claim + release in the same `edit_task` call fails.** kanban-md forbids `--claim` and `--release` in the same command. Split into two calls, or prefer `end_work` which handles this internally.
- **`pick_task` grabs highest-priority unclaimed task.** This may not be the dispatched task. Always use `start_work` with an explicit `task_id` for dispatched work.
- **Binary discovery:** The server resolves `kanban-md.exe` via `KANBAN_BIN` env var, then falls back to `kanban/kanban-md.exe`. If not found, server fails to start with `FileNotFoundError`.
