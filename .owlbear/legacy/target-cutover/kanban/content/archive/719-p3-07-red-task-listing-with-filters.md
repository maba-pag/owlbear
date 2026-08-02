---
id: 719
title: 'P3-07: RED — task listing with filters'
status: archived
priority: medium
created: 2026-04-09T03:25:39.267676+02:00
updated: 2026-04-09T18:11:30.9536645+02:00
started: 2026-04-09T18:11:30.9536645+02:00
completed: 2026-04-09T18:11:30.9536645+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 718
class: standard
---

## Objective
Write failing tests for listing tasks with filtering, sorting, and pagination.

Brief: see parent #712

## AC
- [ ] Test list all tasks from tasks_dir
- [ ] Test filter by status, tag, priority, blocked (tri-state), unclaimed
- [ ] Test full-text search in titles and bodies
- [ ] Test sort by priority, updated, id, title, status, created
- [ ] Test reverse ordering
- [ ] Test limit (pagination cap)
- [ ] Test archived task listing
- [ ] All tests fail

## Files
- `tests/test_kanban_engine_listing.py` (new)

[[2026-04-09]] Thu 15:35
## Architecture Review

### Context
RED phase test task for `KanbanEngine.list_tasks()` with filtering, sorting, and pagination. Parent #712 (archived epic). Dependency #718 (task file I/O GREEN) is `done`. Sibling #720 (GREEN phase) depends on this task and specifies the implementation signature: `list_tasks(status, tag, priority, search, sort, unclaimed, archived, limit, reverse, blocked) -> list[TaskRecord]` in `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py`. Brief API surface and behavioral contracts table provide full behavioral specification.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Test list all tasks from tasks_dir | PASS — clear: populate tmp tasks_dir with task files, call `list_tasks()` with no filters, assert all returned | None |
| Test filter by status, tag, priority, blocked (tri-state), unclaimed | PASS — 5 filter dimensions specified; "tri-state" for blocked clarifies `bool\|None` semantics; unclaimed = `claimed_by is None` per Brief | None |
| Test full-text search in titles and bodies | PASS — verifiable: create tasks with known text, search, assert match/no-match | None |
| Test sort by priority, updated, id, title, status, created | PASS — 6 sort fields listed, matches Brief and MCP tool `_SORT_FIELDS` in `server.py:618` | None |
| Test reverse ordering | PASS — verifiable: assert descending vs ascending | None |
| Test limit (pagination cap) | PASS — verifiable: create N tasks, limit=M, assert len(result)==M | None |
| Test archived task listing | PASS — verifiable: `archived=True` reads from archive directory (kanban-md convention: `v1-archive/` or similar); test-writer creates tasks in archive dir | None |
| All tests fail | PASS — standard RED phase AC | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One thing: write failing tests for list_tasks filtering/sorting/pagination |
| Interface clarity | PASS | API shape derivable from Brief (`KanbanEngine.list_tasks(...)`) and sibling #720's AC; return type `list[TaskRecord]`; import path `owlbear_mcp_kanban.engine` from #720's files section |
| Dependency correctness | PASS | #718 (task_io GREEN) is done — provides `read_task()` which listing will use internally. No missing deps |
| Module layering | PASS | Test file in `tests/` importing from `owlbear_mcp_kanban.engine` — correct direction |
| TDD compliance | PASS | This IS the RED phase; #720 is the GREEN phase |
| KISS/YAGNI | PASS | Minimal scope — tests for each filter/sort dimension, no speculative features |
| Premise challenge | PASS | Listing is core engine operation per Brief's KanbanEngine API surface |
| Pattern consistency | PASS | Follows established RED phase patterns: `TestFromAC_*` classes, pytest `tmp_path` fixtures, imports from `owlbear_mcp_kanban.*`; matches `test_kanban_engine_models.py` and `test_kanban_engine_config.py` conventions |
| Security surface | PASS | Test-only task, no new system boundaries |
| Single domain | PASS | Kanban engine domain exclusively |

