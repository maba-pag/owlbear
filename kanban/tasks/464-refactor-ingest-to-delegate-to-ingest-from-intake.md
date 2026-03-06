---
id: 464
title: Refactor ingest() to delegate to _ingest_from_intake()
status: archived
priority: needed
created: 2026-03-04T07:37:44.6993203+01:00
updated: 2026-03-06T19:28:09.0005048+01:00
started: 2026-03-06T00:29:03.627284+01:00
completed: 2026-03-06T19:28:09.0005048+01:00
tags:
    - audit
    - dry
    - refactor
    - knowledge
class: standard
---

DRY-10/F-05: ingest() reimplements ~55 lines of pipeline steps identical to _ingest_from_intake(). After intake+delta-check, ingest() should call _ingest_from_intake(). ingest_text() already follows this pattern.

## Research Findings (2026-03-06)

See docs/ingest-dry-refactor-research.md for full analysis.

**Confirmed:** Steps 3-9 in ingest() (L308-362) are line-for-line identical to _ingest_from_intake() (L436-493). Only difference: ingest() error handler creates document_id if intake fails before one is assigned.

**Approach (.95 confidence):** Refactor ingest() to call _ingest_from_intake() after intake + delta-check, matching the ingest_text() pattern. Keep intake failure handling in ingest()'s own try/except. Net reduction: ~45 lines.

**Risk:** Minimal. Behavior-preserving. All 50+ existing tests should pass unchanged.

## Architecture Notes

Follow the ingest_text() delegation pattern (L430): intake + delta-check + existing-doc deletion in ingest(), then delegate to _ingest_from_intake(intake_result, scope=scope).

_ingest_from_intake() already handles: document_id creation, status tracking, chunking, embedding, extraction, result processing, content hash, graph enrichment, and its own try/except for pipeline failures.

ingest() only needs its own try/except around the intake steps (read_source + delta check) to handle the document_id=None case where intake fails before a document_id exists.

## Acceptance Criteria

- [ ] ingest() performs intake (_read_source) and delta-check, then delegates to _ingest_from_intake(intake_result, scope=scope)
- [ ] Steps 3-9 (document tracking, chunking, embedding, extraction, result processing, hash update, graph enrichment) appear only in _ingest_from_intake(), not duplicated in ingest()
- [ ] ingest() retains its own try/except around intake steps; if intake fails before document_id is assigned, it creates a document_id and returns IngestResult(status='failed')
- [ ] _ingest_from_intake() signature and behavior are unchanged
- [ ] All existing tests in test_knowledge_ingest.py pass without modification
- [ ] Public API (ingest() signature and return type) unchanged
