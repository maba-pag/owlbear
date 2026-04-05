---
id: 721
title: 'Schema v8: add importance, consolidated, consolidations table'
status: archived
priority: needed
created: 2026-03-10T17:13:04.8182698+01:00
updated: 2026-03-13T17:35:34.2343178+01:00
started: 2026-03-13T17:35:33.5906915+01:00
completed: 2026-03-13T17:35:33.5906915+01:00
tags:
    - scope:core
    - memory
    - knowledge
    - schema
depends_on:
    - 700
    - 769
class: standard
---

## Goal
Extend knowledge graph schema to support consolidation and importance scoring.

## AC
- [ ] `_SCHEMA_VERSION` constant bumped from 7 to 8
- [ ] `_CREATE_ENTITIES` DDL string includes `importance REAL DEFAULT 0.5` column
- [ ] `_CREATE_CHUNKS` DDL string includes `consolidated INTEGER DEFAULT 0` column
- [ ] New `_CREATE_CONSOLIDATIONS` DDL defines: `id TEXT PRIMARY KEY, source_ids TEXT NOT NULL, summary TEXT, insight TEXT, created_at TEXT, scope TEXT DEFAULT 'global'`
- [ ] `_migrate_v7_to_v8()` function adds `importance` to entities via `ALTER TABLE` with `contextlib.suppress(OperationalError)` for idempotency
- [ ] `_migrate_v7_to_v8()` adds `consolidated` to chunks via `ALTER TABLE` (same pattern)
- [ ] `_migrate_v7_to_v8()` creates `consolidations` table via `_CREATE_CONSOLIDATIONS` (`IF NOT EXISTS` for idempotency)
- [ ] `_migrate_v7_to_v8()` bumps stored schema version to 8
- [ ] `init_db` fresh-DB path executes `_CREATE_CONSOLIDATIONS`
- [ ] `init_db` migration chain calls `_migrate_v7_to_v8()` when `current < 8`
- [ ] `init_db` docstring updated to describe v8 migration

## Architecture Notes
- Follow the exact pattern of `_migrate_v6_to_v7`: ALTER TABLE columns use `contextlib.suppress(sqlite3.OperationalError)`, new table uses `CREATE TABLE IF NOT EXISTS`
- `consolidations.source_ids` is `TEXT NOT NULL`  stores a JSON array of chunk IDs (e.g. `'[chunk-1,chunk-2]'`)
- `consolidations` table includes `scope TEXT DEFAULT 'global'` for consistency with all other tables
- No model changes in this task  `Entity.importance` field is #722's responsibility
- No index changes needed for this migration (scope index pattern only applies to `_SCOPE_TABLES`)

## Dependencies
- Preceding test task: #769 (Tests: schema v8 migration RED)

## References
- docs/research/always-on-memory-integration.md section 5c

[[2026-03-13]] Fri 10:39
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| v8 migration adds importance to entities | Clear, verifiable, follows ALTER TABLE pattern | Kept |
| v8 migration adds consolidated to chunks | Clear, verifiable, same pattern | Kept |
| v8 migration creates consolidations table | Original lacked scope column and source_ids type | Refined: added scope, specified TEXT NOT NULL for source_ids |
| init_db handles v7->v8 idempotently | Correct but underspecified | Expanded into 3 precise AC lines (fresh-DB, migration chain, version bump) |
| Tests verify migration | Bundled tests violates TDD convention | Extracted to separate test task #769 |

### Architecture Notes
- **Module layering**: Clean. `schema.py` is in `memory/knowledge/` (memory layer). No cross-layer concerns.
- **Pattern consistency**: v1-v7 migrations all follow identical structure: `contextlib.suppress` for ALTER TABLE, `IF NOT EXISTS` for CREATE TABLE, version bump. v8 must follow the same.
- **Scope column**: All 7 existing tables have `scope TEXT DEFAULT 'global'`. The `consolidations` table must too for query consistency.
- **source_ids type**: TEXT NOT NULL storing JSON arrays matches the metadata pattern (JSON-in-TEXT) used throughout the schema.
- **Separation from #722**: #721 is DDL-only (schema.py). #722 handles Entity model field + extractor prompt + retriever weighting. Clean single-responsibility split.
- **Separation from #723**: #723 (ConsolidationService) depends on #721's schema. Correct dependency direction.

