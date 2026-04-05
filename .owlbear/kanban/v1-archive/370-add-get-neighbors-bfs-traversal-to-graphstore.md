---
id: 370
title: Add get_neighbors() BFS traversal to GraphStore
status: archived
priority: needed
created: 2026-03-01T20:13:09.7557077+01:00
updated: 2026-03-02T09:14:39.0780586+01:00
started: 2026-03-01T20:22:39.2865162+01:00
completed: 2026-03-02T09:14:39.0780586+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 420
class: standard
---

From #258 graph-augmented-retrieval.md. Add get_neighbors() to GraphStore at src/owlbear/memory/knowledge/graph.py (~30 LOC). AC: - Method: get_neighbors(self, entity_id: str, depth: int = 1, max_nodes: int = 20, scopes: list[str] | None = None) -> list[tuple[Entity, Edge]] - BFS traversal from entity_id collecting neighbor entities with their connecting edges - Bidirectional: traverses both outgoing (source_id) and incoming (target_id) edges via existing list_edges() - depth parameter controls hop count (1=direct, 2=neighbors-of-neighbors) - max_nodes cap: stops BFS when visited count reaches limit - scopes passed through to list_edges() for scope filtering - Unknown entity_id returns empty list - Uses existing list_edges() + get_entity() (no raw SQL) - Depends on test task #420
