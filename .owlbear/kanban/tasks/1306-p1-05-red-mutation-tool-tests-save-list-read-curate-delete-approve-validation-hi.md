---
id: 1306
title: 'P1-05: RED — Mutation tool tests (save, list, read, curate, delete, approve
  — validation + hints)'
status: research
priority: needed
created: 2026-05-04T01:32:18.531671+00:00
updated: 2026-05-04T01:34:21.776530+00:00
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

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] Tests assert save_memory creates entry with state=pending, returns guidance hint\n- [ ] Tests assert list_memories returns metadata without body, filters by state/categories/scope_agents\n- [ ] Tests assert read_memory returns full entry by ID, errors on invalid/deleted IDs\n- [ ] Tests assert curate_memory validates: title non-empty, content <=1024, confidence [0.7,1.0], categories >=1\n- [ ] Tests assert curate_memory returns correct guidance hint per state transition\n- [ ] Tests assert delete_memory returns correct hint for hard-delete vs soft-delete\n- [ ] Tests assert approve_memory only works on curated entries, errors on other states\n- [ ] Tests assert OWLBEAR_MEMORY_CALLER env var has no effect (access control removed)\n- [ ] Tests assert MEMORY_TOOLS_EXCLUDE env var has no effect (access control removed)\n- [ ] Tests assert validation errors return teaching messages (Brief guidance hints table)\n- [ ] All tests fail (RED state)\n\n## Scope\n\n- In: 6 mutation tools (save, list, read, curate, delete, approve), parameter validation, guidance hints\n- Out: recall_memory (separate task #1308/#1309), git integration, consumer wiring