---
id: 224
title: Test temporal freshness boost and decay settings
status: archived
priority: nice-to-have
created: 2026-02-28T01:17:58.9587846+01:00
updated: 2026-02-28T23:54:07.1262083+01:00
started: 2026-02-28T01:19:13.1757907+01:00
completed: 2026-02-28T23:54:07.1262083+01:00
tags:
    - phase-9
    - memory
    - test
class: standard
---

TDD test task for #207 and #212. Files: tests/test_knowledge_vectors.py (extend), tests/test_config.py (extend).

AC:
- [ ] Test _compute_recency_score(created_at, decay_rate=0.001) returns expected float for known inputs
- [ ] Test recency of 0 hours => score ~1.0
- [ ] Test recency of 29 days (half-life) => score ~0.5
- [ ] Test search_similar(recency_weight=0.1) re-orders candidates by blended score
- [ ] Test recent entry outranks older entry at equal similarity distance
- [ ] Test recency_weight=0 disables temporal boost (backwards compat)
- [ ] Test OwlBearSettings().temporal_decay_rate == 0.001
- [ ] Test OwlBearSettings().temporal_recency_weight == 0.1
- [ ] Test env override OWLBEAR_TEMPORAL_DECAY_RATE=0.01 changes setting
