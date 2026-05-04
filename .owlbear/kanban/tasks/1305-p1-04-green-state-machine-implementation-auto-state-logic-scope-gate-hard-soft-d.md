---
id: 1305
title: 'P1-04: GREEN — State machine implementation (auto-state logic, scope gate,
  hard/soft deletion)'
status: research
priority: needed
created: 2026-05-04T01:32:18.519500+00:00
updated: 2026-05-04T01:34:21.769549+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1304
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] Auto-promote: curate pending entry with scope_agents -> state=curated\n- [ ] Scope gate: curate pending without scope_agents -> atomic rejection (no partial update)\n- [ ] Auto-downgrade: curate approved entry -> state=curated, approved_at cleared (unconditional, no equality check)\n- [ ] Curate curated entry -> stays curated (no state change)\n- [ ] Hard-delete: pending entry -> file removed from disk entirely\n- [ ] Soft-delete: curated/approved entry -> state=deleted, file retained on disk\n- [ ] Terminal: operations on deleted entries rejected\n- [ ] Invalid transitions raise appropriate errors\n- [ ] All #1304 tests pass\n\n## Scope\n\n- In: state machine module with transition functions, file deletion logic\n- Out: MCP tool registration, parameter schemas, guidance hints, git commits