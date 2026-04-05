---
id: 421
title: 'Test schema migration v5: chunk_id on entities'
status: archived
priority: needed
created: 2026-03-01T22:18:35.3582326+01:00
updated: 2026-03-02T09:15:11.3606749+01:00
started: 2026-03-01T22:18:41.2199194+01:00
completed: 2026-03-02T09:15:11.3606749+01:00
tags:
    - phase-9
    - knowledge-graph
    - test
class: standard
---

TDD test task for #371. File: tests/test_schema_v5.py. AC: - v4-to-v5 migration adds chunk_id TEXT column to entities table - Migration is idempotent (running twice does not error) - init_db on fresh DB creates entities with chunk_id column - Entity model includes chunk_id: str | None = None field - GraphStore.insert_entity persists chunk_id - GraphStore.get_entity reads chunk_id - IngestPipeline._store_extractions populates chunk_id from corresponding chunk
