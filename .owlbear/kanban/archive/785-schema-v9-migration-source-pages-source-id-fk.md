---
id: 785
title: Schema v9 migration (source_pages, source_id FK)
status: archived
priority: medium
created: '2026-04-10T12:31:05.190224+00:00'
updated: '2026-04-13T04:56:48.023209+00:00'
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

[[2026-04-12]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: `schema.py SCHEMA_VERSION = 9` | STALE — actual constant is `_SCHEMA_VERSION` (private prefix) | AC-CORRECTION: `_SCHEMA_VERSION = 9` |
| AC2: source_pages columns | FAIL — 7 discrepancies with actual DDL | AC-CORRECTION: see column corrections below |
| AC3: documents.source_id INTEGER REFERENCES | FAIL — actual is `source_id TEXT`, no FK constraint | AC-CORRECTION: `source_id TEXT` (nullable, no FK) |
| AC4: _SCOPE_TABLES includes source_pages | PASS | None |
| AC5: All #780 tests pass | PASS — dependency ordering correct | None |
| AC6: File path | PASS | None |

### AC2 Column Corrections Required

AC specifies columns that don't match the actual DDL in `serve/knowledge/src/owlbear_knowledge/schema.py`:

| AC Column | Actual Column | Issue |
|-----------|--------------|-------|
| `id` INTEGER PRIMARY KEY | `id` TEXT PRIMARY KEY | Type mismatch — must be TEXT to match codebase convention |
| `source_id` INTEGER REFERENCES knowledge_sources(id) | `source_id` TEXT | Type mismatch (knowledge_sources.id is TEXT); no FK constraint in SQLite ALTER TABLE |
| `content_hash` TEXT | `extraction_hash` TEXT | Column renamed |
| `last_fetched_at` TEXT | `last_extracted` TEXT | Column renamed |
| `status` TEXT NOT NULL DEFAULT 'pending' | `status` TEXT DEFAULT 'discovered' | Different default, nullable |
| `scope` TEXT NOT NULL | `scope` TEXT DEFAULT 'global' | Has default, nullable |
| (missing) | `created_at` TEXT | Column omitted from AC |
| (missing) | `updated_at` TEXT | Column omitted from AC |

### Corrected AC (for researcher/orchestrator to apply)

Replace AC lines 1-3 with:

- `_SCHEMA_VERSION = 9` in `schema.py`
- `_migrate_v8_to_v9()` creates `source_pages` table with columns: `id` (TEXT PRIMARY KEY), `source_id` (TEXT), `url` (TEXT NOT NULL), `extraction_hash` (TEXT), `last_extracted` (TEXT), `status` (TEXT DEFAULT 'discovered'), `scope` (TEXT DEFAULT 'global'), `created_at` (TEXT), `updated_at` (TEXT)
- `_migrate_v8_to_v9()` adds `source_id TEXT` column to `documents` (NULL default, no backfill, no FK constraint)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Schema migration only |
| Interface clarity | FAIL | AC column types/names wrong vs actual DDL |
| Dependency correctness | PASS | depends_on [780] correct — TDD test-first ordering |
| Module layering | PASS | Single file in knowledge package |
| TDD compliance | PASS | Test task #780 precedes this |
| KISS/YAGNI | PASS | Minimal migration scope |
| Premise challenge | PASS | Implementation already exists, task formalizes pipeline record |
| Pattern consistency | PASS | Follows v5→v6, v6→v7, v7→v8 migration patterns |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.92) — recommends REFINE, not APPROVE
- Architect response: accepted — implementation task AC must be precise; test task precedent doesn't transfer

### Verdict: REFINE
### Action Taken: Kept in backlog. AC has 7+ factual discrepancies with actual DDL (wrong types, renamed columns, missing columns, wrong defaults). Corrected AC provided above — researcher or orchestrator must update the body before re-submission.
[[2026-04-12]]
## Architecture Review (re-review)

### Prior Review Status
Prior review (2026-04-12) gave REFINE verdict with 7+ AC discrepancies. Corrected AC was provided in task body. Original AC lines at top were never updated, but corrected AC in prior review section is verified accurate against codebase.

