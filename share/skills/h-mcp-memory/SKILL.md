---
name: h-mcp-memory
description: "Handbook: OwlBear Memory MCP tool reference — 6 shipped tools for agent institutional knowledge"
user-invocable: false
---

# MCP Memory Tool Reference

The `owlbearMemory` MCP server exposes memory operations over stdio. Registered in `.vscode/mcp.json` as `owlbearMemory`.

For pipeline integration (pre-flight, reflection), see `r-pipeline-protocol`.
For curation workflow, see `w-mem-curation`.

## Tool Summary

| Tool | Description | Key parameters |
|------|-------------|----------------|
| `save_memory` | Create a new `pending` memory entry | `title`, `content`, `categories`, `confidence`, `source_agent` |
| `list_memories` | List metadata filtered by state/category/scope | `states`, `categories`, `scope_agents` |
| `read_memory` | Read one full memory entry by ID | `entry_id` |
| `curate_memory` | Curator mutation and state transition tool | `entry_id`, optional mutable fields, optional `state`, `scope_agents` |
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

Returns: full entry object and a guidance hint indicating next-step curation.

## list_memories

Returns metadata-only entries sorted for curation priority (`pending`, then `curated`, then `approved`).

Default behavior (when `states` is omitted): includes `pending`, `curated`, and `approved` entries.

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

## curate_memory

Curator update tool for content edits and lifecycle transitions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | Entry identifier |
| `title` | str \| null | `null` | Replace title |
| `content` | str \| null | `null` | Replace markdown body |
| `categories` | list[str] \| null | `null` | Replace categories |
| `confidence` | float \| null | `null` | Replace confidence |
| `state` | str \| null | `null` | Transition state (restricted rules apply) |
| `scope_agents` | list[str] \| null | `null` | Replace scope list |

Auto-state behavior:

- `pending -> curated` when scope is provided
- any mutation from `approved` downgrades to `curated`
- invalid transitions are rejected

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
- curated/approved entries are soft-deleted (`state=deleted`)
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

## Usage Patterns

### Curator lifecycle (list -> read -> curate -> delete)

1. `list_memories(states=["pending"])` to find candidates
2. `read_memory(entry_id=...)` for full content
3. `curate_memory(...)` to edit/promote with scope
4. `delete_memory(entry_id=...)` for noise/duplicates

### User approval flow

1. Curator leaves entries in `curated`
2. User runs `approve_memory(entry_id=...)`
3. Approved entries become highest-trust retrieval candidates

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
curate_memory(entry_id="...", scope_agents=["builder", "reviewer"])
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

| Env var | Default | Description |
|---------|---------|-------------|
| `OWLBEAR_MEMORY_DIR` | `.owlbear/memory` | Path to memory markdown entry directory |