### Architecture Notes
1. **Archive directory convention**: Existing kanban-md uses `v1-archive/` for archived tasks. The native engine's archive location is an implementation detail for #720, but the test-writer should create tasks in a subdirectory (e.g., `archived/` under `tasks_dir`) and verify `list_tasks(archived=True)` scans it. The exact directory name will be established by the GREEN phase.
2. **Sort by priority**: Priority sort must use the priority ordering from `config.yml` (`someday < nice-to-have < important < needed < critical`), not alphabetical. The test-writer should verify sort order matches config priority rank.
3. **Existing MCP server tests**: `serve/mcp-kanban/tests/test_server.py` has `list_tasks` tests but these test the subprocess-based MCP tool, not the native engine. The new tests target `KanbanEngine.list_tasks()` directly.
4. **Non-impl tag**: Already tagged `type:test` — correct for RED phase.

### Challenge Results
- Challenger: FALLBACK — agent not available in current agent set
- Architect response: Independent evaluation across all 10 criteria; codebase verified (existing list_tasks MCP tool patterns in server.py:163-212, TaskRecord model in engine_models.py, read_task in task_io.py); all AC lines verifiable; no concerns requiring formal challenge

### Verdict: APPROVE
### Action Taken: Approved #719 to todo. AC is verifiable, dependencies correct (#718 done), follows established RED phase patterns. Test-writer should reference Brief API surface and sibling #720's AC for exact `KanbanEngine.list_tasks()` signature.

[[2026-04-09]] Thu 16:34
## Test-Writer Notes
- Test file: tests/test_kanban_engine_listing.py
- Classes: TestFromAC_ListAllTasks, TestFromAC_FilterByStatus, TestFromAC_FilterByTag, TestFromAC_FilterByPriority, TestFromAC_FilterByBlocked, TestFromAC_FilterByUnclaimed, TestFromAC_FullTextSearch, TestFromAC_SortByField, TestFromAC_ReverseOrdering, TestFromAC_LimitPagination, TestFromAC_ArchivedTasks
- Tests per category: happy ~21, edge ~9, boundary ~4
- Total: 34 tests, all FAIL (ImportError — owlbear_mcp_kanban.engine does not exist)
- ruff: clean

### AC Coverage
| AC Line | Tests |
|---------|-------|
| List all tasks from tasks_dir | test_returns_all_task_files, test_empty_tasks_dir_returns_empty_list, test_result_items_are_task_records |
| Filter by status | test_status_filter_returns_only_matching, test_status_filter_no_match_returns_empty, test_empty_status_returns_all |
| Filter by tag | test_tag_filter_returns_tasks_with_tag, test_tag_filter_no_match_returns_empty |
| Filter by priority | test_priority_filter_returns_matching, test_priority_filter_no_match_returns_empty |
| Filter by blocked (tri-state) | test_blocked_true_returns_only_blocked, test_blocked_false_returns_only_unblocked, test_blocked_none_is_tri_state_no_filter |
| Filter by unclaimed | test_unclaimed_returns_only_tasks_without_claimed_by, test_unclaimed_false_returns_all_tasks |
| Full-text search in titles and bodies | test_search_matches_title, test_search_matches_body, test_search_no_match_returns_empty, test_search_matches_both_title_and_body_tasks |
| Sort by priority, updated, id, title, status, created | test_sort_by_id, test_sort_by_title_alphabetical, test_sort_by_status_uses_config_order, test_sort_by_priority_uses_config_rank, test_sort_by_created, test_sort_by_updated |
| Reverse ordering | test_reverse_inverts_default_id_order, test_reverse_with_priority_sort |
| Limit (pagination cap) | test_limit_caps_result_count, test_limit_zero_means_no_cap, test_limit_greater_than_count_returns_all |
| Archived task listing | test_default_excludes_archive_dir_tasks, test_archived_true_returns_tasks_from_archive_dir, test_archived_true_does_not_include_live_tasks, test_archived_true_empty_archive_returns_empty |

### Key design decisions
- Archive dir: v1-archive/ (sibling of tasks/, matches actual kanban-md convention)
- Priority sort: test explicitly verifies config-rank order (not alphabetical) — someday=0, critical=4
- Status sort: test verifies config-index order (not alphabetical) — research=0, done=6
- Blocked tri-state: 3 separate tests (True/False/None)

