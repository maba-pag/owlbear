---
id: 198
title: Model scope field — add scope to Entity, Edge, Document
status: archived
priority: important
created: 2026-02-28T01:10:17.1495345+01:00
updated: 2026-02-28T23:53:46.8664412+01:00
started: 2026-02-28T01:11:43.2993051+01:00
completed: 2026-02-28T23:53:46.8664412+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
class: standard
---

Add scope: str = 'global' field to Entity, Edge, Document Pydantic models.

File: src/owlbear/memory/knowledge/models.py

AC:
- [ ] Entity model gains: scope: str = 'global'
- [ ] Edge model gains: scope: str = 'global'
- [ ] Document model gains: scope: str = 'global'
- [ ] All three models remain frozen=True (ConfigDict unchanged)
- [ ] Default value is 'global' (not None, not empty string)
- [ ] Scope field accepts arbitrary strings (no enum — values like 'global', 'project:owlbear', 'agent:builder')
- [ ] No changes to EntityType or RelationType enums

Depends on: #220 (test task)
See docs/knowledge-scoping-research.md
