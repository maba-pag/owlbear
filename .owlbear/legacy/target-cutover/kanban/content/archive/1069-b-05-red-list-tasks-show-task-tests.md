---
id: 1069
title: 'B-05: RED — list_tasks + show_task tests'
status: archived
priority: medium
created: 2026-04-21T10:48:33.304571+00:00
updated: 2026-04-25T01:53:24.605549+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1068
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.1, §1.2, §3.3, §4
Module: `serve/kanban/tests/test_engine_reads.py`

Test AgentView.list_tasks and AgentView.show_task. Covers query filtering, ids-exclusive validation, section extraction, dep_status computation, archived-task reads, missing_ids population, guidance emission.

## Acceptance Criteria

- [ ] AC1: `show_task(<archived_id>)` returns TaskFull with archived fields populated
- [ ] AC2: `list_tasks(status="archived")` returns archived only
- [ ] AC3: `list_tasks(ids=[active, archived, missing])` returns 2 + `missing_ids=[missing]`
- [ ] AC10: `show_task(id, section="audit")` returns matching heading content (case-insensitive)
- [ ] AC11: `show_task(id, section="missing")` → `body=None`, `missing_sections=["missing"]`
- [ ] AC12: Multiple section matches → guidance includes occurrence count
- [ ] AC15: `list_tasks(ids=[1], status="todo")` → ValidationError(ERR_IDS_EXCLUSIVE)
- [ ] Invalid `status` enum → ValidationError(ERR_INVALID_STATUS)
- [ ] Invalid `priority` enum → ValidationError(ERR_INVALID_PRIORITY)
- [ ] Invalid `archival_reason` enum → ValidationError(ERR_ARCHIVAL_REASON_INVALID)
- [ ] `show_task` with empty `section=""` → ValidationError(ERR_SECTION_EMPTY)
- [ ] `show_task` with non-existent id → NotFoundError(ERR_NOT_FOUND)
- [ ] Default: excludes archived unless `status="archived"` or `ids` used
- [ ] `dep_status` computed per §3.3 (blocked > redirect > ok > None)
- [ ] All tests fail (RED phase)
[[2026-04-24]]
## Test-Writer Notes
- Test file: `serve/kanban/tests/test_engine_reads_1069.py`
- Classes: `TestFromAC_ListTasksValidation`, `TestFromAC_ListTasksArchivedReads`, `TestFromAC_ShowTaskArchived`, `TestFromAC_ShowTaskSectionConcat`, `TestFromAC_DepStatus`
- Tests per category: happy 0, edge 3, error 11, boundary 6
- Total: 20 tests, all FAIL
- ruff: clean

**AC coverage:**
| AC | Tests |
|---|---|
| AC1 — show_task(archived_id) returns TaskFull | 4 tests in TestFromAC_ShowTaskArchived |
| AC2 — list_tasks(status="archived") returns archived only | 2 tests |
| AC3 — list_tasks(ids=[active, archived, missing]) → 2 + missing_ids | 3 tests |
| AC12 / D56 — multiple section matches body concatenated | 1 test (shows only first returned) |
| AC14 — dep_status ok for active dep in different status bucket | 1 test (gets "blocked" instead of "ok") |
| AC15 — ids exclusive with status/priority/tag/unclaimed/blocked/search | 6 tests |
| Invalid status enum → ERR_INVALID_STATUS | 1 test |
| Invalid priority enum → ERR_INVALID_PRIORITY | 1 test |
| Invalid archival_reason enum → ERR_ARCHIVAL_REASON_INVALID | 1 test |

**Key findings for builder:**
- `AgentView.list_tasks` has no `archival_reason` parameter yet
- `status="archived"` must trigger reading from `archive/` dir (currently does not)
- `ids` must search both `tasks/` and `archive/` dirs (currently active-only)
- No validation exists for ids-exclusive, invalid status, priority, or archival_reason
- `dep_status` uses filtered `active_ids` — must use all tasks/ IDs, not just filtered result
- Section multi-match: `matches[0].content` must become all matches concatenated (D56)

