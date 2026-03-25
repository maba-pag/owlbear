---
id: 563
title: Add _SELECT_COLS constant to source_store.py
status: archived
priority: someday
created: 2026-03-04T07:39:06.1335739+01:00
updated: 2026-03-25T18:02:36.5298308+01:00
started: 2026-03-07T04:26:04.7057558+01:00
completed: 2026-03-25T18:02:31.5775497+01:00
tags:
    - audit
    - dry
    - knowledge
depends_on:
    - 892
class: standard
---

DRY-11: SELECT column list inlined 6 times in source_store.py. BookmarkStore already uses _SELECT_COLS pattern. Follow same pattern.

Findings:
- File: src/owlbear/memory/knowledge/source_store.py
- 6 identical SELECT column lists at lines 93, 107, 120, 127, 140, 149
- Column list: id, name, source_type, config, scope, enabled, priority, last_refreshed_at, last_error, created_at, updated_at (11 cols)
- Prior art: BookmarkStore._SELECT_COLS in bookmark.py (class attr, string constant, used in f-string queries)
- INSERT at line 70 also lists columns but uses different formatting (parenthesized, with VALUES) - not a candidate for _SELECT_COLS
- _row_to_model already maps by positional index (row[0]..row[10]) - column order must stay stable

Approach:
1. Add _SELECT_COLS class attr (same pattern as BookmarkStore line 90)
2. Replace all 6 inline SELECTs with f-string referencing self._SELECT_COLS
3. Add noqa: S608 to f-string queries (same as BookmarkStore)
4. Existing tests should pass unchanged

AC:
1. _SELECT_COLS defined once as class attribute on KnowledgeSourceStore
2. All 6 SELECT queries reference _SELECT_COLS instead of inline column list
3. Column order unchanged (positional _row_to_model depends on it)
4. Existing tests pass unchanged
5. ruff clean

[[2026-03-21]] Sat 13:12
## Architecture Review\nSee docs/scratch/563-architect.md for the refined AC, implementation guidance, and full review.

[[2026-03-21]] Sat 13:13
## Architecture Review

See docs/scratch/563-architect.md for the refined AC, implementation guidance, and full review.

[[2026-03-25]] Wed 06:58
## Test-Writer Notes
- Overtaken RED: task #892 (dedicated TDD RED phase) completed and archived before #563 reached test-writer slot.
- Test file: tests/test_knowledge_source_store.py
- Classes already present: TestFromAC_SelectColsAttribute, TestFromAC_SelectColsInReadPaths, TestFromAC_SelectColsDynamicReuse
- Tests per category: happy 2, edge 2, boundary 6 (total 10 FromAC tests), plus 32 existing CRUD tests
- Total: 42 tests, all PASS (green-on-arrival)
- Source implementation already complete: _SELECT_COLS class attr + _select_from_sources() helper in source_store.py
- ruff: clean (both src and test files)
- AC coverage: AC1 covered by TestFromAC_SelectColsAttribute, AC2-AC4 covered by TestFromAC_SelectColsInReadPaths + TestFromAC_SelectColsDynamicReuse, AC5 see ruff above

[[2026-03-25]] Wed 12:20
## Builder Notes
- Files changed: None by builder. Existing implementation in src/owlbear/memory/knowledge/source_store.py already satisfied AC at pickup.
- Tests: 42 passed in scoped run for tests/test_knowledge_source_store.py.
- Coverage: 98% on src/owlbear/memory/knowledge/source_store.py (53 statements, 1 miss).
- Lint: ruff clean for src/owlbear/memory/knowledge/source_store.py and tests/test_knowledge_source_store.py.
- Evidence: Scoped pytest run finished with 42 passed in 1.05s. Scoped coverage run finished with 42 passed in 3.33s.
- Fixes applied: None. Task was green on arrival from upstream implementation.

[[2026-03-25]] Wed 12:46
## Review Evidence

### Review: #563 - Add _SELECT_COLS constant to source_store.py

### Test Results
- pytest: 42 passed, 0 failed
- Evidence: isolated scoped pytest-cov run completed with 42 passed in 0.83s.

