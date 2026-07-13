---
id: 1586
title: 'P1-02: Knowledge schema constraint enforcement'
status: archived
priority: medium
created: 2026-05-15T16:24:24.505992+00:00
updated: 2026-05-16T06:29:24.912129+00:00
tags:
  - phase-1
  - scope:knowledge
  - type:build
  - db-integrity
  - hardening
parent: 1580
depends_on:
  - 1585
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
Parent: #1580

Scope:
- In scope: Add schema migration v12→v13 that rebuilds `entities` and `edges` tables with `document_id TEXT NOT NULL`, handle pre-existing NULL rows and transitively-orphaned edges during migration, bump `_SCHEMA_VERSION` to 13, verify existing write paths (`store_chunks`, `store_extractions`, `delete_document_data`) still succeed under enforced constraints.
- Out of scope: Audit tooling, vector payload linkage checks, new indexes beyond FK enforcement, scope_transfer (does not exist in codebase).

Acceptance Criteria:
AC-1: `_SCHEMA_VERSION` constant is bumped to 13; `init_db()` continues to execute `PRAGMA foreign_keys = ON` (pre-existing behavior preserved); `_apply_migrations` dispatch tuple includes the new (13, _migrate_v12_to_v13) entry.
AC-2: Migration `_migrate_v12_to_v13` (a) deletes `entities` rows where `document_id IS NULL`, (b) deletes `edges` rows where `document_id IS NULL` or where `source_id`/`target_id` references no existing entity after step (a), (c) rebuilds `entities` and `edges` tables with `document_id TEXT NOT NULL` constraint preserving all remaining data, (d) updates `schema_version` row to 13.
AC-3: On a post-migration database: `DocumentStore.store_chunks()` with a valid `document_id` referencing an existing `documents` row completes without `sqlite3.IntegrityError`; `DocumentStore.store_extractions()` for the same document (producing at least one entity and one edge) completes without error; `DocumentStore.delete_document_data()` removes all associated rows (edges before entities, chunks before document) without FK violation.

Proof bundle: behavioral

## Architect Note (updated 2026-05-16)
### Current code state (verified against live repo)
- `_SCHEMA_VERSION = 12` — already bumped by re-attributed commit `4751a74b`
- `PRAGMA foreign_keys = ON` — already in `init_db()` (line ~358)
- DDL for `entities` and `edges` already has `document_id TEXT NOT NULL` — applies to fresh databases only
- Migration `_migrate_v11_to_v12` already exists — drops bookmarks/consolidations tables only
- The v11→v12 migration does NOT rebuild entities/edges with NOT NULL

### Why v12→v13 (not modifying v11→v12)
Databases that already ran v11→v12 have `schema_version = 12`. The `_apply_migrations` dispatcher skips migrations where `current >= target_version`. Modifying v11→v12 would never execute on already-v12 databases. A new v12→v13 migration cleanly covers all existing databases.

### Transitive cleanup requirement
When deleting entities with NULL document_id, edges that reference those entities via `source_id`/`target_id` FK become invalid. AC-2(b) requires cleaning these transitively-orphaned edges before the rebuild step, which re-creates the FK constraints.

### Builder guidance
- DO NOT modify `_migrate_v11_to_v12` — leave existing bookmarks/consolidation drop in place
- ADD `_migrate_v12_to_v13` following the existing migration pattern
- Table rebuild uses SQLite pattern: CREATE new table, INSERT FROM old, DROP old, RENAME
- The rebuild step re-creates `REFERENCES entities(id)` on edges.source_id and edges.target_id
- `delete_document_data` already deletes in correct FK order — verify, don't rewrite

