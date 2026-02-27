---
id: 109
title: Create owlbear.memory.knowledge.graph module
status: todo
priority: high
created: 2026-02-27T03:31:26.1657627+01:00
updated: 2026-02-27T03:45:12.9823131+01:00
started: 2026-02-27T03:32:49.0400117+01:00
tags:
    - memory
    - knowledge-graph
    - phase-2
depends_on:
    - 107
    - 108
    - 117
class: standard
---

CRUD operations for the knowledge graph. Adapted from tool.graphicator `db/graph.py`.

## Acceptance Criteria

- [ ] New file: `src/owlbear/memory/knowledge/graph.py`
- [ ] `GraphStore` class, initialized with `sqlite3.Connection`
- [ ] Entity operations:
  - `insert_entity(entity: Entity) -> None` — inserts, raises on duplicate id
  - `get_entity(entity_id: str) -> Entity | None`
  - `list_entities(entity_type: EntityType | None = None) -> list[Entity]` — optional type filter
  - `delete_entity(entity_id: str) -> bool` — cascades to edges, returns whether found
- [ ] Edge operations:
  - `insert_edge(edge: Edge) -> None` — validates source_id and target_id exist, raises on duplicate id
  - `get_edge(edge_id: str) -> Edge | None`
  - `list_edges(source_id: str | None = None, target_id: str | None = None) -> list[Edge]` — optional filters
  - `delete_edge(edge_id: str) -> bool`
- [ ] Document operations:
  - `insert_document(doc: Document) -> None` — raises on duplicate id
  - `get_document(doc_id: str) -> Document | None`
  - `list_documents() -> list[Document]`
  - `delete_document(doc_id: str) -> bool`
- [ ] All insert methods use parameterized queries (no SQL injection)
- [ ] Metadata fields stored as JSON strings, deserialized on read
- [ ] `ruff check` clean

See docs/knowledge-graph-research.md section 3.4
