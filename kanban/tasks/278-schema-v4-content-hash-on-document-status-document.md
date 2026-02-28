---
id: 278
title: 'Schema v4: content_hash on document_status, document_id on entities, source index'
status: archived
priority: needed
created: 2026-02-28T22:56:30.2038541+01:00
updated: 2026-03-01T00:02:51.5300519+01:00
started: 2026-02-28T23:12:14.470423+01:00
completed: 2026-03-01T00:02:51.5300519+01:00
tags:
    - phase-9
    - knowledge-graph
    - config
class: standard
---

Unified schema v4 migration combining content-hashing (#253) and entity provenance (#255) DDL changes.

AC:
- [ ] Add content_hash TEXT column to document_status table
- [ ] Add document_id TEXT column to entities table
- [ ] Add CREATE INDEX idx_document_status_source ON document_status(source)
- [ ] Single _migrate_v3_to_v4() function in schema.py
- [ ] Bump _SCHEMA_VERSION to 4
- [ ] Existing rows get NULL for new columns (backward compatible)
- [ ] Tests: v3-to-v4 migration, idempotent re-run, both new columns present with correct defaults

Pattern: follow existing _migrate_v2_to_v3() in schema.py (ALTER TABLE + contextlib.suppress for idempotency).
See docs/content-hashing-research.md and docs/intra-document-graph-research.md
