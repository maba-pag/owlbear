---
id: 210
title: Importance-based decay resistance for temporal retrieval
status: archived
priority: nice-to-have
created: 2026-02-28T01:10:52.3145555+01:00
updated: 2026-02-28T23:53:56.4104269+01:00
started: 2026-02-28T01:11:45.7211818+01:00
completed: 2026-02-28T23:53:56.4104269+01:00
tags:
    - phase-9
    - memory
class: standard
---

Add entity-type-based importance weighting to temporal decay formula.

File: src/owlbear/memory/knowledge/vectors.py

AC:
- [ ] Module-level IMPORTANCE_BY_TYPE: dict[str, float] mapping EntityType values to importance weights
- [ ] Values: decision=0.9, pattern=0.8, concept=0.7, class_=0.5, function=0.4, file=0.3
- [ ] Default importance for documents (no entity_type): 0.5
- [ ] Modified decay formula: recency_score = (1 - decay_rate * (1 - importance)) ** hours
- [ ] _compute_recency_score gains importance: float = 0.5 parameter
- [ ] Importance looked up from bridge table -> source table -> entity_type -> IMPORTANCE_BY_TYPE
- [ ] Higher importance = slower effective decay (decision with 0.9 importance has ~289-day half-life)

Depends on: #225 (test task), #207
See docs/research/temporal-memory.md
