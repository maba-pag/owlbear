---
id: 420
title: Test get_neighbors() BFS traversal
status: archived
priority: needed
created: 2026-03-01T22:18:18.6290038+01:00
updated: 2026-03-02T09:15:09.5006605+01:00
started: 2026-03-01T22:18:26.6459401+01:00
completed: 2026-03-02T09:15:09.5006605+01:00
tags:
    - phase-9
    - knowledge-graph
    - test
class: standard
---

TDD test task for #370. File: tests/test_graph_store_neighbors.py. AC: - get_neighbors(entity_id, depth=1) returns directly connected entities with their edges - get_neighbors(entity_id, depth=2) returns 2-hop neighbors - scopes parameter filters results to matching scopes - max_nodes cap prevents unbounded expansion (>20 neighbors returns at most 20) - Unknown entity_id returns empty result - Bidirectional: finds neighbors via both outgoing and incoming edges
