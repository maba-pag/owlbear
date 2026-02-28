---
id: 283
title: Wire document_id provenance into IngestPipeline and GraphStore
status: done
priority: needed
created: 2026-02-28T22:57:32.3172477+01:00
updated: 2026-03-01T00:09:58.2989448+01:00
started: 2026-02-28T23:12:22.7437356+01:00
completed: 2026-03-01T00:09:58.2989448+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
depends_on:
    - 278
class: standard
---

Application-logic counterpart to schema v4 (#278). Stamps document_id on entities during ingestion and adds a query method to retrieve entities by document.

AC:
- [ ] IngestPipeline._store_extractions() passes document_id when inserting entities
- [ ] GraphStore.insert_entity() accepts and stores document_id column
- [ ] GraphStore.list_entities_for_document(doc_id, scopes) -> list[Entity]
- [ ] Entity model gains optional document_id: str | None = None field
- [ ] Tests: inserted entity has document_id, list_entities_for_document returns correct set, scope filtering works

Pattern: follow existing GraphStore.list_entities() for query pattern.
Depends on #278 (schema v4 must create the column first).
See docs/intra-document-graph-research.md
