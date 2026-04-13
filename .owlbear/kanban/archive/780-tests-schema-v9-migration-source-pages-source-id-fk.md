---
id: 780
title: Tests — Schema v9 migration (source_pages, source_id FK)
status: done
priority: needed
created: '2026-04-10T12:30:43.970655+00:00'
updated: '2026-04-11T14:36:20.339961+00:00'
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

[[2026-04-11]]
## Architecture Review

### AC Refinement

AC2 column list updated to match implemented schema (`schema.py` L153–165):
- **Was:** `id, source_id, url, content_hash, last_fetched_at, status, scope`
- **Now:** `id, source_id, url, status, extraction_hash, last_extracted, scope, created_at, updated_at`

Root cause: AC written from research F6 before schema was finalized. Tests in `tests/test_schema_v9_775.py` already verify the correct columns.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only task for schema v9 migration path |
| Interface clarity | PASS (after refinement) | AC2 column list corrected to match implementation |
| Dependency correctness | PASS | No dependencies; parent #775 archived |
| Module layering | PASS | Tests import only from `owlbear_knowledge.schema` |
| TDD compliance | PASS | This IS the test task |
| KISS/YAGNI | PASS | 14 focused migration-path tests |
| Premise challenge | PASS | Migration path coverage needed alongside fresh-init tests (#754, #757) |
| Pattern consistency | PASS | Follows `_make_v8_db()` pattern from prior schema test files |
| Security surface | PASS | No security surface — test-only |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: proceed (confidence 0.92)
- Architect response: accepted — AC refinement is documentation-only, no code risk

### Notes
- Test file `tests/test_schema_v9_775.py` (252 LOC) already exists with comprehensive coverage
- 1 test (`test_source_pages_scope_index_exists_after_migration`) intentionally fails until #785 adds `source_pages` to `_SCOPE_TABLES`
- Non-impl tag `type:test` already present

### Verdict: APPROVE
### Action Taken: Refined AC2 column list, approved to todo
[[2026-04-11]]
## Test-Writer Notes
- Non-implementation task (tagged `type:test`) — no tests to write.
- Test file `tests/test_schema_v9_775.py` (252 LOC) already exists with comprehensive coverage per Architecture Review.
- 14 tests across 4 `TestFromAC_` classes covering all 4 AC lines.
- 1 test (`test_source_pages_scope_index_exists_after_migration`) intentionally fails until #785 adds `source_pages` to `_SCOPE_TABLES`.
- Passing through to builder.
[[2026-04-11]]
## Builder Notes
- Non-implementation task (tagged `type:test`) — no code changes needed.
- Test file `tests/test_schema_v9_775.py` verified: **21 passed, 0 failed**.
- Previously expected failure (`test_source_pages_scope_index_exists_after_migration`) now passes — `#785` must have landed `source_pages` in `_SCOPE_TABLES`.
- Lint: not run (no changed files).
- Passing through to review.
[[2026-04-11]]
## Review Evidence

### Test Results (independent run via quality-runner)
- **pytest:** 21 passed, 0 failed, 0 skipped — exit code 0
- **ruff:** clean, no violations — exit code 0
- **Coverage:** `owlbear_knowledge.schema` at 63% (informational — no code changed in this pass-through task)

### AC Compliance Table

| AC Line | TestFromAC_ Class | Test Instances | Would Fail If Violated? | Verdict |
|---------|------------------|----------------|------------------------|---------|
| AC1: migration runs without error on v8 DB | `TestFromAC_V8ToV9MigrationRuns` | 3 | Yes — exception propagates; data-preservation test catches silent corruption | COVERED |
| AC2: source_pages has all required columns (refined: extraction_hash, last_extracted, created_at, updated_at) | `TestFromAC_SourcePagesAfterMigration` | 12 (1 table + 9 parametrized columns + 2 indexes) | Yes — parametrized `assert column in cols` fails on any absent column | COVERED |
| AC3: documents.source_id nullable, NULL for legacy rows | `TestFromAC_DocumentsSourceIdAfterMigration` | 3 | Yes — PRAGMA notnull=0 check and explicit NULL assertion | COVERED |
| AC4: SCHEMA_VERSION == 9 | `TestFromAC_SchemaVersion9AfterMigration` | 3 | Yes — strict equality `== 9` catches any wrong version | COVERED |

### Test Count Discrepancy Resolved
- Test-writer reported 14 test *methods*; pytest ran 21 *instances*.
- Delta of 7 = `test_source_pages_has_column` parametrized across 9 columns (1 method → 9 instances, net +8 on 14 methods = 21 pytest-reported instances... wait, re-count: 3 + 1 + 9 + 2 + 3 + 3 = 21). Fully explained.

### Previously Expected Failure — Now Passing
- `test_source_pages_scope_index_exists_after_migration`: docstring says "FAILS until #785."
- Code-reader confirmed `source_pages` IS in `_SCOPE_TABLES` in `schema.py`. The index is created by `init_db` for all `_SCOPE_TABLES`. Test passes correctly.
- No assertion weakness — `assert row is not None` on a `sqlite_master` query is the correct idiom.
- Builder's explanation ("must have landed with #785") is accurate.

### TestFromAC Modifications
None. No code changes — pass-through task. Builder made no edits.

### Security Review
Test-only file. Parameterized SQL in `_make_v8_db` (no injection risk). In-memory SQLite. No secrets, no PII, no new dependencies.

### Minor Documentation Debt (non-blocking)
1. Test docstring for `test_source_pages_scope_index_exists_after_migration` still reads "FAILS until #785" — outdated, test passes. Does not affect correctness.
2. AC2 original text in task body still lists old column names (`content_hash`, `last_fetched_at`); arch review correction is in body notes only. Tests verify correct columns.

### Deductions
- Stale docstring: −0.01
- Stale AC2 text in task body (pre-existing from arch review): −0.01

### Verdict
**Confidence: .97 → PASS**
[[2026-04-11]]
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 0a | Review Evidence section present | Yes | PASS | `## Review Evidence` present with full AC compliance table, test results, and confidence verdict |
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | Test-only pass-through task; no behavior, API, or convention changed |
| 2 | Module docstrings | No | N/A | No `.py` source modules created or modified; no production code changes |
| 3 | External attribution → sources/overview.md | No | N/A | No external patterns used |
| 4 | CLI changes → README.md | No | N/A | No CLI changes |
| 5 | Research doc | N/A | N/A | No research doc produced for this task; parent #775 research doc `.owlbear/research/775-phase1-browser-pipeline-schema.md` exists and is referenced in task body |
| 6 | Stale docstrings (reviewer debt) | Yes | FIXED | Removed 3 stale "FAILS until #785" references from module docstring, method docstring, and inline comment in `tests/test_schema_v9_775.py` |

**Files updated:** `tests/test_schema_v9_775.py` — docstrings only  
**Commit:** `0319a87f` — `docs: remove stale FAILS-until-#785 docstrings from test_schema_v9_775.py (#780, doc-writer)`  
**Scratch files:** none found for `780-*`
[[2026-04-11]]
## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: v8→v9 migration runs without error | `TestFromAC_V8ToV9MigrationRuns` — 3 tests pass (migration, data preservation, no dupes) | PASS |
| AC2: source_pages has correct columns (refined) | `TestFromAC_SourcePagesAfterMigration` — 12 instances: table exists, 9 parametrized columns (`id`, `source_id`, `url`, `status`, `extraction_hash`, `last_extracted`, `scope`, `created_at`, `updated_at`), 2 indexes | PASS |
| AC3: documents.source_id nullable, NULL for legacy | `TestFromAC_DocumentsSourceIdAfterMigration` — 3 tests (column exists, PRAGMA notnull=0, legacy row=NULL) | PASS |
| AC4: SCHEMA_VERSION == 9 | `TestFromAC_SchemaVersion9AfterMigration` — 3 tests (exact ==9, applied_at valid, ≥9) | PASS |

### Spot-Check Notes
- All 4 `TestFromAC_` classes inspected; each maps cleanly to one AC line.
- Parametrized column test (`test_source_pages_has_column`) verifies all 9 columns individually — would fail on any missing column.
- `test_source_pages_scope_index_exists_after_migration` now passes (stale docstring removed by doc-writer in `0319a87f`).
- Reviewer evidence section is detailed with full AC compliance table and "Would Fail If Violated?" analysis — trusted.

### Test Results
- **Task-scoped:** 21 passed, 0 failed — `tests/test_schema_v9_775.py`
- **Full suite:** 3430 passed, 304 failed, 8 skipped, 6 errors
  - **Cross-task scope:** All 304 failures are in unrelated domains (kanban MCP `next_id`, `AppContext` signature, `engine_models.py` deletion, agent validation, knowledge graph). No failures in `owlbear_knowledge.schema` or migration tests. This is a test-only pass-through task with zero production code changes — cannot cause regressions.
- **ruff:** clean, exit code 0

### Commit Integrity
- `257a88d6` — `test: add failing tests for schema v9 migration path (#780, test-writer)`
- `0319a87f` — `docs: remove stale FAILS-until-#785 docstrings from test_schema_v9_775.py (#780, doc-writer)`
- Working tree: `git diff` shows zero content changes (phantom modification from line-ending normalization).

### Architect Quality: 4/5
AC lines were clear and verifiable — each mapped directly to a `TestFromAC_` class. Minor gap: original AC2 column names were stale (from research F6 before schema finalization). Architect caught and corrected this during arch review. No builder/reviewer improvisation needed.

### Deduction Breakdown
- All 4 AC lines have specific test evidence: no deduction
- Lint: clean: no deduction
- AC quality 4/5 (>3): no deduction
- Reviewer evidence present and detailed: no deduction
- Full-suite failures outside task scope: no deduction
- Stale AC2 text in original body (cosmetic, corrected in arch review section): −0.01

### Confidence: .99
### Action: archive