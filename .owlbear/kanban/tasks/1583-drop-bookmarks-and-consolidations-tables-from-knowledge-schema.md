---
id: 1583
title: Drop bookmarks and consolidations tables from knowledge schema
status: review
priority: nice-to-have
created: 2026-05-15T16:22:28.270394+00:00
updated: 2026-05-16T04:22:03.024872+00:00
tags:
  - scope:knowledge
  - type:cleanup
  - maintainability
parent:
depends_on:
  - 1576
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Context: Research #1576 classified bookmarks and consolidations tables as retire — no active write or read path (tests use mocks, not live SQL).

Objective: Remove table DDL from schema.py and add a v12 migration step that drops both tables.

Proof bundle: smoke

Acceptance Criteria:
- [ ] `schema.py`: `_CREATE_BOOKMARKS` and `_CREATE_CONSOLIDATIONS` DDL constants are deleted.
- [ ] `init_db`: `conn.execute(_CREATE_BOOKMARKS)`, `conn.execute(_CREATE_CONSOLIDATIONS)`, and the `idx_bookmarks_url_scope` / `idx_bookmarks_scope` index-creation statements are removed.
- [ ] `_migrate_v11_to_v12(conn)` executes `DROP TABLE IF EXISTS bookmarks` and `DROP TABLE IF EXISTS consolidations`; registered as `(12, _migrate_v11_to_v12)` in `_apply_migrations`.
- [ ] `_SCHEMA_VERSION` bumped from 11 to 12.
- [ ] Module docstring updated to remove bookmarks and consolidations from the table list.
- [ ] Given a fresh (empty) database, `init_db(path)` creates no `bookmarks` or `consolidations` entries in `sqlite_master`.
- [ ] Given a v11 database containing bookmarks and consolidations tables, `_apply_migrations` produces a database with no `bookmarks` or `consolidations` entries in `sqlite_master`.

Out of scope: Code module deletion (handled by sibling task #1582).
2026-05-15T19:18:27+00:00
## Architecture Review

**Verdict:** APPROVE → todo

### AC Assessment

| AC line | Assessment | Action |
|---------|-----------|--------|
| DDL constants deleted | B1 ✓ — names concrete targets | Refined from vague "CREATE TABLE statements" |
| init_db removals | B1/B2 ✓ — names specific execute calls and indexes | Added index lines (461-462) missed by original |
| v12 migration + registration | B1/B2 ✓ — names function, SQL, and registration tuple | Explicit registration requirement added |
| Version bump 11→12 | B1/B2 ✓ — concrete constant, concrete values | No change needed |
| Docstring update | B1/B2 ✓ — observable artifact change | New — addresses stale contract surface |
| Fresh DB verification | B2 ✓ — input (empty DB), output (no sqlite_master entries) | Strengthened with verification method |
| Migration path verification | B2 ✓ — input (v11 DB with tables), output (tables absent) | New — addresses challenger's test-proof gap |

### Architecture Notes

- **Pattern:** Follows existing v1→v11 migration chain pattern exactly. Approach A (add v12 DROP, keep v7/v8 immutable) is the only viable approach per research.
- **Module layering:** Schema-only change within `serve/knowledge/`. No upward imports, no cross-domain concerns.
- **KISS:** Minimal scope — DDL removal + one migration function. No new abstractions (Deletion Test: N/A).
- **Single domain:** `scope:knowledge` only.
- **Security:** No new system boundaries.

### Dependency Analysis

- **#1576 (research):** Archived/complete ✓ — provides the evidence base for table retirement.
- **#1582 (retire dead code):** NOT a dependency. Dead code still exists but is never called at runtime — tests use mocks/patches (confirmed via test_browser_fetcher_wiring.py and test_knowledge_guard_removal_1579.py). Dropping tables before removing dead modules is safe.

### Challenger Results

- **Verdict:** block (confidence 0.34)
- **Override rationale:** Challenger's primary concern (sequencing with #1582) is addressed by research evidence: no test exercises live SQL against these tables — all consumer tests mock BookmarkStore/ConsolidationService. The "unsupported premise" was actually supported by completed research #1576. AC quality concerns accepted and addressed via refinement. Test-proof gap addressed by adding AC-7 (migration path verification).
- **Accepted findings:** AC quality issues (B1/B2 violations) → all AC lines rewritten; stale contract surface (docstring) → added AC-5; migration test gap → added AC-7.

### Proof Bundle

`smoke` — straightforward schema cleanup with low blast radius. Migration and init_db correctness verified by AC-6 and AC-7.
2026-05-15T19:21:31+00:00
## Test-Writer Notes
- Test file: tests/test_schema_bookmark_drop_1583.py
- Classes: TestFromAC_SchemaBookmarkConsolidationDrop
- Tests per category: happy 7, edge 0, error 0, boundary 0
- Total: 7 tests, all FAIL
- ruff: clean
- AC coverage:
  | AC | Test |
  |----|------|
  | AC-1 DDL constants deleted | test_ac1_ddl_constants_removed |
  | AC-2 init_db bookmark indexes removed | test_ac2_init_db_no_bookmark_indexes |
  | AC-3 _migrate_v11_to_v12 drops tables + registered | test_ac3_migration_v11_to_v12_drops_tables |
  | AC-4 _SCHEMA_VERSION == 12 | test_ac4_schema_version_is_12 |
  | AC-5 docstring updated | test_ac5_docstring_excludes_retired_tables |
  | AC-6 fresh DB no retired tables | test_ac6_fresh_db_no_retired_tables |
  | AC-7 v11→v12 migration drops tables | test_ac7_migration_from_v11_drops_retired_tables |
- Proof bundle: smoke (one test per AC line, happy path only)

[[2026-05-16T06:22:03+02:00]]
## Builder Notes
- Implementation: No code changes required by builder; AC-aligned implementation already present in serve/knowledge/src/owlbear_knowledge/schema.py.
- Files changed: none
- Test results:
  - Task-scoped smoke proof (`tests/test_schema_bookmark_drop_1583.py`): 7 passed, 0 failed, 0 skipped
  - Module-level durable test file: not present (`serve/knowledge/tests/test_schema.py` missing; `tests/test_schema.py` missing)
- Lint status:
  - Task-scoped test lint: clean
- Coverage evidence:
  - Scoped run overall: 23%
  - `owlbear_knowledge/schema.py`: 54%
  - Note: task proof bundle is smoke; this run confirms AC behavior for #1583 and no builder edits were needed.
- Evidence summary by AC:
  - AC-1: `_CREATE_BOOKMARKS` and `_CREATE_CONSOLIDATIONS` are absent.
  - AC-2: `init_db` does not execute bookmarks/consolidations DDL or bookmark index creation.
  - AC-3: `_migrate_v11_to_v12` exists, drops both retired tables, and migration tuple includes `(12, _migrate_v11_to_v12)`.
  - AC-4: `_SCHEMA_VERSION` is 12.
  - AC-5: module docstring no longer lists bookmarks/consolidations.
  - AC-6: fresh in-memory DB has no `bookmarks`/`consolidations` tables.
  - AC-7: migration from version 11 removes both tables.
- Fixes applied: none (pass-through; implementation already satisfied acceptance criteria before builder intervention).
