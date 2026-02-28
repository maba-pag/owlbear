---
id: 223
title: Test IngestPipeline scope passthrough
status: archived
priority: important
created: 2026-02-28T01:17:48.8048974+01:00
updated: 2026-02-28T23:54:06.4585648+01:00
started: 2026-02-28T01:19:12.5829495+01:00
completed: 2026-02-28T23:54:06.4585648+01:00
tags:
    - phase-9
    - knowledge-graph
    - memory
    - test
class: standard
---

TDD test task for #206. File: tests/test_knowledge_ingest.py (extend existing).

AC:
- [ ] Test ingest(source, scope='project:owlbear') passes scope to GraphStore.insert_entity, insert_edge
- [ ] Test ingest(source, scope='project:owlbear') passes scope to VectorStore.store_embedding
- [ ] Test ingest_text(text, scope='agent:builder') propagates scope
- [ ] Test ingest(source) without scope defaults to 'global'
- [ ] Test IngestResult unchanged (no scope field needed in result)

Depends on: #202, #205
File: tests/test_knowledge_ingest.py
