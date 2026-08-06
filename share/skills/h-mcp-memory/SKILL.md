---
name: h-mcp-memory
description: "Handbook: OwlBear Memory MCP tool reference — 8 shipped tools for agent institutional knowledge"
user-invocable: false
---

# MCP Memory Tool Reference

> **Audience:** Any agent with `save_memory` or `recall_memory` in its tools list, plus the memory-curator agent. **When:** Pre-flight knowledge loading, post-task reflection, and curation sessions. **Why:** Authoritative reference for all 8 MCP memory tools — parameters, behavior, error cases, and usage patterns.

The `owlbear-memory` MCP server exposes memory operations over stdio. The MCPServer app name is `owlbear-memory`; VS Code registers it in `.vscode/mcp.json` as `owlbear-memory`.

For curation workflow, see `w-mem-curation`.

## Agent Access Matrix

| Role | Agents | Available Tools |
|------|--------|----------------|
| Native implementation role | builder | `assess_memories`, `save_memory`, `recall_memory` |
| Candidate producer | test-curator | `save_memory` |
| Memory curator | memory-curator | `list_memories`, `read_memory`, `curate_memory`, `delete_memory` |

These profiles are intentionally asymmetric. A candidate producer may save a pending lesson without
recalling prior entries; the curator later deduplicates and scopes it. Recall-only and assessment-only
profiles are not assigned to active agents. Challengers report insights to their task-owning parent,
which owns task memory assessment and any resulting candidate.

`approve_memory` is not exposed to any agent — user-initiated only via the memory review prompt.

## Usage Patterns

### Curator lifecycle (list -> read -> curate -> delete)

1. `list_memories(states=["pending"])` to find candidates
2. `read_memory(entry_id=...)` for full content
3. `curate_memory(...)` to edit/promote with scope
4. `delete_memory(entry_id=...)` for noise/duplicates

### User approval flow

1. Curator leaves entries in `curated`
2. User runs the memory audit prompt for guided review
3. Approved entries become highest-trust retrieval candidates

### Exceptional-state resolution

1. Assessment transitions an entry to `contested`, `disputed`, or `stale`
2. The memory audit prompt surfaces the exceptional-state metadata
3. The user resolves or retires the entry from Cockpit's `/memories` page

There is no MCP resolution tool. `curate_memory` rejects exceptional states until Cockpit resolves
them to `approved`; `delete_memory` may soft-delete them when the user chooses retirement.

### Batch commits

Pending entries are not committed. After curation or review, use the state-aware
helper instead of broad-adding `.owlbear/memory`:

```text
uv --project ../owlbear run python -m owlbear_memory_mcp.git curation
uv --project ../owlbear run python -m owlbear_memory_mcp.git review
```

The `--project` path must point to the OwlBear installation root. Find the correct value from the `owlbear-memory` server entry in `.vscode/mcp.json` (look for the `--project` argument in the `args` array).

## Tool Summary

| Tool | Description | Key parameters |
|------|-------------|----------------|
| `save_memory` | Create a new `pending` memory entry | `title`, `content`, `categories`, `confidence`, `source_agent`, `scope_agents` |
| `list_memories` | List metadata filtered by state/category/scope | `states`, `categories`, `scope_agents` |
| `recall_memory` | Recall scoped identity-bearing memory blocks for agent pre-flight | `agent`, `categories`, `limit` |
| `read_memory` | Read one full memory entry by ID | `entry_id` |
| `assess_memories` | Record whether recalled entries were useful for a completed task | `task_id`, `assessments` |
| `curate_memory` | Curator mutation and code-managed state transition tool | `entry_id`, optional mutable fields, `scope_agents` |
| `delete_memory` | Lifecycle-aware deletion with hard/soft semantics | `entry_id` |
| `approve_memory` | Promote `curated -> approved` | `entry_id` |

## save_memory

Creates a new `pending` entry in `.owlbear/memory/*.md`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | str | (required) | Human-readable title, used for stable filename slug at creation |
| `content` | str | (required) | Markdown body content |
| `categories` | list[str] | (required) | One or more category values |
| `confidence` | float | (required) | Must be within `[0.7, 1.0]` |
| `source_agent` | str | (required) | Agent identifier recorded on the entry |
| `scope_agents` | list[str] \| null | `[source_agent]` | Initial scope; defaults to the source agent |

Returns: full entry object and a guidance hint indicating next-step curation.

## list_memories

Returns metadata-only entries sorted for lifecycle priority. `contested` shares curated priority;
`disputed` and `stale` sort after ordinary live entries.

Default behavior (when `states` is omitted): includes every non-deleted state.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `states` | list[str] \| null | `null` | Optional explicit state filter |
| `categories` | list[str] \| null | `null` | Optional category filter |
| `scope_agents` | list[str] \| null | `null` | Optional agent-scope filter |

Returns: metadata entries (no `content`) with fields including `id`, `title`, `categories`, `confidence`, `state`, `scope_agents`, `source_agent`, `created_at`, `updated_at`, `approved_at`.

## read_memory

Reads one full entry by `entry_id`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | Entry identifier |

Behavior:

- returns full entry including `content`
- errors if the entry is in `deleted` state

## recall_memory