### Changes Made
- Created test task #769 (Tests: schema v8 migration RED) at backlog
- Rewrote AC with 11 precise, mechanically verifiable criteria
- Added Architecture Notes section with pattern guidance
- Added depends_on: #769
- Removed bundled test AC (moved to #769)
- Added scope column to consolidations table spec
- Specified source_ids as TEXT NOT NULL (JSON array)

### Dependencies
- Added: #769 (preceding test task) as dependency
- Verified: #723 depends on #721 (declared in #723 body)
- Verified: #722 is independent (model layer, no schema dependency)

[[2026-03-13]] Fri 14:42
## Test-Writer Notes
- Preceding test task #769 already wrote all RED-phase tests for this task's AC.
- Test file: tests/test_schema_v8.py
- Classes: TestFromAC_SchemaVersionConstant, TestFromAC_FreshDbEntitiesImportance, TestFromAC_FreshDbChunksConsolidated, TestFromAC_FreshDbConsolidationsTable, TestFromAC_MigrateV7ToV8EntitiesImportance, TestFromAC_MigrateV7ToV8ChunksConsolidated, TestFromAC_MigrateV7ToV8ConsolidationsTable, TestFromAC_MigrateV7DataPreserved, TestFromAC_MigrateV7DefaultValues, TestFromAC_Idempotency
- Total: 32 tests covering all 11 AC lines
- Pass-through: no new tests needed.

[[2026-03-13]] Fri 15:14
## Builder Notes
- Files changed: src/owlbear/memory/knowledge/schema.py (v8 DDL + migration), tests/test_bookmark.py (version assertions 7->8)
- Tests: 32 passed (test_schema_v8.py), 42 passed (test_bookmark.py), 74 total green
- Lint: ruff clean
- Coverage: 67% on schema.py (old v1-v6 migrations not exercised by v8 tests; all v8-specific code fully covered)
- Fixes applied: Updated 2 hardcoded version==7 assertions in test_bookmark.py (test_schema_version_is_7, test_version_bumped_to_7) to expect 8
- Note: Implementation was already present as uncommitted changes from previous builder session; verified tests pass and fixed regressions

[[2026-03-13]] Fri 16:07
## Review Evidence (2026-03-13 reviewer)

### Test Results
- pytest: 32 passed, 0 failed (test_schema_v8.py)
- pytest: 74 passed, 0 failed (test_schema_v8.py + test_bookmark.py combined)

### Lint Results
- ruff: All checks passed (schema.py, test_schema_v8.py, test_bookmark.py)

### Coverage
- schema.py: 67% (missed lines: v1-v6 migration functions not exercised by v8 tests; all v8-specific code fully covered)

### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact value checks: `== 8`, `== 'REAL'`, `== 0.5`, exact column sets via set equality, `pytest.raises(IntegrityError)` for NOT NULL |
| Negative/error paths | ADEQUATE | NOT NULL constraint tested via IntegrityError; idempotency double-run tests; scope appropriate for pure DDL migration |
| Mutation reasoning | STRONG | Removing column, changing default, changing type, skipping migration, reordering columns all caught by specific assertions |
| Test independence | STRONG | Fresh fixture per test; migration tests each create own `_create_v7_db()` connection |
| Descriptive names | STRONG | e.g. `test_existing_entity_gets_default_importance`, `test_idempotent_preserves_consolidation_data` |

### Security Review
- Static DDL strings only, no user input in SQL
- Parameterized queries for data inserts
- `contextlib.suppress(OperationalError)` for idempotent ALTER TABLE (correct pattern)
- No secrets, deserialization, path traversal, or dependency changes
- No security issues found

### TestFromAC Comparison

| Original Test | Change Made | Assessment |
|--------------|-------------|------------|
| TestFromAC_SchemaVersionConstant (1 test) | No change | PRESERVED |
| TestFromAC_FreshDbEntitiesImportance (3 tests) | No change | PRESERVED |
| TestFromAC_FreshDbChunksConsolidated (3 tests) | No change | PRESERVED |
| TestFromAC_FreshDbConsolidationsTable (6 tests) | No change | PRESERVED |
| TestFromAC_MigrateV7ToV8EntitiesImportance (2 tests) | No change | PRESERVED |
| TestFromAC_MigrateV7ToV8ChunksConsolidated (2 tests) | No change | PRESERVED |
| TestFromAC_MigrateV7ToV8ConsolidationsTable (3 tests) | No change | PRESERVED |
| TestFromAC_MigrateV7DataPreserved (6 tests) | No change | PRESERVED |
| TestFromAC_MigrateV7DefaultValues (2 tests) | No change | PRESERVED |
| TestFromAC_Idempotency (4 tests) | No change | PRESERVED |

Note: test_schema_v8.py is untracked (new file). Builder notes state no TestFromAC modifications. File content matches test-writer's AC coverage table (32 tests, 10 classes). No weakened/removed patterns detected.

### Additional Changes (outside test_schema_v8.py)
Builder updated 2 assertions in test_bookmark.py to reflect v8:
- L441: `_SCHEMA_VERSION == 7` -> `== 8` (necessary: constant changed)
- L514: `row[0] == 7` -> `== 8` (necessary: init_db now produces v8)
These are NOT TestFromAC classes. They are pre-existing v7 bookmark tests that hardcoded the version number. The fix is correct and was required to avoid regressions.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| _SCHEMA_VERSION bumped to 8 | schema.py L22: `_SCHEMA_VERSION: int = 8` | test_schema_version_is_8 | PASS |
| _CREATE_ENTITIES includes importance REAL DEFAULT 0.5 | schema.py L62 | test_entities_has_importance_column, test_entities_importance_type_is_real, test_entities_importance_default_is_half | PASS |
| _CREATE_CHUNKS includes consolidated INTEGER DEFAULT 0 | schema.py L89 | test_chunks_has_consolidated_column, test_chunks_consolidated_type_is_integer, test_chunks_consolidated_default_is_zero | PASS |
| _CREATE_CONSOLIDATIONS DDL correct | schema.py L141-149: all 6 columns present | test_consolidations_table_exists, test_consolidations_has_all_columns, test_consolidations_source_ids_not_null, test_consolidations_scope_default_global | PASS |
| _migrate_v7_to_v8 adds importance with suppress | schema.py L282 | test_entities_importance_added, test_entities_importance_type_after_migration | PASS |
| _migrate_v7_to_v8 adds consolidated with suppress | schema.py L284 | test_chunks_consolidated_added, test_chunks_consolidated_type_after_migration | PASS |
| _migrate_v7_to_v8 creates consolidations table | schema.py L285 | test_consolidations_table_created, test_consolidations_has_all_columns_after_migration | PASS |
| _migrate_v7_to_v8 bumps version to 8 | schema.py L288-290 | test_schema_version_bumped_to_8 | PASS |
| init_db fresh-DB executes _CREATE_CONSOLIDATIONS | schema.py L328 | test_fresh_db_schema_version_is_8 | PASS |
| init_db migration chain calls _migrate_v7_to_v8 | schema.py L357 | test_idempotent_v7_migration | PASS |
| init_db docstring describes v8 | schema.py L303-316: mentions v8 migration | N/A (docstring) | PASS |

### Verdict: PASS (confidence .93)

[[2026-03-13]] Fri 16:56
## Docs Gate (2026-03-13 writer)

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | DDL-only schema migration; no tech stack change |
| 2 | Docstrings complete | Yes | Pass | Module docstring lists consolidations; _migrate_v7_to_v8 and init_db docstrings describe v8 |
| 3 | sources/overview.md | No | N/A | Pure internal DDL pattern; no external patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/always-on-memory-integration.md exists and is referenced |
| 6 | No impact | -- | -- | Items 2 and 5 apply |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/721-* files found)