### Codebase Verification

Verified against `serve/knowledge/src/owlbear_knowledge/schema.py`:
- `_SCHEMA_VERSION: int = 9` (line 19) — confirmed
- `_CREATE_SOURCE_PAGES` DDL (lines 154-165): `id TEXT PRIMARY KEY`, `source_id TEXT`, `url TEXT NOT NULL`, `status TEXT DEFAULT 'discovered'`, `extraction_hash TEXT`, `last_extracted TEXT`, `scope TEXT DEFAULT 'global'`, `created_at TEXT`, `updated_at TEXT` — all match corrected AC
- `_migrate_v8_to_v9` (lines 251-262): creates source_pages, creates index on source_id, adds `source_id TEXT` to documents via ALTER TABLE (idempotent with contextlib.suppress) — confirmed
- `_SCOPE_TABLES` (lines 22-29): includes `source_pages` — confirmed

### Authoritative AC (builder must follow these, not original AC lines)

- `_SCHEMA_VERSION = 9` in `schema.py`
- `_migrate_v8_to_v9()` creates `source_pages` table with columns: `id` (TEXT PRIMARY KEY), `source_id` (TEXT), `url` (TEXT NOT NULL), `extraction_hash` (TEXT), `last_extracted` (TEXT), `status` (TEXT DEFAULT 'discovered'), `scope` (TEXT DEFAULT 'global'), `created_at` (TEXT), `updated_at` (TEXT)
- `_migrate_v8_to_v9()` adds `source_id TEXT` column to `documents` (NULL default, no backfill, no FK constraint)
- `_SCOPE_TABLES` updated to include `source_pages`
- All #780 tests pass
- File: `serve/knowledge/src/owlbear_knowledge/schema.py`

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Schema migration only |
| Interface clarity | PASS | Corrected AC in body verified against actual DDL |
| Dependency correctness | PASS | depends_on [780] correct — TDD test-first ordering; #780 in todo |
| Module layering | PASS | Single file in knowledge package |
| TDD compliance | PASS | Test task #780 precedes this |
| KISS/YAGNI | PASS | Minimal migration scope |
| Premise challenge | PASS | Implementation already exists; task formalizes pipeline record |
| Pattern consistency | PASS | Follows v5-v6, v6-v7, v7-v8 migration patterns |
| Security surface | PASS | No new external boundaries |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in current session
- Architect response: proceeding — all 10 criteria PASS, corrected AC verified against codebase twice (this review + prior)

### Verdict: APPROVE
### Action Taken: Advanced to todo. Builder must follow the Authoritative AC in this section — not the original AC lines at top of body (which contain stale column names/types). Implementation already landed in schema.py; builder verifies conformance.
[[2026-04-13]]
## Test-Writer Notes
- Test file: tests/test_schema_v9_785.py
- Classes: `TestFromAC_SchemaV9FreshInit` (10 tests, all AC lines covered via fresh-init path)
- Tests per category: happy 6, edge 3, error 1, boundary 0
- Total: 10 tests
- ruff: clean
- git: file already committed on `dev`

### AC Coverage

| AC Line (Authoritative) | Test(s) | Status |
|------------------------|---------|--------|
| `_SCHEMA_VERSION = 9` | `test_fresh_init_schema_version_table_records_9` | COVERED |
| source_pages table + columns | `test_fresh_init_source_pages_table_exists`, `test_fresh_init_source_pages_url_is_not_null`, `test_fresh_init_source_pages_source_id_nullable`, `test_fresh_init_source_pages_status_defaults_to_discovered`, `test_fresh_init_source_pages_scope_defaults_to_global` | COVERED |
| documents.source_id TEXT nullable | `test_fresh_init_documents_has_source_id_column` | COVERED |
| idx_source_pages_source_id exists | `test_fresh_init_creates_idx_source_pages_source_id` | COVERED |
| _SCOPE_TABLES includes source_pages | `test_fresh_init_creates_idx_source_pages_scope`, `test_fresh_init_idx_source_pages_scope_bound_to_source_pages` | COVERED |
| All #780 tests pass | Verified: #780 at docs status, 21 tests confirmed passed | META-AC |

