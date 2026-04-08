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
| `get_knowledge` | Retrieve memory entries for an agent, sorted by scope-specificity | `agent_id` (required), `limit`, `categories`, `min_confidence` |
| `record_learning` | Record a new learning entry | `agent_id`, `content`, `category`, `confidence` (all required), `scope_agent`, `scope_project` |
| `list_entries` | List entries with optional filters | `agent_id`, `category`, `status`, `include_deleted` |
| `set_approval_state` | Transition an entry's approval state | `entry_id`, `new_state` (both required) |
| `mark_for_deletion` | Soft-delete an entry (idempotent) | `entry_id` (required) |

## get_knowledge

Retrieves relevant entries for the agent, sorted by scope-specificity (most specific first), then approval state (approved first), then confidence descending. Deleted entries are always excluded.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | str | (required) | Agent name (matches `name:` in `.agent.md`) |
| `limit` | int | `50` | Maximum entries to return |
| `categories` | list[str] \| null | `null` | Filter by category (see valid values below) |
| `min_confidence` | float \| null | `null` | Minimum confidence threshold |

Returns: `list[dict]` — each entry has `id`, `content`, `category`, `confidence`, `created_at`, `updated_at`, `source`, `scope_agent`, `scope_project`, `approval_state`, `deleted_at`.

**Sort tiers** (1=most specific, 4=global):

| Tier | scope_agent | scope_project |
|------|-------------|---------------|
| 1 | matches agent | matches project |
| 2 | matches agent | null |
| 3 | null | matches project |
| 4 | null | null |

**Standard pre-flight call:**

```
get_knowledge(agent_id=<agent_name>, limit=20, min_confidence=0.7)
```

## record_learning

Records a new learning entry in `pending` state. Returns a bare UUID string on success, or `error: ...` on validation failure (confidence below 0.7 or invalid category). Does not raise ToolError.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | str | (required) | Source agent name (the `name:` field) |
| `content` | str | (required) | The learning text |
| `category` | str | (required) | One of: `preference`, `knowledge`, `context`, `behavior`, `goal` |
| `confidence` | float | (required) | Must be ≥ 0.7 |
| `scope_agent` | str \| null | `null` | Scope to specific agent (pass agent name for agent-specific entries) |
| `scope_project` | str \| null | auto-detected | Scope to specific project (auto-populated from server config if null) |

Returns: UUID string on success, `error: {msg}` on failure.

**Category mapping for post-task reflection:**

| Bullet type | Category |
|-------------|----------|
| `problems_faced` | `knowledge` |
| `workarounds_applied` | `knowledge` |
| `patterns_discovered` | `behavior` |
| `time_sinks` | `context` |
| `quality_gaps` | `context` |

## list_entries

Lists memory entries with optional filters. By default excludes deleted entries.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `agent_id` | str \| null | `null` | Filter by `scope_agent` |
| `category` | str \| null | `null` | Filter by category |
| `status` | str \| null | `null` | Filter by `approval_state` (`pending`, `approved`, `deleted`) |
| `include_deleted` | bool | `false` | Include deleted entries |

Returns: `list[dict]` or `error: {msg}`.

## set_approval_state

Transitions an entry's approval state. Raises `ToolError` if the entry does not exist. Returns `error: ...` string for disallowed or same-state transitions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | UUID of the entry |
| `new_state` | str | (required) | One of: `approved`, `deleted`, `pending` |

**Allowed transitions:** `pending → approved`, `pending → deleted`, `deleted → pending`.

Returns: success message string, or `error: {msg}` for disallowed transitions. Raises `ToolError` if entry not found.

## mark_for_deletion

Soft-deletes an entry by setting `approval_state` to `deleted`. Idempotent — calling on an already-deleted entry is a no-op.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `entry_id` | str | (required) | UUID of the entry |

Returns: success message string. Raises `ToolError` if entry not found.

## Configuration

| Env var | Default | Description |
|---------|---------|-------------|
| `MEMORY_TOOLS_EXCLUDE` | (unset) | Comma-separated tool names to remove at startup; unknown names silently ignored |
| `OWLBEAR_MEMORY_DB_PATH` | `store/memory/memory.db` | Path to the SQLite database file |

**Tool exclusion example:** Set `MEMORY_TOOLS_EXCLUDE=mark_for_deletion,set_approval_state` to restrict agents to read-only + record operations.
