---
id: 785
title: Schema v9 migration (source_pages, source_id FK)
status: done
priority: needed
created: '2026-04-10T12:31:05.190224+00:00'
updated: '2026-04-11T16:29:37.796664+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 780
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `schema.py` `SCHEMA_VERSION = 9`
- `_migrate_v8_to_v9()` creates `source_pages` table with columns: `id` (INTEGER PRIMARY KEY), `source_id` (INTEGER REFERENCES knowledge_sources(id)), `url` (TEXT NOT NULL), `content_hash` (TEXT), `last_fetched_at` (TEXT), `status` (TEXT NOT NULL DEFAULT 'pending'), `scope` (TEXT NOT NULL)
- `_migrate_v8_to_v9()` adds `source_id INTEGER REFERENCES knowledge_sources(id)` to `documents` (NULL default, no backfill)
- `_SCOPE_TABLES` updated to include `source_pages`
- All #780 tests pass
- File: `serve/knowledge/src/owlbear_knowledge/schema.py`

## Context
- WS-A: Schema + Models Foundation
- Scope item 5 from #775
- See research F2: NULL source_id for legacy, F6: source_pages ships for Phase 2 readiness

[[2026-04-11]]
## Review Evidence

**Pipeline anomaly:** Task was in `backlog` status (not `review`) when review was invoked. No prior Review Evidence sections found — first review cycle.

### Quality-Runner Results
- pytest: **24 passed, 0 failed** (tests/test_schema_v9_785.py + tests/test_schema_v9_775.py)
- ruff: **clean**
- coverage: **64%** on owlbear_knowledge.schema (untouched v1–v8 migration paths account for gaps)

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| `SCHEMA_VERSION = 9` | schema.py:18 `_SCHEMA_VERSION: int = 9` | PASS |
| `source_pages.id` (INTEGER PRIMARY KEY) | schema.py:167 `id TEXT PRIMARY KEY` — wrong type | FAIL |
| `source_pages.source_id` (INTEGER REFERENCES knowledge_sources(id)) | schema.py:168 `source_id TEXT` — wrong type, no FK reference | FAIL |
| `source_pages.url` (TEXT NOT NULL) | schema.py:169 `url TEXT NOT NULL` | PASS |
| `source_pages.content_hash` (TEXT) | Column missing — `extraction_hash TEXT` used instead | FAIL |
| `source_pages.last_fetched_at` (TEXT) | Column missing — `last_extracted TEXT` used instead | FAIL |
| `source_pages.status` (TEXT NOT NULL DEFAULT 'pending') | `status TEXT DEFAULT 'discovered'` — wrong default, missing NOT NULL | FAIL |
| `source_pages.scope` (TEXT NOT NULL) | `scope TEXT DEFAULT 'global'` — missing NOT NULL | FAIL |
| documents: add `source_id INTEGER REFERENCES knowledge_sources(id)` | `_migrate_v8_to_v9`: `ALTER TABLE documents ADD COLUMN source_id TEXT` — wrong type, no FK | FAIL |
| `_SCOPE_TABLES` includes `source_pages` | schema.py:21-28, confirmed | PASS |
| All #780 tests pass | 24/0 | PASS |

### Pass 1 Findings

**5.3 Test Quality — WEAK (AC violation, automatic FAIL)**

`TestFromAC_SourcePagesAfterMigration.test_source_pages_has_column` (test_schema_v9_775.py) parametrizes against `["id","source_id","url","status","extraction_hash","last_extracted","scope","created_at","updated_at"]`. This asserts the implementation's column names, not the AC's column names (`content_hash`, `last_fetched_at`). A correctly implemented schema per the AC would FAIL these tests. The test suite provides false confidence on two of seven required columns.

**AC2/AC3 Implementation Violations:** The implementation consistently uses `TEXT` rather than `INTEGER` for `id` and `source_id`, omits all FK references, renames two columns, and drops NOT NULL constraints on `status` and `scope`. These are architectural choices, not typos — 6 of 7 column-spec lines in AC2 are incorrect + AC3 type/FK.

