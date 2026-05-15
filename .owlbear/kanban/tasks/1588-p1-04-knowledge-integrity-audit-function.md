---
id: 1588
title: 'P1-04: Knowledge integrity audit function'
status: backlog
priority: needed
created: 2026-05-15T16:24:50.332910+00:00
updated: 2026-05-15T16:24:53.574228+00:00
tags:
  - phase-1
  - scope:knowledge
  - type:build
  - db-integrity
parent: 1580
depends_on:
  - 1587
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Parent: #1580

Scope:
- In scope: New `owlbear_knowledge.integrity` module exporting a read-only `audit_integrity()` function that detects orphan and dangling rows across knowledge tables.
- Out of scope: Schema DDL changes (done in #1586), data mutation/repair, vector payload linkage, CLI entry point.

Acceptance Criteria:
AC-1: `owlbear_knowledge.integrity` exports `audit_integrity(conn: sqlite3.Connection) -> dict` that returns a dict with keys `chunks_orphaned`, `entities_orphaned`, `edges_dangling`, `status_orphaned`; each value is a dict with `count: int` and `ids: list[str]`.
AC-2: `audit_integrity()` detects orphan chunks (chunk.document_id not in documents), orphan entities (entity.document_id not in documents), dangling edges (edge.source_id or edge.target_id not in entities), and orphan document_status entries (document_status.document_id not in documents) using LEFT JOIN / NOT IN queries.
AC-3: `audit_integrity()` executes no INSERT, UPDATE, or DELETE statements; connection `total_changes` before and after calling the function is unchanged.

Proof bundle: behavioral