### Lint Results
- ruff: clean on src/owlbear/memory/knowledge/source_store.py and tests/test_knowledge_source_store.py
- Evidence: task-scoped ruff returned All checks passed.

### Coverage
- src/owlbear/memory/knowledge/source_store.py: 98 percent (53 statements, 1 missed line)
- Note: bare coverage reports the whole repo under the global source config. I used the touched-file line plus AC-mapped tests, not the repo total, for review confidence.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1. _SELECT_COLS exists once on KnowledgeSourceStore with the exact 11-column string | TestFromAC_SelectColsAttribute::test_attribute_exists_on_store_class; test_attribute_equals_canonical_column_list | Yes. The class-attribute existence and exact-string assertion at tests/test_knowledge_source_store.py:355-360 fail if the constant is missing or reordered. | COVERED |
| AC2. All six read queries build SELECT from _SELECT_COLS instead of inline lists | TestFromAC_SelectColsInReadPaths::{6 methods}; TestFromAC_SelectColsDynamicReuse::{6 methods} | Yes. The trace-callback assertions at tests/test_knowledge_source_store.py:366-448 and the sentinel monkeypatch tests at :477-584 fail if any read path hardcodes the old column list. | COVERED |
| AC3. Query behavior stays unchanged: get() filters by id, get_by_name() filters by name and scope, scoped list methods keep scope filtering, list_enabled() keeps priority ordering | Legacy CRUD tests plus the TestFromAC path tests above | No for the single-row lookup predicates. The suite covers scope filtering and priority order, but no test asserts the exact WHERE id = ? predicate in get() or the full WHERE name = ? AND scope = ? predicate in get_by_name(). A regression that returns the first row would still pass the current single-row happy-path tests. | LAX |
| AC4. Column order stays aligned with _row_to_model | TestFromAC_SelectColsAttribute::test_attribute_equals_canonical_column_list plus existing CRUD round trips | Yes for the _SELECT_COLS order change this task introduces. The exact constant check, current _row_to_model mapping, and round-trip CRUD tests collectively protect the intended contract. | COVERED |
| AC5. Scoped pytest passes | Isolated scoped pytest-cov run | Yes. | COVERED |
| AC6. Scoped ruff passes | Task-scoped ruff run | Yes. | COVERED |

#### Security Review
- No security issues found. _SELECT_COLS is a class-owned constant interpolated into read-only SELECT clauses; all runtime values still flow through parameterized sqlite placeholders.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_SelectColsAttribute::* | No diff from test-writer commit 9220f1a to HEAD; git diff on tests/test_knowledge_source_store.py after 9220f1a is empty. | PRESERVED |
| TestFromAC_SelectColsInReadPaths::* | No diff from test-writer commit 9220f1a to HEAD; latest test-file commit is still 9220f1a. | PRESERVED |
| TestFromAC_SelectColsDynamicReuse::* | No diff from test-writer commit 9220f1a to HEAD; builder notes also reported no file changes on this card. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The task-specific tests prove _SELECT_COLS reuse, but they do not assert the lookup predicates that AC3 calls out. There is no test asserting WHERE id = ? in get() or the full name-and-scope predicate in get_by_name(). |
| Negative/error paths | ADEQUATE | Missing lookups, duplicate name plus scope, delete missing, and update missing are covered in the legacy CRUD suite. |
| Mutation reasoning | WEAK | If get() or get_by_name() degraded to a first-row lookup while preserving the column list, the current tests could still pass because the positive cases use only one matching row. |
| Test independence | STRONG | Each test uses a fresh in-memory sqlite database and isolated fixtures. |
| Descriptive names | STRONG | Test names are specific and scenario-based across the file. |

#### Data Safety
- No data safety issues found.

#### Implementation-Aware Test Gaps
- No test protects the get() id predicate against a regression that still returns the only row in the table.
- No test protects the name portion of get_by_name() against a regression that matches by scope only.
- No compensating TestBuilderDiscovered coverage exists; the builder reported no file changes on this card.

