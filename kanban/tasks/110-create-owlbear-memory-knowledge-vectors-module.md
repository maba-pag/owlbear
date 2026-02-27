---
id: 110
title: Create owlbear.memory.knowledge.vectors module
status: todo
priority: high
created: 2026-02-27T03:31:31.4159779+01:00
updated: 2026-02-27T03:45:24.0908145+01:00
started: 2026-02-27T03:32:49.431151+01:00
tags:
    - memory
    - knowledge-graph
    - phase-2
depends_on:
    - 106
    - 107
    - 118
class: standard
---

Vector storage and similarity search using sqlite-vec. Adapted from tool.graphicator `db/vectors.py`.

## Acceptance Criteria

- [ ] New file: `src/owlbear/memory/knowledge/vectors.py`
- [ ] `VectorStore` class, initialized with `sqlite3.Connection`
- [ ] `store_embedding(entity_or_doc_id: str, embedding: list[float], embedding_type: Literal["entity", "document"]) -> None`
  - Inserts into vec0 virtual table + rowid_map bridge table
  - Validates embedding length == `EMBEDDING_DIM` (384), raises `ValueError` otherwise
  - Updates existing embedding if entity_or_doc_id already has one (upsert)
- [ ] `search_similar(query_embedding: list[float], top_k: int = 5, embedding_type: Literal["entity", "document"] | None = None) -> list[tuple[str, float]]`
  - Returns list of `(entity_or_doc_id, distance)` ordered by ascending distance
  - Optional `embedding_type` filter
  - Uses sqlite-vec `knn_search` or vec0 `MATCH` syntax
- [ ] `get_embedding(entity_or_doc_id: str) -> list[float] | None`
  - Returns stored embedding vector, or None if not found
- [ ] `delete_embedding(entity_or_doc_id: str) -> bool`
  - Removes from vec0 table + rowid_map, returns whether found
- [ ] rowid_map bridge table maps vec0 rowids to entity/document string ids
- [ ] `ruff check` clean

See docs/knowledge-graph-research.md section 3.1, 3.4
