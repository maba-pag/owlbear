---
id: 279
title: Implement find_status_by_source() query
status: archived
priority: needed
created: 2026-02-28T22:56:37.3065174+01:00
updated: 2026-03-01T17:07:29.3424076+01:00
started: 2026-02-28T23:12:15.0052802+01:00
completed: 2026-03-01T17:07:29.3424076+01:00
tags:
    - phase-9
    - knowledge-graph
depends_on:
    - 278
class: standard
---

Query helper for looking up previously-ingested documents by source URI.

AC:
- [ ] Add find_status_by_source(source: str, scope: str = 'global') method to IngestPipeline or a new query module
- [ ] SQL: SELECT document_id, content_hash, status FROM document_status WHERE source = ? AND scope = ?
- [ ] Returns DocumentStatus | None (Pydantic model with document_id, content_hash, status fields)
- [ ] Tests: source found returns correct row, source not found returns None, scope filtering works

Pattern: follow existing _set_status() in ingest.py for DB access.
Depends on #278 (content_hash column must exist).
See docs/research/content-hashing.md
