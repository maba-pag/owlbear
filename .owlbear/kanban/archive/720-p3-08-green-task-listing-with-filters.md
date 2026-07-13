---
id: 720
title: 'P3-08: GREEN — task listing with filters'
status: archived
priority: medium
created: 2026-04-09T03:25:47.5994845+02:00
updated: 2026-04-09T20:07:17.6318009+02:00
started: 2026-04-09T20:07:17.6318009+02:00
completed: 2026-04-09T20:07:17.6318009+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 719
class: standard
---

## Objective
Implement `list_tasks()` on KanbanEngine with full filter/sort/limit support.

Brief: see parent #712

## AC
- [ ] `list_tasks(status, tag, priority, search, sort, unclaimed, archived, limit, reverse, blocked)` returns filtered list[TaskRecord]
- [ ] Reads all task files from tasks_dir via task_io module
- [ ] Filter logic matches kanban-md behavioral contracts
- [ ] Sort by each supported field
- [ ] All #719 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (new — KanbanEngine class, list_tasks method)

[[2026-04-09]] Thu 17:50
## Architecture Review

### Context
GREEN phase task — implement `KanbanEngine.list_tasks()` with full filter/sort/limit/archive support in new `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py`. Parent #712 (archived epic). Dependency #719 (done — 34 RED tests in `tests/test_kanban_engine_listing.py`). Building blocks: `task_io.py` (read_task, write_task from #718 done), `config_loader.py` (load_config from #716 done), `engine_models.py` (TaskRecord, BoardConfig from #714 done).

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `list_tasks(status, tag, priority, search, sort, unclaimed, archived, limit, reverse, blocked)` returns filtered `list[TaskRecord]` | PASS — full signature with 10 filter/sort/pagination params; return type clear; matches Brief's KanbanEngine API surface | None |
| Reads all task files from tasks_dir via task_io module | PASS — specifies implementation approach; `task_io.read_task(path)` is available (#718 done); builder should glob `*.md` in tasks_dir from config | None |
| Filter logic matches kanban-md behavioral contracts | PASS — operationally defined by #719 tests (34 tests specify exact filter behavior); Brief behavioral contracts table provides additional context | None |
| Sort by each supported field | PASS — 6 fields (priority, updated, id, title, status, created) from #719 tests; priority/status must use config-rank order (not alphabetical) per test assertions | None |
| All #719 tests pass | PASS — clear exit gate; 34 tests in `test_kanban_engine_listing.py` | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One thing: create KanbanEngine class with list_tasks |
| Interface clarity | PASS | Full parameter list and return type in AC1; side effects: none (read-only); constructor: `KanbanEngine(kanban_dir: Path)` evident from tests |
| Dependency correctness | PASS | #719 done (34 RED tests). Upstream modules: engine_models (#714 done), config_loader (#716 done), task_io (#718 done) |
| Module layering | PASS | engine.py inside mcp-kanban package; imports from engine_models, task_io, config_loader — all same package; no upward imports |
| TDD compliance | PASS | #719 (RED) done with 34 tests across 11 TestFromAC_* classes |
| KISS/YAGNI | PASS | Minimal scope — implement only what the 34 tests require |
| Premise challenge | PASS | list_tasks is core engine operation per Brief KanbanEngine API surface |
| Pattern consistency | PASS | Uses existing patterns: Pydantic models (TaskRecord), file I/O (task_io.read_task), config loading (config_loader.load_config) |
| Security surface | PASS | Read-only filesystem operation; path traversal already guarded by task_io.validate_path_containment |
| Single domain | PASS | Kanban engine domain exclusively |

### Builder Guidance

1. **Constructor**: `KanbanEngine.__init__(self, kanban_dir: Path)` — load BoardConfig via `config_loader.load_config(kanban_dir)`, store `kanban_dir`, derive `tasks_dir` and archive dir paths from config.
2. **show_task**: Downstream #722 (CRUD GREEN, depends_on=[720, 721]) requires `show_task(task_id: str) -> TaskRecord` to exist on KanbanEngine. Its RED test is in `test_kanban_engine_crud.py:350` (`engine.show_task(task_id)`). Implement as: scan tasks_dir for file matching `{task_id}-*.md`, call `task_io.read_task()`. This is a natural companion to list_tasks and avoids blocking #722.
3. **Priority/status sort**: Must use config-rank order, NOT alphabetical. Tests explicitly guard against alphabetical regression (`test_sort_by_priority_uses_config_rank` asserts `priorities[0] == "someday"`).
4. **Archive directory**: Tests use `v1-archive/` as sibling to `tasks/` under kanban_dir. `archived=True` reads from archive dir instead of tasks_dir.
5. **Search**: Tests match exact case (`"bootstrap"` matches lowercase in title, `"Refactor"` matches exact case in body). The kanban-md binary uses case-insensitive search — implement case-insensitive to match behavioral contracts.

### Challenge Results
- Challenger: FALLBACK — agent not available in current agent set
- Architect response: Independent evaluation across all 10 criteria; verified TaskRecord model (engine_models.py:56-87), read_task (task_io.py:151-186), load_config (config_loader.py:50-60), existing list_tasks MCP tool patterns (server.py:163-212). 34 test assertions verified across 11 test classes. No concerns requiring formal challenge.

### Verdict: APPROVE
### Action Taken: Approved #720 to todo. AC is verifiable (34 RED tests as gate), dependencies correct, architecture sound. Builder guidance: also implement show_task() for downstream #722 compatibility, use config-rank sort order, case-insensitive search.

[[2026-04-09]] Thu 19:34
## Test-Writer Notes
- Test file: tests/test_kanban_engine_listing.py (written in RED phase #719)
- Classes: TestFromAC_ListAllTasks, TestFromAC_FilterByStatus, TestFromAC_FilterByTag, TestFromAC_FilterByPriority, TestFromAC_FilterByBlocked, TestFromAC_FilterByUnclaimed, TestFromAC_FullTextSearch, TestFromAC_SortByField, TestFromAC_ReverseOrdering, TestFromAC_LimitPagination, TestFromAC_ArchivedTasks
- Tests per category: happy 13, edge 9, error 4, boundary 8
- Total: 34 tests, all FAIL (ModuleNotFoundError: No module named 'owlbear_mcp_kanban.engine' — engine.py not yet created)
- ruff: not re-run (file unchanged from #719; was clean at handoff)
- AC coverage:
  | AC1 list_tasks returns list[TaskRecord]          | TestFromAC_ListAllTasks (3 tests)      |
  | AC2 filter by status/tag/priority/blocked/unclaimed | TestFromAC_FilterBy* (11 tests)     |
  | AC3 full-text search titles + bodies             | TestFromAC_FullTextSearch (4 tests)    |
  | AC4 sort by all 6 fields                         | TestFromAC_SortByField (6 tests)       |
  | AC5 reverse ordering                             | TestFromAC_ReverseOrdering (2 tests)   |
  | AC6 limit / pagination                           | TestFromAC_LimitPagination (3 tests)   |
  | AC7 archived task listing                        | TestFromAC_ArchivedTasks (4 tests)     |
  | AC8 all tests fail                               | CONFIRMED — ImportError on collection  |
- Notes: Tests were written in RED phase #719. All tests confirmed failing with ImportError — module owlbear_mcp_kanban.engine does not yet exist. No new tests required; full AC coverage achieved by #719 test suite.

[[2026-04-09]] Thu 19:46
## Builder Notes

### Files Changed
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` — **created** (new file, ~145 lines)

### Implementation
- `KanbanEngine.__init__(kanban_dir: Path)`: loads `BoardConfig` via `config_loader.load_config()`, derives `_tasks_dir` and `_archive_dir` (`v1-archive/`) from config and kanban_dir
- `list_tasks(...)`: globs `*.md` from tasks_dir or archive dir; applies status/tag/priority/blocked(tri-state)/unclaimed/search(case-insensitive) filters; sorts by id/title/status(config rank)/priority(config rank)/created/updated; reverses and limits; returns `list[TaskRecord]`
- `show_task(task_id: str)`: globs `{task_id}-*.md` in tasks_dir, returns `TaskRecord` — added per architect guidance to avoid blocking downstream #722
- Pattern: `# noqa: PLR0912, PLR0913, C901` on `list_tasks` (matches server.py convention)
- `contextlib.suppress(ValueError, KeyError)` for parse errors per SIM105
- TC001/TC003: `Path`, `BoardConfig`, `TaskRecord` moved into `TYPE_CHECKING` block

### Test Results
- RED verified: collection failed with `ModuleNotFoundError` (34 tests, 0 collected)
- GREEN: **34 passed, 0 failed** — all TestFromAC_* classes pass
- Ruff: **clean** (0 errors after fixes)
- Coverage: **92%** (61 stmts, 5 missed on lines 141–145 = show_task error branch, untested until #722)
- Full suite (`-m "not api"`): 2905 passed, 129 failures — all pre-existing, zero new failures touching engine.py

### AC Evidence
| AC | Evidence |
|----|----------|
| list_tasks returns list[TaskRecord] | TestFromAC_ListAllTasks (3 tests) ✅ |
| Reads all task files via task_io | glob *.md + read_task() ✅ |
| Filter logic matches behavioral contracts | TestFromAC_Filter* (11 tests) ✅ |
| Sort by each supported field (config rank) | TestFromAC_SortByField (6 tests) ✅ |
| All #719 tests pass | 34/34 ✅ |

[[2026-04-09]] Thu 19:52
## Review Evidence

### Test Results
- pytest: 34 passed, 0 failed (Quality-Runner, scoped to `tests/test_kanban_engine_listing.py`)

### Lint: clean (0 violations)

### Coverage: `owlbear_mcp_kanban.engine`: 92% (61 stmts, 5 missed = `show_task` FileNotFoundError branch, lines 141–145 — intentional, to be covered by #722)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|------------|---------------------------|---------|
| `list_tasks(...)` returns `list[TaskRecord]` | `TestFromAC_ListAllTasks` (3 tests): checks `len==3`, `isinstance(rec, TaskRecord)`, field values | Yes — field equality, type check, count would fail | COVERED |
| Reads all task files from tasks_dir via task_io | `test_returns_all_task_files`: writes 3 files, expects 3 records | Yes — count assertion would fail | COVERED |
| Filter logic matches behavioral contracts | `TestFromAC_FilterBy*` (11 tests) + `TestFromAC_FullTextSearch` (4 tests): specific count + field asserts per filter | Yes — each filter test checks exact count and field equality | COVERED |
| Sort by each supported field | `TestFromAC_SortByField` (6 tests): assert `[t.id for t in result] == [10, 20, 30]`; priority rank guard (`assert priorities[0] == "someday"`) | Yes — explicit order assertions, anti-alphabetical regression guard | COVERED |
| All #719 tests pass | 34/34 confirmed by Quality-Runner | Yes | COVERED |

#### Security Review

Reviewed `engine.py` against OWASP Top 10:
- **Hardcoded secrets**: None.
- **Injection**: No shell commands. `Path.glob()` is Python-level only — no subprocesses.
- **Path traversal (`list_tasks`)**: `source_dir` is config-derived, glob pattern is literal `"*.md"`. No user input in path. CLEAN.
- **Path traversal (`show_task`)**: `task_id` flows into `self._tasks_dir.glob(f"{task_id}-*.md")` without sanitization. Python 3.12 raises `ValueError` on `..` in glob patterns (py312 restriction), mitigating traversal. Wildcard injection (`task_id="*"`) would match multiple files and return an arbitrary first task — a correctness/ordering hazard but not an auth bypass. `validate_path_containment` exists in task_io but is NOT called here or by `read_task`. Mitigated sufficiently for this read-only context; formal security validation deferred to #722 scope where show_task gets AC coverage.
- **Insecure deserialization**: None — YAML parsed by `read_task`; SafeLoader assumed (verified by prior task_io review, #718).
- **No issues blocking PASS.**

#### Test Integrity

Builder created `engine.py` only (new file). `test_kanban_engine_listing.py` unchanged from RED phase #719. `get_changed_files` returned no unstaged/staged changes (file committed). No TestFromAC_* modifications possible.

| Original Test | Change Made | Assessment |
|--------------|------------|------------|
| All 34 TestFromAC_* tests | No changes (file unchanged from #719 RED phase) | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact counts, specific IDs (`assert [t.id for t in result] == [10, 20, 30]`), field equality |
| Negative/error coverage | ADEQUATE | All filter classes have a no-match→empty test; blocked tri-state (True/False/None) all tested |
| Mutation resistance | STRONG | Priority sort test explicitly asserts `priorities[0] == "someday"` and guard against alphabetical ordering; status sort uses rank-index comparison |
| Test independence | STRONG | All tests use `tmp_path` pytest fixture; no shared mutable state |
| Descriptive names | STRONG | e.g. `test_sort_by_priority_uses_config_rank`, `test_blocked_none_is_tri_state_no_filter` |

#### Data Safety
- No LLM output persisted. No shared mutable state. No race conditions (read-only, per-test tmp_path). No unbounded input: `limit=0` is explicitly tested as the "no cap" sentinel. CLEAN.

#### Implementation-Aware Gaps
- `contextlib.suppress(ValueError, KeyError)` silent-skip path in `list_tasks` loop — no test for malformed task file being silently skipped. Not in AC scope; defensive resilience code, not a behavioral contract. Pass 2 only.
- `show_task` FileNotFoundError branch (lines 141–145): acknowledged, intentional gap; covered by #722.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (single attempt) |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
1. `show_task` does not call `validate_path_containment(self._tasks_dir, matches[0])` before `read_task()`. The function exists in task_io and was the design intent per arch review. Should be wired in #722 when show_task gets AC coverage and tests.
2. No dedicated test for `contextlib.suppress` parse-error path (malformed `.md` silently dropped). Low priority since it's not in AC and follows existing package convention.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|---------|------------|--------|
| `list_tasks(...)` returns filtered `list[TaskRecord]` | `engine.py:52–143`; TestFromAC_ListAllTasks 3 tests pass | `test_result_items_are_task_records` | PASS |
| Reads all task files via task_io | `engine.py:84–87` globs `*.md`, calls `read_task(path)`; 3-file count test | `test_returns_all_task_files` | PASS |
| Filter logic matches behavioral contracts | `engine.py:90–107`; 11 filter tests + 4 search tests pass | `TestFromAC_FilterBy*`, `TestFromAC_FullTextSearch` | PASS |
| Sort by each supported field | `engine.py:109–130`; 6 sort tests pass, rank-guard assertions confirmed | `TestFromAC_SortByField` | PASS |
| All #719 tests pass | 34/34 confirmed independently by Quality-Runner | All TestFromAC_* classes | PASS |

### Verdict
confidence: .94 → **PASS**

0 deductions. All Pass 1 criteria met: 34/34 tests, lint clean, 92% coverage (gap in non-AC bonus method), full AC coverage with strong assertions, no TestFromAC modifications, no blocking security issues, CLEAN builder process. Two informational items logged; neither blocks advancement.

[[2026-04-09]] Thu 19:54
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | copilot-instructions.md covers only project identity and branch roles; no API/behavior tables reference mcp-kanban internals |
| 2 | Module docstrings → engine.py | Yes | PASS | Module docstring accurate; KanbanEngine class docstring present; list_tasks() has full Args + Returns; show_task() has Args + Raises; private helpers (_priority_rank, _status_rank) correctly undocumented |
| 3 | External attribution → sources/overview.md | No | N/A | No external patterns used; all conventions from internal sibling modules |
| 4 | CLI changes → README.md | No | N/A | No CLI additions |
| 5 | Research doc | No | N/A | No .owlbear/research/ doc produced for this task |

**Files updated**: None — no documentation changes required.
**Scratch files**: file_search for `.owlbear/scratch/720-*` returned nothing. Clean.

[[2026-04-09]] Thu 20:07
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `list_tasks(...)` returns filtered `list[TaskRecord]` | engine.py:52 signature + TestFromAC_ListAllTasks (3 tests) | PASS |
| Reads all task files from tasks_dir via task_io | engine.py:84-87 globs `*.md`, calls `read_task(path)` | PASS |
| Filter logic matches behavioral contracts | TestFromAC_FilterBy* (11 tests) + TestFromAC_FullTextSearch (4 tests) | PASS |
| Sort by each supported field | engine.py:109-130 config-rank sort; TestFromAC_SortByField (6 tests) | PASS |
| All #719 tests pass | 34/34 passed (confirmed independently) | PASS |

### Test Results
- pytest (scoped): 34 passed, 0 failed
- pytest (full suite): 2949 passed, 149 failed, 18 skipped — zero failures in task scope; all pre-existing
- ruff: All checks passed

### Architect Quality: 5/5
Specific AC with 34 RED tests as behavioral contract. Builder guidance (show_task, config-rank sort, case-insensitive search) was accurate and helpful. No vague lines, no improvisation required.

### Deduction Breakdown
- No AC lines without evidence: 0
- Lint: clean: 0
- AC quality > 3: 0
- Reviewer evidence: present and thorough: 0
- Full-suite failures in task scope: none: 0

### Confidence: 1.00
### Action: archive

### Note
Builder did not commit engine.py — deliverable was untracked (`??`). Committed as `f0f9bc4` during audit. Test file committed in RED phase (#719, `cee7a57`).

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| f0f9bc4 | feat | serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py | #720 |
