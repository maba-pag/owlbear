---
id: 754
title: 'P1-01: Tests — Schema: source type, entity/relation types, source_pages, source_id
  FK'
status: archived
priority: medium
created: '2026-04-10T10:55:24.860558+00:00'
updated: '2026-04-15T08:15:57.504644+00:00'
tags:
- phase-1
- type:test
- scope:knowledge
- schema
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for schema extensions:
1. AUTHENTICATED_WEB in SourceType enum
2. Corporate EntityType values: REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD
3. Corporate RelationType values: GOVERNS, SUPERSEDES_VERSION
4. SourcePage model: source_id, url, status (discovered/approved/rejected/ingested/stale), extraction_hash, last_extracted
5. source_id FK on documents table
6. Cascade delete from source → pages → documents → entities → edges

All tests fail (RED). No dependency on Phase 0 — schema is needed regardless.

Parent: #751

[[2026-04-10]]
## Research
- Research doc: .owlbear/research/754-schema-extensions-red-tests.md
- Sources: 7 studied, 7 high-relevance (all internal — codebase patterns)
- Recommendation: Write RED tests using established project conventions — `_make_db()` fixture, `TestFromAC_*` class naming, `:memory:` SQLite + `init_db()`. SourcePage status as StrEnum (Option A). Cascade delete as application-level (Option A, matches existing `delete_document_data()` pattern). Schema version v9. (confidence: .85)
- Follow-up tasks created: none — #754 is itself the follow-up from #751 research
- Decision requests: none (T1 — tests for pre-approved schema extensions)

## Challenge Results
- Challenger: FALLBACK — subagent not available
- Confidence in original: .85
- Key findings: all 6 test areas have clear existing patterns to follow; no design ambiguity

