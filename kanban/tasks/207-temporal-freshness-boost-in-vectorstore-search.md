---
id: 207
title: Temporal freshness boost in VectorStore.search_similar
status: archived
priority: nice-to-have
created: 2026-02-28T01:10:46.2780283+01:00
updated: 2026-02-28T23:53:53.6575664+01:00
started: 2026-02-28T01:11:45.231796+01:00
completed: 2026-02-28T23:53:53.6575664+01:00
tags:
    - phase-9
    - memory
class: standard
---

Add query-time temporal freshness boost to VectorStore.search_similar().

File: src/owlbear/memory/knowledge/vectors.py

AC:
- [ ] search_similar() gains params: recency_weight: float = 0.0, decay_rate: float = 0.001
- [ ] When recency_weight > 0: after resolving candidate IDs via bridge table, look up created_at from source table (entities/documents/chunks)
- [ ] Compute per-candidate recency_score = (1 - decay_rate) ** hours_since_created
- [ ] Non-reranker path: adjusted_score = distance - recency_weight * recency_score (lower = better)
- [ ] Reranker path: adjusted_score = reranker_score + recency_weight * recency_score (higher = better)
- [ ] Re-sort candidates by adjusted_score, return top_k
- [ ] recency_weight=0.0 (default) disables boost entirely — exact same behavior as before
- [ ] Helper function _compute_recency_score(created_at_iso: str, decay_rate: float) -> float extracted for testability
- [ ] Parse created_at ISO-8601 string to datetime for hour calculation

Depends on: #224 (test task)
See docs/temporal-memory-research.md