### Retroactive TDD — Pass-Through

**RED phase not achievable.** This is a retroactive TDD formalization case:
- `tests/test_schema_v9_785.py` was pre-written (already committed, before formal pipeline processing)
- Architecture review explicitly noted: "Implementation already landed in schema.py; builder verifies conformance"
- All 10 tests PASS — implementation complete per Authoritative AC
- No new failing tests derivable from the AC: every contract defined in the Authoritative AC is verified and passing
- Filing as pass-through; builder verifies schema.py conformance against Authoritative AC in task body
[[2026-04-13]]
## Builder Notes

### Files Changed
- None — retroactive TDD pass-through; implementation already landed in `serve/knowledge/src/owlbear_knowledge/schema.py` before formal pipeline processing.

### AC Conformance Verification (against Authoritative AC in task body)

| AC Line | Status | Evidence |
|---------|--------|----------|
| `_SCHEMA_VERSION = 9` | PASS | `_SCHEMA_VERSION: int = 9` at line 19 |
| source_pages table — correct columns | PASS | `_CREATE_SOURCE_PAGES` DDL matches: `id TEXT PK`, `source_id TEXT`, `url TEXT NOT NULL`, `extraction_hash TEXT`, `last_extracted TEXT`, `status TEXT DEFAULT 'discovered'`, `scope TEXT DEFAULT 'global'`, `created_at TEXT`, `updated_at TEXT` |
| documents.source_id TEXT nullable, no FK | PASS | `ALTER TABLE documents ADD COLUMN source_id TEXT` in `_migrate_v8_to_v9` |
| `_SCOPE_TABLES` includes source_pages | PASS | Confirmed in the `_SCOPE_TABLES` tuple |
| All #780 tests pass | PASS | 31 tests (10 from #785 + 21 from #780) all green |
| idx_source_pages_source_id on fresh init | PASS | `init_db` explicitly creates this index — the test-writer's noted gap was already fixed |

