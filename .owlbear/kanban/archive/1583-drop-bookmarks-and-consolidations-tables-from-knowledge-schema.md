---
id: 1583
title: Drop bookmarks and consolidations tables from knowledge schema
status: archived
priority: nice-to-have
created: 2026-05-15T16:22:28.270394+00:00
updated: 2026-05-16T07:31:40.585446+00:00
tags:
  - scope:knowledge
  - type:cleanup
  - maintainability
parent:
depends_on:
  - 1576
ac:
  - '`schema.py`: `_CREATE_BOOKMARKS` and `_CREATE_CONSOLIDATIONS` DDL constants are
    deleted.'
  - '`init_db`: `conn.execute(_CREATE_BOOKMARKS)`, `conn.execute(_CREATE_CONSOLIDATIONS)`,
    and the `idx_bookmarks_url_scope` / `idx_bookmarks_scope` index-creation statements
    are removed.'
  - '`_migrate_v11_to_v12(conn)` executes `DROP TABLE IF EXISTS bookmarks` and `DROP
    TABLE IF EXISTS consolidations`; registered as `(12, _migrate_v11_to_v12)` in
    `_apply_migrations`.'
  - '`_SCHEMA_VERSION` is at least 12 (v12 introduced the table-drop migration; later
    tasks own higher versions).'
  - Module docstring updated to remove bookmarks and consolidations from the 
    table list.
  - Given a fresh (empty) database, `init_db(path)` creates no `bookmarks` or 
    `consolidations` entries in `sqlite_master`.
  - Given a database at schema version 11 containing bookmarks and 
    consolidations tables, calling `_migrate_v11_to_v12(conn)` directly removes 
    both tables from `sqlite_master` and advances `schema_version` to 12.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
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

[[2026-05-16T06:49:54+02:00]]
## Review Evidence
- Verdict: FAIL
- Current implementation satisfies AC-1..AC-7 on direct inspection:
| AC | Code Evidence | Task Proof | Status |
|---|---|---|---|
| AC-1 | serve/knowledge/src/owlbear_knowledge/schema.py:36; serve/knowledge/src/owlbear_knowledge/schema.py:216-259; serve/knowledge/src/owlbear_knowledge/schema.py:310-313 | tests/test_schema_bookmark_drop_1583.py:19 | pass |
| AC-2 | serve/knowledge/src/owlbear_knowledge/schema.py:345 | tests/test_schema_bookmark_drop_1583.py:28; tests/test_schema_bookmark_drop_1583.py:69 | pass |
| AC-3 | serve/knowledge/src/owlbear_knowledge/schema.py:310-313; serve/knowledge/src/owlbear_knowledge/schema.py:333 | tests/test_schema_bookmark_drop_1583.py:43; tests/test_schema_bookmark_drop_1583.py:80 | pass |
| AC-4 | serve/knowledge/src/owlbear_knowledge/schema.py:19 | tests/test_schema_bookmark_drop_1583.py:59 | pass |
| AC-5 | serve/knowledge/src/owlbear_knowledge/schema.py:1-6 | tests/test_schema_bookmark_drop_1583.py:63 | pass |
| AC-6 | serve/knowledge/src/owlbear_knowledge/schema.py:345 | tests/test_schema_bookmark_drop_1583.py:69 | pass |
| AC-7 | serve/knowledge/src/owlbear_knowledge/schema.py:333 | tests/test_schema_bookmark_drop_1583.py:80 | pass |
- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | Proof sufficiency for migration surface | Adjacent durable migration suite is still red against the live v12 schema. `init_db(v10_conn)` now correctly ends at schema version 12, but `tests/test_enrichment_schema.py:522-527` still asserts version 11. Independent quality-runner verification on `tests/test_schema_bookmark_drop_1583.py` and `tests/test_enrichment_schema.py` reported 31/32 passed with 1 failure: `AssertionError: Expected schema version 11, got 12`. Builder evidence omitted this adjacent proof surface, so the task would false-green if advanced. | serve/knowledge/src/owlbear_knowledge/schema.py:19; serve/knowledge/src/owlbear_knowledge/schema.py:310-313; serve/knowledge/src/owlbear_knowledge/schema.py:333; tests/test_enrichment_schema.py:522-527; quality-runner report | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update the durable migration proof so the v10 upgrade path asserts the correct terminal schema version (12) or explicitly isolates any intended intermediate v11-state assertions before v12 runs. Re-run the task smoke file and the adjacent durable suite together. | tests/test_enrichment_schema.py; tests/test_schema_bookmark_drop_1583.py | quality-runner failure for `tests/test_enrichment_schema.py::TestFromAC_MigrationUpgradePath::test_v10_to_v11_schema_version_updated_to_11`; serve/knowledge/src/owlbear_knowledge/schema.py:19; serve/knowledge/src/owlbear_knowledge/schema.py:310-313; serve/knowledge/src/owlbear_knowledge/schema.py:333 |

## Observations
- No live source usage of `bookmarks` or `consolidations` was found outside legacy migration helpers and the new drop migration in `serve/knowledge/src/owlbear_knowledge/schema.py`.
- The task-scoped smoke tests in `tests/test_schema_bookmark_drop_1583.py` are specific enough for AC-1..AC-7; the rejection is for stale adjacent durable proof, not for a schema implementation defect.

[[2026-05-16T07:08:37+02:00]]
## Test-Writer Notes
- Retry: fixed stale adjacent durable proof per reviewer Required Follow-up #1.
- File updated: tests/test_enrichment_schema.py
- Change: renamed `test_v10_to_v11_schema_version_updated_to_11` → `test_v10_to_v12_schema_version_updated_to_12`; updated docstring and assertion from `== 11` to `== 12` (terminal schema version after v12 migration drops bookmarks/consolidations).
- Quality-runner: 39 passed, 0 failed across `tests/test_schema_bookmark_drop_1583.py` + `tests/test_enrichment_schema.py`; lint clean.
- Builder skip: test-only retry, all tests green against current impl — advancing directly to review.

[[2026-05-16T07:33:53+02:00]]
## Review Evidence
- Verdict: FAIL
- Review route: backlog
- Summary: Independent reviewer verification of [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py) and [tests/test_enrichment_schema.py](tests/test_enrichment_schema.py) against the live tree returned 36 passed / 3 failed, contradicting the retry note at [.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md](.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md#L150). The table-drop implementation itself is still present, but the task contract and proof surface are stale against the current repo state.
- Current implementation check: [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L310) still defines `_migrate_v11_to_v12`, the drop statements remain at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L312) and [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L313), and the dispatcher still includes [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L422). No blocking defect was found in the v11→v12 table-drop logic itself.
- AC snapshot:

| AC | Evidence | Status |
|---|---|---|
| AC-1 | Task-local rerun still passes [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L19). | pass |
| AC-2 | Task-local rerun still passes [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L28). | pass |
| AC-3 | Drop migration remains present at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L310) and registered at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L422). | pass |
| AC-4 | Task contract still requires schema version 12 at [.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md](.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md#L31), but live source is now version 13 at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L19) and the task-local assertion at [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L59) now fails. | fail |
| AC-5 | Task-local rerun still passes [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L63). | pass |
| AC-6 | Task-local rerun still passes [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L69). | pass |
| AC-7 | The task-local `_apply_migrations(conn, 11)` proof at [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L80) no longer models the live migration chain once [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L423) runs v12→v13. | fail |

- Blocking findings:
| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-4 and adjacent durable version proof | The task now has a contract-level version-ceiling conflict. #1583 still requires `_SCHEMA_VERSION` to be 12 at [.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md](.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md#L31), but live source is 13 at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L19). A separate review task explicitly owns that bump: [task 1586 status](.owlbear/kanban/tasks/1586-p1-02-knowledge-schema-constraint-enforcement.md#L4), [AC-1](.owlbear/kanban/tasks/1586-p1-02-knowledge-schema-constraint-enforcement.md#L31), and [builder note](.owlbear/kanban/tasks/1586-p1-02-knowledge-schema-constraint-enforcement.md#L147). Independent rerun failed [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L59), [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L60), [tests/test_enrichment_schema.py](tests/test_enrichment_schema.py#L522), and [tests/test_enrichment_schema.py](tests/test_enrichment_schema.py#L527) with schema-version-12 expectations that are no longer true. This is not a test-writer-only fix, because changing those assertions would contradict the current AC text. | quality-runner: 36 passed / 3 failed; `AssertionError: _SCHEMA_VERSION must be 12, got 13`; `AssertionError: Expected schema version 12, got 13` | backlog |
| 2 | AC-7 | The retry proof for `_apply_migrations(conn, 11)` is now under-specified for the live migration chain. The synthetic v11 fixture in [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L80) seeds only `schema_version`, `bookmarks`, and `consolidations`, then calls `_apply_migrations`. Once the dispatcher includes [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L423), the live v12→v13 migration at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L320) touches [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L327) and fails with `sqlite3.OperationalError: no such table: edges`. The task needs contract clarification on whether AC-7 should prove a real v11 database shape or isolate `_migrate_v11_to_v12` directly. | [.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md](.owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md#L34); [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L80); [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L320); [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L327); quality-runner failure `sqlite3.OperationalError: no such table: edges` | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Reconcile task #1583 with the live v13 schema ceiling introduced by task #1586: either redefine AC-4 and the adjacent durable version proof so they verify retained v11→v12 drop behavior without asserting terminal schema version 12, or explicitly isolate review scope from the v13 task. | .owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md, .owlbear/kanban/tasks/1586-p1-02-knowledge-schema-constraint-enforcement.md, tests/test_schema_bookmark_drop_1583.py, tests/test_enrichment_schema.py | Blocking finding #1 |
| 2 | architect | Refine AC-7 proof shape so the retry uses either a realistic v11 fixture that remains valid when later migrations exist or a direct `_migrate_v11_to_v12` proof surface, then reroute to test-writer for aligned test updates. | .owlbear/kanban/tasks/1583-drop-bookmarks-and-consolidations-tables-from-knowledge-schema.md, tests/test_schema_bookmark_drop_1583.py | Blocking finding #2 |

## Observations
- No safety or security issue was identified; the blockers are contract drift and stale proof, not unsafe behavior.
- The live source has moved beyond the terminal-v12 assumption in this task. As additional non-blocking evidence of that drift, the `init_db()` docstring still says migrations run through v2-v12 at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L442).

[[2026-05-16T08:00:06+02:00]]
## Architecture Review (re-review after reviewer rejection)

**Verdict:** APPROVE → todo

### Reviewer Findings Addressed

| # | Finding | Resolution |
|---|---------|------------|
| 1 | AC-4 asserts terminal `_SCHEMA_VERSION == 12` but live source is now 13 (task #1586) | Rewrote AC-4: `_SCHEMA_VERSION` is at least 12 — resilient to subsequent schema bumps |
| 2 | AC-7 calls `_apply_migrations(conn, 11)` which chains into v12→v13, fails on missing `edges` table | Rewrote AC-7: calls `_migrate_v11_to_v12(conn)` directly — isolates this task's migration from later chain steps |

### AC Assessment (refined lines only)

| AC line | Assessment | Action |
|---------|-----------|--------|
| AC-4 (revised) | B1/B2 ✓ — `>= 12` is verifiable, scoped to this task's contribution | Changed from `== 12` to `>= 12` with explanation |
| AC-7 (revised) | B1/B2 ✓ — names function, precondition (v11 + tables present), two observable outputs (tables absent, version == 12) | Changed from `_apply_migrations` chain test to direct `_migrate_v11_to_v12` call |

### Architecture Notes

- Implementation already complete and correct (builder pass-through confirmed in prior cycle).
- Only the proof surface (tests) needs updating to match refined AC-4 and AC-7.
- No source code changes required — schema.py already has the v12 migration at L310-316.
- v12→v13 chain is correctly registered at L422-423 and owned by #1586.

### Proof Bundle

`smoke` — unchanged. Low blast radius, straightforward AC refinement.

### Challenge Results

Skipped — re-review of AC precision only; architecture was validated in the first review cycle (challenger confidence was overridden with evidence). No new architectural decisions introduced.

### Action Taken

Refined AC-4 and AC-7 via `edit_task` to resolve reviewer blocking findings. Task re-advances to `todo` for test-writer to update the proof surface.

[[2026-05-16T08:19:08+02:00]]
## Test-Writer Notes
- Retry: updated stale assertions per architect's revised AC-4 and AC-7 (second re-review).
- Files changed: tests/test_schema_bookmark_drop_1583.py, tests/test_enrichment_schema.py

### Changes made
| File | Change |
|------|--------|
| tests/test_schema_bookmark_drop_1583.py | AC-4: renamed `test_ac4_schema_version_is_12` → `test_ac4_schema_version_at_least_12`; assertion changed from `== 12` to `>= 12` per revised AC-4 |
| tests/test_schema_bookmark_drop_1583.py | AC-7: changed `test_ac7_migration_from_v11_drops_retired_tables` to call `_migrate_v11_to_v12(conn)` directly instead of `_apply_migrations(conn, 11)`; avoids v12→v13 chain that fails on missing `edges` table; added schema_version == 12 assertion |
| tests/test_schema_bookmark_drop_1583.py | Removed unused `_apply_migrations` import; split compound `assert` (PT018) |
| tests/test_enrichment_schema.py | Renamed `test_v10_to_v12_schema_version_updated_to_12` → `test_v10_to_v13_schema_version_updated_to_v13`; updated assertion from `== 12` to `== 13` (current terminal schema version introduced by task #1586) |

### Quality-runner evidence
- 39 passed, 0 failed across both test files
- ruff: clean

### AC coverage
| AC | Test |
|----|------|
| AC-1 | test_ac1_ddl_constants_removed |
| AC-2 | test_ac2_init_db_no_bookmark_indexes |
| AC-3 | test_ac3_migration_v11_to_v12_drops_tables |
| AC-4 (>= 12) | test_ac4_schema_version_at_least_12 |
| AC-5 | test_ac5_docstring_excludes_retired_tables |
| AC-6 | test_ac6_fresh_db_no_retired_tables |
| AC-7 (direct call) | test_ac7_migration_from_v11_drops_retired_tables |

- Builder skip: test-only retry, all tests green against current impl — advancing directly to review.

[[2026-05-16T08:46:25+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1583 -> docs | AC mapped to code and evidence sufficient.
- Independent reviewer verification:
  - Scoped `quality-runner` reran `uv run pytest tests/test_schema_bookmark_drop_1583.py tests/test_enrichment_schema.py -v --tb=short` and returned 39 passed, 0 failed, 0 skipped.
  - Scoped `quality-runner` reran `uv run ruff check tests/test_schema_bookmark_drop_1583.py tests/test_enrichment_schema.py serve/knowledge/src/owlbear_knowledge/schema.py` and returned clean lint.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | Retired DDL constants are absent from the live module surface in [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L1-L140). | [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L19) proves `_CREATE_BOOKMARKS` / `_CREATE_CONSOLIDATIONS` are not exported. | pass |
| AC-2 | Current `init_db` starts at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L435-L520) and no longer issues retired bookmark/consolidation DDL or bookmark-index creation there. | [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L28) proves bookmark indexes are absent; [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L69) proves fresh `init_db()` creates neither retired table. | pass |
| AC-3 | `_migrate_v11_to_v12` is defined at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L310-L316) with the required `DROP TABLE IF EXISTS` statements at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L312-L313), and `_apply_migrations` still registers `(12, _migrate_v11_to_v12)` at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L422). | [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L43) proves the direct v11→v12 drop behavior. | pass |
| AC-4 | `_SCHEMA_VERSION` is 13 at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L19), satisfying the refined `>= 12` contract. | [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L59) proves the lower bound; adjacent durable proof at [tests/test_enrichment_schema.py](tests/test_enrichment_schema.py#L522-L527) proves the live terminal version is 13. | pass |
| AC-5 | The module docstring table list at [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L1-L6) no longer mentions bookmarks or consolidations. | [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L63) proves those terms are absent from `schema_mod.__doc__`. | pass |
| AC-6 | Fresh-schema creation is still rooted in [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L435-L520) without retired-table creation. | [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L69) proves `sqlite_master` contains neither retired table after `init_db()` on an empty database. | pass |
| AC-7 | `_migrate_v11_to_v12` still drops both retired tables and updates `schema_version` to 12 in [serve/knowledge/src/owlbear_knowledge/schema.py](serve/knowledge/src/owlbear_knowledge/schema.py#L310-L316). | [tests/test_schema_bookmark_drop_1583.py](tests/test_schema_bookmark_drop_1583.py#L80) directly exercises `_migrate_v11_to_v12(conn)` against a synthetic v11 database and proves both table removal and version bump to 12. | pass |
- Blocking findings: none.

## Observations
- The earlier contract drift is resolved: task-local AC-4 now asserts `>= 12`, while the adjacent durable migration proof correctly asserts the current terminal version 13 at [tests/test_enrichment_schema.py](tests/test_enrichment_schema.py#L522-L527).
- I could not execute a scoped `git status --porcelain` contamination check because no terminal tool was exposed in this session. This review verdict is therefore based on live-tree inspection, zero in-editor diagnostics on the scoped files, and independent scoped test/lint proof.

[[2026-05-16T09:10:11+02:00]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | README Verification | Yes — `serve/knowledge/src/**` → `serve/knowledge/README.md` | PASS | Layer 1 (grep): searched README for bookmark/consolidation/schema_version. Lines 57–58 state "Inactive bookmark, scope-transfer, and consolidation surfaces are retained in code only as cleanup/deferred targets" — still accurate post-#1583; schema tables dropped, code modules retained pending #1582. No removed symbols or stale flags. Layer 2 (editorial): README is coherent; module groups table correctly omits BookmarkStore/ConsolidationService from operational API. No contradictions. No updates required. |
| 2 | External Attribution | N/A | PASS | Schema cleanup using internal migration chain patterns. The only external reference in the research doc is sqlite.org DROP TABLE docs (basic SQL reference, not a novel library dependency). No `.owlbear/sources/overview.md` update needed. |
| 3 | Research Doc | Yes — `.owlbear/research/drop-bookmark-consolidation-tables.md` exists (owned by #1583) | PASS | Research doc correctly identifies owning task #1583 in header. Not hyperlinked from task body (pre-existing gap; multiple prior review cycles did not flag it). No gate impact. |
| 4 | Deletion Detection | N/A | PASS | No source files deleted in this task. `schema.py` modified (not deleted). Test files created/updated. No orphaned README references. |

### Files Updated
None — README accurately reflects post-#1583 state with no changes required.

### Scratch Cleanup
No `.owlbear/scratch/1583-*` files found.

[[2026-05-16T09:31:40+02:00]]
## Audit
### Regression Detection
- quality-runner mode full: 4618 passed, 239 failed, 14 skipped, 9 errors
- All 239 failures are in unrelated domains: test_support_module_migration (config cleanup), test_engine_dep_lookup, test_dispatch_gate_port, test_frontend_polling, test_cockpit_pds_build_compat, test_graph_store_counts (runtime errors), test_knowledge_integrity_audit_1587 (TDD RED expected). Zero failures in knowledge schema domain.
- Task-scoped tests (test_schema_bookmark_drop_1583.py) and adjacent durable suite (test_enrichment_schema.py) all passed.
- regression verdict: PASS (no cross-task regressions from #1583)

### Intent Verification
- scope alignment: PASS (changed files: schema.py in serve/knowledge/, task-scoped test, durable enrichment test -- all knowledge domain)
- purpose match: PASS (retired DDL removed, v12 migration added, proof surface updated)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
Initial AC was specific and well-structured. Version ceiling (AC-4 == 12) and migration chain coupling (AC-7 via _apply_migrations) broke when concurrent task #1586 introduced v13. This triggered two review rejection cycles. Architect responded well: refined AC-4 to >= 12 and AC-7 to direct _migrate_v11_to_v12 call. Gaps were concurrency artifacts, not design failures. Overall adequate with minor adaptation needed.

### Commit Integrity
- upstream commit presence: PARTIAL
  - schema.py: implementation was pre-existing (builder pass-through confirmed); no builder commit needed
  - test_schema_bookmark_drop_1583.py: original smoke tests committed (0c7631cb), but second test-writer cycle (AC-4 >= 12, AC-7 direct call) is UNCOMMITTED (modified in working tree)
  - test_enrichment_schema.py: first fix committed (31fa7663), but second fix (v12 to v13 terminal version) is UNCOMMITTED (modified in working tree)
- PROCESS CONCERN: Two test files have uncommitted modifications from the final test-writer cycle. Reviewer PASS verdict is based on these uncommitted changes. These must be committed separately.
- kanban commit packaging: pending (will commit after archival)

### Deduction Breakdown
- Evidence integrity concern: -.05 (uncommitted test deliverables; reviewer verdict relies on working-tree state not yet in git)
- No other deductions.

### Confidence: .95
### Action: archive

### Process Note
Two test files require a commit from an upstream agent or user:
- tests/test_schema_bookmark_drop_1583.py (AC-4/AC-7 refinements)
- tests/test_enrichment_schema.py (v13 terminal version assertion)
