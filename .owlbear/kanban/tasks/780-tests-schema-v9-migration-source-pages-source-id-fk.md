---
id: 780
title: Tests — Schema v9 migration (source_pages, source_id FK)
status: review
priority: needed
created: '2026-04-10T12:30:43.970655+00:00'
updated: '2026-04-12T22:27:53.878350+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify v8→v9 migration runs without error on a v8 database
- Tests assert `source_pages` table exists with columns: `id`, `source_id`, `url`, `content_hash`, `last_fetched_at`, `status`, `scope`
- Tests assert `documents` table has `source_id` column, nullable (NULL for legacy rows)
- Tests verify `SCHEMA_VERSION == 9`
- File: `tests/test_schema_v9_775.py`

## Context
- WS-A: Schema + Models Foundation
- Scope item 5 from #775
- See research F2: NULL source_id for legacy, F6: source_pages for Phase 2 readiness

[[2026-04-12]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: v8→v9 migration runs without error | PASS — verifiable, tested in `TestFromAC_V8ToV9MigrationRuns` (3 tests) | None |
| AC2: source_pages columns | STALE — AC says `content_hash`, `last_fetched_at`; actual DDL uses `extraction_hash`, `last_extracted`. AC also omits `created_at`, `updated_at`. Tests correctly verify actual columns. | AC-CORRECTION: replace `content_hash` → `extraction_hash`, `last_fetched_at` → `last_extracted`, add `created_at`, `updated_at` |
| AC3: documents.source_id nullable | PASS — verifiable, tested in `TestFromAC_DocumentsSourceIdAfterMigration` (3 tests) | None |
| AC4: SCHEMA_VERSION == 9 | PASS — verifiable, tested in `TestFromAC_SchemaVersion9AfterMigration` (3 tests) | None |
| AC5: File location | PASS — file exists at `tests/test_schema_v9_775.py` | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only v8→v9 migration path |
| Interface clarity | PASS (with caveat) | AC column names stale but tests verify correct schema |
| Dependency correctness | PASS | No task deps needed; schema.py implementation already landed |
| Module layering | PASS | Tests import only from `owlbear_knowledge.schema` |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | 12 tests, focused scope |
| Premise challenge | PASS | Migration path tests complement fresh-init tests in #785 |
| Pattern consistency | PASS | Class-per-AC, parametrized columns, follows test_schema_v9_785 pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: proceed (confidence 0.87)
- Architect response: accepted — AC column name staleness is documentation, not structural

### Note
Tests already exist at `tests/test_schema_v9_775.py` with 12 tests across 4 classes. All tests correctly verify the actual DDL columns. The type:test tag ensures pass-through handling downstream.

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC column discrepancies noted above for downstream awareness.
[[2026-04-12]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — pass-through to in-progress.
- Test file `tests/test_schema_v9_775.py` already exists (pre-written, validated by Architecture Review).
- Classes: `TestFromAC_V8ToV9MigrationRuns`, `TestFromAC_SourcePagesAfterMigration`, `TestFromAC_DocumentsSourceIdAfterMigration`, `TestFromAC_SchemaVersion9AfterMigration`
- AC coverage: all 4 AC lines covered.
- Architecture Review verdict: APPROVE (2026-04-12). No test-writer action required.
[[2026-04-12]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Test file `tests/test_schema_v9_775.py` already exists (pre-written).
- Verified: 21 tests passed, 0 failed.
- Passing through to review.