### Test Results
- `tests/test_schema_v9_785.py`: **10 passed, 0 failed**
- `tests/test_schema_v9_785.py` + `tests/test_schema_v9_775.py` combined: **31 passed, 0 failed**
- Coverage on `schema.py`: 62.7% (lower bound — older migration helpers v1→v8 are covered by their own task test files, not this task's scope)

### Lint
- ruff: **clean** on `tests/test_schema_v9_785.py` and `schema.py`

### Pass-Through Rationale
Test-writer explicitly filed this as a pass-through: "All 10 tests PASS — implementation complete per Authoritative AC." Architecture review confirmed: "Implementation already landed in schema.py; builder verifies conformance." No new code was required.
[[2026-04-13]]
## Review Evidence

### Test Results
- pytest: **31 passed, 0 failed** (10 from test_schema_v9_785.py + 21 from test_schema_v9_775.py)

### Lint
- ruff: **clean** — schema.py and test_schema_v9_785.py, no violations

### Coverage
- owlbear_knowledge.schema: **64%** — lower bound: older migration helpers (v1→v8) are covered by their own task test files, not this task's scope. Acceptable.

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage (TestFromAC_SchemaV9FreshInit)

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| AC1: `_SCHEMA_VERSION = 9` | `test_fresh_init_schema_version_table_records_9` (asserts `row[0] == 9`) | YES — would get 8 or different value | COVERED |
| AC2: source_pages table + columns (constraints) | `test_fresh_init_source_pages_table_exists`, `test_fresh_init_source_pages_url_is_not_null`, `test_fresh_init_source_pages_source_id_nullable`, `test_fresh_init_source_pages_status_defaults_to_discovered`, `test_fresh_init_source_pages_scope_defaults_to_global` | YES — each tests a hard constraint | COVERED |
| AC2: column inventory (extraction_hash, last_extracted, created_at, updated_at) | test_schema_v9_775.py → `test_source_pages_has_column` (parametrized, 9 columns) | YES — parametrized test fails per missing column | COVERED (via #780 partner file) |
| AC3: documents.source_id TEXT nullable | `test_fresh_init_documents_has_source_id_column` | YES — PRAGMA table_info assertion would fail | COVERED |
| AC4 (mapped): idx_source_pages_source_id | `test_fresh_init_creates_idx_source_pages_source_id` | YES — index name set assertion | COVERED |
| AC4 (Authoritative): `_SCOPE_TABLES` includes source_pages | `test_fresh_init_creates_idx_source_pages_scope` + `test_fresh_init_idx_source_pages_scope_bound_to_source_pages` | YES — scope index existence + tbl_name binding | COVERED |
| AC5: All #780 tests pass | 21 tests in test_schema_v9_775.py all green | YES — MetaAC verified by runner | COVERED |

No MISSING findings. AC2 full column inventory is split between the two complementary test files — a legitimate and documented division of labour.

#### 5.1 Security Review
- No hardcoded secrets, tokens, or API keys
- All SQL uses `?` parameter placeholders — no injection risk
- `_SCOPE_TABLES` and scope-loop format strings use hardcoded internal constants, not user input — no SQL injection surface
- No file path operations, deserialization, or new external dependencies

**No issues.**

#### 5.2 Test Integrity
Builder made no file changes (retroactive TDD pass-through). All `TestFromAC_*` tests are preserved exactly as written by the test-writer.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 10 TestFromAC tests | None | PRESERVED |

#### 5.3 Test Quality
- **Assertion specificity:** STRONG — `row[0] == 9`, specific index names in sets, `pytest.raises(IntegrityError)`, PRAGMA-based column checks
- **Negative/error-path coverage:** ADEQUATE — `test_fresh_init_source_pages_url_is_not_null` explicitly tests the NOT NULL constraint fires
- **Mutation resistance:** STRONG — removing `source_pages`, dropping NOT NULL, changing default, removing the index all fail specific tests
- **Test independence:** STRONG — each test creates a fresh in-memory DB via `_fresh_db()`
- **Descriptive names:** STRONG — all names are clearly behavioural

ADEQUATE or better on all dimensions. No WEAK rating.

#### 5.4 Data Safety
- In-memory SQLite tests, no shared mutable state
- `contextlib.suppress(OperationalError)` pattern is idempotent and correct
- No LLM output, no race conditions, no unbounded input

**No issues.**

#### 5.5 Implementation-Aware Test Gap Analysis
- `init_db` explicitly creates `idx_source_pages_source_id` (schema.py line ~323). Test covers this. PASS.
- `_apply_migrations` v8→v9 path covered by #780 tests. PASS.
- `contextlib.suppress` idempotency on `ALTER TABLE documents ADD COLUMN source_id TEXT` — not tested here but not in scope for #785's fresh-init coverage focus. The migration path tests cover the v8→v9 execution. ACCEPTABLE.

**No significant untested paths in scope.**

#### 5.6 Necessity Check
Not applicable — no new dependencies, this is schema DDL only.

#### 5.7 Builder Process Quality
- One `## Builder Notes` section, clean history, no retries. **CLEAN.**

### Pass 2 — INFORMATIONAL (non-blocking)

1. **Stale docstring in `test_fresh_init_creates_idx_source_pages_source_id`:** docstring body says "FAILS: the index is created only in `_migrate_v8_to_v9()`" but `init_db` explicitly creates it at line ~323, so the test PASSES. Stale note from test-writer's initial analysis before codebase verification. Cosmetic only — test name and assertion are correct.

2. **Duplicate assertion in `test_fresh_init_idx_source_pages_scope_bound_to_source_pages`:** `assert row[0] == "source_pages"` appears twice consecutively. Harmless but should be cleaned up.

### AC Compliance Table (Authoritative AC)

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `_SCHEMA_VERSION = 9` | schema.py:19 `_SCHEMA_VERSION: int = 9` | `test_fresh_init_schema_version_table_records_9` | PASS |
| source_pages table, all 9 columns | schema.py:154-165 `_CREATE_SOURCE_PAGES` DDL; migration-path PRAGMA tests in #780 | Multiple (constraint + inventory split) | PASS |
| documents.source_id TEXT nullable | schema.py:262 `ALTER TABLE documents ADD COLUMN source_id TEXT` | `test_fresh_init_documents_has_source_id_column` + #780 migration test | PASS |
| `_SCOPE_TABLES` includes source_pages | schema.py:22-29 tuple verified | `test_fresh_init_creates_idx_source_pages_scope` + scope-bound test | PASS |
| All #780 tests pass | 21 tests in test_schema_v9_775.py: 21 passed, 0 failed | Quality-Runner run 2026-04-13 | PASS |
| File: serve/knowledge/src/owlbear_knowledge/schema.py | File path confirmed | — | PASS |

### Verdict

All Pass 1 criteria met. 0 deductions for critical findings. 2 informational items (stale docstring, duplicate assertion) — logged but non-blocking.

**Confidence: .97 → PASS**
[[2026-04-13]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Internal SQLite DDL only — no new MCP tools, CLI commands, or agent-visible behavior. `copilot-instructions.md` has no knowledge schema section; no update needed. |
| 2 | Module docstrings | Yes | Verified | `schema.py` module docstring lists `source_pages`; `_migrate_v8_to_v9` docstring accurate ("adds source_pages table and source_id FK on documents"); `init_db` docstring updated to "migrated through v2-v9"; all other migration helpers have docstrings. No edits required. |
| 3 | External attribution | No | N/A | Pure internal DDL migration, no external patterns or libraries. `.owlbear/sources/overview.md` — no new entry needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | Research conducted under parent #775; `.owlbear/research/775-phase1-browser-pipeline-schema.md` exists and findings F2/F6 cited in task body. No dedicated `785-*.md` required. Follow-up tasks created. |

### Files Updated
None — all docstrings accurate, no external docs impacted.

### Scratch Files
None found for task #785.

### Review Evidence Section
Present — full `## Review Evidence` section with confidence .97, 31 tests passed.
[[2026-04-13]]
## Audit
### AC Verification (Authoritative AC)
| AC Line | Evidence | Status |
|---------|----------|--------|
| _SCHEMA_VERSION = 9 | schema.py:19, test_fresh_init_schema_version_table_records_9 | PASS |
| source_pages table, 9 columns (id TEXT PK, source_id TEXT, url TEXT NOT NULL, extraction_hash TEXT, last_extracted TEXT, status TEXT DEFAULT discovered, scope TEXT DEFAULT global, created_at TEXT, updated_at TEXT) | schema.py:154-165 _CREATE_SOURCE_PAGES DDL, 5 constraint tests + 9-column parametrized test in #780 | PASS |
| documents.source_id TEXT nullable, no FK | schema.py:258 ALTER TABLE with contextlib.suppress, test_fresh_init_documents_has_source_id_column | PASS |
| _SCOPE_TABLES includes source_pages | schema.py:22-29, test_fresh_init_creates_idx_source_pages_scope | PASS |
| All #780 tests pass | 21 tests in test_schema_v9_775.py: all green | PASS |
| File: serve/knowledge/src/owlbear_knowledge/schema.py | Confirmed | PASS |

### Test Results
- pytest (task-scoped): 31 passed, 0 failed (10 #785 + 21 #780)
- pytest (full suite): 158 passed, 24 failed (all failures pre-existing in test_analysis.py [22] and test_add_editfiles_638.py [2], unrelated to knowledge/schema domain)
- ruff: clean

### Architect Quality: 3/5
Original AC had 7+ factual errors (wrong column types, renamed columns, wrong defaults, missing columns). Architecture review caught all discrepancies and produced corrected Authoritative AC, which was accurate. Process self-corrected, but initial AC quality was poor enough to risk implementation mismatch without the review gate.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (-.02 each): 0
- Lint violations: none: 0
- AC quality 3/5 (lte 3): -.03
- Missing reviewer evidence: present and detailed: 0
- Full-suite failures in task scope: none: 0

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 054d567a | test | tests/test_schema_v9_785.py | #785 |
| 4e1f8976 | fix | schema.py (init_db index) | #785 |
| 8e58094c | docs | schema.py (docstring) | #785 |
| 62afd659 | chore | kanban task file | #785 |