[[2026-05-16T06:42:54+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One domain (knowledge schema), one concern (migration constraint enforcement) |
| Interface clarity | PASS | AC names specific functions, migration steps, and expected behaviors |
| Dependency correctness | PASS | #1585 (archived/completed); no missing dependencies |
| Module layering | PASS | All changes within serve/knowledge package |
| TDD compliance | PASS | Test-writer will process before builder (behavioral bundle) |
| KISS/YAGNI | PASS | Minimal scope — single migration function, no new abstractions |
| Premise challenge | PASS | FK enforcement needed to prevent orphan data; entities/edges nullable in migrated DBs |
| Pattern consistency | PASS | Follows existing migration pattern (_migrate_vN_to_vM, registered in dispatch tuple) |
| Security surface | PASS | Internal SQLite constraints only, no new system boundaries |
| Single domain | PASS | Knowledge module only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| _migrate_v12_to_v13 entity deletion | Edges orphaned by entity deletion | IntegrityError on rebuild | Yes (AC-2b) | Migration failure if not handled |
| store_extractions with empty document_id | NOT NULL violation on entities/edges | IntegrityError | No (caller must provide) | Write path rejection |
| delete_document_data wrong order | FK violation on entity/document deletion | IntegrityError | Already handled | Cascade delete failure |

### Design Diverge
- Trigger: evaluated (v11→v12 modification vs v12→v13 new migration)
- Decision: v12→v13 — only valid approach because `_apply_migrations` skips where `current >= target_version`; databases already at v12 would miss a rewritten v11→v12
- No parallel subagent dispatch needed — one approach is clearly correct

### Challenge Results
- Challenger: reconsider (confidence 0.28)
- Valid findings addressed:
  1. Migration version ceiling (critical) → rewrote as v12→v13 instead of v11→v12
  2. Transitive orphan cleanup → added AC-2(b) explicit requirement for orphaned edges
  3. AC-3 vague "source-linked" → reworded to specify exact preconditions
  4. Stale architect note → replaced with accurate current-state documentation
  5. scope_transfer reference → removed from scope (does not exist in codebase)
- Architect response: accepted all findings; REFINE applied before approval

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVED (after REFINE)
### Action Taken: Rewrote ACs to use v12→v13 migration path, added transitive edge cleanup, tightened AC-3 preconditions, updated architect note with accurate code state. Advanced to todo.

[[2026-05-16T07:00:44+02:00]]
## Test-Writer Notes

**Test file:** `tests/test_schema_constraint_enforcement_1586.py`

**Classes:**
- `TestFromAC_SchemaVersion` — 4 tests (AC-1)
- `TestFromAC_MigrationV12ToV13` — 10 tests (AC-2)
- `TestFromAC_WritePathsPostMigration` — 3 tests (AC-3)

**Tests per category:**
- Happy path: 5 (preserves valid entities, valid edges, store_chunks, store_extractions, delete cascade)
- Edge/boundary: 3 (empty-string document_id, orphan via target_id, orphan via source_id)
- Error/constraint: 4 (NOT NULL on entities, NOT NULL on edges, schema version mismatch x2)
- Structural: 5 (version constant, init_db schema, init_db FK, dispatch table, migration runs)

**Total: 17 tests — all FAIL confirmed by quality-runner**

**AC coverage:**
| AC | Tests |
|----|-------|
| AC-1: _SCHEMA_VERSION = 13 | test_schema_version_constant_is_13 |
| AC-1: init_db writes v13 | test_fresh_db_schema_version_is_13_after_init_db, test_init_db_enables_foreign_keys_and_reaches_v13 |
| AC-1: dispatch includes (13, _migrate_v12_to_v13) | test_apply_migrations_dispatches_v12_to_v13 |
| AC-2a: delete NULL entities | test_migration_deletes_entities_with_null_document_id, test_migration_preserves_entities_with_non_null_document_id, test_migration_preserves_entities_with_empty_string_document_id |
| AC-2b: delete NULL edges + orphans | test_migration_deletes_edges_with_null_document_id, test_migration_deletes_transitively_orphaned_edges, test_migration_deletes_edges_orphaned_via_target_id, test_migration_preserves_valid_edges |
| AC-2c: NOT NULL enforced after rebuild | test_migration_enforces_not_null_on_entities_document_id, test_migration_enforces_not_null_on_edges_document_id |
| AC-2d: schema_version = 13 | test_migration_updates_schema_version_to_13 |
| AC-3: store_chunks | test_store_chunks_succeeds_with_valid_document_id_on_migrated_db |
| AC-3: store_extractions | test_store_extractions_entity_and_edge_succeed_on_migrated_db |
| AC-3: delete_document_data | test_delete_document_data_removes_all_rows_without_fk_violation |

**Lint:** ruff clean (exit 0)
**Fail evidence:** quality-runner: 17 failed, 0 passed, 0 skipped

[[2026-05-16T07:19:54+02:00]]
## Builder Notes
Files changed:
- serve/knowledge/src/owlbear_knowledge/schema.py

Implementation summary:
- Bumped `_SCHEMA_VERSION` from 12 to 13.
- Added `_migrate_v12_to_v13` migration.
- Migration now:
  - Deletes `entities` rows with `document_id IS NULL`.
  - Deletes `edges` rows with `document_id IS NULL`.
  - Deletes `edges` that would become orphaned because `source_id`/`target_id` points to a NULL-document entity being removed.
  - Deletes remaining orphaned edges (missing `source_id`/`target_id` targets).
  - Rebuilds `entities` and `edges` tables with `document_id TEXT NOT NULL` and preserved FK structure.
  - Re-creates `idx_edges_d17_unique`.
  - Updates `schema_version` to 13.
- Registered migration dispatch entry `(13, _migrate_v12_to_v13)` in `_apply_migrations`.
- Preserved existing `init_db()` foreign key behavior (`PRAGMA foreign_keys = ON`) and existing write-path code.

RED verification (quality-runner):
- tests/test_schema_constraint_enforcement_1586.py
- Result before implementation: 17 failed / 0 passed (expected RED).

GREEN verification (quality-runner):
- tests/test_schema_constraint_enforcement_1586.py
- lint paths: serve/knowledge/src/owlbear_knowledge/schema.py, tests/test_schema_constraint_enforcement_1586.py
- coverage module: owlbear_knowledge.schema
- Final result: 17 passed / 0 failed / 0 skipped
- Lint: clean
- Coverage: owlbear_knowledge.schema 58%

Module-level durable test file check:
- No canonical serve/knowledge/tests schema durable file found for this module path in current workspace; skip recorded per workflow guidance.

Fixes applied during GREEN loop:
- Fixed migration delete ordering to avoid FK violations when removing entities referenced by edges.
- Applied FK-safe rebuild flow (disable FK checks during table swap, restore afterward) to prevent rebuild-time FK conflicts.

Commit:
- e27e3e84
- feat: enforce v13 knowledge schema constraints (task 1586)

[[2026-05-16T07:44:10+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation (one line): PASS #1586 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: task-scoped quality-runner RED recorded 17 failed before implementation; GREEN recorded 17 passed / 0 failed / 0 skipped on `tests/test_schema_constraint_enforcement_1586.py`, lint clean, and coverage summary present for `owlbear_knowledge.schema`.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/knowledge/src/owlbear_knowledge/schema.py:19` sets `_SCHEMA_VERSION = 13`; `serve/knowledge/src/owlbear_knowledge/schema.py:423` registers `(13, _migrate_v12_to_v13)`; `serve/knowledge/src/owlbear_knowledge/schema.py:448` preserves `PRAGMA foreign_keys = ON` in `init_db()` | `tests/test_schema_constraint_enforcement_1586.py:137`; `tests/test_schema_constraint_enforcement_1586.py:145`; `tests/test_schema_constraint_enforcement_1586.py:154` | pass |
| AC-2 | `serve/knowledge/src/owlbear_knowledge/schema.py:320-404` defines `_migrate_v12_to_v13`; deletes NULL-document edges at `:327`; deletes edges referencing NULL-document entities before entity delete at `:328-333`; deletes NULL-document entities at `:335`; deletes remaining orphaned edges at `:337-341`; rebuilds `entities_v13` and `edges_v13` with `document_id TEXT NOT NULL` at `:346-398`; updates `schema_version` to 13 at `:404` | `tests/test_schema_constraint_enforcement_1586.py:171`; `tests/test_schema_constraint_enforcement_1586.py:180`; `tests/test_schema_constraint_enforcement_1586.py:219`; `tests/test_schema_constraint_enforcement_1586.py:240`; `tests/test_schema_constraint_enforcement_1586.py:290`; `tests/test_schema_constraint_enforcement_1586.py:311`; `tests/test_schema_constraint_enforcement_1586.py:323` | pass |
| AC-3 | `serve/knowledge/src/owlbear_knowledge/document_store.py:90-118` inserts chunks against a valid document id; `serve/knowledge/src/owlbear_knowledge/document_store.py:207-256` stamps `document_id` onto entity/edge writes; `serve/knowledge/src/owlbear_knowledge/graph_store.py:198-216` persists edge `document_id`; `serve/knowledge/src/owlbear_knowledge/document_store.py:287-294` deletes edges before entities, then chunks/status/document | `tests/test_schema_constraint_enforcement_1586.py:348`; `tests/test_schema_constraint_enforcement_1586.py:360`; `tests/test_schema_constraint_enforcement_1586.py:386` | pass |
- 3-item checklist result:
  - AC->code mapping: all AC lines satisfied on direct inspection.
  - Test->AC alignment: task-scoped tests would fail on the targeted contract breaks (version/dispatch/FK enablement, NULL/orphan cleanup, NOT NULL enforcement, and post-migration write/delete paths).
  - Proof sufficiency: adequate for this behavioral bundle; no blocking false-green gap found on the changed v13 migration surface.
- Challenger cross-check: `reconsider` (0.74) based on adjacent schema-suite drift from task #1583. Reviewed and not blocking here because that red surface is already isolated to a separate backlog task with its own contract drift; it does not contradict task #1586 ACs or the builder’s scoped proof.
- Safety & security: no new dependency, credential, injection, or data-handling issue identified in the touched schema/write-path surface.

## Observations
- `init_db()` docstring still says automatic migration runs through `v2-v12` at `serve/knowledge/src/owlbear_knowledge/schema.py:442`; that text is stale after the v13 bump but does not affect runtime behavior.
- AC-3 proof is appropriately smoke-level for this task: it proves post-migration writes and deletion complete without integrity failures on the exercised path, while persistence semantics remain supported by the direct `DocumentStore`/`GraphStore` code inspection.

[[2026-05-16T08:09:40+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README verification | Yes | N/A (no drift) | `serve/knowledge/README.md` has no schema version mentions; no doc drift from the v12→v13 bump. Stale docstring in `schema.py:442` was task-caused (reviewer flagged it): "migrated through v2-v12" → fixed to "v2-v13". |
| 2 | External attribution | No | N/A | Internal SQLite migration only; no external sources. |
| 3 | Research doc | No | N/A | No research artifact referenced in task body. |
| 4 | Deletion detection | No | N/A | No files deleted; only `schema.py` modified. |

### Verification Layers
- Layer 1 — grep: `v2-v` search confirms single match "through v2-v13" at line 442. Remaining `v12` hits are function names (`_migrate_v11_to_v12`, `_migrate_v12_to_v13`) — accurate. No stale references remain.
- Layer 2 — editorial: `serve/knowledge/README.md` is coherent and makes no schema-version claims. The fix aligns the docstring with current behavior.

### Files Updated
- `serve/knowledge/src/owlbear_knowledge/schema.py` — docstring fix only

### Commit
- `18f37a12` docs: fix stale init_db docstring v12→v13 (task 1586)

### Scratch Cleanup
- No `.owlbear/scratch/1586-*` files existed.

[[2026-05-16T08:29:24+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 6486 passed, 266 failed (all in unrelated domains: cockpit_view, ideation_diagram, server, engine_accessor_migration). Zero knowledge/schema failures. Task-scoped 17/17 passed.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (only serve/knowledge/src/owlbear_knowledge/schema.py changed, within knowledge domain)
- purpose match: PASS (v12 to v13 migration with NOT NULL enforcement matches AC scope exactly)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 5/5
ACs highly specific: AC-1 names exact constant/function/dispatch tuple; AC-2 has 4 sub-steps (a-d) covering NULL deletion, transitive orphan cleanup, table rebuild, version update; AC-3 specifies preconditions and expected behaviors. Challenger cycle improved quality further (v12 to v13 path correction, transitive cleanup addition, tightened preconditions). No gaps.

### Commit Integrity
- upstream commit presence: PARTIAL (builder e27e3e84 and doc-writer 18f37a12 present and correctly scoped; test file tests/test_schema_constraint_enforcement_1586.py is UNTRACKED and never committed by test-writer or builder)
- kanban commit packaging: pending

### Deduction Breakdown
- Intent mismatch: 0
- Evidence integrity concern: -.05 (test file uncommitted, process gap)
- Lint violations: 0
- AC quality: 5/5, no deduction
- Missing reviewer evidence: 0 (detailed PASS verdict with full AC map present)
- Regression failures: 0 (no task-domain regressions)

### Confidence: 0.95
### Action: archive

### Process Note
Test file tests/test_schema_constraint_enforcement_1586.py exists on disk and passes (17/17) but was never committed to git by the test-writer or builder. This is a recurring upstream process gap. The file must be committed separately.
