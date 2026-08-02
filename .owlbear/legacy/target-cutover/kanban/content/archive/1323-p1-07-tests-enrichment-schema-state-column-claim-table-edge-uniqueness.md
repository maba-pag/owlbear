---
id: 1323
title: 'P1-07: Tests — Enrichment schema (state column, claim table, edge uniqueness)'
status: archived
priority: medium
created: 2026-05-04T05:48:50.064935+00:00
updated: 2026-05-04T14:53:08.877898+00:00
tags:
- phase-1
- scope:knowledge
- knowledge
- test
parent: 1316
depends_on:
- 1320
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Brief: see parent #1316 → `.owlbear/briefs/draft-knowledge-activation/brief.md` (§4.4)

## Acceptance Criteria

- [ ] Tests verify enrichment_state column on chunks table (values: pending, claimed, enriched) (td:1)
- [ ] Tests verify enrichment_state does NOT reuse the existing consolidated column (td:1)
- [ ] Tests verify claimed_at timestamp column on chunks table for lease tracking (td:1)
- [ ] Tests verify reviewed_pairs table: entity_name + source_a + source_b (td:1)
- [ ] Tests verify edge UNIQUE constraint: UNIQUE(source_entity, target_entity, relation, document_id) (D17) (td:1)
- [ ] Tests verify new chunks default to enrichment_state='pending' (td:1)

## Scope

- **In scope:** Schema addition tests — columns, tables, constraints, defaults
- **Out of scope:** Worker claim logic (Layer 2), enrichment tool behavior (Layer 2)
[[2026-05-04]]
## Research

