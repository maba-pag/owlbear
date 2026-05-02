---
name: h-mcp-memory
description: "Handbook: owlbearMemory MCP tool reference — 5 tools for agent institutional knowledge"
user-invocable: false
---

# MCP Memory Tool Reference

The `owlbearMemory` MCP server exposes agent memory operations as MCP tools over stdio transport. Registered in `.vscode/mcp.json` as `owlbearMemory`.

For pipeline integration (pre-flight, reflection), see `r-pipeline-protocol`.
For curation workflow, see `w-mem-curation`.

## Tool Summary

| Tool | Description | Key parameters |
|------|-------------|----------------|
| `store_learning` | Create a new `pending` memory entry | `title`, `content`, `categories`, `confidence`, `scope_agents` |
| `query_memory` | Read entries by lifecycle state with curated defaults | `states` (optional) |
| `update_entry` | Edit an entry (curator-only) | `entry_id`, optional mutable fields, optional `state` |
| `delete_entry` | Mark an entry as `deleted` (curator-only) | `entry_id` |
| `approve_entry` | Promote `curated -> approved` (user-only) | `entry_id` |

## store_learning

Creates a new `pending` entry in `.owlbear/memory/*.md` using YAML frontmatter plus markdown body.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `title` | str | (required) | Human-readable title, used for stable filename slug at creation |
| `content` | str | (required) | Markdown body content |
| `categories` | list[str] | (required) | One or more category values |
| `confidence` | float | (required) | Must be within `[0.7, 1.0]` |
| `scope_agents` | list[str] \| null | `null` | Optional audience scoping |

Returns: entry object with `id`, `title`, `categories`, `confidence`, `state`, `content`, `scope_agents`, `created_at`, `updated_at`.

## query_memory

Reads memory entries from the markdown file engine.

Default behavior (when `states` is omitted):

- include only `curated` and `approved`
- sort `approved` first, then `curated`
- within each state, sort by `confidence` descending

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `states` | list[str] \| null | `null` | Optional explicit state filter |

Returns: `list[entry]` with the same entry fields as `store_learning`.

## update_entry

Curator-only mutation tool for in-place updates.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | Entry identifier |
| `title` | str \| null | `null` | Replace title |
| `content` | str \| null | `null` | Replace markdown body |
| `categories` | list[str] \| null | `null` | Replace categories |
| `confidence` | float \| null | `null` | Replace confidence |
| `state` | str \| null | `null` | Transition state (restricted rules apply) |
| `scope_agents` | list[str] \| null | `null` | Replace scope list |

State rules:

- allowed: `pending -> curated`
- rejected: promotion from `deleted`
- other transitions must use dedicated tools

Returns: updated entry object.

## delete_entry

Curator-only lifecycle mutation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | Entry identifier |

Behavior:

- sets `state=deleted`
- allowed from `pending`, `curated`, or `approved`
- idempotent for already deleted entries

Returns: updated entry object.

## approve_entry

User-only lifecycle mutation.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | Entry identifier |

Behavior:

- only valid transition is `curated -> approved`
- raises `ToolError` for any other current state

Returns: updated entry object.

## Categories

Allowed category values:

| Value | Meaning |
|-------|---------|
| `knowledge` | Verified technical fact |
| `behaviour` | Repeatable process behavior |
| `pitfall` | Failure mode and prevention |
| `process` | Workflow execution pattern |
| `tool` | Tool-specific usage insight |
| `goal` | User or system objective constraint |
| `personality` | Operator interaction preference |
| `preference` | Stable choice preference |
| `context` | Situational or environment constraint |

## Reflection Mapping

Recommended category mapping for post-task reflection bullets:

| Bullet type | Category |
|-------------|----------|
| `problems_faced` | `knowledge` |
| `workarounds_applied` | `knowledge` |
| `patterns_discovered` | `behaviour` |
| `time_sinks` | `context` |
| `quality_gaps` | `context` |

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `MEMORY_TOOLS_EXCLUDE` | (unset) | Comma-separated tool names to remove at startup; unknown names silently ignored |
| `OWLBEAR_MEMORY_DIR` | `.owlbear/memory` | Path to memory markdown entry directory |
| `OWLBEAR_MEMORY_CALLER` | `unknown` | Default caller identity in non-interactive server contexts |

**Tool exclusion example:** Set `MEMORY_TOOLS_EXCLUDE=update_entry,delete_entry,approve_entry` to force read-and-capture mode.
