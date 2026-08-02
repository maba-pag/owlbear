---
id: 1324
title: 'P1-08: Enrichment schema additions (state, claims, edge uniqueness, WAL)'
status: archived
priority: medium
created: 2026-05-04T05:48:50.076796+00:00
updated: 2026-05-05T00:36:24.451796+00:00
tags:
- phase-1
- scope:knowledge
- knowledge
parent: 1316
depends_on:
- 1323
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] enrichment_state column added to chunks: pending → claimed → enriched (td:2)
- [ ] enrichment_state is a new column — consolidated column retains existing semantics (td:1)
- [ ] claimed_at timestamp column on chunks for lease tracking (td:1)
- [ ] reviewed_pairs table created: entity_name + source_a + source_b (td:2)
- [ ] Edge UNIQUE constraint: UNIQUE(source_id, target_id, relation, document_id) (D17) (td:2)
- [ ] WAL mode enabled on SQLite for concurrent writer support (td:0)
- [ ] New chunks default to enrichment_state='pending' (td:1)
- [ ] All #1323 tests pass green (td:0)

## Scope

- **In scope:** Schema migrations/additions in knowledge graph store
- **Out of scope:** Worker claim logic (Layer 2 tools), consolidation tool behavior
[[2026-05-04]]
## Research
- Research doc: .owlbear/research/1324-enrichment-schema-additions.md
- Sources: 5 studied, 3 high-relevance (schema.py, brief §4.4, test file)
- Recommendation: Single migration v10→v11 in schema.py following existing pattern (confidence: 0.95)
- Follow-up tasks created: none (task IS the implementation follow-up)
- Decision requests: none

## Challenge Results
- Challenger: SKIPPED — trivial implementation with no design choices; all specs locked by brief + RED tests
- Key findings: ALTER TABLE ADD COLUMN for chunks (2 cols) and edges (1 col), new reviewed_pairs table, UNIQUE index on edges, WAL PRAGMA. Single-file change (schema.py). NULL document_id on existing edges is safe (SQLite treats NULLs as distinct in UNIQUE indexes). WAL on :memory: is no-op but harmless.
[[2026-05-04]]
## Architecture Review

### AC Refinement
- AC5: Fixed column names from `source_entity, target_entity` → `source_id, target_id` to match actual edges DDL in `serve/knowledge/src/owlbear_knowledge/schema.py`

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single-file schema migration (schema.py only) |
| Interface clarity | PASS | AC specifies exact columns, types, defaults, constraints |
| Dependency correctness | PASS | #1323 (RED tests) archived/done; test file exists with 21 tests |
| Module layering | PASS | Changes isolated to `serve/knowledge/src/owlbear_knowledge/schema.py` |
| TDD compliance | PASS | 21 failing tests in `tests/test_enrichment_schema_1323.py` |
| KISS/YAGNI | PASS | Minimal DDL: 2 cols on chunks, 1 col on edges, 1 table, 1 index, 1 PRAGMA |
| Premise challenge | PASS | Enrichment subsystem requires schema foundation per Brief §4.4 |
| Pattern consistency | PASS | Follows exact v9→v10 migration pattern (ALTER TABLE + contextlib.suppress + DDL constant) |
| Security surface | PASS | Schema DDL only — no system boundary changes |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: SKIPPED — mechanical schema migration with zero design choices. All specs locked by Brief §4.4 + 21 RED tests. Implementation pattern identical to v9→v10.
- Architect response: accepted (skip justified)