**Commit:** `690566b1` — test: add failing tests for list_tasks + show_task reads (#1069, test-writer)
[[2026-04-24]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py.
- Fixes applied:
  - AgentView.list_tasks now validates ids-exclusive filters (ERR_IDS_EXCLUSIVE).
  - AgentView.list_tasks now validates status/priority/archival_reason enums (ERR_INVALID_STATUS, ERR_INVALID_PRIORITY, ERR_ARCHIVAL_REASON_INVALID).
  - list_tasks(status="archived") now reads archive dir; ids-based reads now search both tasks and archive and report missing_ids correctly.
  - KanbanEngine.list_tasks dep_status now computes against all active task IDs, not just filtered result.
  - KanbanEngine.show_task now falls back to archive when id is absent from tasks.
  - show_task(section=...) now concatenates all matching sections and emits occurrence-count guidance.
- Tests:
  - RED pre-check: serve/kanban/tests/test_engine_reads_1069.py -> 20 failed.
  - GREEN check: serve/kanban/tests/test_engine_reads_1069.py -> 20 passed.
  - Regression spot-check: serve/kanban/tests/test_engine_coverage_1068.py -k "AgentViewShowTask or dep_status" -> 12 passed.
- Coverage:
  - Task-scoped coverage (engine target via test_engine_reads_1069): 31%.
  - Broad kanban-suite run: 74% (run also shows pre-existing unrelated failures in other tests).
- Ruff: clean on changed source + task test.
- Commit: 486f15bf (feat: implement list/show reads for archived + ids semantics (#1069, builder)).
[[2026-04-24]]
## Review Evidence

Tests
- Quality-Runner scoped run on serve/kanban/tests/test_engine_reads_1069.py: 20 passed, 0 failed.
- Editor diagnostics: no errors in serve/kanban/src/owlbear_kanban/engine.py or serve/kanban/tests/test_engine_reads_1069.py.

Lint
- Initial scoped lint on serve/kanban/src/ plus the task test surfaced one unrelated W293 in serve/kanban/src/owlbear_kanban/storage.py:252.
- Reran lint on the builder-owned surface only: serve/kanban/src/owlbear_kanban/engine.py and serve/kanban/tests/test_engine_reads_1069.py. Result: clean.

Coverage
- Quality-Runner scoped coverage for owlbear_kanban.engine: 30%.

AC compliance

| AC line | Evidence | Status |
|---|---|---|
| AC1: show_task on an archived id returns archived fields | serve/kanban/tests/test_engine_reads_1069.py:321-382 proves lookup, id, status, and archival_reason, but never asserts archival_refs even though the fixture always sets archival_refs to an empty list at serve/kanban/tests/test_engine_reads_1069.py:83 | FAIL: proof incomplete |
| AC2: list_tasks with archived status returns archived only | serve/kanban/tests/test_engine_reads_1069.py:219-257 asserts archived membership and active exclusion | PASS |
| AC3: list_tasks with active, archived, and missing ids returns exactly two tasks and missing_ids equal to the missing id | serve/kanban/tests/test_engine_reads_1069.py:259-311 checks membership only; it never asserts exact cardinality or exact missing_ids equality | FAIL: proof incomplete |
| AC10: show_task section lookup is case-insensitive | No task-owned assertion for section audit or any case-variant lookup. The only section test is exact-case Goals at serve/kanban/tests/test_engine_reads_1069.py:392-418 | FAIL: missing |
| AC11: missing section returns body None and missing_sections populated | No task-owned assertion. No missing_sections match exists in serve/kanban/tests/test_engine_reads_1069.py | FAIL: missing |
| AC12: multiple section matches emit occurrence-count guidance | The task-owned test at serve/kanban/tests/test_engine_reads_1069.py:392-418 checks concatenated body only. No guidance assertion exists in the file | FAIL: missing |
| AC15: ids exclusive with status | serve/kanban/tests/test_engine_reads_1069.py:144-149 asserts ERR_IDS_EXCLUSIVE | PASS |
| Invalid status enum raises ERR_INVALID_STATUS | serve/kanban/tests/test_engine_reads_1069.py:186-191 asserts ERR_INVALID_STATUS | PASS |
| Invalid priority enum raises ERR_INVALID_PRIORITY | serve/kanban/tests/test_engine_reads_1069.py:193-198 asserts ERR_INVALID_PRIORITY | PASS |
| Invalid archival_reason enum raises ERR_ARCHIVAL_REASON_INVALID | serve/kanban/tests/test_engine_reads_1069.py:200-209 asserts ERR_ARCHIVAL_REASON_INVALID | PASS |
| Empty section raises ERR_SECTION_EMPTY | No task-owned assertion. No ERR_SECTION_EMPTY match exists in serve/kanban/tests/test_engine_reads_1069.py | FAIL: missing |
| Non-existent id raises ERR_NOT_FOUND | No task-owned assertion for a missing id in serve/kanban/tests/test_engine_reads_1069.py | FAIL: missing |
| Default list_tasks excludes archived unless archived status or ids are used | No bare view.list_tasks() assertion exists in serve/kanban/tests/test_engine_reads_1069.py | FAIL: missing |
| dep_status precedence is blocked, then redirect, then ok, then None | serve/kanban/tests/test_engine_reads_1069.py:432-458 proves only one ok path. Blocked, redirect, and None are unproved | FAIL: proof incomplete |
| Historical RED prerequisite: all task tests failed before implementation | Builder note records 20 failing tests before the fix, but this state is not independently reproducible from the current snapshot | N/A: historical only |

Critical findings
- Live implementation defect in the changed archived-read path: KanbanEngine.show_task trusts the warm active-file index first at serve/kanban/src/owlbear_kanban/engine.py:808-817 and raises immediately when that active path is gone, so it never reaches the archive fallback at serve/kanban/src/owlbear_kanban/engine.py:831-833. move_task with archived status moves the file at serve/kanban/src/owlbear_kanban/engine.py:1022-1068 but does not clear _task_cache or _id_to_filename; those caches are only cleared by refresh_config at serve/kanban/src/owlbear_kanban/engine.py:527-542. storage.write_task also writes to tasks/ before the move at serve/kanban/src/owlbear_kanban/storage.py:355-385. Result: after archiving a previously indexed task in the same engine instance, show_task can incorrectly report not found even though the archived file exists.
- The task-owned TestFromAC suite is weaker than the written AC. Literal AC text governs. Current gaps are not rescued by adjacent suites.

Security and process checks
- No secret, injection, or path-traversal issue found in the changed read paths.
- Snapshot-only review could not attribute any TestFromAC drift to builder edits specifically, but the current AC-scoped suite is objectively insufficient against the task body.
- One builder section only. No retry-loop issue detected.

Deductions
- 0.25 deduction for the live warm-cache archived show_task defect.
- 0.20 deduction for missing task-owned AC proof on AC10, AC11, AC12, empty-section validation, not-found handling, and default archived exclusion.
- 0.10 deduction for lax proof on AC1, AC3, and dep_status precedence.
- 0.05 deduction for low scoped module coverage on owlbear_kanban.engine.

Verdict
- FAIL.
- Confidence: 0.40.
- Action: reject to in-progress. Fix the warm-cache archived show_task path and restore task-owned AC proof for the missing and lax cases before returning to review.
[[2026-04-24]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) to fix warm-cache archived lookup behavior and cache invalidation during archive moves.
- Fixes applied:
  - In `KanbanEngine.show_task`, stale `id -> filename` entries no longer raise immediately when the active file was moved; the code now clears stale cache/index entries and falls back to the archived file when present.
  - In `KanbanEngine.move_task(status="archived")`, the moved task's `_task_cache` and `_id_to_filename` entries are invalidated immediately after file move to avoid stale active-path lookups.
- Tests:
  - `uv run pytest serve/kanban/tests/test_engine_reads_1069.py -q --tb=short` -> 20 passed.
  - `uv run pytest serve/kanban/tests/test_engine_coverage_1068.py -k "AgentViewShowTask or dep_status" -q --tb=short` -> 12 passed.
  - Scoped combined check: `uv run pytest serve/kanban/tests/test_engine_reads_1069.py serve/kanban/tests/test_engine_coverage_1068.py -q --tb=short --cov=owlbear_kanban.engine --cov-report=term-missing` -> 248 passed.
  - Repro check for review finding: warm-cache + archive + show_task now returns archived task successfully (no FileNotFoundError).
- Coverage:
  - Scoped pair coverage on `owlbear_kanban.engine`: 84%.
  - Broader engine test sweep (`serve/kanban/tests/test_engine*.py`): 95% on `owlbear_kanban.engine`.
- Lint: `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/tests/test_engine_reads_1069.py` -> clean.
- Evidence summary:
  - The specific live defect reported in review (stale active cache preventing archive fallback in same engine instance) is fixed and reproducible as resolved.
  - Broad engine sweep still contains 5 unrelated pre-existing failures in `test_engine_storage.py` and `test_engine_crash_safety_1101.py` due config schema/agent_map assumptions; task-owned read-path suites remain green.
[[2026-04-24]]
## Review Evidence
### Test Results
- Quality-Runner scoped run on serve/kanban/tests/test_engine_reads_1069.py and serve/kanban/tests/test_engine_coverage_1068.py: 248 passed, 0 failed, 0 skipped.

### Lint
- Quality-Runner scoped lint on serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/tests/test_engine_reads_1069.py, and serve/kanban/tests/test_engine_coverage_1068.py: clean.

### Coverage
- owlbear_kanban.engine: 84%. This is below the reviewer target of 90% for the touched module.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 archived show_task returns archived fields | test_show_archived_task_returns_response, test_show_archived_task_id_matches, test_show_archived_task_archival_reason_populated, test_show_archived_task_status_is_archived at serve/kanban/tests/test_engine_reads_1069.py:324,339,354,369 | Partially. Cold archive lookup, id, status, and archival_reason are asserted, but archival_refs and the warmed cache archive transition are not. | LAX |
| AC2 list_tasks with archived status returns archived only | test_status_archived_returns_archived_task and test_status_archived_excludes_active_tasks at serve/kanban/tests/test_engine_reads_1069.py:224,241 | Yes. | COVERED |
| AC3 ids lookup returns exactly two tasks and missing_ids equal to the missing id | test_ids_with_archived_task_returns_it, test_ids_found_archived_not_in_missing_ids, test_ids_truly_missing_id_in_missing_ids at serve/kanban/tests/test_engine_reads_1069.py:259,277,294 | No. Membership is checked, but exact task count and exact missing_ids equality are not. | LAX |
| AC10 single-section lookup is case-insensitive | none in the task-owned file | No. | MISSING |
| AC11 missing section returns body None and missing_sections populated | none in the task-owned file | No. | MISSING |
| AC12 multiple section matches include occurrence-count guidance | test_multiple_section_matches_body_contains_all_content at serve/kanban/tests/test_engine_reads_1069.py:399 | No. The test checks concatenated body only and never inspects guidance. | MISSING |
| AC15 ids exclusive with status raises ERR_IDS_EXCLUSIVE | test_ids_exclusive_with_status_raises at serve/kanban/tests/test_engine_reads_1069.py:144 | Yes. | COVERED |
| Invalid status raises ERR_INVALID_STATUS | test_invalid_status_raises_err_invalid_status at serve/kanban/tests/test_engine_reads_1069.py:186 | Yes. | COVERED |
| Invalid priority raises ERR_INVALID_PRIORITY | test_invalid_priority_raises_err_invalid_priority at serve/kanban/tests/test_engine_reads_1069.py:193 | Yes. | COVERED |
| Invalid archival_reason raises ERR_ARCHIVAL_REASON_INVALID | test_invalid_archival_reason_raises_err_archival_reason_invalid at serve/kanban/tests/test_engine_reads_1069.py:200 | Yes. | COVERED |
| Empty section raises ERR_SECTION_EMPTY | none in the task-owned file | No. | MISSING |
| Missing task id raises ERR_NOT_FOUND | none in the task-owned file | No. | MISSING |
| Default list_tasks excludes archived unless archived status or ids is used | none in the task-owned file | No. | MISSING |
| dep_status precedence is blocked, then redirect, then ok, then None | test_dep_status_ok_when_dep_active_in_different_status at serve/kanban/tests/test_engine_reads_1069.py:437 | No. Only the ok branch is task-owned. | LAX |
| Historical RED precondition | builder note only | Not independently verifiable from the current snapshot. | N/A |

#### Security Review
- No secret, injection, traversal, unsafe deserialization, or unsafe path handling issue found in the changed read-path code.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_ListTasksValidation, TestFromAC_ListTasksArchivedReads, TestFromAC_ShowTaskArchived | No direct assertion deletions or relaxed checks observed in the current snapshot. | PRESERVED |
| TestFromAC_ShowTaskSectionConcat | Still proves concatenated body only, not the occurrence-count guidance required by the literal AC12 text. | WEAKENED |
| TestFromAC_DepStatus | Still proves only the ok branch, not blocked, redirect, and None precedence from the task AC. | WEAKENED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC3 does not assert exact result count or exact missing_ids; AC12 does not assert guidance. |
| Negative and error-path coverage | WEAK | No task-owned tests cover missing section, empty section, or not-found wrapping. |
| Manual mutation reasoning | WEAK | Removing the guidance append at serve/kanban/src/owlbear_kanban/engine.py:1741-1742, the empty-section validation at serve/kanban/src/owlbear_kanban/engine.py:1721-1724, or the default archived exclusion path would still leave the task file green. |
| Test independence | ADEQUATE | Each test creates a fresh board and fresh AgentView instance. |
| Descriptive test names | STRONG | Test names are scenario-specific and readable throughout the file. |

#### Data Safety
- No data safety issue found in the scoped read-path changes.

#### Implementation-Aware Gaps
- The prior runtime defect from the first review appears addressed in source. KanbanEngine.show_task now clears stale index entries and checks the archive path in serve/kanban/src/owlbear_kanban/engine.py:808-823, and move_task(status="archived") invalidates cache entries in serve/kanban/src/owlbear_kanban/engine.py:1058-1059.
- The remaining failure is proof quality. The task-owned TestFromAC file still does not exercise case-insensitive single-section lookup, missing-section handling, empty-section validation, not-found wrapping, default archived exclusion, or full dep_status precedence.
- Adjacent engine coverage tests do prove some nearby behavior, including not-found and blocked or redirect dep_status branches in serve/kanban/tests/test_engine_coverage_1068.py:901,1666,1675, but AC proof must exist in the task-owned TestFromAC surface as well.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation across retries | Yes |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- serve/kanban/tests/test_engine_reads_1069.py still contains RED-phase commentary describing the pre-fix state, which makes the file harder to trust during review.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 archived show_task returns archived fields | serve/kanban/tests/test_engine_reads_1069.py:324,339,354,369 proves cold archived lookup, id, status, and archival_reason only. | test_show_archived_task_returns_response, test_show_archived_task_id_matches, test_show_archived_task_archival_reason_populated, test_show_archived_task_status_is_archived | FAIL |
| AC2 archived list returns archived only | serve/kanban/tests/test_engine_reads_1069.py:224,241 asserts archived membership and active exclusion. | test_status_archived_returns_archived_task, test_status_archived_excludes_active_tasks | PASS |
| AC3 ids lookup returns two tasks plus missing_ids equal to the missing id | serve/kanban/tests/test_engine_reads_1069.py:259,277,294 checks membership only. | test_ids_with_archived_task_returns_it, test_ids_found_archived_not_in_missing_ids, test_ids_truly_missing_id_in_missing_ids | FAIL |
| AC10 section lookup is case-insensitive | No task-owned assertion. Implementation branch exists at serve/kanban/src/owlbear_kanban/engine.py:1729-1736 only. | none | FAIL |
| AC11 missing section returns body None and missing_sections | No task-owned assertion. Implementation branch exists at serve/kanban/src/owlbear_kanban/engine.py:1736-1737 only. | none | FAIL |
| AC12 multiple matches include occurrence-count guidance | serve/kanban/tests/test_engine_reads_1069.py:399 checks body concatenation only; guidance emission at serve/kanban/src/owlbear_kanban/engine.py:1741-1742 is unasserted. | test_multiple_section_matches_body_contains_all_content | FAIL |
| AC15 ids exclusive with status raises ERR_IDS_EXCLUSIVE | serve/kanban/tests/test_engine_reads_1069.py:144 asserts ERR_IDS_EXCLUSIVE. | test_ids_exclusive_with_status_raises | PASS |
| Invalid status raises ERR_INVALID_STATUS | serve/kanban/tests/test_engine_reads_1069.py:186 asserts ERR_INVALID_STATUS. | test_invalid_status_raises_err_invalid_status | PASS |
| Invalid priority raises ERR_INVALID_PRIORITY | serve/kanban/tests/test_engine_reads_1069.py:193 asserts ERR_INVALID_PRIORITY. | test_invalid_priority_raises_err_invalid_priority | PASS |
| Invalid archival_reason raises ERR_ARCHIVAL_REASON_INVALID | serve/kanban/tests/test_engine_reads_1069.py:200 asserts ERR_ARCHIVAL_REASON_INVALID. | test_invalid_archival_reason_raises_err_archival_reason_invalid | PASS |
| Empty section raises ERR_SECTION_EMPTY | No task-owned assertion. Validation exists at serve/kanban/src/owlbear_kanban/engine.py:1721-1724 only. | none | FAIL |
| Missing task id raises ERR_NOT_FOUND | No task-owned assertion. Wrapper exists at serve/kanban/src/owlbear_kanban/engine.py:1708-1711 and 1578-1581 only. | none | FAIL |
| Default list_tasks excludes archived unless explicitly requested | No bare view.list_tasks() assertion in the task-owned file. | none | FAIL |
| dep_status precedence is blocked, then redirect, then ok, then None | serve/kanban/tests/test_engine_reads_1069.py:437 proves the ok branch only. | test_dep_status_ok_when_dep_active_in_different_status | FAIL |
| Historical RED precondition | Builder body records the earlier red run. Current snapshot cannot re-prove it. | builder note only | N/A |

### Confidence: 0.68
### Verdict: FAIL
### Action
- Reject to todo. The current snapshot looks implementation-correct on the previously reported runtime bug, but the task-owned TestFromAC proof and scoped module coverage remain insufficient for a review pass.

### Reflection
- The scoped quality run cleanly separated this task from unrelated engine-suite failures.
- Adjacent engine regression tests prove some nearby behavior, but they do not replace task-owned AC proof.
- The builder retry changed the routing: the first review found a live runtime defect, while this review finds a test-proof gap.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: reviewer cited missing AC proof for 9 AC lines / lax proof for 3 others.
- Test file: `serve/kanban/tests/test_engine_reads_1069.py`
- New classes added: `TestFromAC_ShowTaskArchivedFields`, `TestFromAC_ListTasksIdsExact`, `TestFromAC_ShowTaskSectionLookup`, `TestFromAC_ListTasksDefaultExclusion`, `TestFromAC_ShowTaskSectionGuidance`
- New methods added to existing classes: `TestFromAC_DepStatus` (+3 methods), `TestFromAC_ShowTaskSectionConcat` (+guidance assertion via new class)
- Tests per category (new): happy 0, edge 3, error 4, boundary 7 — 14 new tests
- Total: 34 tests (20 original + 14 new), all PASS
- ruff: clean
- Commit: bc716fd6

**AC coverage (retry gaps closed):**
| Gap | New Test(s) |
|---|---|
| AC1: archival_refs field asserted | test_show_archived_task_archival_refs_is_list |
| AC1: warm-cache archive transition | test_show_archived_task_after_warm_cache_move |
| AC3: exact task count == 2 | test_ids_result_count_is_exactly_two |
| AC3: missing_ids == [999] exactly | test_ids_missing_ids_exact_equality |
| AC10: case-insensitive section | test_case_insensitive_section_lookup_returns_content |
| AC11: missing section body=None | test_missing_section_body_is_none |
| AC11: missing_sections populated | test_missing_section_populates_missing_sections |
| AC12: guidance occurrence count | test_multiple_section_matches_guidance_has_occurrence_count |
| ERR_SECTION_EMPTY | test_empty_section_raises_err_section_empty |
| ERR_NOT_FOUND | test_not_found_id_raises_err_not_found |
| Default excludes archived | test_default_list_excludes_archived_task |
| dep_status blocked (dropped reason) | test_dep_status_blocked_when_dep_archived_dropped |
| dep_status redirect (duplicate reason) | test_dep_status_redirect_when_dep_archived_duplicate |
| dep_status None (no deps) | test_dep_status_none_when_task_has_no_deps |

**Note on PASS vs FAIL:** All 14 new tests PASS because the builder already implemented all behaviors across 2 prior rounds. Tests serve as direct AC regression guards. Implementation is complete; no new builder work needed for these specific paths.
[[2026-04-24]]
## Builder Notes
- Code changes: none required in this cycle. Current implementation in serve/kanban/src/owlbear_kanban/engine.py already satisfies the retry AC-proof test additions from test-writer commit bc716fd6.
- Verification run (task-owned):
  - uv run pytest serve/kanban/tests/test_engine_reads_1069.py -q --tb=short --cov=owlbear_kanban.engine --cov-report=term-missing -> 34 passed, 0 failed; module coverage 30% on this narrow slice.
  - uv run pytest serve/kanban/tests/test_engine_coverage_1068.py -k "AgentViewShowTask or dep_status" -q --tb=short -> 12 passed, 0 failed.
  - uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/tests/test_engine_reads_1069.py -> clean.
- Additional regression sampling:
  - uv run pytest tests/test_engine_coverage_1113.py serve/kanban/tests/test_engine_coverage_1068.py serve/kanban/tests/test_engine_coverage_1110.py serve/kanban/tests/test_engine_reads_1069.py -q --tb=short --cov=owlbear_kanban.engine --cov-report=term-missing -> 344 passed, 0 failed; module coverage 85%.
- Broad-suite context:
  - Broad non-API suite remains red from unrelated pre-existing failures in cockpit and storage suites; this task’s owned surfaces are green.
- Evidence summary:
  - AC-proof additions introduced by test-writer are now green against existing engine behavior.
  - No further surgical code intervention required for #1069 in builder phase.
[[2026-04-24]]
## Review Evidence

### Test Results
- Quality-Runner expanded engine-only run on `tests/test_engine_coverage_1113.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, `serve/kanban/tests/test_engine_coverage_1110.py`, `serve/kanban/tests/test_engine_reads_1069.py`, `serve/kanban/tests/test_engine_init_1067.py`, `serve/kanban/tests/test_engine_models.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_create_edit_1070.py`, `serve/kanban/tests/test_engine_init_1068.py`, and `serve/kanban/tests/test_engine_atomicity_1104.py`: 603 passed, 0 failed, 0 skipped.

### Lint
- Quality-Runner scoped lint on `serve/kanban/src/owlbear_kanban/engine.py` plus the 10 engine test files above: clean.

### Coverage
- `owlbear_kanban.engine`: 94% (Quality-Runner expanded scoped run). Coverage is no longer the blocker for this task.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1: `show_task(<archived_id>)` returns archived fields populated | `test_show_archived_task_returns_response` (`serve/kanban/tests/test_engine_reads_1069.py:325`), `test_show_archived_task_id_matches` (`:340`), `test_show_archived_task_archival_reason_populated` (`:355`), `test_show_archived_task_status_is_archived` (`:370`), `test_show_archived_task_archival_refs_is_list` (`:529`, asserts `archival_refs == []` at `:542-543`), `test_show_archived_task_after_warm_cache_move` (`:545`) | Yes. Archived response shape and the warm-cache regression path are both pinned. | COVERED |
| AC2: `list_tasks(status="archived")` returns archived only | `test_status_archived_returns_archived_task` (`:225`), `test_status_archived_excludes_active_tasks` (`:242`) | Yes. | COVERED |
| AC3: `list_tasks(ids=[active, archived, missing])` returns 2 + `missing_ids=[missing]` | `test_ids_with_archived_task_returns_it` (`:260`), `test_ids_found_archived_not_in_missing_ids` (`:278`), `test_ids_truly_missing_id_in_missing_ids` (`:295`), `test_ids_result_count_is_exactly_two` (`:579`, asserts exact count at `:593`), `test_ids_missing_ids_exact_equality` (`:597`, asserts exact equality at `:611`) | Yes. | COVERED |
| AC10: case-insensitive section lookup | `test_case_insensitive_section_lookup_returns_content` (`:627`, asserts body content at `:642`) | Yes. | COVERED |
| AC11: missing section returns `body=None`, `missing_sections=["missing"]` | `test_missing_section_body_is_none` (`:644`, asserts `body is None` at `:656`), `test_missing_section_populates_missing_sections` (`:658`) | Partially. The task-owned test checks containment only at `:670-671`; it does not pin the exact single-item list shape required by the AC, even though the implementation contract is explicit at `serve/kanban/src/owlbear_kanban/engine.py:1738`. | LAX |
| AC12: multiple section matches include occurrence count in guidance | `test_multiple_section_matches_body_contains_all_content` (`:400`) and `test_multiple_section_matches_guidance_has_occurrence_count` (`:727`) | No. The guidance test asserts non-empty guidance at `:744` and only that some entry contains the word `occurrences` at `:745`; it does not assert the numeric count required by the AC, while the implementation contract is `f"Section '{section_name}' matched {len(matches)} occurrences."` at `serve/kanban/src/owlbear_kanban/engine.py:1742-1743`. A mutation from `matched 2 occurrences` to `matched occurrences` would still pass. | LAX |
| AC15: `ids` exclusive with `status` | `test_ids_exclusive_with_status_raises` (`:145`) | Yes. | COVERED |
| Invalid `status` enum | `test_invalid_status_raises_err_invalid_status` (`:187`) | Yes. | COVERED |
| Invalid `priority` enum | `test_invalid_priority_raises_err_invalid_priority` (`:194`) | Yes. | COVERED |
| Invalid `archival_reason` enum | `test_invalid_archival_reason_raises_err_archival_reason_invalid` (`:201`) | Yes. | COVERED |
| Empty `section=""` | `test_empty_section_raises_err_section_empty` (`:673`) | Yes. | COVERED |
| Non-existent id -> `ERR_NOT_FOUND` | `test_not_found_id_raises_err_not_found` (`:683`, asserts code at `:689`) | Yes. | COVERED |
| Default excludes archived unless explicitly requested | `test_default_list_excludes_archived_task` (`:700`) | Yes. | COVERED |
| `dep_status` precedence `blocked > redirect > ok > None` | `test_dep_status_ok_when_dep_active_in_different_status` (`:438`), `test_dep_status_blocked_when_dep_archived_dropped` (`:462`), `test_dep_status_redirect_when_dep_archived_duplicate` (`:485`), `test_dep_status_none_when_task_has_no_deps` (`:508`) | Yes. | COVERED |
| Historical RED prerequisite | Builder/test-writer notes only | Not independently reproducible from the current snapshot. | N/A |

#### Security Review
- No secret exposure, injection, traversal, unsafe deserialization, or boundary-validation issue found in the reviewed read paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| Existing `TestFromAC_*` coverage in `serve/kanban/tests/test_engine_reads_1069.py` | Additive retry-cycle tests only; no weakened or removed builder-side assertions found in the current snapshot. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC11 pins presence of `"nonexistent"` in `missing_sections` but not exact equality (`serve/kanban/tests/test_engine_reads_1069.py:670-671`). AC12 checks only for the substring `"occurrences"` (`:745`), not the actual count promised by the AC and implementation contract. |
| Negative and error-path coverage | STRONG | Missing section, empty section, not-found, invalid enums, and ids-exclusive validation are all covered in the task-owned file. |
| Manual mutation reasoning | WEAK | Replacing `missing_sections = [section_name]` in `serve/kanban/src/owlbear_kanban/engine.py:1738` with a broader list, or changing the guidance text at `:1742-1743` to omit the numeric count, would still leave the task-owned suite green. |
| Test independence | STRONG | Each test builds a fresh board and fresh `AgentView`/engine instance. |
| Descriptive test names | STRONG | Names are specific and scenario-oriented throughout the task-owned file. |

#### Data Safety
- No data-safety issue found.

#### Implementation-Aware Gaps
- The previously reported warm-cache archive lookup defect is fixed in the live code. `KanbanEngine.show_task` now clears stale index entries and falls back to archive reads (`serve/kanban/src/owlbear_kanban/engine.py:795-833`), and `move_task(status="archived")` invalidates cache/index entries on move (`serve/kanban/src/owlbear_kanban/engine.py:1055-1061`).
- The remaining blocker is test-proof quality in the task-owned RED suite, not implementation correctness.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Prior `## Review Evidence` sections before this review | 2 |
| `## Builder Notes` sections | 3 |
| Approach variation across retries | Yes |
| Assessment | FRICTION |

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 archived fields populated | `serve/kanban/tests/test_engine_reads_1069.py:325,340,355,370,529,545` | archived response + warm-cache regression tests | PASS |
| AC2 archived-only listing | `serve/kanban/tests/test_engine_reads_1069.py:225,242` | archived listing tests | PASS |
| AC3 exact count + exact missing_ids | `serve/kanban/tests/test_engine_reads_1069.py:260,278,295,579,597` with exact asserts at `:593` and `:611` | ids lookup tests | PASS |
| AC10 case-insensitive section lookup | `serve/kanban/tests/test_engine_reads_1069.py:627` with body assertion at `:642` | case-insensitive section test | PASS |
| AC11 `body=None`, exact `missing_sections=[...]` | `serve/kanban/tests/test_engine_reads_1069.py:644,656,658,670-671`; implementation contract `serve/kanban/src/owlbear_kanban/engine.py:1738` | missing section tests | FAIL |
| AC12 guidance includes occurrence count | `serve/kanban/tests/test_engine_reads_1069.py:400,727,744-745`; implementation contract `serve/kanban/src/owlbear_kanban/engine.py:1742-1743` | section concat + guidance tests | FAIL |
| AC15 ids exclusive | `serve/kanban/tests/test_engine_reads_1069.py:145` | ids-exclusive validation test | PASS |
| Invalid status enum | `serve/kanban/tests/test_engine_reads_1069.py:187` | invalid status test | PASS |
| Invalid priority enum | `serve/kanban/tests/test_engine_reads_1069.py:194` | invalid priority test | PASS |
| Invalid archival_reason enum | `serve/kanban/tests/test_engine_reads_1069.py:201` | invalid archival reason test | PASS |
| Empty section -> `ERR_SECTION_EMPTY` | `serve/kanban/tests/test_engine_reads_1069.py:673` | empty section validation test | PASS |
| Missing id -> `ERR_NOT_FOUND` | `serve/kanban/tests/test_engine_reads_1069.py:683,689` | not-found test | PASS |
| Default excludes archived | `serve/kanban/tests/test_engine_reads_1069.py:700` | default list exclusion test | PASS |
| `dep_status` precedence | `serve/kanban/tests/test_engine_reads_1069.py:438,462,485,508` | dep_status tests | PASS |
| Historical RED precondition | prior body notes only | historical | N/A |

### Deductions
- 0.07 deduction for AC12 proof remaining lax on the exact occurrence-count contract.
- 0.03 deduction for AC11 proof remaining lax on the exact `missing_sections` payload shape.

### Confidence: 0.88
### Verdict: FAIL
### Action
- Reject to `backlog`. This is the third review failure on the task, so loop-breaker routing applies. The live implementation now looks correct and the expanded engine-only suite clears coverage, but the task-owned RED suite still does not prove AC11 and AC12 with the exactness required by the written AC.
[[2026-04-24]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests for list_tasks + show_task reads — single test module |
| Interface clarity | PASS | AC lines are precise; 13/15 proven, 2 need assertion tightening |
| Dependency correctness | PASS | Depends on #1068 (done/archived) |
| Module layering | PASS | Test-only; no production layering concern |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | No unnecessary scope |
| Premise challenge | PASS | Tests required per Brief B |
| Pattern consistency | PASS | Follows existing TestFromAC_ class naming pattern |
| Security surface | N/A | Read-only test file |
| Single domain | PASS | Kanban engine domain only |

### Challenge Results
- Challenger: reconsider (0.73)
- Key point: RED task deliverable = test assertions; lax assertions = incomplete deliverable
- Architect response: accepted — REFINE to add surgical fix guidance, then approve

### Loop-Breaker Context
3rd review FAIL at 0.88 confidence. Only two lax assertions remain. Implementation is fully correct. The loop-breaker routing exists for architect intervention — providing surgical direction to break the cycle.

### Test-Writer Fix Guidance (MUST follow exactly)

**AC11 — exact missing_sections shape** (`serve/kanban/tests/test_engine_reads_1069.py:670-671`):
Replace:
```python
assert resp.missing_sections is not None
assert "nonexistent" in resp.missing_sections
```
With:
```python
assert resp.missing_sections == ["nonexistent"]
```
Rationale: AC says `missing_sections=["missing"]` (exact single-item list). Implementation at engine.py:1738 assigns `missing_sections = [section_name]`. Containment check wouldn't catch a broader list mutation.

**AC12 — numeric occurrence count** (`serve/kanban/tests/test_engine_reads_1069.py:745`):
Replace:
```python
assert any("occurrences" in g for g in resp.guidance), f"guidance must include occurrence count; got {resp.guidance!r}"
```
With:
```python
assert any("2 occurrences" in g for g in resp.guidance), (
    f"guidance must include numeric occurrence count; got {resp.guidance!r}"
)
```
Rationale: AC says "guidance includes occurrence count". Implementation at engine.py:1742-1743 emits `f"Section '{section_name}' matched {len(matches)} occurrences."`. The fixture has 2 `## Goals` sections, so the count is 2. Substring-only check wouldn't catch a dropped numeric.

### Verdict: REFINE → APPROVE
### Action: Added surgical test-writer guidance for the 2 remaining assertion tightenings. Advanced to todo. No AC change needed — the AC is already specific; the tests just need to match that specificity.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: architect-loop-breaker provided surgical fix guidance for 2 remaining lax assertions after 3rd review FAIL.
- Test file: `serve/kanban/tests/test_engine_reads_1069.py`
- Changes (assertion tightenings only — no new tests):
  - **AC11** (`test_missing_section_populates_missing_sections`, line 670): replaced `assert resp.missing_sections is not None` + `assert "nonexistent" in resp.missing_sections` → `assert resp.missing_sections == ["nonexistent"]` (exact single-item list equality per AC and engine.py:1738 contract).
  - **AC12** (`test_multiple_section_matches_guidance_has_occurrence_count`, line 745): replaced `"occurrences" in g` → `"2 occurrences" in g`; fixture has 2 `## Goals` sections, so numeric count must appear (per engine.py:1742-1743 contract `f"Section '{section_name}' matched {len(matches)} occurrences."`).
- Verification: 34 tests pass (implementation already satisfies stricter assertions), ruff clean.
- Commit: 52f54417
[[2026-04-24]]
## Builder Notes
- Code changes: none in this cycle. Existing implementation and tests already satisfy the tightened AC assertions from the latest test-writer retry.
- Verification (quality-runner, scoped):
  - `serve/kanban/tests/test_engine_reads_1069.py` + adjacent engine coverage tests (`serve/kanban/tests/test_engine_coverage_1068.py`, `serve/kanban/tests/test_engine_coverage_1110.py`, `tests/test_engine_coverage_1113.py`) -> 344 passed, 0 failed.
  - Ruff on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_reads_1069.py` -> clean.
  - Coverage on `owlbear_kanban.engine` from this narrower set -> 86%.
- Verification (quality-runner, expanded engine-only):
  - Engine-focused suite (`tests/test_engine_coverage_1113.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, `serve/kanban/tests/test_engine_coverage_1110.py`, `serve/kanban/tests/test_engine_reads_1069.py`, `serve/kanban/tests/test_engine_init_1067.py`, `serve/kanban/tests/test_engine_models.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_create_edit_1070.py`, `serve/kanban/tests/test_engine_init_1068.py`, `serve/kanban/tests/test_engine_atomicity_1104.py`) -> 603 passed, 0 failed.
  - Ruff on `serve/kanban/src/owlbear_kanban/engine.py` plus the same test set -> clean.
  - Coverage on `owlbear_kanban.engine` -> 94%.
- Evidence summary:
  - AC-tightened task-owned tests remain green.
  - Lint is clean on source + task surfaces.
  - Coverage gate met via expanded engine-scoped verification.
- Reflection:
  - A narrow task-only coverage run can under-report module confidence for mature shared modules; expanded engine-scoped verification provided the reliable gate signal.
  - No implementation delta was required; this cycle was strictly a verification-and-release pass.
[[2026-04-24]]
## Review Evidence

### Test Results
- Quality-Runner expanded engine-scoped run on `tests/test_engine_coverage_1113.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, `serve/kanban/tests/test_engine_coverage_1110.py`, `serve/kanban/tests/test_engine_reads_1069.py`, `serve/kanban/tests/test_engine_init_1067.py`, `serve/kanban/tests/test_engine_models.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_create_edit_1070.py`, `serve/kanban/tests/test_engine_init_1068.py`, and `serve/kanban/tests/test_engine_atomicity_1104.py`: 608 passed, 0 failed, 0 skipped.

### Lint
- Quality-Runner scoped lint on `serve/kanban/src/owlbear_kanban/engine.py` plus the same engine test set: clean.

### Coverage
- `owlbear_kanban.engine`: 95%.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---|---|---|
| AC1 archived `show_task` returns archived fields | `serve/kanban/tests/test_engine_reads_1069.py:324,339,355,370,529,545` cover archived response shape and warm-cache archive transition | PASS |
| AC2 `list_tasks(status="archived")` returns archived only | `serve/kanban/tests/test_engine_reads_1069.py:224,241` | PASS |
| AC3 ids lookup returns exactly two tasks and exact `missing_ids` | `serve/kanban/tests/test_engine_reads_1069.py:259,277,294,579,597` | PASS |
| AC10 case-insensitive section lookup | `serve/kanban/tests/test_engine_reads_1069.py:627` | PASS |
| AC11 missing section returns `body=None` and exact `missing_sections` | `serve/kanban/tests/test_engine_reads_1069.py:644,658,670` | PASS |
| AC12 multiple section matches include numeric occurrence count in guidance | `serve/kanban/tests/test_engine_reads_1069.py:399,727,744`; implementation message at `serve/kanban/src/owlbear_kanban/engine.py:1743` | PASS |
| AC15 ids exclusive with status raises `ERR_IDS_EXCLUSIVE` | `serve/kanban/tests/test_engine_reads_1069.py:144` | PASS |
| Invalid status raises `ERR_INVALID_STATUS` | `serve/kanban/tests/test_engine_reads_1069.py:186` | PASS |
| Invalid priority raises `ERR_INVALID_PRIORITY` | `serve/kanban/tests/test_engine_reads_1069.py:193` | PASS |
| Invalid archival_reason raises `ERR_ARCHIVAL_REASON_INVALID` | `serve/kanban/tests/test_engine_reads_1069.py:201` | PASS |
| Empty section raises `ERR_SECTION_EMPTY` | `serve/kanban/tests/test_engine_reads_1069.py:673` | PASS |
| Missing task id raises `ERR_NOT_FOUND` | `serve/kanban/tests/test_engine_reads_1069.py:683` | PASS |
| Default `list_tasks()` excludes archived unless explicitly requested | `serve/kanban/tests/test_engine_reads_1069.py:700` | PASS |
| `dep_status` precedence is blocked, redirect, ok, None | The contract remains explicit in the task body at `.owlbear/kanban/tasks/1069-b-05-red-list-tasks-show-task-tests.md:44`. The implementation encodes precedence at `serve/kanban/src/owlbear_kanban/engine.py:584,598,600`, but the task-owned tests at `serve/kanban/tests/test_engine_reads_1069.py:438,462,485,508` cover only isolated single-outcome cases. No mixed-dependency scenario proves blocked beats redirect or redirect beats ok. | FAIL |
| Historical RED precondition | Earlier task body notes only | N/A |

#### Security Review
- No secret exposure, injection, traversal, unsafe deserialization, or boundary-validation issue found in the reviewed read paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| Current `TestFromAC_*` suite in `serve/kanban/tests/test_engine_reads_1069.py` | Current snapshot shows additive and tightened assertions only; no weakened or removed assertions were observed in the live file. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Current task-owned suite uses exact error-code and payload assertions throughout. |
| Negative and error-path coverage | STRONG | Invalid enums, empty section, missing section, and not-found handling are all task-owned. |
| Manual mutation reasoning | WEAK | A regression that misorders multi-dependency precedence would still leave the current single-dependency `dep_status` tests green. |
| Test independence | STRONG | Each test builds an isolated board and fresh view. |
| Descriptive test names | STRONG | Names remain scenario-specific and readable throughout the task-owned file. |

#### Data Safety
- No data-safety issue found.

#### Implementation-Aware Gaps
- The remaining blocker is task-owned proof quality on the explicit `dep_status` precedence contract. The latest architect loop-breaker refined AC11 and AC12 only; it did not remove the `dep_status` AC line from the task body.
- A mixed-dependency case is a significant path here because `_compute_dep_status()` iterates all dependencies and returns early on blocked conditions. Without a test combining redirect and blocked candidates, the precedence claim is under-proved.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Prior review FAIL confidences already recorded in task body | 0.40, 0.68, 0.88 |
| Assessment | Loop-breaker routing applies on this cycle |

### Deductions
- 0.14 deduction for the missing task-owned mixed-dependency proof on the explicit `dep_status` precedence AC.

### Confidence: 0.86
### Verdict: FAIL
### Action
- Reject to `backlog`. Tests, lint, and expanded module coverage are now clean, but the task-owned suite still does not prove the explicit precedence contract for `dep_status`, and this is beyond the third review failure threshold.

### Reflection
- Expanded engine-scoped coverage removed coverage noise; the remaining issue is proof quality, not runtime behavior.
- The latest architect refinement was narrower than the full task header, so the live AC lines still had to be checked directly.
- Single-outcome tests are not enough when the AC names an ordering relation across multiple dependency states.
[[2026-04-24]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only module for list_tasks + show_task reads |
| Interface clarity | PASS | 14/15 AC lines proven; 1 needs a mixed-dependency test |
| Dependency correctness | PASS | Depends on #1068 (archived) |
| Module layering | PASS | Test file, no production layering concern |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | No unnecessary scope |
| Premise challenge | PASS | Tests required per Brief B |
| Pattern consistency | PASS | Follows existing TestFromAC_ class naming |
| Security surface | N/A | Read-only test file |
| Single domain | PASS | Kanban engine domain only |

### Challenge Results
- Challenger: SKIP (REFINE verdict — challenge optional per w-arch-review Step 2.5)
- Rationale: 4th loop-breaker cycle with a single, precisely identified remaining gap. Surgical fix guidance is the correct response, not a full challenge.

### Loop-Breaker Context
4th review FAIL at 0.86 confidence. Only one gap remains: dep_status precedence needs a mixed-dependency test. Implementation is fully correct (verified across 608 engine tests at 95% coverage). All other 14 AC lines PASS. The reviewer correctly identified that single-outcome tests don't prove ordering.

### Test-Writer Fix Guidance (MUST follow exactly)

**dep_status precedence — mixed-dependency test** (add to `TestFromAC_DepStatus` class in `serve/kanban/tests/test_engine_reads_1069.py`):

Add TWO new test methods:

**Test 1: blocked beats redirect**
```python
def test_dep_status_blocked_beats_redirect_with_mixed_deps(self, tmp_path: Path) -> None:
    """Task with two deps: one archived/dropped (→blocked), one archived/duplicate (→redirect).

    §3.3 precedence: blocked > redirect → result must be 'blocked'.
    """
    kanban_dir = _make_board(tmp_path)
    _write_task(kanban_dir, task_id=1, title="A", status="todo", depends_on="[2, 3]")
    _write_task(
        kanban_dir,
        task_id=2,
        title="DepDropped",
        status="archived",
        archival_reason="dropped",
        subdir="archive",
    )
    _write_task(
        kanban_dir,
        task_id=3,
        title="DepDuplicate",
        status="archived",
        archival_reason="duplicate",
        subdir="archive",
    )
    view = _make_view(kanban_dir)
    resp = view.list_tasks(status="todo")
    task_a = next((t for t in resp.tasks if t.id == 1), None)
    assert task_a is not None
    assert task_a.dep_status == "blocked", (
        f"Mixed deps (dropped+duplicate); §3.3 blocked > redirect → expected 'blocked' but got {task_a.dep_status!r}"
    )
```

**Test 2: redirect beats ok**
```python
def test_dep_status_redirect_beats_ok_with_mixed_deps(self, tmp_path: Path) -> None:
    """Task with two deps: one archived/duplicate (→redirect), one active (→ok).

    §3.3 precedence: redirect > ok → result must be 'redirect'.
    """
    kanban_dir = _make_board(tmp_path)
    _write_task(kanban_dir, task_id=1, title="A", status="todo", depends_on="[2, 3]")
    _write_task(
        kanban_dir,
        task_id=2,
        title="DepDuplicate",
        status="archived",
        archival_reason="duplicate",
        subdir="archive",
    )
    _write_task(kanban_dir, task_id=3, title="DepActive", status="research")
    view = _make_view(kanban_dir)
    resp = view.list_tasks(status="todo")
    task_a = next((t for t in resp.tasks if t.id == 1), None)
    assert task_a is not None
    assert task_a.dep_status == "redirect", (
        f"Mixed deps (duplicate+active); §3.3 redirect > ok → expected 'redirect' but got {task_a.dep_status!r}"
    )
```

Rationale: The implementation at engine.py:579-605 uses early-return for "blocked" and accumulation for "redirect", but without a test exercising both paths in one task, a mutation reordering the conditionals would leave the suite green. These two tests prove the pairwise ordering: blocked > redirect and redirect > ok.

### Verdict: REFINE → APPROVE
### Action: Added surgical test-writer guidance for the 1 remaining mixed-dependency precedence test. Advanced to todo. AC text is already specific — tests just need a multi-dep scenario to prove ordering.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: architect loop-breaker (5th cycle) provided surgical fix guidance for the 1 remaining lax AC: dep_status precedence needed mixed-dependency tests.
- Test file: `serve/kanban/tests/test_engine_reads_1069.py`
- Changes: added 2 new test methods to `TestFromAC_DepStatus`:
  - `test_dep_status_blocked_beats_redirect_with_mixed_deps` — task with deps archived/dropped + archived/duplicate → proves blocked > redirect
  - `test_dep_status_redirect_beats_ok_with_mixed_deps` — task with deps archived/duplicate + active → proves redirect > ok
- Total: 36 tests (34 prior + 2 new), all PASS (implementation already satisfies §3.3 precedence)
- ruff: clean
- Commit: 46f30fa3

**AC coverage (gap closed):**
| Gap | New Test(s) |
|---|---|
| dep_status blocked > redirect (mixed deps) | test_dep_status_blocked_beats_redirect_with_mixed_deps |
| dep_status redirect > ok (mixed deps) | test_dep_status_redirect_beats_ok_with_mixed_deps |
[[2026-04-24]]
## Builder Notes
- Implementation: no code changes in this cycle; existing `serve/kanban/src/owlbear_kanban/engine.py` behavior already satisfies the latest task-owned AC assertions.
- Tests (quality-runner): scoped + adjacent engine run is green with 346 passed, 0 failed, 0 skipped.
- Coverage: `owlbear_kanban.engine` at 86% for this scoped verification slice.
- Ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_reads_1069.py`.
- Evidence summary: all task-owned `TestFromAC_*` paths for archived reads, section handling, ids semantics, and dep_status precedence are currently passing; no additional surgical implementation required.

- Reflection:
  - Historical retries created heavy task-body noise; current-cycle decisions were based on fresh quality-runner evidence only.
  - Scoped verification avoided unrelated suite failures and kept this cycle task-owned.
  - Expanded adjacent engine tests gave a more trustworthy confidence signal than single-file coverage alone.
  - Verification-only builder cycles should explicitly state "no code changes" to prevent ambiguity downstream.
[[2026-04-25]]
## Review Evidence

### Test Results
- Quality-Runner task-plus-adjacent engine run on `serve/kanban/tests/test_engine_reads_1069.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, `serve/kanban/tests/test_engine_coverage_1110.py`, and `tests/test_engine_coverage_1113.py`: 346 passed, 0 failed, 0 skipped.
- Quality-Runner expanded engine-scoped run on the four files above plus `serve/kanban/tests/test_engine_init_1067.py`, `serve/kanban/tests/test_engine_models.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_create_edit_1070.py`, `serve/kanban/tests/test_engine_init_1068.py`, and `serve/kanban/tests/test_engine_atomicity_1104.py`: 610 passed, 0 failed, 0 skipped.

### Lint
- Quality-Runner lint on `serve/kanban/src/owlbear_kanban/engine.py` plus the 10 engine test files above: clean.

### Coverage
- `owlbear_kanban.engine`: 94% on the expanded engine-scoped run.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage / AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| AC1 archived `show_task` returns archived fields populated | `serve/kanban/tests/test_engine_reads_1069.py:338,353,368,383,603,629` prove archived response shape, `archival_refs`, and the warm-cache archive transition | COVERED |
| AC2 `list_tasks(status="archived")` returns archived only | `serve/kanban/tests/test_engine_reads_1069.py:238,257` | COVERED |
| AC3 ids lookup returns 2 tasks and exact `missing_ids` | `serve/kanban/tests/test_engine_reads_1069.py:276,293,310,654,672` | COVERED |
| AC10 case-insensitive section lookup returns matching heading content | `serve/kanban/tests/test_engine_reads_1069.py:688,701-703` proves case-insensitive positive lookup only. It seeds no unrelated section text and no task-owned assertion checks exclusion. A regression that returns the full body would still pass. Literal AC remains at `.owlbear/kanban/tasks/1069-b-05-red-list-tasks-show-task-tests.md:34` | LAX |
| AC11 missing section returns `body=None` and exact `missing_sections` | `serve/kanban/tests/test_engine_reads_1069.py:717,731` | COVERED |
| AC12 multiple section matches include numeric occurrence count in guidance | `serve/kanban/tests/test_engine_reads_1069.py:400,417-419,787,804-805` | COVERED |
| AC15 ids exclusive with status raises `ERR_IDS_EXCLUSIVE` | `serve/kanban/tests/test_engine_reads_1069.py:150` | COVERED |
| Invalid status raises `ERR_INVALID_STATUS` | `serve/kanban/tests/test_engine_reads_1069.py:192` | COVERED |
| Invalid priority raises `ERR_INVALID_PRIORITY` | `serve/kanban/tests/test_engine_reads_1069.py:199` | COVERED |
| Invalid archival_reason raises `ERR_ARCHIVAL_REASON_INVALID` | `serve/kanban/tests/test_engine_reads_1069.py:210` | COVERED |
| Empty section raises `ERR_SECTION_EMPTY` | `serve/kanban/tests/test_engine_reads_1069.py:741` | COVERED |
| Missing task id raises `ERR_NOT_FOUND` | `serve/kanban/tests/test_engine_reads_1069.py:749` | COVERED |
| Default `list_tasks()` excludes archived unless explicitly requested | `serve/kanban/tests/test_engine_reads_1069.py:775-776` | COVERED |
| `dep_status` precedence is blocked, redirect, ok, then None | `serve/kanban/tests/test_engine_reads_1069.py:457,480,503,516,549,576` | COVERED |
| Historical RED prerequisite | Prior task-body notes only; not independently reproducible from the current snapshot | N/A |

#### Security Review
- No secret exposure, injection, traversal, unsafe deserialization, or boundary-validation issue found in the reviewed read paths.

#### Test Integrity
| Original Test Surface | Change Made | Assessment |
|---|---|---|
| Current `TestFromAC_*` suite in `serve/kanban/tests/test_engine_reads_1069.py` | Current snapshot shows additive or tightened assertions only; no weakened or removed assertions observed live | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC10 uses positive-only inclusion assertions at `serve/kanban/tests/test_engine_reads_1069.py:702-703`. The multi-match body test also omits any exclusion check for the unrelated Notes content seeded at `serve/kanban/tests/test_engine_reads_1069.py:408-409` and exercised at `serve/kanban/tests/test_engine_reads_1069.py:417-419`. |
| Negative and error-path coverage | STRONG | Missing section, empty section, not-found, invalid enums, and ids-exclusive validation are all task-owned in `serve/kanban/tests/test_engine_reads_1069.py:150,192,199,210,717,731,741,749`. |
| Manual mutation reasoning | WEAK | Changing the section path to return the full body instead of matched sections would still satisfy the current task-owned assertions at `serve/kanban/tests/test_engine_reads_1069.py:417-419` and `serve/kanban/tests/test_engine_reads_1069.py:702-703`, even though the live implementation correctly filters headings at `serve/kanban/src/owlbear_kanban/engine.py:1756` and joins matched sections only at `serve/kanban/src/owlbear_kanban/engine.py:1762`. |
| Test independence | STRONG | Fresh board and fresh view per case throughout the file. |
| Descriptive test names | STRONG | Scenario-specific names throughout the task-owned suite. |

#### Data Safety
- No data-safety issue found in the reviewed scope.

#### Implementation-Aware Gaps
- No live implementation defect found in the current engine snapshot for the reviewed paths. Section matching is correctly filtered by heading at `serve/kanban/src/owlbear_kanban/engine.py:1756` and assembled from matched sections only at `serve/kanban/src/owlbear_kanban/engine.py:1762`.
- The remaining blocker is task-owned proof quality: no task-owned assertion proves that unrelated section content is excluded from `show_task(section=...)` responses.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Prior review history | The task body already records the 3rd review fail at `.owlbear/kanban/tasks/1069-b-05-red-list-tasks-show-task-tests.md:420` and the 4th review fail at `.owlbear/kanban/tasks/1069-b-05-red-list-tasks-show-task-tests.md:576` |
| Assessment | Loop-breaker routing applies on this cycle |

### Deductions
- 0.08 deduction for lax AC10 proof on section scoping.
- 0.04 deduction for weak mutation resistance on section extraction.

### Confidence: 0.88
### Verdict: FAIL
### Action
- Reject to `backlog`. Tests, lint, and expanded engine-scoped coverage are clean, and the live implementation looks correct, but the task-owned section tests still do not prove that `show_task(section=...)` excludes unrelated body content.
- Surgical fix guidance: add a non-matching heading to the AC10 fixture and assert that unrelated content is absent from the returned body; add the same negative exclusion assertion to the multi-match section-body test.

### Reflection
- Expanded engine-scoped coverage resolved the module-coverage question; the blocker remained proof quality in the task-owned RED suite.
- Adjacent green suites do not rescue a task-owned false-green risk.
- Positive-only inclusion checks are not enough for section-extraction contracts.
[[2026-04-25]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test-only module for list_tasks + show_task reads |
| Interface clarity | PASS | 14/15 AC lines COVERED; 1 LAX (section exclusion) |
| Dependency correctness | PASS | Depends on #1068 (archived) |
| Module layering | PASS | Test file — no production layering concern |
| TDD compliance | PASS | This IS the RED task |
| KISS/YAGNI | PASS | No unnecessary scope |
| Premise challenge | PASS | Tests required per Brief B |
| Pattern consistency | PASS | Follows existing TestFromAC_ class naming |
| Security surface | N/A | Read-only test file |
| Single domain | PASS | Kanban engine domain only |

### Challenge Results
- Challenger: reconsider (0.66)
- Key points: (1) AC10 may understate Brief B §1.2 scope (heading-level independence, whitespace trimming); (2) D56 document-order not strictly proven; (3) markdown-vs-content rendering unresolved
- Architect response: REBUTTED — literal AC text governs test scope, not full Brief B §1.2. AC10 says "case-insensitive" only. D56 ordering and markdown rendering are implementation-contract questions for separate tasks if needed. The reviewer's 5th review identified exactly one gap (section exclusion not proven), and the proposed guidance closes it. Expanding scope beyond written AC after 6 cycles violates KISS/YAGNI.

### Loop-Breaker Context
6th pipeline cycle (3rd loop-breaker backlog return). 14/15 AC lines COVERED. Single remaining gap: AC10 and multi-match section tests use positive-only inclusion assertions — don't prove unrelated content is excluded. Implementation is correct (610 engine tests, 94% coverage, lint clean). The fix is minimal.

### Test-Writer Fix Guidance (MUST follow exactly)

**AC10 — section exclusion proof** (`test_case_insensitive_section_lookup_returns_content` in `serve/kanban/tests/test_engine_reads_1069.py`):
Change the fixture from:
```python
_write_task(
    kanban_dir,
    task_id=11,
    title="CaseTest",
    body="## Goals\nSome goal text.\n",
)
```
To:
```python
_write_task(
    kanban_dir,
    task_id=11,
    title="CaseTest",
    body="## Goals\nSome goal text.\n\n## Notes\nIrrelevant note.\n",
)
```
And add after `assert "Some goal text." in resp.body`:
```python
assert "Irrelevant note." not in resp.body, "Section filter must exclude unrelated headings"
```
Rationale: The implementation at engine.py:1753 filters by casefold heading match. Without an unrelated section in the fixture, a mutation returning the full body would still pass.

**Multi-match — section exclusion proof** (`test_multiple_section_matches_body_contains_all_content` in `serve/kanban/tests/test_engine_reads_1069.py`):
The fixture already seeds `## Notes\nUnrelated note.` — add after the existing "Second goal content." assertion:
```python
assert "Unrelated note." not in resp.body, "Section filter must exclude non-matching headings from concatenated result"
```
Rationale: Same mutation resistance. The fixture already has the unrelated content — just needs the negative assertion.

### Verdict: REFINE → APPROVE
### Action: Added surgical test-writer guidance for section-exclusion assertions. Advanced to todo.
[[2026-04-25]]
## Test-Writer Notes
- Retry cycle: architect loop-breaker (7th cycle) provided surgical fix guidance for the 1 remaining lax AC: section-exclusion assertions for AC10 and AC12.
- Test file: `serve/kanban/tests/test_engine_reads_1069.py`
- Changes (assertion tightenings only — no new tests):
  - **AC10** (`test_case_insensitive_section_lookup_returns_content`): added `## Notes\nIrrelevant note.` to the task fixture body + added `assert "Irrelevant note." not in resp.body` — proves section filter excludes unrelated headings from the response.
  - **AC12 / multi-match** (`test_multiple_section_matches_body_contains_all_content`): added `assert "Unrelated note." not in resp.body` — proves section filter excludes non-matching headings from the concatenated result (fixture already had `## Notes\nUnrelated note.` seeded).
- Total: 36 tests, all PASS (implementation already satisfies stricter assertions), ruff clean.
- Commit: a18eb571

**AC coverage (gaps closed):**
| Gap | Fix |
|---|---|
| AC10: section exclusion (unrelated heading excluded) | Added unrelated `## Notes` section to fixture + negative assertion |
| AC12: multi-match exclusion (non-matching heading excluded) | Added negative assertion for `## Notes` content already seeded in fixture |
[[2026-04-25]]
## Builder Notes
- Implementation: no code changes in this cycle; current `serve/kanban/src/owlbear_kanban/engine.py` behavior already satisfies latest AC-tightened task tests.
- Files changed: none.
- Tests:
  - Scoped read/coverage slice: `serve/kanban/tests/test_engine_reads_1069.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, `serve/kanban/tests/test_engine_coverage_1110.py`, `tests/test_engine_coverage_1113.py` -> 346 passed, 0 failed.
  - Expanded engine verification: `tests/test_engine_coverage_1113.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, `serve/kanban/tests/test_engine_coverage_1110.py`, `serve/kanban/tests/test_engine_reads_1069.py`, `serve/kanban/tests/test_engine_init_1067.py`, `serve/kanban/tests/test_engine_models.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_create_edit_1070.py`, `serve/kanban/tests/test_engine_init_1068.py`, `serve/kanban/tests/test_engine_atomicity_1104.py` -> 610 passed, 0 failed.
- Coverage:
  - `owlbear_kanban.engine` = 84% on narrow scoped slice.
  - `owlbear_kanban.engine` = 93% on expanded engine-scoped verification (gate pass).
- Ruff:
  - `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/tests/test_engine_reads_1069.py` -> clean.
  - Expanded lint over the same 10-file engine test set -> clean.
- Evidence summary:
  - AC10/AC12 section exclusion assertions are present and currently green in `serve/kanban/tests/test_engine_reads_1069.py`.
  - Task-owned and adjacent engine verification is fully green with no builder-side code delta required.

- Reflection:
  - Scoped-only coverage can understate confidence for shared engine behavior; expanded engine-scoped verification gave the reliable gate signal.
  - The remaining work in this cycle was verification quality, not implementation.
  - Keeping this cycle code-free avoided unnecessary risk in a historically looped task.
  - Re-checking the exact tightened assertions first prevented another proof-gap bounce in review.
[[2026-04-25]]
## Review Evidence

### Test Results
- Quality-Runner task-plus-adjacent engine run on [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py), [serve/kanban/tests/test_engine_coverage_1110.py](serve/kanban/tests/test_engine_coverage_1110.py), and [tests/test_engine_coverage_1113.py](tests/test_engine_coverage_1113.py): 346 passed, 0 failed, 0 skipped.
- Quality-Runner expanded engine-scoped run on the four files above plus [serve/kanban/tests/test_engine_init_1067.py](serve/kanban/tests/test_engine_init_1067.py), [serve/kanban/tests/test_engine_models.py](serve/kanban/tests/test_engine_models.py), [serve/kanban/tests/test_engine_activity.py](serve/kanban/tests/test_engine_activity.py), [serve/kanban/tests/test_engine_create_edit_1070.py](serve/kanban/tests/test_engine_create_edit_1070.py), [serve/kanban/tests/test_engine_init_1068.py](serve/kanban/tests/test_engine_init_1068.py), and [serve/kanban/tests/test_engine_atomicity_1104.py](serve/kanban/tests/test_engine_atomicity_1104.py): 610 passed, 0 failed, 0 skipped.

### Lint
- Quality-Runner lint on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1656) plus the same expanded engine test set: clean.
- Editor diagnostics on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1656) and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L145): no errors.

### Coverage
- Narrow task-plus-adjacent slice: owlbear_kanban.engine at 84%.
- Expanded engine-scoped verification: owlbear_kanban.engine at 93%.
- Gate decision: PASS. The narrow slice under-represents shared engine coverage; the expanded engine-only scope clears the 90% module threshold.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage / AC Compliance
| AC line | Evidence | Status |
|---|---|---|
| AC1 archived show_task returns archived fields populated | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L325), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L340), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L355), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L370), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L593), and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L609) prove archived response fields plus the warm-cache archive transition. | PASS |
| AC2 list_tasks(status="archived") returns archived only | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L225) and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L242). | PASS |
| AC3 ids lookup returns exactly 2 tasks plus exact missing_ids | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L260), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L278), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L295), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L643), and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L661). | PASS |
| AC10 case-insensitive section lookup returns matching heading content | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L691) proves positive case-insensitive lookup and exclusion of unrelated section text. | PASS |
| AC11 missing section returns body=None and exact missing_sections | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L711) and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L725). | PASS |
| AC12 multiple section matches include numeric occurrence count guidance | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L400) and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L793) prove concatenated matching content, exclusion of unrelated content, and exact numeric guidance. | PASS |
| AC15 ids exclusive with status raises ERR_IDS_EXCLUSIVE | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L145). | PASS |
| Invalid status enum raises ERR_INVALID_STATUS | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L187). | PASS |
| Invalid priority enum raises ERR_INVALID_PRIORITY | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L194). | PASS |
| Invalid archival_reason enum raises ERR_ARCHIVAL_REASON_INVALID | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L201). | PASS |
| Empty section raises ERR_SECTION_EMPTY | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L739). | PASS |
| Missing task id raises ERR_NOT_FOUND | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L749). | PASS |
| Default list_tasks excludes archived unless explicitly requested | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L766), with explicit archived and ids cases already pinned at [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L225) and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L260). | PASS |
| dep_status precedence is blocked, redirect, ok, then None | [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L441), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L465), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L488), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L511), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L523), and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L557) prove the single-state and mixed-dependency precedence contract implemented at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L575). | PASS |
| Historical RED precondition | Prior task-body history documents the original red run; this state is not replayable from the current snapshot. | N/A |

