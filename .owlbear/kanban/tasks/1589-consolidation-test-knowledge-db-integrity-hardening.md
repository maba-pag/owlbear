---
id: 1589
title: 'Consolidation test: knowledge DB integrity hardening'
status: backlog
priority: important
created: 2026-05-15T16:25:02.116082+00:00
updated: 2026-05-15T16:25:05.329349+00:00
tags:
  - consolidation-test
  - scope:knowledge
  - type:test
  - db-integrity
parent: 1580
depends_on:
  - 1586
  - 1588
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Parent: #1580

Scope:
- In scope: Integration test that exercises schema constraints and audit function together end-to-end.
- Out of scope: Unit-level constraint tests (covered by #1585), unit-level audit tests (covered by #1587).

Acceptance Criteria:
AC-1: Test creates a v12 schema, inserts a source→document→chunk→entity→edge chain via `DocumentStore` APIs, calls `audit_integrity(conn)`, and asserts zero violations across `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, `status_orphaned`.
AC-2: Test creates orphan rows by executing direct SQL with `PRAGMA foreign_keys = OFF`, re-enables FK enforcement, calls `audit_integrity(conn)`, and asserts the reported violation categories and counts match the injected orphans.

Proof bundle: behavioral