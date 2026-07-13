---
id: 780
title: Tests — Schema v9 migration (source_pages, source_id FK)
status: archived
priority: medium
created: '2026-04-10T12:30:43.970655+00:00'
updated: '2026-04-13T02:55:28.471632+00:00'
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
[[2026-04-13]]
## Review Evidence

### Source Control
No changed files — `type:test` pass-through task. Test file `tests/test_schema_v9_775.py` pre-existed.

### Tests
pytest: **21 passed, 0 failed** — quality-runner confirmed independently.

### Lint
ruff: **clean** — 0 violations across test file and schema.py.

### Coverage
`owlbear_knowledge.schema`: **63%** under scoped run (only `test_schema_v9_775.py`). Expected — other migrations (v1→v8) covered by sibling test files; this task's scope is exclusively the v8→v9 path.

### AC Compliance

| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| AC1: v8→v9 migration runs without error | `test_migration_runs_without_error` (no exception raised); supplemented by state-verification tests confirming correct post-state | `TestFromAC_V8ToV9MigrationRuns` (3 tests) | PASS |
| AC2: source_pages columns (corrected DDL: extraction_hash, last_extracted) | `test_source_pages_table_exists_after_migration`; `test_source_pages_has_column` parametrized over 9 columns: id, source_id, url, status, extraction_hash, last_extracted, scope, created_at, updated_at; + 2 index tests | `TestFromAC_SourcePagesAfterMigration` (12 test cases) | PASS |
| AC3: documents.source_id nullable, NULL for legacy | `test_documents_has_source_id_column_after_migration`; `test_legacy_document_source_id_is_null_after_migration`; `test_documents_source_id_column_is_nullable` (PRAGMA notnull=0) | `TestFromAC_DocumentsSourceIdAfterMigration` (3 tests) | PASS |
| AC4: SCHEMA_VERSION == 9 (via DB record) | `test_schema_version_is_9_after_v8_migration` — `assert row[0] == 9` (exact equality) | `TestFromAC_SchemaVersion9AfterMigration` (3 tests) | PASS |
| AC5: File at tests/test_schema_v9_775.py | File confirmed present by quality-runner and direct read | — | PASS |

### TestFromAC Integrity (Step 5.2)
No code changes — no builder modifications possible. All 4 `TestFromAC_*` classes intact: `V8ToV9MigrationRuns`, `SourcePagesAfterMigration`, `DocumentsSourceIdAfterMigration`, `SchemaVersion9AfterMigration`. Status: **PRESERVED**.

### Test Quality (Step 5.3) — STRONG
- **Assertion specificity:** Direct SQL queries on sqlite_master; `PRAGMA table_info` for nullable check; `datetime.fromisoformat()` for applied_at validity. No lazy `assert result` patterns.
- **Negative/error paths:** AC1 explicitly tests the no-exception happy path; NULL-for-legacy row tested with specific row retrieval.
- **Mutation resistance:** Column parametrization (9 params) would catch any renamed column. `assert row[0] == 9` (exact equality) would catch version increment. `assert col_info[3] == 0` would catch NOT NULL added. All critical assertions are tight.
- **Test independence:** Each test calls `_make_v8_db()` (fresh in-memory connection) — no shared mutable state.
- **Descriptive names:** All test names are `test_{action}_{condition}` format.

### Migration Logic Coverage
| `_migrate_v8_to_v9` code path | Covered? |
|-------------------------------|----------|
| `conn.execute(_CREATE_SOURCE_PAGES)` | Yes — table existence test |
| `CREATE INDEX idx_source_pages_source_id` | Yes — index existence test |
| `ALTER TABLE documents ADD COLUMN source_id TEXT` (contextlib.suppress) | Yes — column existence + nullable + NULL value tests |
| `UPDATE schema_version ... version=9` | Yes — exact version test |
| `idx_source_pages_scope` (via _SCOPE_TABLES loop in init_db) | Yes — scope index test |

### Security (Step 5.1)
No vulnerabilities. DDL strings are hardcoded (no injection surface). Parameterized queries used for all data operations in tests. In-memory databases; no PII. Foreign keys enforced via PRAGMA.

### Builder Process (Step 5.7)
Single `## Builder Notes` section — **CLEAN**.

### Deductions
None.

### Verdict
Confidence: **0.96** → **PASS**
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:test` pass-through — no production code created or modified at any pipeline stage |
| 2 | Module docstrings | No | N/A | No `.py` production modules created or modified; test file pre-existed |
| 3 | External attribution | No | N/A | Standard SQLite/pytest patterns; no external repo or article required attribution |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | Task #780 had no research phase; parent research doc `.owlbear/research/775-phase1-browser-pipeline-schema.md` exists and is contextually referenced in task body |

### Files Updated
- None

### Scratch Files Cleaned
- None found (`780-*` pattern returned 0 results)
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: v8→v9 migration runs without error | `TestFromAC_V8ToV9MigrationRuns` — 3 tests pass (no-exception, row preservation, no duplicate schema row) | PASS |
| AC2: source_pages columns (corrected: extraction_hash, last_extracted) | `TestFromAC_SourcePagesAfterMigration` — 11 tests: table exists, 9 parametrized columns, 2 index existence checks | PASS |
| AC3: documents.source_id nullable, NULL for legacy | `TestFromAC_DocumentsSourceIdAfterMigration` — 3 tests: column exists, NULL value for legacy, PRAGMA notnull=0 | PASS |
| AC4: SCHEMA_VERSION == 9 | `TestFromAC_SchemaVersion9AfterMigration` — 3 tests: exact equality, applied_at validity, >= 9 guard | PASS |
| AC5: File at tests/test_schema_v9_775.py | File exists and committed | PASS |

### Test Results
- pytest (scoped): 21 passed, 0 failed
- pytest (full suite): 4,065 passed, 339 failed, 8 skipped — zero failures in task scope; 339 are pre-existing cross-task issues (orchestrator, planner, MCP browser ctx) unrelated to this type:test pass-through
- ruff: clean (0 violations)

### Architect Quality: 3/5
AC column names were stale (content_hash→extraction_hash, last_fetched_at→last_extracted, omitted created_at/updated_at). Architecture review caught and corrected. Tests verify actual DDL. Gap is documentation lag from parent task evolution, not structural design failure.

### Deduction Breakdown
- Start: 1.00
- AC quality score 3/5: -.03
- All 5 AC lines have specific evidence: no deduction
- Reviewer evidence present and detailed (PASS at 0.96): no deduction
- Full-suite failures outside task scope: no deduction
- Lint clean: no deduction

### Confidence: 0.97
### Action: archive