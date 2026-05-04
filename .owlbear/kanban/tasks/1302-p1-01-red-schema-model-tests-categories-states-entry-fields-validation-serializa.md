---
id: 1302
title: 'P1-01: RED — Schema model tests (categories, states, entry fields, validation,
  serialization)'
status: research
priority: needed
created: 2026-05-04T01:32:18.473705+00:00
updated: 2026-05-04T01:37:31.037212+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-04T01:37:31.037212+00:00
archival_reason:
archival_refs: []
---

Brief: see parent #1301\n\n## Acceptance Criteria\n\n- [ ] Tests assert MemoryCategory enum has 9 values (domain-knowledge, behaviour, pitfall, process, tool-usage, goal, personality, preference, env-context)\n- [ ] Tests assert MemoryState enum has 4 values (pending, curated, approved, deleted)\n- [ ] Tests assert Entry model fields: id (UUIDv4), title, categories, confidence, state, scope_agents, source_agent, created_at, updated_at, approved_at\n- [ ] Tests assert confidence validation rejects values outside [0.7, 1.0]\n- [ ] Tests assert content length validation rejects >1024 chars\n- [ ] Tests assert categories validation requires >=1 value from enum\n- [ ] Tests assert source_agent is required and immutable\n- [ ] Tests assert frontmatter YAML serialization roundtrip (write → read preserves all fields)\n- [ ] All tests fail (RED state — no implementation yet)\n\n## Scope\n\n- In: model definitions, enum values, field constraints, serialization format\n- Out: state machine logic, tool handlers, git integration