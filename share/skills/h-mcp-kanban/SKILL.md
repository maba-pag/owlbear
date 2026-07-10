---
name: h-mcp-kanban
description: "Handbook: Owlbear Kanban MCP tool reference — 11 tools for programmatic board management"
user-invocable: false
---

# MCP Kanban Tool Reference

The Owlbear Kanban MCP server exposes the native kanban engine operations as MCP tools over stdio transport. Registered in `.vscode/mcp.json` as `ob-kanban`.

Server startup resolves board location from `KANBAN_DIR` when set. If unset or empty, it falls back to `.owlbear/kanban` relative to the process working directory.

For pipeline conventions and claiming protocol, see `r-pipeline-protocol`.

## Tool Summary

Exactly 11 tools are exposed:

<!-- markdownlint-disable MD056 -- pipe chars in Python union types (str | None) inside table cells -->
| Tool | Signature |
|------|-----------|
| `list_tasks` | `list_tasks(status: str | None = None, priority: str | None = None, tag: str | None = None, archival_reason: str | None = None, ids: list[int] | None = None, unclaimed: bool = False, blocked: bool | None = None, parent: int | None = None, search: str | None = None, sort: str | None = None, reverse: bool = False, limit: int = 0)` |
| `show_task` | `show_task(id: str | int, section: str | None = None)` |
| `pick_tasks` | `pick_tasks(wave_size: int | None = None, max_waves: int = 3)` |
| `create_task` | `create_task(title: str, body: str = "", status: str = "", priority: str = "", tags: list[str] | None = None, parent: int | None = None, depends_on: list[int] | None = None, ac: list[str] | None = None, proof_bundle: str | None = None)` |
| `edit_task` | `edit_task(id: str | int, title: str | None = None, body: str | None = None, append_body: str | None = None, timestamp: bool = False, priority: str | None = None, parent: int | None = None, ac: list[str] | None = None, add_ac: list[str] | None = None, remove_ac: list[str] | None = None, proof_bundle: str | None = None, add_dep: list[int] | None = None, remove_dep: list[int] | None = None, add_tag: list[str] | None = None, remove_tag: list[str] | None = None, block_reason: str | None = None, archival_reason: str | None = None, archival_refs: list[int] | None = None)` |
| `move_task` | `move_task(id: str | int, status: str, archival_reason: str | None = None, archival_refs: list[int] | None = None)` |
| `start_work` | `start_work(id: str | int)` |
| `end_work` | `end_work(id: str | int, outcome: str, move_to: str | None = None, note: str | None = None, archival_reason: str | None = None, archival_refs: list[int] | None = None, block_reason: str | None = None)` |
| `create_request` | `create_request(task_id: str | int, kind: str, title: str, summary: str, agent: str, options: list[dict] | None = None, body: str = "")` |
| `list_requests` | `list_requests(status: str = "pending", task_id: str | int | None = None)` |
| `show_request` | `show_request(request_id: str)` |
<!-- markdownlint-enable MD056 -->

### Filter and Retrieval Additions

- `list_tasks.ids`: direct ID lookup list. Must not be combined with other filter fields.
- `list_tasks.archival_reason`: filter archived tasks by reason.
- `show_task.section`: case-insensitive body-section extraction by heading; when missing, returns `body=None` and `missing_sections=[section]`.

### Creation Semantics

- `create_task.status`: omitted or `""` uses the product topology entry status (`shape`). Pipeline agents should pass this explicitly: `"build"` for build-ready leaf tasks and `"collect"` for aggregate parent/EPIC tasks parked behind child dependencies. Shaper should not rely on the default except for explicit raw manual intake.
- `create_task.priority`: omitted or `""` uses the product topology default priority (`medium`). Pass an explicit value when a different priority is intended.

### edit_task Semantics

- `title`: replaces task title; empty or whitespace-only values are rejected.
- `body`: omitted or `null` means no change, `""` clears body, non-empty text replaces body.
- `parent`: positive ID sets parent; `0` clears parent; omitted or `null` means no change.
- `ac`: full replacement of the AC list. Mutually exclusive with `add_ac`/`remove_ac`.
- `add_ac` / `remove_ac`: atomic add/remove of individual AC items. Mutually exclusive with `ac`.
- `proof_bundle`: normalized (lowercase, modifiers sorted) by model; validated against known values by engine.

## Projection Schemas

The engine projects task data through explicit MCP-facing envelopes.

### TaskSummary

List projection with dependency and archival context.

- Core: `id`, `title`, `status`, `priority`, `updated`
- Optional/context: `tags`, `blocked`, `block_reason`, `claimed_at`, `claimed`
- Archival fields: `archival_reason`, `archival_refs`
- Dependency projection: `dep_status` in `{ok, redirect, blocked}` (or `None` when no dependencies). `blocked` includes dependencies that are still active, missing, or archived with a blocking archival reason.
- `proof_bundle`: normalized string or `null`

### TaskFull

Full projection for show/update operations.

- Inherits `TaskSummary`
- Adds `created`, `body`, `ac: list[str]` (acceptance-criteria lines)

### DispatchEntry

Dispatch projection used by `pick_tasks` waves.

