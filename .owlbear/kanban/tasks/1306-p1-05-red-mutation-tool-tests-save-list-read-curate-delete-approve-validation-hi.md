---
id: 1306
title: 'P1-05: RED — Mutation tool tests (save, list, read, curate, delete, approve
  — validation + hints)'
status: backlog
priority: needed
created: 2026-05-04T01:32:18.531671+00:00
updated: 2026-05-04T14:51:06.404175+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1305
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] Tests assert save_memory creates entry with state=pending, returns guidance hint
- [ ] Tests assert list_memories returns metadata without body, filters by state/categories/scope_agents
- [ ] Tests assert read_memory returns full entry by ID, errors on invalid/deleted IDs
- [ ] Tests assert curate_memory validates: title non-empty, content <=1024, confidence [0.7,1.0], categories >=1
- [ ] Tests assert curate_memory returns correct guidance hint per state transition
- [ ] Tests assert delete_memory returns correct hint for hard-delete vs soft-delete
- [ ] Tests assert approve_memory only works on curated entries, errors on other states
- [ ] Tests assert OWLBEAR_MEMORY_CALLER env var has no effect (access control removed)
- [ ] Tests assert MEMORY_TOOLS_EXCLUDE env var has no effect (access control removed)
- [ ] Tests assert validation errors return teaching messages (Brief guidance hints table)
- [ ] All tests fail (RED state)

## Scope

- In: 6 mutation tools (save, list, read, curate, delete, approve), parameter validation, guidance hints
- Out: recall_memory (separate task #1308/#1309), git integration, consumer wiring
[[2026-05-04]]
## Research

Research gate passed — T1 autonomous, no blockers.

**RED guarantees (6 mechanisms):**
1. `save_memory`, `list_memories`, `read_memory`, `approve_memory` — ImportError (functions don't exist)
2. `curate_memory`/`delete_memory` exist but return plain dicts without `"hint"` key
3. `OWLBEAR_MEMORY_CALLER` env var still active in server.py `app_lifespan`/`_require_role`
4. `MEMORY_TOOLS_EXCLUDE` env var still applies tool exclusions
5. Validation errors return raw Pydantic `str(exc)`, not teaching messages from Brief
6. No `list_memories` (metadata-without-body) or `read_memory` (by-ID) functions exist

**Test file:** `tests/test_mutation_tools_1306.py`
**Pattern:** Same as test_memory_schema_1302 and test_state_machine_1304 — mock MemoryEngine in tmp_path, mock MCP context, import from `owlbear_mcp_memory.tools`

**Sources:** Brief (.owlbear/briefs/draft-memory-mcp-ux/brief.md), existing tools.py, server.py, predecessor test files
**Follow-up tasks:** None needed — #1307 (GREEN) already exists as the implementation counterpart
**Decision requests:** None