#### Security Review
- No secret exposure, injection, traversal, unsafe deserialization, or boundary-validation issue found in the reviewed read paths at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1656) and dependency projection at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L575).

#### Test Integrity
| Original test surface | Change made | Assessment |
|---|---|---|
| Current TestFromAC suite in [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py) | Live snapshot shows additive or tightened assertions only; no weakened or removed assertions observed. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Exact error-code assertions at [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L145), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L187), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L194), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L201), exact missing_ids equality at [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L661), and exact occurrence-count guidance at [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L793). |
| Negative and error-path coverage | STRONG | Invalid enums, empty section, missing section, and not-found handling are all task-owned at [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L187), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L201), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L711), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L739), and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L749). |
| Manual mutation reasoning | ADEQUATE | Mutations that remove archive fallback, section exclusion, numeric guidance, or dep_status ordering would trip task-owned tests at [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L400), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L691), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L793), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L523), and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L557). The additional ids-plus-archival_reason exclusivity clause at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1692) is outside the written task contract and is therefore non-gating here. |
| Test independence | STRONG | Fresh board and fresh view per case via [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L91) and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L125). |
| Descriptive names | STRONG | Scenario-specific names throughout [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L145) through [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L793). |

#### Data Safety
- No data-safety issue found in the reviewed scope.

