---
id: 1307
title: 'P1-06: GREEN — Mutation tools + access control removal (6 tools, schemas,
  hints, env var cleanup)'
status: research
priority: critical
created: 2026-05-04T01:32:18.543007+00:00
updated: 2026-05-04T01:34:21.782703+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1306
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] 6 MCP tools registered: save_memory, list_memories, read_memory, curate_memory, delete_memory, approve_memory\n- [ ] Each tool has correct parameter schema with types, required flags, and descriptions\n- [ ] Validation errors return teaching messages per Brief guidance hints table\n- [ ] State transitions delegate to state machine module (#1305)\n- [ ] OWLBEAR_MEMORY_CALLER env var and all references deleted from codebase\n- [ ] MEMORY_TOOLS_EXCLUDE env var and all references deleted from codebase\n- [ ] All role-check/caller-gating code removed\n- [ ] list_memories: sorted by curation priority (pending first, then by created_at)\n- [ ] All #1306 tests pass\n\n## Scope\n\n- In: MCP tool registration, parameter schemas, handler implementations, access control removal\n- Out: recall_memory handler (task #1309), git batch commit, consumer agent wiring