Returns identity-bearing markdown blocks scoped to one agent for pre-flight loading.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent` | str | (required) | Agent name requesting relevant memory |
| `categories` | list[str] \| null | `null` | Optional category filter |
| `limit` | int \| null | `20` | Maximum entries to return; non-negative |

Behavior:

- includes `curated`, `approved`, and `contested` entries scoped to the agent
- returns `approved` entries before `curated`
- formats each block as `## {title}`, `Entry ID:`{id}``, and the body on consecutive lines
- omits all other entry metadata
- rejects blank or wildcard agent names

## assess_memories

Records how useful recalled memory entries were for a completed task. Include every entry returned
by `recall_memory` in one assessment batch.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `task_id` | str | (required) | Non-empty identifier for the completed task |
| `assessments` | list[dict[str, str]] | (required) | Non-empty list of per-entry assessments |

Each assessment item requires these fields:

| Field | Type | Description |
|-------|------|-------------|
| `entry_id` | str | Recalled memory entry identifier |
| `bucket` | str | One of the accepted bucket values below |

| Bucket | Meaning |
|--------|---------|
| `outstanding` | The entry's guidance was genuinely great for this task |
| `unremarkable` | The entry was applied or referenced and was adequate |
| `didnt_use` | The entry was not applied or referenced |
| `factually_wrong` | The entry contains incorrect information |

Behavior:

- a malformed item or invalid bucket rejects the entire batch before any entry is updated
- validly shaped items are processed individually
- entry-level failures such as a missing entry or invalid state are returned in `results` with
 `success: false`; other valid items may still succeed

Returns: `results`, containing `entry_id` and `success` for each item, plus `error` for failed items.

## curate_memory

Curator update tool for content edits and lifecycle transitions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | Entry identifier |
| `title` | str \| null | `null` | Replace title |
| `content` | str \| null | `null` | Replace markdown body |
| `categories` | list[str] \| null | `null` | Replace categories |
| `confidence` | float \| null | `null` | Replace confidence |
| `scope_agents` | list[str] \| null | `null` | Replace scope list |

State is code-managed and is not a caller-supplied parameter.

Auto-state behavior:

- `pending -> curated` when scope is provided
- any mutation from `approved` downgrades to `curated`
- mutations from `contested`, `disputed`, or `stale` are rejected until Cockpit resolves the entry
- other invalid transitions are rejected

Response hint values clarify what happened, for example:

- `Promoted from pending to curated with explicit scope.`
- `Downgraded from approved to curated; re-approve after review.`
- `Curated entry updated.`

Returns: updated entry object.

## delete_memory

Curator-only lifecycle mutation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | Entry identifier |

Behavior:

- pending entries are hard-deleted from disk
- curated/approved/contested/disputed/stale entries are soft-deleted (`state=deleted`)
- returns a hint describing hard vs soft delete path

Returns: updated entry object.

## approve_memory

Approves a curated entry.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | Entry identifier |

Behavior:

- only valid transition is `curated -> approved`
- raises `ToolError` for any other current state
- sets `approved_at` timestamp

Returns: updated entry object.

## Categories

Allowed category values:

| Value | Meaning |
|-------|---------|
| `domain-knowledge` | Verified technical fact |
| `behaviour` | Repeatable process behavior |
| `pitfall` | Failure mode and prevention |
| `process` | Workflow execution pattern |
| `tool-usage` | Tool-specific usage insight |
| `goal` | User or system objective constraint |
| `personality` | Operator interaction preference |
| `preference` | Stable choice preference |
| `env-context` | Situational or environment constraint |

## Examples

```text
save_memory(
 title="MCP server labels must stay <=13 chars",
 content="Tool prefix truncation broke matching in task #1307...",
 categories=["tool-usage", "pitfall"],
 confidence=0.8,
 source_agent="builder"
)
```

```text
list_memories(states=["pending"], categories=["tool-usage"])
read_memory(entry_id="...")
curate_memory(entry_id="...", scope_agents=["builder", "build-reviewer"])
```

```text
recall_memory(agent="builder", categories=["pitfall"], limit=10)
```

```text
assess_memories(
 task_id="1846",
 assessments=[
  {"entry_id": "...", "bucket": "outstanding"},
  {"entry_id": "...", "bucket": "didnt_use"}
 ]
)
```

```text
delete_memory(entry_id="...")
approve_memory(entry_id="...")
```

## Reflection Mapping

Recommended category mapping for post-task reflection bullets:

| Bullet type | Category |
|-------------|----------|
| `problems_faced` | `domain-knowledge` |
| `workarounds_applied` | `domain-knowledge` |
| `patterns_discovered` | `behaviour` |
| `time_sinks` | `env-context` |
| `quality_gaps` | `env-context` |

## Configuration

Memory entries are stored at `.owlbear/memory` under the current initialized workspace. The server
has no environment configuration.

## Error Behavior

All tools raise `ToolError` (surfaced as MCP error responses) for invalid operations:

| Error | Trigger | Example |
|-------|---------|---------|
| Entry not found | Invalid `entry_id` | `read_memory(entry_id="nonexistent")` |
| Invalid state transition | Wrong source state | `approve_memory` on a `pending` entry |
| Deleted entry access | Reading a soft-deleted entry | `read_memory` on `state=deleted` |
| Validation failure | Bad confidence, empty title, invalid category | `save_memory(confidence=0.5, ...)` |
| Blank agent | Empty or whitespace-only agent name | `recall_memory(agent="")` |

Tool responses include a `hint` field with human-readable guidance about what happened and suggested next steps.