- `id`, `status`, `priority`, `title`, `tags`, `proof_bundle`, `agent`

### Wave

Dispatch wave envelope.

- `index` (0-based)
- `tasks: list[DispatchEntry]`

## Archival Semantics

`archival_reason` enum:

- `completed`
- `deprecated`
- `dropped`
- `duplicate`
- `wontfix`

`archival_refs` rules:

- Required for `deprecated` and `duplicate`
- Forbidden for `completed`, `dropped`, and `wontfix`
- Used only when the operation archives a task (`move_task(status="archived")` or `end_work(..., move_to="archived", ...)`)

## Response: Guidance Field

Mutation and lifecycle responses include `guidance: list[str]`.

`guidance` is advisory. An empty list means no guidance applies.

| Operation | When populated |
|-----------|---------------|
| `edit_task(block_reason=...)` | After blocking (DR-required message) |
| `end_work(outcome="block")` | After blocking (DR-required message) |
| `end_work(outcome="success")` | Always (commit-pushed reminder) |
| `move_task` to a status > 1 slot ahead | Forward-skip warning |

**Agent obligation:** If `guidance` is non-empty, read it before proceeding — it may require an immediate follow-up action such as creating a Decision Request with `create_request`.

### `block:user` Tag Exemption

Blocks initiated by a human via the Cockpit carry the `block:user` tag. When `block:user` is present on the after-state task, the block guidance rule fires with an **empty list** — the agent does not need to create a DR for user-driven blocks.

When an MCP agent calls `edit_task(block_reason=...)` or `end_work(outcome="block")`, the server automatically removes any stale `block:user` tag — the agent takes ownership of the block.

## Compound Tools

### start_work

Checks blocked and claim status, claims the task, and returns its full details. No status change.

On failure: raises `ToolError` (MCP `isError: true`).

### end_work

Counterpart to `start_work`. Appends a timestamped note, resolves the task based on `outcome`, and releases the claim.

`collect` is the pipeline's terminal on-board status. When a collector calls `end_work(outcome="success")` from `collect`, the task archives because `collect` is the last configured status. For direct user-directed cleanup outside the pipeline, do not report a task as closed while it remains in `collect`; either leave it intentionally for collector dispatch or archive it explicitly before calling the work complete.

Required outcomes to use in agent workflows:

| Outcome | Behaviour |
|---------|----------|
| `success` | Advance to next status (or to `move_to` if specified). If already at last status, archive. |
| `fail` | Record a failed attempt and release claim without progressing status. |
| `reject` | Move to `move_to` status, release claim. |
| `release` | Release claim, no status change (note appended if provided; no-op when unclaimed) |
| `block` | Mark blocked with `block_reason`, release claim. Optionally move to `move_to` status. |

**Forward skip:** `end_work(outcome="success", move_to="verify")` advances directly to `verify` (skipping intermediate statuses).

On failure: raises `ToolError` (MCP `isError: true`).

## Agent Lifecycle Pattern

Every pipeline agent follows a 2-call MCP lifecycle per task:

```python
# 1. Claim + read
task = start_work(id=480)

# 2. (do the actual work)

# 3. Append agent notes + advance + release — all in one call
end_work(id=480, note="## Builder Notes\n- Files changed: ...\n\n12 tests passed, ruff clean", outcome="success")
```

> **Anti-pattern:** Do NOT call `show_task` before `start_work`. `start_work` already returns the full task body — a preceding `show_task` is a redundant read. Use `show_task` only for secondary lookups (dependencies, parent briefs, re-reads).

Put your full agent section (header + content + summary) into the `note` parameter of `end_work`. The note is appended to the task body with a timestamp, then the task advances and the claim is released — all atomically.

For the section header to use per agent, see `pipeline-agents.instructions.md` — `## Per-Agent Section Mapping`.

### edit_task (advanced)

`edit_task` is available for field edits (tags, dependencies, blocking, unblocking) but is **not needed** for the standard lifecycle. The server auto-resolves claim identity when the calling agent owns the claim.

Do not use `edit_task` to append agent notes — use `end_work(note="...")` instead.

## Compound vs Single Tool Guidance

| Situation | Recommended Tools |
|-----------|------------------|
| Normal lifecycle (claim, work, advance) | `start_work` → `end_work` |
| Block mid-task | `end_work(outcome="block", block_reason="...")` |
| Reject (send back in pipeline) | `end_work(outcome="reject", move_to="shape")` |
| Inspect without claiming | `show_task` only |
| Scan the board | `list_tasks` with filters |
| Edit fields on a claimed task | `edit_task` (auto-resolves claim) |

## Error Handling

All tools raise `ToolError` (MCP `isError: true`) on failure.

## Body Content Gotchas

These affect both MCP `append_body`/`body` parameters and CLI `-a` arguments, because kanban-md parses the content internally.

- **`->` arrows** — parsed as CLI flag fragments. Use prose ("hands off to") instead.
- **`--token` patterns** — parsed as flags. Never paste raw CLI output containing `--cov`, `--tb`, etc. Describe in prose.
- **Pipe `|` characters** — safe through MCP (server handles escaping). Backtick-escape only when calling kanban-md CLI directly.