### Pass 2 - INFORMATIONAL
- The implementation itself is correct by inspection: _SELECT_COLS is defined once at src/owlbear/memory/knowledge/source_store.py:60-63, _select_from_sources() centralizes the read-query prefix at :65-66, and the six read call sites keep their existing filters and ordering at :99, :109, :120, :125, :136, and :143.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1. _SELECT_COLS defined once with the canonical value | src/owlbear/memory/knowledge/source_store.py:60-63 | TestFromAC_SelectColsAttribute::* | PASS |
| AC2. All six read queries reference _SELECT_COLS | src/owlbear/memory/knowledge/source_store.py:99, 109, 120, 125, 136, 143 | TestFromAC_SelectColsInReadPaths::* and TestFromAC_SelectColsDynamicReuse::* | PASS |
| AC3. Query behavior unchanged | Source inspection confirms current predicates and ordering at src/owlbear/memory/knowledge/source_store.py:99-143; legacy CRUD tests cover scope and ordering at tests/test_knowledge_source_store.py:171-174, 207-210, 224-228, 242-246, 250-254 | Legacy CRUD coverage is partial for this AC | PASS |
| AC4. Column order remains aligned with _row_to_model | src/owlbear/memory/knowledge/source_store.py:44-57 and :60-63 | TestFromAC_SelectColsAttribute::test_attribute_equals_canonical_column_list | PASS |
| AC5. Scoped pytest passes | Isolated scoped pytest-cov run: 42 passed | tests/test_knowledge_source_store.py | PASS |
| AC6. Scoped ruff passes | Task-scoped ruff clean | source and test files | PASS |

### Verdict: FAIL
- The implementation satisfies the acceptance criteria by inspection, but the review gate fails because the tests do not adequately enforce AC3. Confidence stays below the reviewer pass threshold without predicate-level coverage for the single-row lookup queries.

### Action Taken
- Appended review evidence to task #563.
- Moving task #563 back to todo for stronger query-behavior tests.

[[2026-03-25]] Wed 13:39
## Test-Writer Notes (retry)
- Retry reason: reviewer cited missing predicate-level tests for AC3
- Added: 6 new tests in TestFromAC_QueryBehaviorPredicates
  - test_get_discriminates_by_id_not_by_position (multi-row, catches first-row mutation)
  - test_get_returns_none_when_id_absent_but_other_rows_exist
  - test_get_sql_where_clause_filters_by_id (SQL trace: WHERE id =)
  - test_get_by_name_discriminates_by_name_within_same_scope (multi-row, catches scope-only mutation)
  - test_get_by_name_returns_none_when_name_wrong_scope_exists
  - test_get_by_name_sql_where_clause_filters_by_name_and_scope (SQL trace: WHERE name = ... AND scope =)
- Green-on-arrival: implementation already correct, tests enforce contract for future regressions
- Preserved: 42 existing tests (all still PASS)
- Total: 48 tests, 48 PASS
- ruff: clean
- Commit: 22279c6

[[2026-03-25]] Wed 17:15
## Builder Notes
- Files changed: None by builder in this run.
- Tests: 48 passed in tests/test_knowledge_source_store.py.
- Coverage: 98 percent on src/owlbear/memory/knowledge/source_store.py.
- Lint: ruff clean on scoped source and test files.
- Evidence: pytest scoped run reported 48 passed in 0.65s; coverage run exit code 0 with source_store.py 53 statements and 1 missed line; ruff reported All checks passed.
- Fixes applied: None. Implementation already satisfied AC at pickup after test-writer retry.

[[2026-03-25]] Wed 17:29
## Review Evidence

### Review: #563 - Add _SELECT_COLS constant to source_store.py

### Test Results
- pytest: 48 passed, 0 failed in 1.18s on tests/test_knowledge_source_store.py.
- coverage: scoped run passed with 48 passed in 3.79s; src/owlbear/memory/knowledge/source_store.py reports 53 statements, 1 missed, 98 percent. The 4 percent repo total is expected from bare scoped coverage and was not used for the verdict.