### Key Findings
1. Current state: SourceType has 2 members, EntityType 6, RelationType 7. SourcePage model and source_id FK do not exist. Schema at v8.
2. Test patterns well-established: `TestFromAC_*` classes, `_make_db()` helper, enum value assertions, cascade verification via row counts
3. SourcePage status should be a StrEnum (PageStatus) — matches all 3 existing enum conventions
4. Cascade delete should be application-level — matches `DocumentStore.delete_document_data()` pattern, avoids silent DB-level cascades
5. Schema migration v8→v9: one migration covering source_pages table + source_id column on documents
[[2026-04-10]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| 1. AUTHENTICATED_WEB in SourceType enum | PRECISE — single enum member, testable via import + value equality | None |
| 2. Corporate EntityType values (5 members) | PRECISE — all 5 values named explicitly | None |
| 3. Corporate RelationType values (2 members) | PRECISE — GOVERNS, SUPERSEDES_VERSION named explicitly | None |
| 4. SourcePage model fields + PageStatus enum | PRECISE — fields, types, and 5 status values listed | None |
| 5. source_id FK on documents table | PRECISE — testable via PRAGMA table_info introspection | None |
| 6. Cascade delete chain | **REFINED** — original said "source → pages → documents → entities → edges", missing chunks and document_status. Existing `delete_document_data()` tests verify all 5 downstream tables (see tests/test_knowledge_intake_docstore_ingest.py L502-L1112). **Corrected chain:** source → source_pages + documents (via source_id FK) → entities, edges, chunks, document_status. Test must verify all 6 downstream tables have zero rows after source deletion. |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All 6 items are RED tests for schema v9 extensions — one test file, one migration |
| Interface clarity | PASS | After AC #6 refinement, all inputs/outputs/assertions are mechanically derivable |
| Dependency correctness | PASS | `depends_on: []` correct — schema needed regardless of Phase 0 |
| Module layering | PASS | Tests import from `owlbear_knowledge` (correct direction) |
| TDD compliance | PASS | This IS the RED phase test task, tagged `type:test` |
| KISS/YAGNI | PASS | Minimal scope — only tests for pre-approved schema extensions |
| Premise challenge | PASS | Enums/models don't exist yet (verified: SourceType has 2 members, SourcePage absent, no source_id on documents DDL) |
| Pattern consistency | PASS | Research identifies correct patterns: `_make_db()`, `TestFromAC_*`, `:memory:` + `init_db()`, enum value assertions — all verified in tests/test_knowledge_foundation.py and tests/test_knowledge_intake_docstore_ingest.py |
| Security surface | PASS | N/A — RED tests introduce no security surface |
| Single domain | PASS | `scope:knowledge` only |
| Failure mode map | N/A | RED tests don't introduce failure codepaths |
| Decision-request verification | PASS | T1 task — tests for pre-approved schema. No DR needed |
| User-action detection | NOT TRIGGERED | Counter-signal C3: tagged `type:test` |

### AC #6 Refinement (applied)

Original: "Cascade delete from source → pages → documents → entities → edges"

Refined: "Cascade delete: deleting a source removes all associated source_pages, and all documents (via source_id FK on documents), and for each document: entities, edges, chunks, document_status. Test inserts full chain (source → page → document → entity + edge + chunk + document_status), deletes the source, asserts zero rows in all 6 downstream tables."

### Architecture Notes

- Schema migration v8→v9 is correct target — one migration for source_pages table, source_id column on documents, PageStatus enum
- `init_db()` migration ladder pattern in schema.py (L251-L295) is well-established; v9 follows naturally
- No existing `delete` method chains through source → documents; `KnowledgeSourceStore.delete()` only removes the source row (source_store.py L165-171)
- Application-level cascade is the correct pattern — matches `DocumentStore.delete_document_data()` (document_store.py L243-265)

### Challenge Results

- Challenger: FALLBACK — no challenger agent available
- Confidence in approval: .90
- Key risk: none — all patterns well-established, AC now precise

### Verdict: APPROVE
### Action Taken: Refined AC #6 to include full cascade chain (chunks, document_status). Advanced to todo.
[[2026-04-10]]
## Test-Writer Notes

**Test file:** `tests/test_schema_extensions_754.py`

**Run result:** 59 tests, 0 passed, 59 failed — confirmed RED.

### Test classes and counts

| Class | Category | Tests |
|---|---|---|
| `TestFromAC_SourceTypeAuthenticatedWeb` | happy/boundary | 4 |
| `TestFromAC_EntityTypeCorporate` | happy/boundary | 15 |
| `TestFromAC_RelationTypeCorporate` | happy/boundary | 6 |
| `TestFromAC_SourcePageModel` | happy/edge/boundary | 14 |
| `TestFromAC_DocumentsSourceIdFK` | schema/boundary | 9 |
| `TestFromAC_CascadeDelete` | happy/edge/error | 11 |
| **Total** | | **59** |

### AC coverage

| AC line | Tests |
|---|---|
| 1. AUTHENTICATED_WEB in SourceType | `TestFromAC_SourceTypeAuthenticatedWeb` (4 tests) |
| 2. Corporate EntityType values (5 members) | `TestFromAC_EntityTypeCorporate` (15 tests) |
| 3. Corporate RelationType values (GOVERNS, SUPERSEDES_VERSION) | `TestFromAC_RelationTypeCorporate` (6 tests) |
| 4. SourcePage model + PageStatus enum | `TestFromAC_SourcePageModel` (14 tests) |
| 5. source_id FK on documents table | `TestFromAC_DocumentsSourceIdFK` (9 tests) |
| 6. Cascade delete (refined chain: source→pages+docs→entities+edges+chunks+document_status) | `TestFromAC_CascadeDelete` (11 tests) |

### Failure root causes (correct RED behaviour)
- AC 1–3: `AttributeError` / `AssertionError` — enum members not yet added to models.py
- AC 4: `ImportError` — `PageStatus`/`SourcePage` not yet implemented
- AC 5: `AssertionError` — schema still at v8; `source_pages` table absent, `source_id` column absent from documents
- AC 6: `sqlite3.OperationalError` — `source_pages` table absent; `delete_cascade()` method not yet on `KnowledgeSourceStore`

### Builder notes
- Add `AUTHENTICATED_WEB = "authenticated_web"` to `SourceType`
- Add 5 corporate values to `EntityType`, 2 to `RelationType`
- Add `PageStatus` StrEnum and `SourcePage` Pydantic model to `models.py`
- Schema migration v8→v9: `source_pages` table + `source_id` column on `documents`
- Add `delete_cascade(source_id) -> bool` to `KnowledgeSourceStore` (application-level, mirrors `delete_document_data` pattern)
[[2026-04-10]]
## Builder Notes

### Files changed
- `serve/knowledge/src/owlbear_knowledge/models.py` — added `PageStatus` StrEnum (5 values: DISCOVERED, APPROVED, REJECTED, INGESTED, STALE) and `SourcePage` Pydantic model (fields: id, source_id, url, status, extraction_hash, last_extracted)
- `serve/knowledge/src/owlbear_knowledge/schema.py` — fixed `_CREATE_SOURCE_PAGES` DDL: replaced `approval_state`/`extraction_status` columns with `status`, `extraction_hash`, `last_extracted` to match AC and test expectations
- `serve/knowledge/src/owlbear_knowledge/source_store.py` — added `delete_cascade(source_id: str) -> bool` method following the `delete_document_data()` application-level cascade pattern

### Test results
- 59 passed, 0 failed (was 29 failed before implementation)
- Test classes: SourceTypeAuthenticatedWeb(4), EntityTypeCorporate(15), RelationTypeCorporate(6), SourcePageModel(16), DocumentsSourceIdFK(9), CascadeDelete(11) — all green

### Coverage
- `models.py` — 100% (87/87 lines)
- `schema.py` / `source_store.py` — lower % due to pre-existing code exercised by other test suites; new code fully covered

### Lint
- ruff: all checks passed (0 issues)

### Builder-discovered tests
- None — `TestFromAC_*` coverage was complete; no edge cases warranted additional tests

### Notes
- Schema DDL mismatch (approval_state → status) was pre-existing from an earlier stub; corrected to match AC specification
- Cascade: `_seed_full_chain` uses self-referencing edge (source_id=entity_id, target_id=entity_id); `delete_cascade` correctly uses `DELETE FROM edges WHERE source_id = ? OR target_id = ?` pattern inherited from `delete_document_data`

[[2026-04-10]]
## Review Evidence

### Test Results
Not independently executed — Quality-Runner not in agent roster. Builder self-reports: 59 passed, 0 failed (`test_schema_extensions_754.py`). Cannot verify. `test_results_clean.txt` shows the captured RED-phase state (59 failures before builder changes) and is consistent with the test-writer's 59-test count.

### Lint
Not independently verified.

### Coverage
Not independently verified.

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|----------------|---------------------------|---------|
| AC1: AUTHENTICATED_WEB in SourceType | `TestFromAC_SourceTypeAuthenticatedWeb` (4) — member exists, value, isinstance str, round-trip | Yes — direct hasattr, equality, SourceType() call | COVERED |
| AC2: Corporate EntityType values (5) | `TestFromAC_EntityTypeCorporate` (15) — member_exists x5, value_matches x5, round_trips x5 | Yes — KeyError / AssertionError on each missing value | COVERED |
| AC3: GOVERNS, SUPERSEDES_VERSION | `TestFromAC_RelationTypeCorporate` (6) — exists, value, round_trip per member | Yes | COVERED |
| AC4: SourcePage model + PageStatus | `TestFromAC_SourcePageModel` (16) — import, parametrized members, isinstance str, field access, nullable fields, auto_id | Yes — ImportError or AttributeError if missing | COVERED |
| AC5: source_id FK on documents | `TestFromAC_DocumentsSourceIdFK` (8) — PRAGMA table_info for both tables, schema version = 9 | Yes — introspection assertions | COVERED |
| AC6: Cascade delete (refined chain — 6 downstream tables) | `TestFromAC_CascadeDelete` (10) — zero-row assertion per table, returns True/False, isolation test | Yes — row count assertions | COVERED |

Note: Test-writer counted 14 for SourcePageModel and 9/11 for FK/Cascade — actual file has 16/8/10. Parametrize expansion accounts for the discrepancy. Minor documentation error; test file is correct.

#### 5.1 Security Review

- `delete_cascade` uses parameterised queries throughout — no SQL injection surface ✓
- No hardcoded secrets, no dangerous deserialization, no path traversal ✓
- New code: enum additions, Pydantic model, schema DDL, one store method — zero new trust boundaries

#### 5.2 Test Integrity (TestFromAC Modifications)

Builder reports no TestFromAC_* methods were modified. No modifications visible in the changed-files diff (builder changed source files only: `models.py`, `schema.py`, `source_store.py`). PRESERVED.

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Direct value equality, PRAGMA introspection, row count = 0 |
| Negative/error-path coverage | STRONG | `test_cascade_delete_nonexistent_source_returns_false` covers the error path |
| Mutation resistance | STRONG | Removing any enum member → KeyError/AssertionError; removing DDL column → AssertionError; removing method → AttributeError |
| Test independence | STRONG | Each test uses fresh `_make_db()` `:memory:` connection; no shared state |
| Descriptive names | STRONG | All TestFromAC_* with descriptive method names |

Minor LAX: `test_cascade_delete_does_not_remove_unrelated_documents` only checks document row survives, not whether unrelated entities/edges are intact. Adequate for stated AC scope.

#### 5.4 Data Safety
No unbounded inputs, no race conditions introduced. N/A.

#### 5.5 Implementation-Aware Analysis (code reads)

**models.py** (verified by direct read):
- `PageStatus` StrEnum: DISCOVERED, APPROVED, REJECTED, INGESTED, STALE ✓
- `SourcePage` model: `id` (uuid_hex), `source_id: str`, `url: str`, `status: PageStatus`, `extraction_hash: str | None = None`, `last_extracted: str | None = None` ✓
- EntityType extended with 5 corporate values ✓
- RelationType extended with GOVERNS, SUPERSEDES_VERSION ✓
- SourceType extended with AUTHENTICATED_WEB ✓

**schema.py** (verified by direct read):
- `_CREATE_DOCUMENTS` includes `source_id TEXT` at column level ✓
- `_CREATE_SOURCE_PAGES` DDL: `id, source_id REFERENCES knowledge_sources, url NOT NULL, status TEXT DEFAULT 'discovered', extraction_hash TEXT, last_extracted TEXT, scope, created_at, updated_at` ✓
- `_migrate_v8_to_v9`: `CREATE INDEX on source_pages(source_id)`, `ALTER TABLE documents ADD COLUMN source_id TEXT` ✓

**source_store.py** `delete_cascade` (verified by direct read, lines 165-210):
- Returns `False` if source not found ✓
- Collects doc_ids via `SELECT id FROM documents WHERE source_id = ?`
- Per doc: deletes edges (WHERE source_id OR target_id = entity_id), entities, chunks, document_status ✓
- Deletes documents, source_pages, knowledge_sources row ✓
- Returns `True` after cascade ✓
- Parameterised throughout ✓

Implementation appears correct for the #754 AC from code analysis. Runtime verification pending.

#### **5.1 / 5.5 CRITICAL FINDING — DDL Column Conflict (Cross-Task Regression)**

The #754 builder changed `schema.py` source_pages DDL from the prior stub (`approval_state`, `extraction_status`) to `status`, `extraction_hash`, `last_extracted` (matching the #754 AC).

However, `tests/test_authenticated_content_pipeline_751.py` (`TestFromAC_AuthenticatedContentSchema`) — a test file in the active workspace — contains:

- `test_source_pages_has_approval_state_column` — asserts `"approval_state" in cols` (line ~345)
- `test_source_pages_has_extraction_status_column` — asserts `"extraction_status" in cols` (line ~352)

With the current schema (no `approval_state`, no `extraction_status` columns), both tests **will fail**. The builder's note confirms this: "Schema DDL mismatch (approval_state → status) was pre-existing from an earlier stub; corrected to match AC specification." The correction is correct for #754's AC but introduces failures in the #751 test file.

**Evidence:** Direct file reads of `schema.py` L152-165 (DDL) and `test_authenticated_content_pipeline_751.py` L343-360 (assertions). No test execution required to confirm the conflict.

#### 5.7 Builder Process Quality
- Single `## Builder Notes` section: CLEAN
- No loop pattern ✓

---

### Pass 2 — INFORMATIONAL

- `test_cascade_delete_does_not_remove_unrelated_documents` does not verify that entities/edges from other documents are unaffected (cross-document edge contamination is a theoretically possible side effect of the `OR target_id = ?` pattern). Scope is acceptable for the AC, but a future iteration could add coverage.
- `_CREATE_SOURCE_PAGES` includes `scope` column not tested by #754 tests — not required by the AC.

---

### AC Compliance Table (code-reading evidence only — no test execution)

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 AUTHENTICATED_WEB | `models.py` — `SourceType.AUTHENTICATED_WEB = "authenticated_web"` | `TestFromAC_SourceTypeAuthenticatedWeb` (4) | PASS (code read) |
| AC2 EntityType corporate | `models.py` — REQUIREMENT, SOLUTION, PROCEDURE, POLICY, STANDARD present | `TestFromAC_EntityTypeCorporate` (15) | PASS (code read) |
| AC3 RelationType corporate | `models.py` — GOVERNS, SUPERSEDES_VERSION present | `TestFromAC_RelationTypeCorporate` (6) | PASS (code read) |
| AC4 SourcePage + PageStatus | `models.py` — PageStatus(5 values), SourcePage(6 fields) | `TestFromAC_SourcePageModel` (16) | PASS (code read) |
| AC5 source_id FK on documents | `schema.py` L43 — `source_id TEXT` in DDL; migration L255 alters table | `TestFromAC_DocumentsSourceIdFK` (8) | PASS (code read) |
| AC5 source_pages columns | `schema.py` L152-165 — status, extraction_hash, last_extracted present | `TestFromAC_DocumentsSourceIdFK` (8) | PASS (code read) |
| AC6 cascade delete | `source_store.py` L165-210 — `delete_cascade()` with full 6-table chain | `TestFromAC_CascadeDelete` (10) | PASS (code read) |
| **Side-effect** | `test_authenticated_content_pipeline_751.py` L343-360 — approval_state/extraction_status columns absent | N/A to #754 | **FAIL (runtime)** |

---

### Pre-Block Deductions

| Finding | Severity | Deduction |
|---------|----------|-----------|
| Quality-Runner unavailable — runtime verification impossible | Blocker | Cannot reach ≥.90 confidence |
| DDL conflict — 2 tests in test_authenticated_content_pipeline_751.py will fail | Critical | Must be resolved before re-review |

**Confidence: N/A — BLOCK (runtime verification required; DDL conflict must be resolved first)**

### Resolution Path

1. The #751 test file (`tests/test_authenticated_content_pipeline_751.py`) must be updated: replace `test_source_pages_has_approval_state_column` and `test_source_pages_has_extraction_status_column` with tests for the actual column names (`status`, `extraction_hash`/`last_extracted`) per the #751 AC and refined architecture note.
2. Quality-Runner must be available for the re-review to independently execute `tests/test_schema_extensions_754.py` and verify 59 passing.
3. Code analysis suggests the #754 implementation is correct — the block is not due to suspected code defect but due to the DDL conflict and inability to run tests independently.
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: all tests passed in batch run (`test_schema_extensions_754.py`). Unblocked for review continuation.
[[2026-04-14]]
## Review Evidence

### Test Results
Quality-Runner executed independently: **59 passed, 0 failed, 0 skipped** (`tests/test_schema_extensions_754.py`). Exit code 0. Builder self-report confirmed.

### Lint
ruff: **clean** — 0 violations across `models.py`, `schema.py`, `source_store.py`, `tests/test_schema_extensions_754.py`. Exit code 0.

### Coverage
| Module | Coverage | Notes |
|--------|----------|-------|
| `owlbear_knowledge.models` | **100%** | All new enums + SourcePage model fully covered |
| `owlbear_knowledge.schema` | 48% | Large pre-existing migration ladder (v1–v8); new v9 migration fully covered |
| `owlbear_knowledge.source_store` | 57% | Pre-existing store methods; new `delete_cascade` fully covered |

Covered by separate test suites for pre-existing code; new code is at 100% — informational only.

---

### Prior Cycle CRITICAL Finding — Resolution Status

Pass 1 of cycle 1 flagged: `test_authenticated_content_pipeline_751.py` asserting `approval_state`/`extraction_status` columns that were removed.

Code-reader verified: **RESOLVED.** `tests/test_authenticated_content_pipeline_751.py` [L388–L426](tests/test_authenticated_content_pipeline_751.py#L388-L426) asserts `source_id`, `url`, `status` — the correct column names. No `approval_state` or `extraction_status` references exist. Prior finding no longer applies.

---

### 5.0 AC Coverage Table

| AC Line | Mapped Tests | Would Fail If Violated? | Verdict |
|---------|-------------|------------------------|---------|
| AC1: AUTHENTICATED_WEB in SourceType | `TestFromAC_SourceTypeAuthenticatedWeb` (4) — hasattr, value equality, isinstance str, round-trip | Yes — AttributeError / AssertionError | COVERED |
| AC2: EntityType REQUIREMENT/SOLUTION/PROCEDURE/POLICY/STANDARD | `TestFromAC_EntityTypeCorporate` (15) — member_exists×5, value_matches×5, round_trips×5 | Yes — KeyError on each missing member | COVERED |
| AC3: RelationType GOVERNS, SUPERSEDES_VERSION | `TestFromAC_RelationTypeCorporate` (6) — exists×2, value×2, round_trip×2 | Yes | COVERED |
| AC4: SourcePage + PageStatus (5 values) | `TestFromAC_SourcePageModel` (16) — import, parametrized members, isinstance, field access, nullable fields, auto_id | Yes — ImportError or AttributeError if missing | COVERED |
| AC5: source_id FK on documents + schema v9 | `TestFromAC_DocumentsSourceIdFK` (8 per runner count) — PRAGMA introspection, schema_version==9 | Yes — AssertionError | COVERED |
| AC6: Cascade delete (6 downstream tables) | `TestFromAC_CascadeDelete` (11) — zero-row per table, returns True, nonexistent returns False, isolation test | Yes — row count AssertionError | COVERED |

---

### 5.1 Security

- `delete_cascade` ([source_store.py L99–L122](serve/knowledge/src/owlbear_knowledge/source_store.py#L99-L122)): all SQL uses parameterised queries `(?, ?)` throughout. Bidirectional edge deletion `WHERE source_id = ? OR target_id = ?` with `(eid, eid)` — correct and injection-safe. ✓
- No hardcoded secrets, no path traversal, no deserialization, no new trust boundaries. ✓

### 5.2 TestFromAC Integrity

Builder changed source files only (`models.py`, `schema.py`, `source_store.py`). No `TestFromAC_*` methods modified. **All PRESERVED.**

### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Direct value equality, PRAGMA column introspection, row count = 0 after cascade |
| Negative/error-path | STRONG | `test_cascade_delete_nonexistent_source_returns_false` ✓ |
| Mutation resistance | STRONG | Remove any enum member → KeyError; remove DDL column → AssertionError; remove method → AttributeError |
| Test independence | STRONG | Fresh `_make_db()` `:memory:` per test; no shared state |
| Descriptive names | STRONG | All `TestFromAC_*` with descriptive method names |

Minor LAX (noted only): `test_cascade_delete_does_not_remove_unrelated_documents` [scope: adequate for AC6 — does not verify unrelated entities/edges]. No compensating gap.

### 5.4 Data Safety — clean. N/A for schema/enum additions.

### 5.5 Implementation Analysis

- **models.py**: `SourceType.AUTHENTICATED_WEB = "authenticated_web"` ✓; EntityType 5 corporate values ✓; RelationType GOVERNS/SUPERSEDES_VERSION ✓; `PageStatus` StrEnum 5 values ✓; `SourcePage` Pydantic model 6 fields ✓.
- **schema.py** [L123–L129](serve/knowledge/src/owlbear_knowledge/schema.py#L123-L129): `_CREATE_SOURCE_PAGES` DDL — `source_id`, `url NOT NULL`, `status DEFAULT 'discovered'`, `extraction_hash`, `last_extracted` ✓. Migration [L184–L191](serve/knowledge/src/owlbear_knowledge/schema.py#L184-L191): `CREATE TABLE source_pages`, `CREATE INDEX idx_source_pages_source_id`, `ALTER TABLE documents ADD COLUMN source_id TEXT` ✓. Schema version advances to v9 ✓.
- **source_store.py** `delete_cascade` [L96–L124](serve/knowledge/src/owlbear_knowledge/source_store.py#L96-L124): returns False if source absent [L99–L102]; collects doc_ids [L106–L107]; per doc: entity IDs → edges (both directions) → entities → chunks → document_status [L111–L118]; then documents → source_pages → knowledge_sources [L120–L122]. Full 6-table chain confirmed. ✓

### 5.7 Builder Process — **CLEAN** (1 Builder Notes section, no retry loop).

---

### AC Compliance Table (runtime evidence)

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 AUTHENTICATED_WEB | 59/59 pass + models.py ✓ | PASS |
| AC2 EntityType corporate | 59/59 pass + models.py ✓ | PASS |
| AC3 RelationType corporate | 59/59 pass + models.py ✓ | PASS |
| AC4 SourcePage + PageStatus | 59/59 pass + models.py ✓ (100% coverage) | PASS |
| AC5 source_id FK + schema v9 | 59/59 pass + schema.py [L79, L185–L191] ✓ | PASS |
| AC6 cascade delete (6 tables) | 59/59 pass + source_store.py [L96–L122] ✓ | PASS |

---

### Deductions
| Finding | Severity | Deduction |
|---------|----------|-----------|
| schema.py/source_store.py overall module coverage below 90% | Informational (new code at 100%; pre-existing code tested by dedicated suites) | −.02 |
| Minor LAX on cascade isolation test (entities/edges from unrelated docs not verified) | Minor informational | −.02 |

**Confidence: .96 → PASS**
[[2026-04-14]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | copilot-instructions.md contains only project identity and branch structure — no knowledge module schema section to update. Enum additions, new SourcePage model, and delete_cascade() method are internal API; no external-facing docs reference them. |
| 2 | Module docstrings | Yes | Verified — no updates needed | models.py: PageStatus has docstring "Status of a SourcePage in the crawl/approval lifecycle." ✓; SourcePage has docstring "A page belonging to an authenticated-web knowledge source." ✓; EntityType/RelationType/SourceType retain accurate class-level docstrings ✓. source_store.py: delete_cascade() has accurate docstring with full cascade chain ✓. All public classes and new functions covered. |
| 3 | External attribution | No | N/A | Research doc section 2 lists 7 sources — all internal codebase files. No external repos, articles, or docs were used. sources/overview.md requires no new entry. |
| 4 | CLI changes | No | N/A | Task scope: schema + model + store method. No CLI commands added or modified. README unaffected. |
| 5 | Research doc | Yes | Verified | .owlbear/research/754-schema-extensions-red-tests.md exists ✓; linked in task body under [[2026-04-10]] Research section ✓; follow-up tasks noted as none (task itself is the follow-up from #751 research) ✓. |

### Files Updated
None — all checklist items verified accurate; no documentation changes required.

### Scratch Files
No .owlbear/scratch/754-* files found. Nothing to clean.

[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: AUTHENTICATED_WEB in SourceType | models.py L50 `AUTHENTICATED_WEB = "authenticated_web"` + 4/4 tests pass | PASS |
| AC2: EntityType corporate (5 values) | models.py verified by reviewer + 15/15 tests pass | PASS |
| AC3: RelationType GOVERNS, SUPERSEDES_VERSION | models.py verified by reviewer + 6/6 tests pass | PASS |
| AC4: SourcePage + PageStatus (5 values) | models.py verified by reviewer + 16/16 tests pass | PASS |
| AC5: source_id FK + schema v9 | schema.py DDL verified by reviewer + 8/8 tests pass | PASS |
| AC6: Cascade delete (6 downstream tables) | source_store.py L165-202 `delete_cascade()` — full chain with parameterized queries + 11/11 tests pass | PASS |

### Test Results
- pytest (scoped): 59 passed, 0 failed
- pytest (full suite): 4386 passed, 191 failed, 8 skipped — 0 failures in #754 scope; 191 failures are pre-existing across unrelated modules (kanban MCP, lint hooks, planner, bookmark pipeline, etc.)
- ruff: 3 violations — all in unrelated files (kanban engine.py, test_refresh_sharepoint_879.py)

### Prior Cycle DDL Conflict — RESOLVED
Reviewer cycle 1 flagged `test_authenticated_content_pipeline_751.py` asserting `approval_state`/`extraction_status` columns no longer in schema. Verified: no references to those column names remain in the 751 test file. Conflict resolved.

### Architect Quality: 4/5
AC lines 1-5 were specific and mechanically verifiable from the start. AC6 had a minor gap (missing chunks and document_status from cascade chain) caught and refined by the architect during review. All 6 AC lines produced clean, unambiguous test targets.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| AC lines with no evidence | 0 (all 6 verified) |
| Lint violations in scope | 0 |
| AC quality ≤ 3 | 0 (score: 4) |
| Missing reviewer evidence | 0 (present, detailed, two-cycle) |
| Full-suite failures in task scope | 0 |

### Confidence: 1.00
### Action: archive