- Research doc: .owlbear/research/1323-enrichment-schema-tests.md
- Sources: 4 studied, 4 high-relevance
- Recommendation: Direct schema introspection tests via PRAGMA statements after init_db() on in-memory SQLite (confidence: 0.92)
- Follow-up tasks created: none (TDD pair #1324 already exists)
- Decision requests: none

## Key Findings

Current schema v10 has: `consolidated INTEGER DEFAULT 0` on chunks (legacy), NO document_id on edges, NO UNIQUE constraint on edges, NO reviewed_pairs table. All 6 AC map to clean PRAGMA-based schema assertions that will FAIL until #1324 adds the schema migration.

Test pattern matches sibling task #1319 — fixture uses `sqlite3.connect(":memory:")` + `init_db(conn)`.

## Challenge Results
- Challenger: SKIPPED — trivial TDD RED test task, all specs from approved brief §4.4
[[2026-05-04]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Pure TDD RED test task — schema introspection assertions only |
| Interface clarity | PASS | AC specifies exact columns, tables, constraints, defaults. Refined AC3 to add table name. |
| Dependency correctness | PASS | #1320 archived (done). TDD pair #1324 depends on this correctly. |
| Module layering | PASS | Tests import from owlbear_knowledge.schema — correct direction |
| TDD compliance | PASS | This IS the RED phase; #1324 is GREEN |
| KISS/YAGNI | PASS | Minimal scope — 6 PRAGMA-based assertions |
| Premise challenge | PASS | Tests required for enrichment schema additions per brief §4.4 |
| Pattern consistency | PASS | Follows sibling #1319 pattern: sqlite3 in-memory + init_db() |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Knowledge domain only |

### Challenge Results
- Challenger: SKIPPED — trivial TDD RED test task, AC derived directly from approved brief §4.4, all assertions are mechanical PRAGMA introspection
- Architect response: accepted (low-value challenge for schema test stubs)

### Test Depth
- Max depth: 1
- Test-writer: SKIP (task tagged `test` — pass-through)

### Refinement Applied
- AC3: added "on chunks table" to disambiguate target table for claimed_at column
- All AC lines annotated with (td:1)

### Verdict: APPROVE
### Action Taken: Refined AC3, added test-depth annotations, advanced to todo
[[2026-05-04]]
## Test-Writer Notes

**Test file:** `tests/test_enrichment_schema_1323.py`

**Classes:**
- `TestFromAC_EnrichmentStateColumn` — 3 tests (AC1)
- `TestFromAC_EnrichmentStateNotConsolidated` — 3 tests (AC2)
- `TestFromAC_ClaimedAtColumn` — 3 tests (AC3)
- `TestFromAC_ReviewedPairsTable` — 5 tests (AC4)
- `TestFromAC_EdgeUniqueConstraint` — 4 tests (AC5)
- `TestFromAC_ChunkDefaultEnrichmentState` — 3 tests (AC6)

**Total: 21 tests, all FAIL** (confirmed via pytest run — exit code 1, 21 failed, 0 passed)

**Strategy:** Direct schema introspection via `PRAGMA table_info()`, `PRAGMA index_list()`, `PRAGMA index_info()` on in-memory SQLite after `init_db()`. Pattern follows sibling #1319. No mocking needed.

**AC Coverage:**

| AC | Tests | Status |
|----|-------|--------|
| AC1: enrichment_state column on chunks | 3 | ❌ FAIL |
| AC2: enrichment_state separate from consolidated | 3 | ❌ FAIL |
| AC3: claimed_at column on chunks | 3 | ❌ FAIL |
| AC4: reviewed_pairs table + 3 columns | 5 | ❌ FAIL |
| AC5: UNIQUE(source_id, target_id, relation, document_id) on edges | 4 | ❌ FAIL |
| AC6: chunks default enrichment_state='pending' | 3 | ❌ FAIL |

**Ruff:** clean (exit 0)
[[2026-05-04]]
## Builder Notes

No source edits were made for #1323 because this is a RED test-spec task (tests-only scope).

Files changed:
- none

Evidence:
- `uv run pytest tests/test_enrichment_schema_1323.py -q --tb=short`
  - Result: `21 failed, 0 passed`
  - Failure pattern matches AC intent: schema elements not yet implemented (`enrichment_state`, `claimed_at`, `reviewed_pairs`, edge uniqueness/default expectations).
- `uv run ruff check tests/test_enrichment_schema_1323.py`
  - Result: clean (`All checks passed!`)

Summary:
- RED verification confirmed.
- Test task is ready for review and paired GREEN implementation task #1324.
[[2026-05-04]]
## Review Evidence
### Test Results
- quality-runner scoped: `0 passed, 21 failed, 0 skipped` in `tests/test_enrichment_schema_1323.py`.
- Failure signature is clean RED, not harness/config noise: the suite fails only on the schema additions that do not exist yet in `serve/knowledge/src/owlbear_knowledge/schema.py` (`chunks` still exposes only the legacy `consolidated` column at lines 77-85; `edges` still exposes `source_id`/`target_id` without the new uniqueness surface at lines 64-71; `init_db()` still installs the current v10 schema at lines 318, 333-342).
- quality-runner failure groups matched task intent exactly: missing `enrichment_state`, missing `claimed_at`, missing `reviewed_pairs`, missing `document_id`/edge uniqueness, and missing default-state behavior.

### Lint
- quality-runner: `ruff check tests/test_enrichment_schema_1323.py` clean.
- VS Code diagnostics: no errors in `tests/test_enrichment_schema_1323.py`.

### Coverage
- quality-runner: `owlbear_knowledge.schema` at 46% module coverage.
- Informational only for this RED pass-through review. The suite is intentionally failing before GREEN schema work exists, so module coverage is not a blocking gate here.

### Critical Checks
- TestFromAC integrity: no evidence of weakened or removed assertions in the live `TestFromAC_*` classes. Builder notes state `Files changed: none`; this is also the first review cycle (no prior `## Review Evidence` section in the task file).
- Test quality: STRONG. Assertions are discriminating, schema-focused, and would fail on the intended regressions rather than on generic truthiness.
- Security/data safety/necessity: N/A for this tests-only schema-introspection task. No new runtime surface or dependency introduced.
- Builder process quality: CLEAN. Single pass-through RED verification, no retry loop.

### AC Compliance
| AC Line | Evidence | Mapped Test(s) | Status |
|---------|----------|----------------|--------|
| AC1 — task line 27: enrichment_state column on chunks with pending/claimed/enriched states | Brief lines 86, 91-93 require `enrichment_state` on `chunks` and the `pending -> claimed -> enriched` workflow. Tests assert column presence/type/default at `tests/test_enrichment_schema_1323.py:82, 85, 91, 98`; explicit claimed/enriched round-trips are asserted at lines 320 and 335. quality-runner reports all of these as failing for the missing column, which is the expected RED signal. | `TestFromAC_EnrichmentStateColumn`; `test_insert_chunk_with_explicit_claimed_state`; `test_insert_chunk_with_explicit_enriched_state` | PASS |
| AC2 — task line 28: enrichment_state does not reuse consolidated | Brief line 86 explicitly says `Replaces nothing — consolidated column retains its existing semantics.` Tests require both columns to coexist and be structurally distinct at `tests/test_enrichment_schema_1323.py:112, 115, 125, 135`. Current schema still defines only `consolidated` on `chunks` at `schema.py:77-85`, so the suite fails for the intended reason. | `TestFromAC_EnrichmentStateNotConsolidated` | PASS |
| AC3 — task line 29: claimed_at timestamp column on chunks | Brief lines 87, 91, 93 require a `claimed_at` lease timestamp tied to chunk claiming/reset. Tests assert column presence/type/null default at `tests/test_enrichment_schema_1323.py:153, 156`. quality-runner reports the three AC3 failures as missing `claimed_at`, matching the contract. | `TestFromAC_ClaimedAtColumn` | PASS |
| AC4 — task line 30: reviewed_pairs table with entity_name + source_a + source_b | Brief lines 88, 96-97 require `reviewed_pairs` for dismissed consolidation pairs. Tests assert table existence, each required column, and a real insert/read path at `tests/test_enrichment_schema_1323.py:181, 184, 189, 195, 199, 203`. quality-runner reports all five failures against the absent table, which is the intended RED behavior. | `TestFromAC_ReviewedPairsTable` | PASS |
| AC5 — task line 31: edge uniqueness with document provenance | Brief line 44 and D17 line 234 require provenance-aware edge uniqueness; brief line 92 spells this as `UNIQUE(source_entity, target_entity, relation, document_id)`. The live knowledge schema and surrounding codebase use `source_id` / `target_id` for edge endpoints (`schema.py:66-67`, broad repo usage), and the research artifact for this task also anchored AC5 as `UNIQUE(source_id, target_id, relation, document_id)` at `.owlbear/research/1323-enrichment-schema-tests.md:14`. Tests assert `document_id` presence, unique-index composition, duplicate rejection, and different-document allowance at `tests/test_enrichment_schema_1323.py:220, 223, 228, 249, 277`. I am treating the naming drift as equivalent live vocabulary rather than a blocking AC miss. | `TestFromAC_EdgeUniqueConstraint` | PASS |
| AC6 — task line 32: new chunks default to enrichment_state='pending' | Brief line 86 and the lease-flow lines 91-93 imply a default pending state before claim/enrich transitions. Tests assert default `pending` plus explicit `claimed` / `enriched` persistence at `tests/test_enrichment_schema_1323.py:300, 303, 320, 335`. quality-runner reports the three AC6 failures as missing `enrichment_state`, which is the correct RED signature. | `TestFromAC_ChunkDefaultEnrichmentState` | PASS |

### Deductions
- `-0.03` Git-level immutability / dirty-tree contamination could not be independently checked in this tool surface because no shell/git-status capability was available. Builder notes reported `Files changed: none`, and the live test file shows no weakening signal, but this remains a small confidence deduction.
- `-0.02` AC5 wording drift between the task/brief (`source_entity` / `target_entity`) and the established repo/test/research vocabulary (`source_id` / `target_id`). I treated this as non-blocking naming drift after verifying actual repo usage.

### Verdict
- PASS -> docs
- Confidence: `0.92`

### Action
- Advance to docs. No blocking implementation defect or test-proof gap is traceable to the current ratified AC for this RED schema-spec task.
[[2026-05-04]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | RED test-only task; no behavior, API, CLI, config, or package structure changes |
| 2 | Module docstrings | No | N/A | No source `.py` files created or modified; only `tests/test_enrichment_schema_1323.py` |
| 3 | External attribution | No | N/A | All 4 research sources are internal files (schema.py, brief.md, sibling test, existing fixture) |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1323-enrichment-schema-tests.md` exists and is linked in task body |
| 5 | Diagram maintenance (describes match) | No | N/A | `mcp-topology.excalidraw` describes `serve/knowledge/src/**` but no source files changed |
| 6 | Explicit diagram creation | No | N/A | None requested in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_enrichment_schema_1323.py | OUT | N/A — test file, not docstrings/README/research doc |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1323-*` files existed)
[[2026-05-04]]
## Audit

### AC Verification
| AC | Evidence | Status |
|----|----------|--------|
| AC1: enrichment_state column on chunks | Tests at L82-98 assert column presence/type/default via PRAGMA. 21 RED failures confirm schema not yet present. | PASS |
| AC2: enrichment_state separate from consolidated | Tests at L112-135 assert both columns coexist. Fails because enrichment_state missing. | PASS |
| AC3: claimed_at column on chunks | Tests at L153-170 assert column presence/type/null default. Clean RED. | PASS |
| AC4: reviewed_pairs table | Tests at L181-203 assert table existence + 3 columns. Fails because table absent. | PASS |
| AC5: edge UNIQUE constraint | Tests at L220-277 assert document_id + uniqueness index. Clean RED. | PASS |
| AC6: default enrichment_state='pending' | Tests at L300-335 assert default + explicit states. Clean RED. | PASS |

### Test Results
- Scoped: 21 failed, 0 passed (correct RED state)
- Full suite: 427 Python failures, 13 frontend failures — ALL pre-existing from other RED-phase tasks (1325, 1266, engine accessor, Shell 966/1227). This task changed NO source files, cannot have caused regressions.
- Lint: ruff clean on task file

### AC Quality Score: 5/5
Specific columns, tables, constraints, and defaults. Clear PRAGMA-based verification path. No ambiguity.

### Deductions
- -.02: Test file `tests/test_enrichment_schema_1323.py` is UNTRACKED (not committed by upstream agents). Process concern noted.

### Confidence: 0.98
### Action: ARCHIVE