# Consumer Updates Phase 1 — Curator Agent Wiring + Skill Rewrites

> **Owning task:** #1312 — P1-11: Consumer updates Phase 1 — Curator agent wiring + skill rewrites
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1307 shipped a rewritten MCP memory server (`serve/mcp-memory/`) with renamed tools, new fields, auto-state logic, and guidance hints. Three consumer skills and one agent file still reference the old API. What changes are needed to bring them into alignment?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/mcp-memory/src/owlbear_mcp_memory/tools.py` | Implementation | 1.0 — definitive tool API |
| `serve/mcp-memory/src/owlbear_mcp_memory/models.py` | Implementation | 1.0 — schema + state machine |
| `serve/mcp-memory/src/owlbear_mcp_memory/engine.py` | Implementation | 0.9 — storage format + deletion semantics |
| `share/agents/memory-curator.agent.md` | Consumer | 0.9 — tools list, persona |
| `share/skills/h-mcp-memory/SKILL.md` | Consumer | 1.0 — full rewrite target |
| `share/skills/h-memory-structure/SKILL.md` | Consumer | 0.9 — schema changes |
| `share/skills/w-mem-curation/SKILL.md` | Consumer | 0.9 — tool name + logic changes |
| `.vscode/mcp.json` | Config | 0.8 — server registration confirms label `ob-memory` |

## 3. Analysis

### 3.1 Tool Name Mapping (old → new)

| Old Name | New MCP Tool | VS Code Runtime ID |
|----------|--------------|-------------------|
| `store_learning` | `save_memory` | `mcp_ob-memory_save_memory` |
| `query_memory` | `list_memories` | `mcp_ob-memory_list_memories` |
| _(no equivalent)_ | `read_memory` | `mcp_ob-memory_read_memory` |
| `update_entry` | `curate_memory` | `mcp_ob-memory_curate_memory` |
| `delete_entry` | `delete_memory` | `mcp_ob-memory_delete_memory` |
| `approve_entry` | `approve_memory` | `mcp_ob-memory_approve_memory` |

### 3.2 Category Renames

| Old | New |
|-----|-----|
| `knowledge` | `domain-knowledge` |
| `tool` | `tool-usage` |
| `context` | `env-context` |
| `behaviour` | `behaviour` (unchanged) |
| `pitfall` | `pitfall` (unchanged) |
| `process` | `process` (unchanged) |
| `goal` | `goal` (unchanged) |
| `personality` | `personality` (unchanged) |
| `preference` | `preference` (unchanged) |

### 3.3 New Schema Fields

| Field | Type | Notes |
|-------|------|-------|
| `source_agent` | `str` (required, frozen) | Identifies recording agent; immutable after creation |
| `approved_at` | `str | None` | Set on curated→approved; cleared on downgrade |

### 3.4 Key Behavioral Changes

| Behavior | Old | New |
|----------|-----|-----|
| `scope_agents` default | `null` | `[]` (empty list) |
| Content limit | Unspecified | 1024 chars max |
| Auto-state: pending→curated | Not documented | Triggered when `scope_agents` provided in `curate_memory` |
| Auto-state: approved→curated | Not documented | Triggered on ANY field mutation via `curate_memory` |
| Deletion | Uniform soft-delete | Hard-delete (pending), soft-delete (curated/approved) |
| Hints | None | 7 guidance messages returned with each mutation |

### 3.5 Agent Tool Wiring Delta

Current `memory-curator.agent.md` tools array needs:
- **Remove:** `vscode/memory`
- **Add:** `ob-memory/save_memory`, `ob-memory/list_memories`, `ob-memory/read_memory`, `ob-memory/curate_memory`, `ob-memory/delete_memory`, `ob-memory/approve_memory`

## 4. Recommendation

**Confidence: 0.92** — Direct mapping task; implementation is stable and tested.

All changes are mechanical rewrites to match the shipped server API. No design choices needed — the implementation defines the contract.

Challenge: N/A — trivial mapping task, no competing options.

### Implementation approach:
1. `memory-curator.agent.md` — swap tool names (1 removal, 6 additions)
2. `h-mcp-memory` — full rewrite: 6 tools, new params, auto-state, hints, categories
3. `h-memory-structure` — add `source_agent` + `approved_at` to schema table, update categories, update scope_agents default
4. `w-mem-curation` — update tool names in state machine table and Step 1/3/4, add auto-state awareness, document guidance hints

## 5. Follow-up Tasks

The task itself (#1312) is the implementation task — it moves to `backlog` for the architect to refine AC then to builder execution. No additional follow-up tasks needed; the scope is self-contained within the 4 files listed.