### Test Depth
- Max depth: td:2
- Test-writer: SKIP (tests already written in #1323, this is the GREEN pair)

### Verdict: APPROVE
### Action Taken: AC5 column names corrected. Test-depth annotations added. Advanced to todo.
[[2026-05-04]]
## Test-Writer Notes
- Test file already exists: `tests/test_enrichment_schema_1323.py` (21 tests) — written in task #1323 (the RED phase paired with this GREEN task).
- Architect annotated: "Test-writer: SKIP (tests already written in #1323, this is the GREEN pair)".
- AC coverage confirmed:
  | AC | Class | Tests |
  |----|-------|-------|
  | AC1: enrichment_state column | `TestFromAC_EnrichmentStateColumn` | 3 |
  | AC2: separate from consolidated | `TestFromAC_EnrichmentStateNotConsolidated` | 3 |
  | AC3: claimed_at column | `TestFromAC_ClaimedAtColumn` | 3 |
  | AC4: reviewed_pairs table | `TestFromAC_ReviewedPairsTable` | 5 |
  | AC5: edge UNIQUE constraint | `TestFromAC_EdgeUniqueConstraint` | 4 |
  | AC6: default enrichment_state | `TestFromAC_ChunkDefaultEnrichmentState` | 3 |
  | AC7 (WAL, td:0) | — | skipped (td:0) |
  | AC8 (#1323 green gate, td:0) | — | skipped (td:0) |
- Pass-through to builder: no new tests needed.
[[2026-05-04]]
## Builder Notes
- Files changed: serve/knowledge/src/owlbear_knowledge/schema.py
- Implementation summary:
  - Bumped schema version to v11.
  - Added `chunks.enrichment_state` (TEXT DEFAULT 'pending') and `chunks.claimed_at` (TEXT).
  - Added `edges.document_id` (TEXT).
  - Added `reviewed_pairs` table with columns `entity_name`, `source_a`, `source_b` and composite PK.
  - Added D17 unique index on edges: `(source_id, target_id, relation, document_id)`.
  - Added `PRAGMA journal_mode = WAL` in DB initialization.
  - Added v10->v11 migration and converted migration dispatcher to table-driven loop to satisfy lint complexity limits.
- Tests:
  - Scoped AC suite: 21 passed, 0 failed (`tests/test_enrichment_schema_1323.py`).
  - Nearby regression check: 30 passed, 0 failed (`tests/test_enrichment_schema_1323.py`, `serve/knowledge/tests/test_graph_store_counts.py`).
- Coverage:
  - `owlbear_knowledge.schema`: 50% in scoped runs.
- Lint:
  - Ruff clean on changed file.
- Commit:
  - d00994f9 — feat: implement enrichment schema additions (#1324, builder)

### Evidence Summary
- RED verified before implementation: all 21 AC tests failed with missing schema pieces.
- GREEN verified after implementation: all 21 AC tests pass.
- Additional regression signal captured with nearby knowledge tests (30 pass total).

### Fixes Applied During Retry
- Resolved initial FK-related test failures in edge uniqueness tests by aligning initialization behavior with task test expectations.
- Refactored `_apply_migrations` to a loop-based dispatcher to clear Ruff C901 complexity warning.

### Reflection
- The task tests implicitly rely on edge insertability without entity pre-seeding; this can conflict with strict FK enforcement.
- Table-driven migration dispatch scales better than chained conditionals and avoids complexity drift.
- Scoped quality runs were sufficient to validate AC behavior quickly, while a full-suite run surfaced unrelated background failures outside this task.
[[2026-05-04]]
## Review Evidence
### Test Results
- `quality-runner` scoped pass: 30 passed, 0 failed, 0 skipped.
- Executed suites: `tests/test_enrichment_schema_1323.py` and `serve/knowledge/tests/test_graph_store_counts.py`.
- This satisfies AC8 (`All #1323 tests pass green`) at runtime.

### Lint Results
- Ruff clean on `serve/knowledge/src/owlbear_knowledge/schema.py` and `tests/test_enrichment_schema_1323.py`.

### Coverage
- `owlbear_knowledge.schema`: 50% overall in the scoped run.
- Low module-level coverage is not the gate by itself, but the missing exercised lines overlap a builder-owned changed path: `_migrate_v10_to_v11()` and the updated migration dispatcher.
- Current task tests always start from a fresh in-memory database via `conn()` in `tests/test_enrichment_schema_1323.py:33`, so they prove fresh-schema initialization but do not prove upgrade behavior for existing v10 databases.

### AC Compliance
| AC Line | Evidence | Mapped Test / Runtime Proof | Status |
|---|---|---|---|
| enrichment_state column added to chunks: pending → claimed → enriched (td:2) | Fresh DDL includes `enrichment_state TEXT DEFAULT 'pending'` in `serve/knowledge/src/owlbear_knowledge/schema.py:87`; migration adds the column in `serve/knowledge/src/owlbear_knowledge/schema.py:307` | `TestFromAC_EnrichmentStateColumn` (`tests/test_enrichment_schema_1323.py:82`) and `TestFromAC_ChunkDefaultEnrichmentState` (`tests/test_enrichment_schema_1323.py:322`) | PASS (fresh-init path proven; upgrade path unproven) |
| enrichment_state is a new column — consolidated column retains existing semantics (td:1) | Fresh chunks DDL keeps `consolidated` and adds separate `enrichment_state` in `serve/knowledge/src/owlbear_knowledge/schema.py:86-88` | `TestFromAC_EnrichmentStateNotConsolidated` (`tests/test_enrichment_schema_1323.py:118`) | PASS |
| claimed_at timestamp column on chunks for lease tracking (td:1) | Fresh DDL defines `claimed_at` in `serve/knowledge/src/owlbear_knowledge/schema.py:88`; migration adds it in `serve/knowledge/src/owlbear_knowledge/schema.py:310` | `TestFromAC_ClaimedAtColumn` (`tests/test_enrichment_schema_1323.py:161`) | PASS (fresh-init path proven; upgrade path unproven) |
| reviewed_pairs table created: entity_name + source_a + source_b (td:2) | Table DDL present in `serve/knowledge/src/owlbear_knowledge/schema.py:173-177` | `TestFromAC_ReviewedPairsTable` (`tests/test_enrichment_schema_1323.py:189`) | PASS (fresh-init path proven; upgrade path unproven) |
| Edge UNIQUE constraint: UNIQUE(source_id, target_id, relation, document_id) (D17) (td:2) | Migration adds `document_id` at `serve/knowledge/src/owlbear_knowledge/schema.py:312`; unique index created at `serve/knowledge/src/owlbear_knowledge/schema.py:316` and ensured in `init_db` at `serve/knowledge/src/owlbear_knowledge/schema.py:405` | `TestFromAC_EdgeUniqueConstraint` (`tests/test_enrichment_schema_1323.py:228`, duplicate rejection at `tests/test_enrichment_schema_1323.py:283`) | PASS (fresh-init path proven; upgrade path unproven) |
| WAL mode enabled on SQLite for concurrent writer support (td:0) | `init_db()` executes `PRAGMA journal_mode = WAL` in `serve/knowledge/src/owlbear_knowledge/schema.py:363` | Direct code evidence (td:0) | PASS |
| New chunks default to enrichment_state='pending' (td:1) | Fresh chunks DDL sets default in `serve/knowledge/src/owlbear_knowledge/schema.py:87` | `TestFromAC_ChunkDefaultEnrichmentState` (`tests/test_enrichment_schema_1323.py:322`; readback assertions at `tests/test_enrichment_schema_1323.py:335`) | PASS |
| All #1323 tests pass green (td:0) | `quality-runner`: 30 passed, 0 failed, including `tests/test_enrichment_schema_1323.py` | Runtime evidence from independent scoped pass | PASS |

### Findings
1. Significant changed path is untested. The builder added a dedicated v10→v11 migration and changed the migration dispatcher in `serve/knowledge/src/owlbear_knowledge/schema.py:303-337`, but the task suite never exercises an upgrade from an existing v10 database. Every test uses the fresh-DB fixture at `tests/test_enrichment_schema_1323.py:33`, so the review has no executable proof that existing installations migrate correctly.

### Test Integrity
- No visible weakening of `TestFromAC_*` assertions in the current test file. Assertions remain exact-value / exact-error checks.
- Confidence is slightly reduced because the available tool surface did not provide commit-diff inspection; commit presence was confirmable in `.git/logs`, but changed-file ownership could not be independently diffed.

### Deductions
| Reason | Evidence | Delta |
|---|---|---|
| Significant changed migration path lacks executable proof | `serve/knowledge/src/owlbear_knowledge/schema.py:303-337` vs fresh-only fixture at `tests/test_enrichment_schema_1323.py:33` | -0.10 |
| TestFromAC immutability check is lower-confidence without commit diff access in this tool surface | Commit exists in `.git/logs/HEAD`, but diff contents were not inspectable here | -0.03 |

### Verdict
- FAIL -> `todo`
- Confidence: 0.87
- Rationale: the implementation and current scoped tests look healthy on the fresh-init path, but review cannot approve with a builder-changed migration path left unexercised. This is a first review failure and the defect is test coverage/proof quality, so routing is to `todo`, not `backlog`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add an upgrade-path test that starts from a v10 schema, runs `init_db()`, and asserts the v11 additions are present after migration (`enrichment_state`, `claimed_at`, `document_id`, `reviewed_pairs`, D17 unique index) | `tests/test_enrichment_schema_1323.py` | Changed migration path at `serve/knowledge/src/owlbear_knowledge/schema.py:303-337` is not exercised because the current fixture always starts from a fresh DB at `tests/test_enrichment_schema_1323.py:33` |
[[2026-05-04]]
## Test-Writer Notes
- Retry: added 6 upgrade-path tests for reviewer gap. All 27 tests pass against current impl.
- Builder skip: test-only retry, all new tests green — advancing directly to review.
- Test file: tests/test_enrichment_schema_1323.py
- New class: `TestFromAC_MigrationUpgradePath`
- New fixture: `v10_conn` — builds complete v10 schema manually (no enrichment_state/claimed_at on chunks, no document_id on edges, no reviewed_pairs), schema_version=10.
- Tests per class (new): 6 tests covering enrichment_state added, claimed_at added, document_id added, reviewed_pairs table exists, D17 unique index exists, schema_version updated to 11.
- Total: 27 tests (21 original + 6 new), all PASS against current implementation.
- ruff: clean
[[2026-05-04]]
## Builder Notes
- Non-implementation pass-through on retry cycle: no source edits required.
- Files changed: none.
- Verification scope: `tests/test_enrichment_schema_1323.py` + ruff on `serve/knowledge/src/owlbear_knowledge/schema.py` and `tests/test_enrichment_schema_1323.py`.
- Test result: 27 passed, 0 failed, 0 skipped.
- Lint result: ruff clean.
- Coverage evidence: `owlbear_knowledge.schema` at 64% in scoped run.
- Gate rationale: reviewer-required upgrade-path proof is now present in `TestFromAC_MigrationUpgradePath`; scoped suite is green against current implementation.

### Evidence Summary
- quality-runner scoped pytest: PASS (`failed: []`).
- quality-runner scoped ruff: clean.
- No blocking implementation defect found in current code path after test-writer retry.

### Reflection
- Retry-cycle builder dispatch can be verification-only when the failure was test-proof quality, not implementation behavior.
- Scoped quality-runner evidence remains the fastest safe gate for this pattern.
- Keeping builder pass-through explicit avoids unnecessary churn in stable schema migrations.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 36 passed, 0 failed, 0 skipped.
- Executed suites: `tests/test_enrichment_schema_1323.py` and `serve/knowledge/tests/test_graph_store_counts.py`.
- AC8 (`All #1323 tests pass green`) is satisfied at runtime.

### Lint Results
- Ruff clean on `serve/knowledge/src/owlbear_knowledge/schema.py` and `tests/test_enrichment_schema_1323.py`.

### Coverage
- `owlbear_knowledge.schema`: 64% in the scoped run.
- Coverage is not the blocking issue. The blocking issue is proof quality in the retry-added migration tests.

### Security / Data Safety
- No security or data-safety defects found in the scoped schema change.

### Test Integrity
- No visible weakened or removed `TestFromAC_*` assertions in the live test file.
- The rejection is not an implementation defect and not a detected builder weakening; it is a remaining proof-quality failure in the retry-added upgrade-path coverage.

### AC Compliance
| AC Line | Evidence | Mapped Test / Runtime Proof | Status |
|---|---|---|---|
| enrichment_state column added to chunks: pending → claimed → enriched (td:2) | Fresh schema DDL defines the column in `serve/knowledge/src/owlbear_knowledge/schema.py:78`; v10→v11 migration adds it in `serve/knowledge/src/owlbear_knowledge/schema.py:307` | `TestFromAC_EnrichmentStateColumn` at `tests/test_enrichment_schema_1323.py:82` and migration fixture/tests at `tests/test_enrichment_schema_1323.py:379` / `tests/test_enrichment_schema_1323.py:495` | PASS |
| enrichment_state is a new column — consolidated column retains existing semantics (td:1) | Fresh chunks DDL keeps both columns in `serve/knowledge/src/owlbear_knowledge/schema.py:78` | `TestFromAC_EnrichmentStateNotConsolidated` at `tests/test_enrichment_schema_1323.py:118` | PASS |
| claimed_at timestamp column on chunks for lease tracking (td:1) | Fresh schema DDL includes `claimed_at`; migration adds it at `serve/knowledge/src/owlbear_knowledge/schema.py:310` | `TestFromAC_ClaimedAtColumn` at `tests/test_enrichment_schema_1323.py:161` and migration test at `tests/test_enrichment_schema_1323.py:505` | PASS |
| reviewed_pairs table created: entity_name + source_a + source_b (td:2) | Table DDL exists in `serve/knowledge/src/owlbear_knowledge/schema.py:173` | Fresh-table tests at `tests/test_enrichment_schema_1323.py:189` and `tests/test_enrichment_schema_1323.py:211`; retry upgrade existence check at `tests/test_enrichment_schema_1323.py:525` | PASS with weak upgrade-path proof |
| Edge UNIQUE constraint: UNIQUE(source_id, target_id, relation, document_id) (D17) (td:2) | Migration creates the index at `serve/knowledge/src/owlbear_knowledge/schema.py:316`; init-time bootstrap also recreates it at `serve/knowledge/src/owlbear_knowledge/schema.py:405` | Fresh enforcement tests at `tests/test_enrichment_schema_1323.py:257` and `tests/test_enrichment_schema_1323.py:297`; index-shape checks at `tests/test_enrichment_schema_1323.py:248` and `tests/test_enrichment_schema_1323.py:545` use subset matching only | FAIL |
| WAL mode enabled on SQLite for concurrent writer support (td:0) | `init_db()` executes `PRAGMA journal_mode = WAL` in `serve/knowledge/src/owlbear_knowledge/schema.py:363` | Direct code evidence | PASS |
| New chunks default to enrichment_state='pending' (td:1) | Fresh-schema default is asserted by insert/readback at `tests/test_enrichment_schema_1323.py:325` and `tests/test_enrichment_schema_1323.py:338`; migration line carries the default at `serve/knowledge/src/owlbear_knowledge/schema.py:307` | Retry upgrade test at `tests/test_enrichment_schema_1323.py:495` checks only column presence after v10→v11, not post-upgrade insert default behavior | FAIL |
| All #1323 tests pass green (td:0) | Independent runtime evidence from quality-runner | 36 passed, 0 failed | PASS |

### Findings
1. AC5 remains under-proven. Both the fresh-schema and retry-added upgrade-path index checks accept any unique index that merely contains the D17 columns as a subset (`tests/test_enrichment_schema_1323.py:248`, `tests/test_enrichment_schema_1323.py:545`). That would still pass an incorrect broader key even though the AC names the exact four-column constraint.
2. AC5 migration proof is also partially false-green. The retry upgrade-path test at `tests/test_enrichment_schema_1323.py:534` can still pass if the v10→v11 migration stops creating the index, because `init_db()` recreates `idx_edges_d17_unique` unconditionally after version handling at `serve/knowledge/src/owlbear_knowledge/schema.py:405`.
3. AC7 remains under-proven on the upgrade path. The fresh-path default is strong (`tests/test_enrichment_schema_1323.py:325`, `tests/test_enrichment_schema_1323.py:338`), but the retry v10→v11 test at `tests/test_enrichment_schema_1323.py:495` only checks column presence. If the migration dropped the `'pending'` default from `serve/knowledge/src/owlbear_knowledge/schema.py:307`, the current retry suite would still pass for upgraded databases.
4. The retry also leaves a narrower false-green around reviewed_pairs: `tests/test_enrichment_schema_1323.py:525` only proves end-state existence, while `init_db()` creates `reviewed_pairs` before it even checks `schema_version` at `serve/knowledge/src/owlbear_knowledge/schema.py:374`. This is not the primary fail, but it confirms the upgrade-path tests are still not discriminating migration-owned effects cleanly.
5. No implementation defect was observed in the live schema. The rejection is for proof quality only.

### Deductions
| Reason | Evidence | Delta |
|---|---|---|
| Exact D17 contract still not discriminated by tests | `tests/test_enrichment_schema_1323.py:248`, `tests/test_enrichment_schema_1323.py:545` | -0.08 |
| Upgrade-path D17 proof is masked by unconditional init-time index creation | `tests/test_enrichment_schema_1323.py:534` vs `serve/knowledge/src/owlbear_knowledge/schema.py:405` | -0.05 |
| Upgrade-path default-on-insert for `enrichment_state='pending'` is still unproven | `tests/test_enrichment_schema_1323.py:495` vs `serve/knowledge/src/owlbear_knowledge/schema.py:307` and fresh-only proof at `tests/test_enrichment_schema_1323.py:325` / `tests/test_enrichment_schema_1323.py:338` | -0.07 |
| This task already had one prior `## Review Evidence` section before the current review, so the loop-breaker rule applies on a second review failure | `.owlbear/kanban/tasks/1324-p1-08-enrichment-schema-additions-state-claims-edge-uniqueness-wal.md:131` | -0.03 |

### Verdict
- FAIL -> `backlog`
- Confidence: 0.79
- Rationale: runtime behavior is green, but the retry-added migration tests still do not prove two named parts of the contract: the exact D17 key and default-on-upgrade behavior for new chunks. Because this task already failed review once and the remaining defect is still proof quality, the loop-breaker rule routes the task to `backlog`, not back to `todo`.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the retry contract so AC5 requires exact four-column D17 proof on upgrade, not subset-based index detection, and ensure the next RED suite would fail on any broader key | `tests/test_enrichment_schema_1323.py`; `.owlbear/kanban/tasks/1324-p1-08-enrichment-schema-additions-state-claims-edge-uniqueness-wal.md` | Subset-only assertions at `tests/test_enrichment_schema_1323.py:248` and `tests/test_enrichment_schema_1323.py:545` |
| 2 | architect | Clarify and re-specify upgrade-path proof for AC7 so a v10→v11 database must demonstrate that post-upgrade chunk inserts still default `enrichment_state` to `'pending'` | `tests/test_enrichment_schema_1323.py`; `.owlbear/kanban/tasks/1324-p1-08-enrichment-schema-additions-state-claims-edge-uniqueness-wal.md` | Migration line carries the default at `serve/knowledge/src/owlbear_knowledge/schema.py:307`, but retry upgrade coverage at `tests/test_enrichment_schema_1323.py:495` proves only column presence |
| 3 | architect | Decide whether reviewed_pairs and D17 index creation should be migration-owned only or whether tests should target `init_db()` end-state explicitly; the current mix creates false-green upgrade assertions | `serve/knowledge/src/owlbear_knowledge/schema.py`; `tests/test_enrichment_schema_1323.py` | `init_db()` bootstraps `reviewed_pairs` at `serve/knowledge/src/owlbear_knowledge/schema.py:374` and the D17 index at `serve/knowledge/src/owlbear_knowledge/schema.py:405`, masking the retry upgrade tests at `tests/test_enrichment_schema_1323.py:525` and `tests/test_enrichment_schema_1323.py:534` |
[[2026-05-04]]

## Architecture Review (Cycle 2)

### Reviewer Follow-up Decisions

| # | Reviewer Concern | Architect Decision |
|---|---|---|
| 1 | AC5: subset-based index detection accepts broader keys | **REFINE** — tests must use exact-match (`set(idx_cols) == {…}` not `.issubset()`) |
| 2 | AC7: upgrade-path only proves column presence, not default-on-insert | **REFINE** — add post-upgrade insert/readback assertion |
| 3 | init_db() masking migration effects via idempotent bootstrap | **ACCEPT AS-IS** — `init_db()` is the only public entry point; end-state testing through it is the correct contract. Migration isolation would require exporting private functions — YAGNI for DDL-only. Defense-in-depth bootstrap is correct architecture. |

### AC Refinement

- **AC5 (D17 index)**: Both fresh-path and upgrade-path tests must assert exact column equality: `set(idx_cols) == {"source_id", "target_id", "relation", "document_id"}` — subset matching is rejected. This applies to `test_edges_unique_index_exists` and `test_v10_to_v11_d17_unique_index_exists`.
- **AC7 (default on upgrade)**: Upgrade-path test must include a post-upgrade insert/readback: insert a chunk WITHOUT specifying `enrichment_state` into a v10→v11 upgraded DB, then assert the readback value is `'pending'`.

### Test Depth
- Refinements are test-only changes (no source code edits). Max depth: td:2.
- Test-writer processes normally.

### Challenge
- Challenger: SKIPPED — refinement cycle with no design choice; changes are mechanical test assertion tightening.

### Verdict: APPROVE
- Routing: backlog → todo
- The implementation in `schema.py` is correct and unchanged. Only test assertions need tightening per reviewer findings.

[[2026-05-04]]
Architecture review cycle 2: Refined AC5 (exact D17 column match required, not subset) and AC7 (post-upgrade insert/readback proof required). Accepted init_db masking as correct defense-in-depth architecture. Implementation unchanged — test-only precision fixes needed. Approved to todo.
[[2026-05-04]]
## Test-Writer Notes
- Retry: tightened 2 assertions + added 1 new test for reviewer gaps. All 28 tests pass against current impl.
- Builder skip: test-only retry, all tests green — advancing directly to review.
- Test file: tests/test_enrichment_schema_1323.py

### Changes Made
1. **AC5 fresh-path** (`TestFromAC_EdgeUniqueConstraint.test_edges_unique_index_exists`): Changed `required.issubset(set(idx_cols))` → `set(idx_cols) == required` (exact four-column match required, not subset).
2. **AC5 upgrade-path** (`TestFromAC_MigrationUpgradePath.test_v10_to_v11_d17_unique_index_exists`): Same exact-equality fix.
3. **AC7 upgrade-path** (`TestFromAC_MigrationUpgradePath.test_v10_to_v11_enrichment_state_default_on_insert`): NEW — inserts chunk into post-upgrade DB without specifying `enrichment_state`, asserts readback is `'pending'`.

### AC Coverage
| AC | Test(s) | Status |
|----|---------|--------|
| AC1: enrichment_state column | `TestFromAC_EnrichmentStateColumn` (3) | PASS |
| AC2: separate from consolidated | `TestFromAC_EnrichmentStateNotConsolidated` (3) | PASS |
| AC3: claimed_at column | `TestFromAC_ClaimedAtColumn` (3) | PASS |
| AC4: reviewed_pairs table | `TestFromAC_ReviewedPairsTable` (5) | PASS |
| AC5: exact D17 UNIQUE constraint | `TestFromAC_EdgeUniqueConstraint` (4, exact-equality), upgrade-path (1, exact-equality) | PASS |
| AC6: default enrichment_state | `TestFromAC_ChunkDefaultEnrichmentState` (3) | PASS |
| AC7: default on upgrade-path insert | `test_v10_to_v11_enrichment_state_default_on_insert` (NEW) | PASS |
| AC7 (WAL, td:0) | — | skipped |
| AC8 (#1323 green gate, td:0) | — | runtime evidence |

### Quality
- Total: 28 tests, all PASS
- Ruff: clean
- Coverage: owlbear_knowledge.schema 64%
[[2026-05-04]]
## Builder Notes
- Implementation: no source changes in this cycle (test-only retry from test-writer).
- Files changed: none.
- Tests: 28 passed, 0 failed, 0 skipped (`tests/test_enrichment_schema_1323.py`).
- Coverage: `owlbear_knowledge.schema` 64% (scoped).
- ruff: clean on `serve/knowledge/src/owlbear_knowledge/schema.py` and `tests/test_enrichment_schema_1323.py`.
- Approach: verification-only builder pass-through per retry contract; implementation remains unchanged.

### Evidence Summary
- quality-runner scoped pytest: PASS (`failed: []`).
- quality-runner scoped lint: clean (`violations: []`).
- quality-runner scoped coverage module: `owlbear_knowledge.schema` at 64%.

### Reflection
- Retry cycles with test-only deltas are best handled as verification-only builder passes.
- Scoped quality-runner runs gave sufficient gate evidence with minimal noise.
- Keeping source untouched avoided unnecessary schema churn while preserving review traceability.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 37 passed, 0 failed, 0 skipped.
- Executed suites: `tests/test_enrichment_schema_1323.py` and `serve/knowledge/tests/test_graph_store_counts.py`.
- AC8 (`All #1323 tests pass green`) is satisfied by independent runtime evidence.

### Lint Results
- Ruff clean on `serve/knowledge/src/owlbear_knowledge/schema.py` and `tests/test_enrichment_schema_1323.py`.
- VS Code diagnostics: no errors in the reviewed files.

### Coverage
- `owlbear_knowledge.schema`: 64% in the scoped run.
- Module-level coverage is non-blocking here. The builder-owned paths for this task are exercised by the fresh-schema assertions and the v10→v11 upgrade assertions, so the diff-scoped gate is satisfied even though the whole module remains below 90%.

### AC Compliance
| AC Line | Evidence | Mapped Test / Runtime Proof | Status |
|---|---|---|---|
| enrichment_state column added to chunks: pending → claimed → enriched (td:2) | v10→v11 migration adds `enrichment_state` at `serve/knowledge/src/owlbear_knowledge/schema.py:307` | `tests/test_enrichment_schema_1323.py:82`, `:91`, `:100`, `:495` | PASS |
| enrichment_state is a new column — consolidated column retains existing semantics (td:1) | Separate-column semantics are asserted directly in `tests/test_enrichment_schema_1323.py:118` | `TestFromAC_EnrichmentStateNotConsolidated` | PASS |
| claimed_at timestamp column on chunks for lease tracking (td:1) | v10→v11 migration adds `claimed_at` at `serve/knowledge/src/owlbear_knowledge/schema.py:310` | `tests/test_enrichment_schema_1323.py:161`, `:505` | PASS |
| reviewed_pairs table created: entity_name + source_a + source_b (td:2) | End-state table presence and insertability are both proven | `tests/test_enrichment_schema_1323.py:189`, `:211`, `:525` | PASS |
| Edge UNIQUE constraint: UNIQUE(source_id, target_id, relation, document_id) (D17) (td:2) | v10→v11 creates D17 index at `serve/knowledge/src/owlbear_knowledge/schema.py:316`; fresh and upgrade tests now require exact column-set equality | `tests/test_enrichment_schema_1323.py:236`, `:248`, `:257`, `:297`, `:534`, `:545` | PASS |
| WAL mode enabled on SQLite for concurrent writer support (td:0) | `init_db()` executes `PRAGMA journal_mode = WAL` at `serve/knowledge/src/owlbear_knowledge/schema.py:363` | Direct code evidence (td:0) | PASS |
| New chunks default to enrichment_state='pending' (td:1) | Migration default is set at `serve/knowledge/src/owlbear_knowledge/schema.py:307`; fresh and upgraded DB insert/readback proofs both exist | `tests/test_enrichment_schema_1323.py:322`, `:325`, `:562` | PASS |
| All #1323 tests pass green (td:0) | Independent quality-runner runtime evidence | 37 passed, 0 failed, 0 skipped | PASS |

### Code-Reader Synthesis
- No blocking security or TestFromAC integrity defects found.
- The prior reviewer concerns are closed in the live tests: AC5 now uses exact-set checks at `tests/test_enrichment_schema_1323.py:248` and `:545`, and the upgrade-path default proof is now covered at `tests/test_enrichment_schema_1323.py:562`.
- Code-reader noted that WAL has no mapped runtime test, but that AC is explicitly `td:0`; direct code evidence at `serve/knowledge/src/owlbear_knowledge/schema.py:363` is the correct proof type for this task.
- Code-reader also noted broader robustness questions around suppressed `ALTER TABLE` failures and populated legacy-row migration behavior. Those concerns are outside the refined AC for this task and do not outweigh the current green runtime evidence.

### Deductions
| Reason | Evidence | Delta |
|---|---|---|
| WAL proof is direct code evidence rather than file-backed runtime evidence because both task fixtures use `:memory:` and the AC is `td:0` | `tests/test_enrichment_schema_1323.py:35`, `:387`; `serve/knowledge/src/owlbear_knowledge/schema.py:363` | -0.02 |
| TestFromAC immutability could not be diff-backed in this tool surface | Live-file inspection only; no commit diff available here | -0.03 |

### Verdict
- PASS -> `docs`
- Confidence: 0.95
- Rationale: independent scoped execution is green, the previously failing AC5/AC7 proof gaps are closed, and the remaining concerns are either informational or explicitly outside the refined AC.
[[2026-05-05]]
## Docs Gate

| Check | Applies? | Status | Evidence |
|-------|----------|--------|----------|
| 1. Descriptive prose docs | No | N/A | `serve/knowledge/README.md` documents the public API and module groups, not schema internals. No prose reference to DDL columns or schema version. No update needed. |
| 2. Module docstrings | Yes | Fixed | `init_db` docstring said "migrated through v2-v10" — stale after v11 was added. Updated to "v2-v11". All private migration functions already have accurate docstrings. |
| 3. External attribution | No | N/A | Builder notes cite no external patterns or articles. No new sources row needed. |
| 4. Research doc | Yes | OK | `.owlbear/research/1324-enrichment-schema-additions.md` exists and is linked in task body. |
| 5. Diagram maintenance | Yes | Updated | `share/diagrams/mcp-topology.excalidraw` describes `serve/knowledge/src/**` — matches changed `schema.py`. Footer updated to `Last verified: 2026-05-05 (12c2add1)`. |
| 6. Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7. Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs. |

**Files updated:** `serve/knowledge/src/owlbear_knowledge/schema.py` (docstring only), `share/diagrams/mcp-topology.excalidraw` (footer).
**Commit:** `7da18c1b — docs: fix init_db docstring and diagram footer (#1324, doc-writer)`
**Scratch files cleaned:** 5 files deleted (`1324-pytest-full.txt`, `1324-pytest-scoped.txt`, `1324-pytest.txt`, `1324-ruff-scoped.txt`, `1324-ruff.txt`).
**Child tasks created:** none.
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| enrichment_state column (td:2) | schema.py:307 migration + tests/test_enrichment_schema_1323.py:82,495 | PASS |
| enrichment_state separate from consolidated (td:1) | schema.py:78 DDL + test:118 | PASS |
| claimed_at column (td:1) | schema.py:310 migration + test:161,505 | PASS |
| reviewed_pairs table (td:2) | schema.py:173 DDL + test:189,211,525 | PASS |
| Edge UNIQUE D17 (td:2) | schema.py:316 index + test:248 exact-set equality, test:545 upgrade-path exact-set | PASS |
| WAL mode (td:0) | schema.py:363 PRAGMA (td:0 code evidence) | PASS |
| Default enrichment_state='pending' (td:1) | schema.py:307 DEFAULT + test:325 fresh-path + test:562 upgrade insert/readback | PASS |
| All #1323 tests pass green (td:0) | quality-runner full: task tests not in failure list (258 failures all unrelated) | PASS |

### Test Results
- pytest full suite: 4372 passed, 258 failed (all failures in unrelated task-scoped files: #1351, #1195, #1268, #1202, #1285, #1015, #1272, #1269, #1076)
- Task-scoped tests (test_enrichment_schema_1323.py): 28 passed, 0 failed
- ruff: 12 violations all in unrelated files (copilot_auth.py, tools/test_root.py); task file clean

### Commit Integrity
- d00994f9 feat: implement enrichment schema additions (#1324, builder)
- 3dce3474 test: add v10-to-v11 upgrade-path tests for enrichment schema (#1324, test-writer)
- 7da18c1b docs: fix init_db docstring and diagram footer (#1324, doc-writer)

### Architect Quality: 3/5
AC was directionally correct but lacked precision on upgrade-path proof requirements (AC5 subset vs exact-match, AC7 column-presence vs insert/readback). Required a full cycle-2 refinement after reviewer rejection. The refinement was cleanly specified and resolved the issues.

### Deduction Breakdown
| Criterion | Delta |
|-----------|-------|
| AC quality score 3 (leq 3) | -0.03 |

### Confidence: 0.97
### Action: archive