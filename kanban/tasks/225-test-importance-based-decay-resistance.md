---
id: 225
title: Test importance-based decay resistance
status: archived
priority: nice-to-have
created: 2026-02-28T01:18:07.2846882+01:00
updated: 2026-02-28T23:54:07.7800568+01:00
started: 2026-02-28T01:19:13.6713465+01:00
completed: 2026-02-28T23:54:07.7800568+01:00
tags:
    - phase-9
    - memory
    - test
class: standard
---

TDD test task for #210. File: tests/test_knowledge_vectors.py (extend).

AC:
- [ ] Test IMPORTANCE_BY_TYPE maps all EntityType values to float in [0,1]
- [ ] Test decision entity (importance=0.9) with old created_at outranks file entity (importance=0.3) with recent created_at at equal similarity
- [ ] Test document type defaults to importance 0.5
- [ ] Test modified decay formula: (1 - decay_rate * (1 - importance)) ^ hours
- [ ] Test importance=1.0 produces zero decay (score always ~1.0)

Depends on: #207