**5.7 Builder Process:** No prior Builder Notes sections — not a loop pattern.

**FALSE RED:** test_schema_v9_785.py comment states "All tests fail (RED phase)" but the implementation was already in place; all 3 tests pass. RED/GREEN state was stale at authoring time.

### Deductions
- AC2 column type/name/constraint violations (6 items): −0.30
- AC3 FK/type violation: −0.10
- Test quality WEAK (#780 asserts wrong column names): −0.15
- False-RED labeling in test file: −0.03

### Verdict

Confidence: **0.42** → **FAIL**

Root cause is AC interpretation: the builder chose different column names, types, and defaults from those in the AC spec. The test-writer then wrote tests matching the implementation rather than the spec. This is an architect-level question — are `extraction_hash`/`last_extracted`/TEXT types correct (and AC needs updating), or should the implementation be corrected to match the AC? Either way, both files need re-work once the architect decides.

Routing: `backlog` (architect re-evaluates schema design intent and updates AC or blesses the implementation's column choices).
[[2026-04-11]]
## Architecture Review

### AC Refinement (supersedes original AC)

Original AC was written from pre-implementation research (F2/F6) and contained speculative types and column names that contradict established codebase patterns. The #780 architect already approved the implementation's column names. This review aligns #785 AC to codebase conventions.

**Revised Acceptance Criteria:**

- `schema.py` `SCHEMA_VERSION = 9`
- `_migrate_v8_to_v9()` creates `source_pages` table with columns: `id` (TEXT PRIMARY KEY), `source_id` (TEXT), `url` (TEXT NOT NULL), `extraction_hash` (TEXT), `last_extracted` (TEXT), `status` (TEXT DEFAULT 'discovered'), `scope` (TEXT DEFAULT 'global'), `created_at` (TEXT), `updated_at` (TEXT)
- `_migrate_v8_to_v9()` adds `source_id TEXT` to `documents` (NULL default, no backfill)
- `_migrate_v8_to_v9()` creates index `idx_source_pages_source_id` on `source_pages(source_id)`
- `_SCOPE_TABLES` updated to include `source_pages`
- All #780 tests pass
- File: `serve/knowledge/src/owlbear_knowledge/schema.py`

**AC change rationale:**

| Original AC | Revised | Reason |
|-------------|---------|--------|
| `id` INTEGER PRIMARY KEY | TEXT PRIMARY KEY | All 9 data tables use TEXT PK; SourcePage model uses `str` with UUID factory |
| `source_id` INTEGER REFERENCES knowledge_sources(id) | TEXT (no REFERENCES) | knowledge_sources.id is TEXT; FK REFERENCES deferred to Phase 2 hardening |
| `content_hash` | `extraction_hash` | Approved in #780 arch review; reflects extraction domain semantics |
| `last_fetched_at` | `last_extracted` | Approved in #780 arch review; consistent with extraction_hash naming |
| `status` TEXT NOT NULL DEFAULT 'pending' | TEXT DEFAULT 'discovered' | PageStatus enum has no 'pending' value; 'discovered' is the only valid initial state; NOT NULL omitted per existing table pattern (documents, consolidations) |
| `scope` TEXT NOT NULL | TEXT DEFAULT 'global' | Matches documents, consolidations — no NOT NULL on scope columns |
| (not specified) | `created_at` TEXT, `updated_at` TEXT | Standard audit columns (knowledge_sources, bookmarks, consolidations) |
| documents: INTEGER REFERENCES | TEXT (no REFERENCES) | Same rationale as source_pages.source_id |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One migration function, one table, one ALTER — single schema change |
| Interface clarity | PASS (after refinement) | All column names, types, defaults, and constraints now precisely specified |
| Dependency correctness | PASS | Depends on #780 (test task, in todo) — correct TDD ordering |
| Module layering | PASS | schema.py is the DDL layer; no upward imports |
| TDD compliance | PASS | #780 test task precedes this implementation task |
| KISS/YAGNI | PASS | Minimal Phase 1 schema; extra columns (created_at/updated_at) are standard audit fields |
| Premise challenge | PASS | source_pages needed for Phase 2 crawler; ships in v9 for readiness (research F6) |
| Pattern consistency | PASS | TEXT PK, DEFAULT without NOT NULL, audit columns — all match existing tables |
| Security surface | PASS | DDL-only change, no user input surface |
| Single domain | PASS | Knowledge domain only |

### Phase 2 Notes

- FK REFERENCES on `source_pages.source_id` → `knowledge_sources(id)` should be added when Phase 2 crawler writes to this table. Manual cascade deletes exist in source_store.py and document_store.py.
- `SourcePage` model intentionally omits `scope`, `created_at`, `updated_at` — schema provisioned for Phase 2, model covers Phase 1 needs. Future round-tripping will require model updates.

### Challenge Results
- Challenger: proceed (confidence 0.78)
- Concerns: FK REFERENCES deferral notation, model-schema column gap acknowledgment
- Architect response: accepted — both items noted in Phase 2 Notes above; 0.78 justified as annotation-level gap, not structural

### Reviewer Feedback Integration

The reviewer's 0.42 FAIL was correct — the implementation diverged from the original AC on 8 of 11 checkpoints. Root cause was stale AC (written from research before schema finalization), not builder error. The builder followed codebase patterns correctly. Both tests and implementation are architecturally sound once AC is realigned.

### Verdict: APPROVE
### Action Taken: Refined AC to match codebase patterns and #780 architect decisions. Advanced to todo.
[[2026-04-11]]
## Test-Writer Notes
- Test file: tests/test_schema_v9_785.py
- Class: `TestFromAC_SchemaV9FreshInit`
- Tests per category: happy 7, edge 1, error 1, boundary 1
- Total: 10 tests — **1 FAIL, 9 PASS**
- ruff: clean

### AC Coverage Table

| Revised AC Line | Test(s) | Fails? |
|-----------------|---------|--------|
| SCHEMA_VERSION = 9 | test_fresh_init_schema_version_table_records_9 | PASS |
| source_pages table exists | test_fresh_init_source_pages_table_exists | PASS |
| url TEXT NOT NULL | test_fresh_init_source_pages_url_is_not_null | PASS |
| source_id TEXT (nullable) | test_fresh_init_source_pages_source_id_nullable | PASS |
| status DEFAULT 'discovered' | test_fresh_init_source_pages_status_defaults_to_discovered | PASS |
| scope DEFAULT 'global' | test_fresh_init_source_pages_scope_defaults_to_global | PASS |
| documents.source_id TEXT | test_fresh_init_documents_has_source_id_column | PASS |
| idx_source_pages_source_id created | test_fresh_init_creates_idx_source_pages_source_id | **FAIL** |
| _SCOPE_TABLES includes source_pages | test_fresh_init_creates_idx_source_pages_scope | PASS |
| _SCOPE_TABLES scope index bound to table | test_fresh_init_idx_source_pages_scope_bound_to_source_pages | PASS |

### Failing Test
`test_fresh_init_creates_idx_source_pages_source_id` — `idx_source_pages_source_id` is created only in `_migrate_v8_to_v9()`; `init_db` has no explicit `CREATE INDEX` for it on the fresh-init path. New installations are missing this index while migrated installations have it.

### Context Note
This is a post-arch-review task: the architecture review (same body) aligned the AC to match an already-correct implementation. Nine of ten tests pass immediately because the implementation was complete before AC alignment. The one failing test (`idx_source_pages_source_id` on fresh init) is a genuine schema consistency gap — the builder must decide whether to add `idx_source_pages_source_id` to `init_db`'s explicit index block (consistent with `idx_knowledge_sources_name_scope` / `idx_bookmarks_url_scope` patterns) or scope the AC to migration-only.

Commit: `054d567a` — test: rewrite schema v9 fresh-init tests (#785, test-writer)
[[2026-04-11]]
## Builder Notes

### Files Changed
- `serve/knowledge/src/owlbear_knowledge/schema.py` — 1 insertion (+1 line)

### Change
Added `CREATE INDEX IF NOT EXISTS idx_source_pages_source_id ON source_pages(source_id)` to `init_db()`'s explicit index block, immediately before the `knowledge_sources` indexes. Follows the existing pattern for `idx_knowledge_sources_name_scope` and `idx_bookmarks_url_scope`.

### RED Verification
Ran `test_fresh_init_creates_idx_source_pages_source_id` before fix — confirmed FAIL:
`AssertionError: 'idx_source_pages_source_id' not in index set`

### Test Results
- pytest: **31 passed, 0 failed** (tests/test_schema_v9_785.py × 10, tests/test_schema_v9_775.py × 21)
- ruff: **clean**
- coverage: **64%** on owlbear_knowledge.schema (unchanged — gaps are v1–v8 migration paths not exercised by these tests)

### Builder-Discovered Tests
None — single root cause, single fix, no edge cases discovered.

### Commit
`4e1f8976` — fix: add idx_source_pages_source_id to init_db fresh-init path (#785)
[[2026-04-11]]
## Review Evidence

### Test Results
- pytest: **31 passed, 0 failed** (tests/test_schema_v9_785.py × 10, tests/test_schema_v9_775.py × 21)

### Lint: clean

### Coverage: owlbear_knowledge.schema: 64% (gap is v1–v8 migration paths, untouched by this task)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| SCHEMA_VERSION = 9 | test_fresh_init_schema_version_table_records_9 | Yes — asserts `row[0] == 9` exactly | COVERED |
| source_pages.url TEXT NOT NULL | test_fresh_init_source_pages_url_is_not_null | Yes — expects IntegrityError on omitted url | COVERED |
| source_pages.source_id nullable | test_fresh_init_source_pages_source_id_nullable | Yes — verifies row[0] is None | COVERED |
| source_pages.status DEFAULT 'discovered' | test_fresh_init_source_pages_status_defaults_to_discovered | Yes — asserts row[0] == "discovered" | COVERED |
| source_pages.scope DEFAULT 'global' | test_fresh_init_source_pages_scope_defaults_to_global | Yes — asserts row[0] == "global" | COVERED |
| documents.source_id TEXT (migration) | test_documents_has_source_id_column_after_migration + test_legacy_document_source_id_is_null_after_migration | Yes — both would fail if column absent or non-null | COVERED |
| idx_source_pages_source_id via migration | test_source_pages_source_id_index_exists_after_migration | Yes — asserts row is not None | COVERED |
| idx_source_pages_source_id via fresh-init | test_fresh_init_creates_idx_source_pages_source_id | Yes — asserts index name in set | COVERED |
| _SCOPE_TABLES includes source_pages | test_fresh_init_creates_idx_source_pages_scope + test_fresh_init_idx_source_pages_scope_bound_to_source_pages | Yes — checks index existence and tbl_name binding | COVERED |

#### Security Review
No issues. DDL-only change. `CREATE INDEX IF NOT EXISTS` — no user input surface, no injection vectors.

#### Test Integrity
Builder changed only `serve/knowledge/src/owlbear_knowledge/schema.py` (1 line insertion). Zero TestFromAC_* modifications. All original assertions preserved.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All TestFromAC_* (both files) | None — builder did not touch test files | PRESERVED |

#### 5.3 Test Quality: STRONG
Constraints validated via IntegrityError (not just column presence), defaults confirmed by omitting column on insert, index binding verified via sqlite_master tbl_name. No lazy assertions. All test names descriptive.

#### 5.5 Implementation-Aware Gap Analysis
Builder's only change: `conn.execute("CREATE INDEX IF NOT EXISTS idx_source_pages_source_id ON source_pages(source_id)")` in init_db() explicit index block. Directly targeted by test_fresh_init_creates_idx_source_pages_source_id. Idempotency of `IF NOT EXISTS` on migration path (double-create harmless) needs no test. No gap.

#### 5.7 Builder Process: CLEAN
Single Builder Notes section. RED verification documented (confirmed FAIL before fix, all 31 pass after).

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| SCHEMA_VERSION = 9 | schema.py:19 `_SCHEMA_VERSION: int = 9` | PASS |
| source_pages table — all 9 columns | schema.py:153–169 _CREATE_SOURCE_PAGES DDL verified | PASS |
| _migrate_v8_to_v9 adds documents.source_id TEXT | schema.py:256–257 (with contextlib.suppress) | PASS |
| _migrate_v8_to_v9 creates idx_source_pages_source_id | schema.py:254 | PASS |
| init_db fresh-init creates idx_source_pages_source_id | schema.py:331 (builder fix) | PASS |
| _SCOPE_TABLES includes source_pages | schema.py:28 | PASS |
| All #780 tests pass | 31 passed, 0 failed (quality-runner) | PASS |

### Deductions
None.

### Verdict
Confidence: **0.98** → **PASS**

The builder's single-line fix correctly closes the fresh-init/migration parity gap. The explicit index block in init_db() now mirrors the migration path. Both code paths produce identical schema state. All 31 tests pass, lint is clean, assertions are strong.
[[2026-04-11]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `init_db()` interface unchanged; index addition is internal DDL not surfaced in public API |
| 2 | Module docstrings | No | N/A | Module docstring already lists `source_pages` (added at 2d70aa70 by #783 doc-writer); `init_db()` docstring accurately describes idempotency and v2-v9 migration path |
| 3 | External attribution | No | N/A | DDL-only change; no external patterns referenced |
| 4 | CLI changes | No | N/A | No CLI touched |
| 5 | Research doc | Yes | Verified | `.owlbear/research/775-phase1-browser-pipeline-schema.md` exists; referenced in task Context (F2, F6) |

### Files Updated
None — all docstrings and module-level documentation were already accurate at HEAD.

### Scratch Files
No `.owlbear/scratch/785-*` files found.
[[2026-04-11]]
## Audit
### AC Verification (Revised AC)
| AC Line | Evidence | Status |
|---------|----------|--------|
| SCHEMA_VERSION = 9 | schema.py:19 `_SCHEMA_VERSION: int = 9` | PASS |
| source_pages table — 9 columns (id TEXT PK, source_id TEXT, url TEXT NOT NULL, extraction_hash TEXT, last_extracted TEXT, status TEXT DEFAULT 'discovered', scope TEXT DEFAULT 'global', created_at TEXT, updated_at TEXT) | schema.py:153–166 `_CREATE_SOURCE_PAGES` DDL | PASS |
| _migrate_v8_to_v9 adds documents.source_id TEXT | schema.py:256–257 (contextlib.suppress) | PASS |
| _migrate_v8_to_v9 creates idx_source_pages_source_id | schema.py:254 | PASS |
| init_db fresh-init creates idx_source_pages_source_id | schema.py:331 (builder fix 4e1f8976) | PASS |
| _SCOPE_TABLES includes source_pages | schema.py:28 | PASS |
| All #780 tests pass | 31 passed, 0 failed (test_schema_v9_785.py × 10, test_schema_v9_775.py × 21) | PASS |

### Test Results
- pytest (task scope): 31 passed, 0 failed
- pytest (full suite): 3,450 passed, 303 failed, 6 collection errors — no failures in task scope; all failures are pre-existing in unrelated modules
- ruff: clean

### Architect Quality: 4/5
Original AC was stale (pre-implementation research with speculative types/names). Architecture review correctly realigned AC to match codebase conventions (TEXT PKs, no FK REFERENCES, extraction-domain naming). Revised AC is specific and verifiable. Deducted from 5 because the original required a full review cycle to correct.

### Deduction Breakdown
- AC lines with no evidence: 0 → −0.00
- Lint violations: 0 → −0.00
- AC quality ≤ 3: N/A (4/5) → −0.00
- Missing reviewer evidence: N/A (detailed, PASS 0.98) → −0.00
- Full-suite failures in task scope: 0 → −0.00

### Confidence: 1.00
### Action: archive

### Commit Integrity
- 054d567a — test: rewrite schema v9 fresh-init tests (#785, test-writer)
- 4e1f8976 — fix: add idx_source_pages_source_id to init_db fresh-init path (#785)
- Both verified via git log. No uncommitted content changes (line-ending-only artifacts in working tree).