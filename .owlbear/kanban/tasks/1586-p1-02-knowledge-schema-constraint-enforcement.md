---
id: 1586
title: 'P1-02: Knowledge schema constraint enforcement'
status: backlog
priority: critical
created: 2026-05-15T16:24:24.505992+00:00
updated: 2026-05-15T18:21:53.844884+00:00
tags:
  - phase-1
  - scope:knowledge
  - type:build
  - db-integrity
  - hardening
parent: 1580
depends_on:
  - 1585
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Parent: #1580

Scope:
- In scope: Enable `PRAGMA foreign_keys = ON` in `init_db()`, add schema migration v12 that rebuilds `entities` and `edges` tables with `document_id TEXT NOT NULL`, handle pre-existing NULL rows during migration, verify existing write paths (`store_chunks`, `store_extractions`, `delete_document_data`, `scope_transfer`) still succeed.
- Out of scope: Audit tooling, vector payload linkage checks, new indexes beyond FK enforcement.

Acceptance Criteria:
AC-1: `init_db()` executes `PRAGMA foreign_keys = ON` and writes schema version 12 to `schema_version` table.
AC-2: Migration v11→v12 rebuilds `entities` and `edges` tables with `document_id TEXT NOT NULL`; rows where `document_id IS NULL` are deleted before rebuild.
AC-3: `DocumentStore.store_chunks()` followed by `DocumentStore.store_extractions()` for a source-linked document complete without `sqlite3.IntegrityError`; `DocumentStore.delete_document_data()` deletes child rows before parent rows without FK violation.

Proof bundle: behavioral
2026-05-15T18:21:53+00:00

## Architect Note (reconciliation from #1585 review cycle)
The base DDL changes (FK ON, NOT NULL on `entities.document_id` and `edges.document_id`) already exist in `serve/knowledge/src/owlbear_knowledge/schema.py` via commit `4751a74b` (erroneously attributed to #1585). Schema version remains 11. Remaining scope for #1586:
- Bump `_SCHEMA_VERSION` to 12
- Implement migration v11→v12 (rebuild tables with NOT NULL, delete NULL rows)
- Write-path compatibility proof (AC-3)
The FK pragma and base DDL constraints do NOT need to be re-implemented — verify they're in place and build the migration on top.