#### Implementation-Aware Gaps
- No blocking implementation or task-owned proof gap remains against the written AC in [.owlbear/kanban/tasks/1069-b-05-red-list-tasks-show-task-tests.md](.owlbear/kanban/tasks/1069-b-05-red-list-tasks-show-task-tests.md#L26). The extra ids-plus-archival_reason exclusivity branch at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1692) is broader than the written task contract and does not block this RED task.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Prior review FAIL sections in task history | Multiple recorded loop cycles; current snapshot re-verified from fresh evidence rather than prior claims. |
| Assessment | CLEAN on the live snapshot. No new code delta was required after the final test-writer tightening. |

### Pass 2 - INFORMATIONAL
- [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L1), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L135), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L216), [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L318), and [serve/kanban/tests/test_engine_reads_1069.py](serve/kanban/tests/test_engine_reads_1069.py#L396) still describe the original RED and pre-fix state. That is documentation drift only; it does not weaken the live assertions.

### Deductions
- 0.02 deduction for stale RED-phase commentary in the task-owned test module.
- 0.02 deduction because the shared engine module needed expanded engine-only coverage evidence after the narrow task slice under-reported coverage.

### Confidence: 0.96
### Verdict: PASS
### Action
- Advance to docs.

### Reflection
- Narrow task-owned coverage materially under-represented the shared engine module; expanded engine-only verification was necessary to apply the module gate correctly.
- Literal task AC governed the review. I did not fail the task for the extra ids-plus-archival_reason exclusivity branch because that path is outside the written contract.
- The live blocker history was loop noise rather than a current behavior defect in the snapshot reviewed.
[[2026-04-25]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | serve/kanban/README.md `KanbanEngine methods` table covers KanbanEngine interface only; AgentView was never documented there — no prose is stale. |
| 2 | Module docstrings | Yes | Updated | `AgentView.list_tasks` and `AgentView.show_task` had no docstrings; added. `KanbanEngine.show_task` Raises clause said "tasks_dir" only but method now also checks archive_dir; updated. |
| 3 | External attribution | No | N/A | No external patterns or sources cited in the task. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: serve/kanban/src/**) and `share/diagrams/mcp-topology.excalidraw` (describes: serve/kanban/src/**) both matched; footers bumped to `2026-04-25 (6fb16629)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| serve/kanban/src/owlbear_kanban/engine.py | IN (docstrings) | Updated docstrings |
| serve/kanban/tests/test_engine_reads_1069.py | OUT (test file) | N/A |
| share/diagrams/kanban.excalidraw | IN | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN | Footer updated |

### Files Updated
- serve/kanban/src/owlbear_kanban/engine.py (docstrings: AgentView.list_tasks, AgentView.show_task, KanbanEngine.show_task Raises clause)
- share/diagrams/kanban.excalidraw (footer: 2026-04-25 6fb16629)
- share/diagrams/mcp-topology.excalidraw (footer: 2026-04-25 6fb16629)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (.owlbear/scratch/1069-* — no matches)

Commit: da3ea68a
[[2026-04-25]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: show_task(archived_id) returns archived fields | test_engine_reads_1069.py:325,340,355,370,593,609 | PASS |
| AC2: list_tasks(status="archived") returns archived only | test_engine_reads_1069.py:225,242 | PASS |
| AC3: ids lookup returns 2 + exact missing_ids | test_engine_reads_1069.py:260,278,295,643,661 | PASS |
| AC10: case-insensitive section lookup + exclusion | test_engine_reads_1069.py:691 (positive + negative assertion) | PASS |
| AC11: missing section → body=None, exact missing_sections | test_engine_reads_1069.py:711,725 | PASS |
| AC12: multi-match guidance with numeric count | test_engine_reads_1069.py:400,793 ("2 occurrences") | PASS |
| AC15: ids exclusive → ERR_IDS_EXCLUSIVE | test_engine_reads_1069.py:145 | PASS |
| Invalid status → ERR_INVALID_STATUS | test_engine_reads_1069.py:187 | PASS |
| Invalid priority → ERR_INVALID_PRIORITY | test_engine_reads_1069.py:194 | PASS |
| Invalid archival_reason → ERR_ARCHIVAL_REASON_INVALID | test_engine_reads_1069.py:201 | PASS |
| Empty section → ERR_SECTION_EMPTY | test_engine_reads_1069.py:739 | PASS |
| Missing id → ERR_NOT_FOUND | test_engine_reads_1069.py:749 | PASS |
| Default excludes archived | test_engine_reads_1069.py:766 | PASS |
| dep_status precedence (blocked > redirect > ok > None) | test_engine_reads_1069.py:441,465,488,511,523,557 (includes mixed-dep tests) | PASS |
| Historical RED precondition | Builder notes only — not independently reproducible | N/A |

### Test Results
- pytest (full suite): 1981 passed, 165 failed, 209 errors. All failures/errors are pre-existing and unrelated (cockpit API mismatch, storage config, migration/corruption). Task-owned test_engine_reads_1069.py not among failures.
- ruff (full): 8 violations, all in unrelated packages. Task-scoped files clean.
- coverage: owlbear_kanban.engine at 97% (full suite).

### Architect Quality: 4/5
AC lines were individually specific and verifiable (exact error codes, exact payload shapes, precedence ordering). The 3 loop-breaker cycles were caused by test-writer assertion laxness (containment vs exact equality, positive-only vs positive+negative), not AC ambiguity.

### Deduction Breakdown
- AC lines with no evidence: 0 (14 PASS, 1 N/A)
- Lint violations in task scope: 0
- AC quality ≤ 3: N/A (scored 4/5)
- Missing reviewer evidence: 0 (present, detailed — 6 review rounds)
- Full-suite failures in task scope: 0
- Commit verification: -.02 (could not run git log independently; files exist and content matches reviewer-cited lines)

### Confidence: .98
### Action: archive