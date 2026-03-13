---
id: 206
title: IngestPipeline scope passthrough
status: archived
priority: important
created: 2026-02-28T01:10:36.0294426+01:00
updated: 2026-02-28T23:53:52.7745298+01:00
started: 2026-02-28T01:11:44.7566782+01:00
completed: 2026-02-28T23:53:52.7745298+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
class: standard
---

Add scope parameter to IngestPipeline.ingest() and ingest_text(), propagate to all downstream stores.

File: src/owlbear/memory/knowledge/ingest.py

AC:
- [ ] ingest(source, scope='global') -> IngestResult: passes scope to _insert_document, _store_chunks, _store_embeddings, _store_extractions
- [ ] ingest_text(text, metadata=None, scope='global') -> IngestResult: passes scope to _ingest_from_intake
- [ ] _ingest_from_intake(intake_result, scope='global') propagates scope
- [ ] _insert_document sets scope column on documents table
- [ ] _store_chunks sets scope column on chunks table
- [ ] _store_embeddings passes scope to VectorStore.store_embedding()
- [ ] _store_extractions creates Entity/Edge with scope field set, then calls GraphStore.insert_entity/insert_edge
- [ ] Default scope='global' preserves backwards compatibility
- [ ] IngestResult model unchanged (no scope in result)

Depends on: #223 (test task), #202, #205
See docs/research/knowledge-scoping.md
