---
id: 506
title: Batch-retrieve in qdrant _apply_temporal_boost
status: ideation
priority: important
created: 2026-03-04T07:38:18.4426963+01:00
updated: 2026-03-04T07:38:18.4426963+01:00
tags:
    - audit
    - performance
    - knowledge
class: standard
---

F-07: _apply_temporal_boost does N+1 retrieves -- one client.retrieve() per result. For top_k=20, thats 20 round-trips. Batch all point IDs in single retrieve(ids=[...]). AC: single batch retrieve, N+1 eliminated. See docs/code-quality-audit.md.
