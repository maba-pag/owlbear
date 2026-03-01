---
id: 281
title: Implement delete_document_data() cascade (SQLite + Qdrant)
status: archived
priority: needed
created: 2026-02-28T22:56:52.1084221+01:00
updated: 2026-03-01T17:07:33.7283586+01:00
started: 2026-02-28T23:12:16.3650553+01:00
completed: 2026-03-01T17:07:33.7283586+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

Cascade-delete all data for a document across SQLite and Qdrant.

AC:
- [ ] delete_document_data(document_id: str, conn: Connection, graph: GraphStore, vectors: QdrantVectorStore) or method on IngestPipeline
- [ ] Delete order: chunks -> entities (by document_id if column exists) -> Qdrant points -> document -> document_status
- [ ] Qdrant: call existing QdrantVectorStore.delete_by_document_id(document_id)
- [ ] SQLite: parameterized DELETE statements (no raw string formatting)
- [ ] Single method orchestrating all deletes in correct FK order
- [ ] Tests: verify all 4 tables cleaned after delete, verify Qdrant points removed, verify no orphan rows

Note: QdrantVectorStore.delete_by_document_id() already exists (see qdrant.py).
See docs/content-hashing-research.md