### Lint Results
- ruff: clean on src/owlbear/memory/knowledge/source_store.py and tests/test_knowledge_source_store.py.
- language service: no errors on either task file.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1. _SELECT_COLS defined once as a class attribute | TestFromAC_SelectColsAttribute::test_attribute_exists_on_store_class at line 354 and test_attribute_equals_canonical_column_list at line 358 | Yes. Missing or reordered columns fail the exact attribute assertions. | COVERED |
| AC2. All 6 SELECT queries reference _SELECT_COLS | TestFromAC_SelectColsInReadPaths methods at lines 366, 381, 396, 410, 424, and 438 plus TestFromAC_SelectColsDynamicReuse methods at lines 477, 496, 515, 533, 551, and 569 | Yes. Hardcoded or partially migrated read paths fail either the emitted-SQL checks or the sentinel monkeypatch checks. | COVERED |
| AC3. Column order remains aligned with _row_to_model | TestFromAC_SelectColsAttribute::test_attribute_equals_canonical_column_list at line 358; _row_to_model starts at src/owlbear/memory/knowledge/source_store.py line 44 | Yes. Reordering the constant breaks the exact string check before positional row mapping can silently drift. | COVERED |
| AC4. Existing tests pass unchanged | Legacy CRUD suites starting at lines 168, 191, 213, 232, 258, 287, and 300 plus the scoped pytest run | Yes. Existing CRUD behavior still passes green, and the retry commit 22279c6 only added the predicate class instead of rewriting earlier tests. | COVERED |
| AC5. ruff clean | Task-scoped ruff check on the source and test files | Yes. The isolated ruff run exits clean on both task files. | COVERED |

#### Security Review
- No security issues found. _SELECT_COLS is class-owned and interpolated only into read-only SELECT clauses; runtime values still flow through sqlite parameter placeholders at lines 99, 109, 120, 136, and 143.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_SelectColsAttribute::* | No diff in this class across 9220f1a to 22279c6; current local drift does not touch the class starting at line 351. | PRESERVED |
| TestFromAC_SelectColsInReadPaths::* | No diff in this class across 9220f1a to 22279c6; current local drift does not touch the class starting at line 363. | PRESERVED |
| TestFromAC_SelectColsDynamicReuse::* | No diff in this class across 9220f1a to 22279c6; current local drift does not touch the class starting at line 465. | PRESERVED |
| TestFromAC_QueryBehaviorPredicates::* | Retry commit 22279c6 adds this class at line 596; current local edits only collapse line wrapping and keep every predicate and assertion intact. | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | The retry tests assert exact ids, exact None behavior for absent lookups, and exact WHERE id / WHERE name plus scope SQL. |
| Negative and error paths | STRONG | Missing-id and missing-name-in-scope cases are covered at lines 620 and 671, and the legacy missing-lookup tests still exist at lines 194 and 204. |
| Mutation reasoning | STRONG | Multi-row tests at lines 605 and 651 catch first-row and scope-only regressions, while SQL trace tests at lines 631 and 682 catch dropped predicates even if result shape stays superficially valid. |
| Test independence | STRONG | Fresh in-memory sqlite fixtures are created at lines 39 and 47, so tests do not share state. |
| Descriptive names | STRONG | The FromAC and CRUD suites use scenario-specific method names throughout the file. |

#### Data Safety
- No data safety issues found.

#### Implementation-Aware Test Gaps
- No significant untested paths in the task scope. _select_from_sources() at lines 65 and 66 and all six read call sites at lines 99, 109, 120, 125, 136, and 143 are exercised by SQL-trace plus dynamic-reuse tests, while CRUD behavior and ordering remain covered by the legacy suites.

