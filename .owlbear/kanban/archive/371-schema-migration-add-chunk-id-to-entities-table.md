---
id: 371
title: 'Schema migration: add chunk_id to entities table'
status: archived
priority: needed
created: 2026-03-01T20:13:17.2265889+01:00
updated: 2026-03-02T09:16:50.541575+01:00
started: 2026-03-01T20:22:40.6433926+01:00
completed: 2026-03-02T09:16:50.541575+01:00
tags:
    - phase-9
    - knowledge-graph
depends_on:
    - 421
class: standard
---

From #258 graph-augmented-retrieval.md. Schema migration v4->v5 + model/CRUD updates. AC: - Schema: _SCHEMA_VERSION bumped from 4 to 5 - New migration _migrate_v4_to_v5: ALTER TABLE entities ADD COLUMN chunk_id TEXT (idempotent via contextlib.suppress) - init_db runs v4->v5 migration for existing DBs; fresh DBs include chunk_id in CREATE TABLE - Entity model: add chunk_id: str | None = None field (same pattern as document_id) - GraphStore.insert_entity: include chunk_id in INSERT statement - GraphStore.get_entity: read chunk_id from SELECT - GraphStore.list_entities + list_entities_for_document: read chunk_id - IngestPipeline._store_chunks: return list of chunk IDs (currently generates uuid4 internally and discards) - IngestPipeline._store_extractions: accept chunk_ids parameter, set chunk_id on each entity from corresponding chunk - IngestPipeline._process_results: pass chunk_ids from _store_chunks to _store_extractions - Depends on test task #421
