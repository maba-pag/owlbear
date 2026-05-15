---
id: 1587
title: 'P1-03: Tests — knowledge integrity audit function'
status: backlog
priority: needed
created: 2026-05-15T16:24:36.952846+00:00
updated: 2026-05-15T16:24:40.360399+00:00
tags:
  - phase-1
  - scope:knowledge
  - type:test
  - db-integrity
parent: 1580
depends_on:
  - 1586
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Parent: #1580

Scope:
- In scope: Failing tests for a read-only integrity audit function that detects orphan rows across knowledge tables.
- Out of scope: Schema constraint changes, vector payload checks, data mutation/repair.

Acceptance Criteria:
AC-1: Test calls `audit_integrity(conn)` on a database containing one orphan chunk row (parent document deleted via direct SQL with FK disabled); asserts the result dict includes key `chunks_orphaned` with value `1` and the orphan chunk ID in the detail list.
AC-2: Test calls `audit_integrity(conn)` on a database containing one edge with `source_id` referencing a non-existent entity (inserted via direct SQL with FK disabled); asserts the result dict includes key `edges_dangling` with value `1` and the edge ID in the detail list.
AC-3: Test calls `audit_integrity(conn)` on a clean database with a source→document→chunk→entity→edge chain and asserts the result reports zero violations across categories: `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, `status_orphaned`.

Proof bundle: behavioral