### Pass 2 - INFORMATIONAL
- Current worktree drift in src/owlbear/memory/knowledge/source_store.py and tests/test_knowledge_source_store.py is formatting-style only. The source diff collapses adjacent string literals at line 143, and the test diff only reflows method signatures and assert wrapping inside the retry class.
- No other informational findings.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1. _SELECT_COLS defined once as class attribute on KnowledgeSourceStore | src/owlbear/memory/knowledge/source_store.py lines 60 to 66 define the constant and shared SELECT helper once. | TestFromAC_SelectColsAttribute::* | PASS |
| AC2. All 6 SELECT queries reference _SELECT_COLS instead of inline column list | Read paths at source_store.py lines 99, 109, 120, 125, 136, and 143 all build from _select_from_sources(). | TestFromAC_SelectColsInReadPaths::* and TestFromAC_SelectColsDynamicReuse::* | PASS |
| AC3. Column order unchanged | _row_to_model starts at source_store.py line 44 and the exact canonical column string is asserted at tests/test_knowledge_source_store.py line 358. | TestFromAC_SelectColsAttribute::test_attribute_equals_canonical_column_list | PASS |
| AC4. Existing tests pass unchanged | Scoped pytest reports 48 passed, and the retry commit only adds the predicate-strengthening class instead of altering earlier CRUD suites. | Legacy CRUD suites and scoped pytest run | PASS |
| AC5. ruff clean | Isolated task-scoped ruff run reports All checks passed. | ruff check on both task files | PASS |

### Verdict: PASS
- Confidence .94. The earlier AC3 predicate gap is closed, the implementation still satisfies the refactor contract, and no critical quality issues remain.

### Action Taken
- Appended review evidence to task #563.
- Preparing to move task #563 to docs.

[[2026-03-25]] Wed 17:36
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | DRY internal refactor; no behavior or API change |
| 2 | Docstrings | Yes | Updated | Added docstring to _select_from_sources(); all other private helpers already had docstrings |
| 3 | docs/sources/overview.md | No | N/A | Pattern is BookmarkStore (internal prior art); no external sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |

### Files Updated
- src/owlbear/memory/knowledge/source_store.py (docstring only)

### Scratch Files Cleaned
- docs/scratch/563-architect.md (deleted)
- docs/scratch/563-builder-notes.tmp (deleted)

[[2026-03-25]] Wed 17:36
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | DRY internal refactor; no behavior or API change |
| 2 | Docstrings | Yes | Updated | Added docstring to _select_from_sources(); all other private helpers already had docstrings |
| 3 | docs/sources/overview.md | No | N/A | Pattern is BookmarkStore (internal prior art); no external sources |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |

### Files Updated
- src/owlbear/memory/knowledge/source_store.py (docstring only)

### Scratch Files Cleaned
- docs/scratch/563-architect.md (deleted)
- docs/scratch/563-builder-notes.tmp (deleted)

[[2026-03-25]] Wed 18:02
## Audit
### AC Verification
| AC | Evidence | Status |
|-----|----------|--------|
| AC1. _SELECT_COLS defined once as class attribute | source_store.py:62-64, class attr with canonical 11-col string | PASS |
| AC2. All 6 SELECT queries reference _SELECT_COLS | _select_from_sources() at :66-68 used in get(:99), get_by_name(:109), list_all(:120,:125), list_enabled(:136,:143) | PASS |
| AC3. Column order unchanged | _row_to_model row[0]=id through row[10]=updated_at matches _SELECT_COLS order | PASS |
| AC4. Existing tests pass unchanged | 48/48 passed; legacy CRUD tests unmodified | PASS |
| AC5. ruff clean | All checks passed on both files | PASS |

### Test Results
- pytest (scoped): 48 passed, 0 failed
- pytest (full suite): 4388 passed, 80 failed (all pre-existing RED-phase or unrelated)
- ruff: clean

### AC Quality Score: 4
AC was specific and verifiable. Minor gap: AC3 lacked predicate-level test guidance, caught by reviewer and fixed in retry cycle. Architect referenced BookmarkStore prior art appropriately.

### Commits Verified
- 358dc7b docs: add docstring to _select_from_sources (#563, writer)
- 22279c6 test: add predicate-level tests (#563, test-writer)
- Upstream implementation via #892 (a1eefc2, 9220f1a, 1a3f1df)

### Uncommitted Worktree Note
- tests/test_knowledge_source_store.py has cosmetic formatting drift (line wrapping collapse). Not task-scoped; not committed by auditor.

### Confidence: .97
### Action: archive
