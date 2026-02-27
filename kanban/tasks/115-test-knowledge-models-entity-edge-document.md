---
id: 115
title: Test knowledge models (Entity, Edge, Document)
status: todo
priority: high
created: 2026-02-27T03:42:28.9270327+01:00
updated: 2026-02-27T03:44:46.3745144+01:00
tags:
    - memory
    - knowledge-graph
    - test
    - phase-2
class: standard
---

TDD test suite for `owlbear.memory.knowledge.models`. Write tests BEFORE implementation (#108).

## Acceptance Criteria

- [ ] New file: `tests/test_knowledge_models.py`
- [ ] Test `EntityType` enum — all 6 values (file, function, class_, decision, pattern, concept) are valid
- [ ] Test `RelationType` enum — all 6 values (defines, imports, depends_on, related_to, implements, documents) are valid
- [ ] Test `Entity` construction with valid data and verify all fields
- [ ] Test `Entity` default id generation (uuid4 hex, 32 chars)
- [ ] Test `Entity` immutability — assignment to frozen model raises `ValidationError`
- [ ] Test `Entity` round-trip: `model_dump()` then `Entity.model_validate()` produces equal object
- [ ] Test `Entity` rejects invalid `entity_type` string
- [ ] Test `Edge` construction, default id, immutability, round-trip, and validation (weight >= 0)
- [ ] Test `Document` construction, default id, immutability, and round-trip
- [ ] Test empty metadata defaults to `{}`
- [ ] All tests initially fail (import error) until #108 implements the module
- [ ] `ruff check` clean on test file
