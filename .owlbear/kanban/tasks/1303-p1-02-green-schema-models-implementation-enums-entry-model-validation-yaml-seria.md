---
id: 1303
title: 'P1-02: GREEN — Schema models implementation (enums, entry model, validation,
  YAML serialization)'
status: research
priority: needed
created: 2026-05-04T01:32:18.491117+00:00
updated: 2026-05-04T01:34:21.754414+00:00
tags:
- phase-2
- scope:mcp-memory
- memory
- mcp
parent: 1301
depends_on:
- 1302
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1301

## Acceptance Criteria

- [ ] MemoryCategory enum with 9 values including 3 renames (domain-knowledge, behaviour, pitfall)
- [ ] MemoryState enum with 4 values (pending, curated, approved, deleted)
- [ ] Entry dataclass with all schema fields, correct types, and defaults (scope_agents=[], approved_at=None)
- [ ] Validation: confidence rejects outside [0.7, 1.0], content rejects >1024 chars, categories requires >=1
- [ ] source_agent immutable after creation
- [ ] YAML frontmatter serialization and deserialization preserve all fields
- [ ] All #1302 tests pass

## Scope

- In: models module, enums, dataclass, validation logic, YAML serializer
- Out: state transitions, tool handlers, MCP registration