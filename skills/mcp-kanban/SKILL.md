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

## Agent Workflow Pattern

Every pipeline agent follows a 3-step MCP lifecycle per task:

1. **`start_work(task_id, claim="<agent>")`** — Claim the task and retrieve full details in one call. Returns JSON with all `show_task` fields plus `claim_name`. Use `claim_name` in subsequent calls to release your claim.
2. **`edit_task(task_id, append_body="## Section\n...", timestamp=true, claim="<agent>")`** — Write Channel B context mid-task (multiple calls allowed). Equivalent to `kanban-md edit {id} -a "..." -t`.
3. **`end_work(task_id, note="...", outcome="success", claim="<agent>")`** — Append a final note, advance status, and release claim in one call. Equivalent to `kanban-md edit {id} --status {next} --release`.

This replaces the 4–5 CLI call pattern (show → claim → Channel B → advance → release) with 3 MCP calls.

### Example

```python
# Step 1: claim + read
task = start_work(task_id="480", claim="cedar-cloud")
claim = task["claim_name"]

# ... do work ...

# Step 2: Channel B (mid-task notes, can repeat)
edit_task(task_id="480", append_body="## Builder Notes\n- Files changed: ...", timestamp=True, claim=claim)

# Step 3: advance + release
end_work(task_id="480", note="12 tests passed, ruff clean", outcome="success", claim=claim)
```

---

## Per-Tool Parameter Reference

Expands the summary table above with full parameter names, types, and defaults.

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

### show_task

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
| `append_body` | str | `""` | Append text to body (use with `timestamp=true`) |
| `timestamp` | bool | `false` | Prepend `[[YYYY-MM-DD]] Day HH:MM` to appended content |
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
| `move` | str | `""` | Move the task to this status after picking |
| `tags` | str | `""` | Filter by tags |

Returns: `TaskDict`. Raises `ToolError` on failure.

### start_work

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_id` | str | (required) | Task ID to claim and read |
| `claim` | str | `""` | Claim name (auto-generated via `agent-name` if omitted) |

Returns: `TaskDict` with injected `claim_name` field, or `error: {msg}`.

### end_work

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_id` | str | (required) | Task ID to close |
| `note` | str | (required) | Note appended to task body before advancing |
| `outcome` | str | `"success"` | `success`, `fail`, `block`, or `reject` |
| `block_reason` | str | `""` | Required when `outcome=block` |
| `move_to` | str | `"ideation"` | Target status when `outcome=reject` |
| `claim` | str | `""` | Claim name (reads from `claimed_by` field if omitted) |

Returns: `TaskDict` or `error: {msg}`.

---

## Channel B Protocol

Channel B writes rich context to the task body for downstream agents to read via `show_task`.

**MCP equivalent of `kanban-md edit {id} -a "## Section\n..." -t`:**

```python
edit_task(
    task_id="{id}",
    append_body="## Builder Notes\n- Files changed: ...\n- Coverage: 95%",
    timestamp=True,
    claim="<agent>",
)
```

The `timestamp=True` flag prepends `[[YYYY-MM-DD]] Day HH:MM` to the appended content, matching the CLI `-t` flag behavior exactly.

Multiple `edit_task` calls with `append_body` are safe — each appends a new block. Use one call per section (Builder Notes, Review Evidence, etc.).

---

## Compound vs Single Tool Guidance

Use compound tools (`start_work` / `end_work`) by default. Fall back to individual calls only when finer control is needed.

| Situation | Recommended tools |
|-----------|------------------|
| Normal task lifecycle (claim → work → advance) | `start_work` → `edit_task` (Channel B) → `end_work` |
| Need to block mid-task | `edit_task(block="reason", release=True)` — no `end_work` |
| Need to reject (send back in pipeline) | `end_work(outcome="reject", move_to="todo")` |
| Need to inspect without claiming | `show_task` only |
| Scanning the board | `list_tasks` with filters |
| Partial status move without release | `edit_task(status="...")` — keeps claim |

`start_work` and `end_work` handle the claim/release protocol internally, avoiding the pitfall described below.

---

## Pitfalls

### Claim + release in the same edit_task call

`edit_task` wraps `kanban-md edit`, which forbids `--claim` and `--release` in the same call. The following will fail:

```python
# WRONG — claim and release in same call
edit_task(task_id="480", status="review", claim="cedar-cloud", release=True)
```

Split into two calls:

```python
# CORRECT — claim first, release separately
edit_task(task_id="480", claim="cedar-cloud")
edit_task(task_id="480", status="review", release=True)
```

**Prefer `end_work`** — it handles claim/release internally and is the correct tool for advancing a task:

```python
end_work(task_id="480", note="...", outcome="success", claim="cedar-cloud")
```

---

## Error handling

Error handling differs by tool:

- **`show_task`, `move_task`, `pick_task`, `edit_task`** — raise `ToolError` when `kanban-md` exits with a non-zero code. The MCP client receives `isError: true` in the call result. These tools also raise `ToolError` when the JSON output cannot be validated into a `KanbanTask` (wraps `ValidationError` with details).
- **`list_tasks`, `create_task`, `start_work`, `end_work`** — return `error: {message}` string on failure. Check for the `error:` prefix to detect failures.

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