### Commit
cee7a57 — tests/test_kanban_engine_listing.py only

[[2026-04-09]] Thu 17:00
## Builder Notes
- **Type**: type:test (RED phase) — non-implementation passthrough
- **Files changed**: none
- **Test results**: 1 collection ERROR — `ModuleNotFoundError: No module named 'owlbear_mcp_kanban.engine'` at line 22; 34 tests blocked (all fail as required)
- **Lint status**: ruff clean (EXIT 0)
- **Evidence**: All 34 `TestFromAC_*` tests fail due to missing `engine.py`. This is the correct RED state. No implementation needed for this task — GREEN phase is #720.
- **Commit**: cee7a57 (test-writer's commit, verified)

[[2026-04-09]] Thu 17:04
## Review Evidence
### Test Results
- pytest: 0 passed, 0 explicitly failed — 1 collection ERROR (ModuleNotFoundError: `owlbear_mcp_kanban.engine` does not exist). pytest exit 1. Correct RED state. 34 tests blocked at import.

### Lint: clean
- ruff: exit 0, 0 violations.

### Coverage: N/A — RED phase, no implementation module to measure.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| List all tasks from tasks_dir | TestFromAC_ListAllTasks (3 tests) | Yes — asserts len==3, IDs set, isinstance(rec, TaskRecord) | COVERED |
| Filter by status | TestFromAC_FilterByStatus (3 tests) | Yes — asserts filtered count + status field values | COVERED |
| Filter by tag | TestFromAC_FilterByTag (2 tests) | Yes — asserts filtered count + tag membership | COVERED |
| Filter by priority | TestFromAC_FilterByPriority (2 tests) | Yes — asserts filtered count + priority field values | COVERED |
| Filter by blocked (tri-state) | TestFromAC_FilterByBlocked (3 tests) | Yes — 3 tests for True/False/None semantics, asserts .blocked field | COVERED |
| Filter by unclaimed | TestFromAC_FilterByUnclaimed (2 tests) | Yes — asserts claimed_by is None for all results | COVERED |
| Full-text search in titles and bodies | TestFromAC_FullTextSearch (4 tests) | Yes — title match, body match, no-match returns [], union match | COVERED |
| Sort by priority, updated, id, title, status, created | TestFromAC_SortByField (6 tests) | Yes — explicit ordered-list assertions; priority and status guard alphabetical regression | COVERED |
| Reverse ordering | TestFromAC_ReverseOrdering (2 tests) | Yes — compares fwd vs rev lists explicitly; priorities[0]==critical | COVERED |
| Limit (pagination cap) | TestFromAC_LimitPagination (3 tests) | Yes — len==3, limit=0 sentinel returns all 5, over-limit returns all | COVERED |
| Archived task listing | TestFromAC_ArchivedTasks (4 tests) | Yes — live/archive exclusion tested both directions, empty archive case | COVERED |
| All tests fail | ImportError at collection, pytest exit 1 | ✓ Confirmed independently | COVERED |

#### Security Review
- No issues. Test-only file; no new system boundaries, no untrusted input, no secrets.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All TestFromAC_* classes | None (builder was passthrough — no files changed) | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `assert [t.id for t in result] == [10, 20, 30]`; `assert priorities[0] == "someday"` — no lazy assertions detected |
| Negative/error paths | STRONG | Every filter class has "no match returns empty" test + complement |
| Mutation resistance | STRONG | Priority/status sort tests guard alphabetical regression via explicit first-element assertions |
| Test independence | STRONG | All tests use pytest `tmp_path` — fresh dir per test, no shared mutable state |
| Descriptive names | STRONG | `test_blocked_none_is_tri_state_no_filter`, `test_sort_by_priority_uses_config_rank` etc. |

#### Data Safety
- No issues. Test-only task.

#### Implementation-Aware Gaps
- N/A — RED phase. No implementation exists yet.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (passthrough role) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- None.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| List all tasks from tasks_dir | test_kanban_engine_listing.py:163–185 | TestFromAC_ListAllTasks | PASS |
| Filter by status, tag, priority, blocked, unclaimed | test_kanban_engine_listing.py:193–329 | TestFromAC_Filter* (5 classes) | PASS |
| Full-text search | test_kanban_engine_listing.py:337–377 | TestFromAC_FullTextSearch | PASS |
| Sort by 6 fields | test_kanban_engine_listing.py:385–470 | TestFromAC_SortByField | PASS |
| Reverse ordering | test_kanban_engine_listing.py:478–502 | TestFromAC_ReverseOrdering | PASS |
| Limit (pagination cap) | test_kanban_engine_listing.py:510–535 | TestFromAC_LimitPagination | PASS |
| Archived task listing | test_kanban_engine_listing.py:543–619 | TestFromAC_ArchivedTasks | PASS |
| All tests fail | pytest exit 1, collection ERROR confirmed independently | All 34 tests | PASS |

### Confidence: .97
### Verdict: PASS

[[2026-04-09]] Thu 17:07
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | RED phase only — `owlbear_mcp_kanban.engine` does not exist; no production code added; copilot-instructions.md has no entries for this engine yet |
| 2 | Module docstrings | No | N/A | Only file changed is `tests/test_kanban_engine_listing.py` (test file, not a module) |
| 3 | External attribution | No | N/A | Standard TDD RED conventions; no external sources cited in task body or builder notes |
| 4 | CLI changes | No | N/A | No CLI modifications |
| 5 | Research doc | No | N/A | No research doc; task derives from parent Brief #712 |

### Files Updated
None — no docs impact for a RED phase test-only task.

### Scratch Files
None found matching `.owlbear/scratch/719-*`.

### Commit
No documentation commit required.

[[2026-04-09]] Thu 18:11
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| List all tasks from tasks_dir | TestFromAC_ListAllTasks (3 tests, L155–185): asserts len==3, ID set, isinstance(TaskRecord) | PASS |
| Filter by status, tag, priority, blocked (tri-state), unclaimed | TestFromAC_Filter* (5 classes, 12 tests, L193–329): status/tag/priority match+no-match, blocked tri-state True/False/None, unclaimed claimed_by is None | PASS |
| Full-text search in titles and bodies | TestFromAC_FullTextSearch (4 tests, L337–377): title match, body match, no-match, union OR | PASS |
| Sort by priority, updated, id, title, status, created | TestFromAC_SortByField (6 tests, L385–470): all 6 fields; priority+status guard alphabetical regression | PASS |
| Reverse ordering | TestFromAC_ReverseOrdering (2 tests, L478–502): fwd vs rev, priority[0]==critical | PASS |
| Limit (pagination cap) | TestFromAC_LimitPagination (3 tests, L510–535): cap, zero-sentinel, over-limit | PASS |
| Archived task listing | TestFromAC_ArchivedTasks (4 tests, L543–619): live/archive exclusion both dirs, empty archive | PASS |
| All tests fail | ImportError at collection (owlbear_mcp_kanban.engine missing), pytest exit 1 — confirmed independently | PASS |

### Test Results
- pytest (full suite, excl. RED/collection-error files): 2851 passed, 130 failed — failures are pre-existing in unrelated files; #719 adds 1 test file + 0 source changes → zero regression risk
- ruff: clean (0 violations)

### Architect Quality: 4/5
AC lines are specific, testable, and scoped. "All tests fail" is standard RED-phase meta-AC. Tri-state blocked semantics and config-rank sort explicitly specified — quality above average. Minor: archive directory convention left somewhat open ("v1-archive/" noted in architecture review but not in AC itself); test-writer resolved correctly.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 8 covered) → 0
- Lint violations: 0 → 0
- AC quality ≤ 3: no (4/5) → 0
- Missing reviewer evidence: no (detailed, PASS) → 0
- Full-suite failures in task scope: 0 → 0

### Confidence: .98
### Action: archive

### Commit Verification
- cee7a57: `test: add failing tests for task listing with filters (#719, test-writer)` — tests/test_kanban_engine_listing.py only. Verified via git log.
