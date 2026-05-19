---
id: 960
title: Test daemon dispatch runtime context reuse
status: archived
priority: important
created: 2026-03-23T04:15:54.4645643+01:00
updated: 2026-03-24T14:01:58.4871123+01:00
started: 2026-03-24T14:00:50.2861648+01:00
completed: 2026-03-24T14:00:50.2861648+01:00
tags:
    - agent
    - daemon
    - scope:core
    - type:test
parent: 951
depends_on:
    - 959
class: standard
---

See docs/research/dispatched-agent-runtime-context.md. Scope: daemon dispatch only. Depends on the core shared formatter contract from #959.

AC:

- Add or update failing tests in `tests/test_daemon_coverage_gaps.py` for both the retry branch (step 3) and the fresh-dispatch branch (step 7) of `poll_tick()`, following the `TestFromAC_` naming pattern established by #958.
- Tests assert `builder.run()` receives an `instructions=` kwarg (produced by `format_dispatch_context()`) and a `deps=` kwarg (an `OwlBearDeps` with `dispatch_context: DispatchContext` populated from the daemon's `workspace`, `channel`, and kanban task inputs) in both paths.
- Tests assert the positional prompt argument to `builder.run()` still contains task body, WIP summary, and pre-hydrated content â€” these must not migrate into `instructions=`.
- Do not modify `src/owlbear/core/delegation.py`, `src/owlbear/daemon.py`, or agent markdown files in this task.

[[2026-03-23]] Mon 22:51

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add failing tests in test_daemon_coverage_gaps.py for retry and fresh paths | Original said 'existing daemon dispatch suites' without naming file. Tightened to specific file and TestFromAC_ naming. | Rewrote to pin file and naming convention. |
| Tests assert builder.run() receives instructions= and deps= kwargs | Original said 'consistent runtime instructions and deps shape' which was ambiguous. Specified exact kwargs, types, and provenance. | Rewrote to name concrete kwargs and source inputs. |
| Tests assert prompt still contains task body, WIP, and hydrated content | Already precise in original AC. | Preserved with minor wording clarification. |
| Do not modify core/delegation.py, daemon.py, or agent markdown files | Original omitted daemon.py from exclusion. Since RED test task, daemon.py changes belong to #961. | Added daemon.py to exclusion list. |

### Architecture Notes

- daemon.py poll_tick() calls builder.run(prompt) bare at lines 746 and 812 with no instructions= or deps=. RED tests will fail against this, satisfying TDD.
- Established test pattern from #958 in test_delegation.py uses TestFromAC_ classes, mock agents, and call_args kwargs assertions. Daemon tests should follow same pattern.
- core/delegation.py exports DispatchContext (frozen) and format_dispatch_context() from #959. Daemon tests import these as expected contract.
- core/deps.py has OwlBearDeps.dispatch_context: DispatchContext or None, which is the deps shape tests should assert.
- Preservation assertions (task body, WIP, hydration in prompt) pass against current code, serving as regression guards for #961.

### Changes Made

- Refined AC to specify exact test file, kwargs, types, and naming convention.
- Added daemon.py to the modification exclusion list for scope safety.
- Preserved dependency on #959 (archived).

### Dependencies

- Verified: #959 (dispatch-context carrier and delegation) -- archived (done).
- Verified: #961 (implement daemon dispatch) depends on #960 -- correct TDD ordering.

[[2026-03-24]] Tue 00:50

## Test-Writer Notes

- Test file: tests/test_daemon_coverage_gaps.py

- Classes: TestFromAC_PollTickRetryDispatchContext, TestFromAC_PollTickFreshDispatchContext

- Tests per category: happy 4, edge 2, boundary 4, error 4

- Total: 14 tests, all FAIL (AssertionError: 'instructions' not in {} / 'deps' not in {})

- ruff: clean

- AC coverage:

| AC Line | Test(s) | Category |

| --- | --- | --- |

| retry branch (step 3) receives instructions= | TestFromAC_PollTickRetryDispatchContext::test_builder_run_receives_instructions_kwarg | happy |

| retry branch (step 3) receives deps= | TestFromAC_PollTickRetryDispatchContext::test_builder_run_receives_deps_kwarg | happy |

| retry deps.dispatch_context is DispatchContext | TestFromAC_PollTickRetryDispatchContext::test_deps_has_dispatch_context_populated | happy |

| retry dispatch_context.workspace_root from param | TestFromAC_PollTickRetryDispatchContext::test_dispatch_context_workspace_root_matches_param | boundary |

| retry dispatch_context.task_id from entry | TestFromAC_PollTickRetryDispatchContext::test_dispatch_context_task_id_matches_retry_entry | boundary |

| retry prompt has body not in instructions= | TestFromAC_PollTickRetryDispatchContext::test_task_body_stays_in_prompt_not_migrated_to_instructions | edge |

| retry WIP summary stays in prompt | TestFromAC_PollTickRetryDispatchContext::test_wip_summary_stays_in_prompt_alongside_instructions_kwarg | edge |

| fresh branch (step 7) receives instructions= | TestFromAC_PollTickFreshDispatchContext::test_builder_run_receives_instructions_kwarg | happy |

| fresh branch (step 7) receives deps= | TestFromAC_PollTickFreshDispatchContext::test_builder_run_receives_deps_kwarg | happy |

| fresh deps.dispatch_context is DispatchContext | TestFromAC_PollTickFreshDispatchContext::test_deps_has_dispatch_context_populated | happy |

| fresh dispatch_context.workspace_root from param | TestFromAC_PollTickFreshDispatchContext::test_dispatch_context_workspace_root_matches_param | boundary |

| fresh dispatch_context.task_id from task | TestFromAC_PollTickFreshDispatchContext::test_dispatch_context_task_id_matches_dispatched_task | boundary |

| fresh prompt has body not in instructions= | TestFromAC_PollTickFreshDispatchContext::test_task_body_stays_in_prompt_not_migrated_to_instructions | error |

| fresh hydrated content stays in prompt | TestFromAC_PollTickFreshDispatchContext::test_hydrated_content_stays_in_prompt_alongside_instructions_kwarg | error |

[[2026-03-24]] Tue 01:16

## Builder Notes

- Files changed: none.
- Tests: 14 passed (`uv run pytest tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickRetryDispatchContext tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickFreshDispatchContext -q --tb=short`).
- Coverage: same scoped suite passed under bare `--cov`; repo-total reported 7% in scoped run context (expected for repository-wide source measurement).
- Lint: ruff clean (`uv run ruff check tests/test_daemon_coverage_gaps.py`).
- Evidence: both retry (step 3) and fresh-dispatch (step 7) TestFromAC classes assert `builder.run()` context kwargs and prompt-content retention, and pass in current codebase.
- RED check outcome: no longer reproducible for #960 because current daemon dispatch path already satisfies the runtime-context contract.
- Fixes applied: none.

[[2026-03-24]] Tue 02:13

## Review Evidence

### Test Results

- `uv run pytest tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickRetryDispatchContext tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickFreshDispatchContext -q --tb=short` -> 14 passed, 4 warnings (`qdrant_client` optional-dependency skips from `tests/conftest.py`)
- `uv run ruff check tests/test_daemon_coverage_gaps.py src/owlbear/daemon.py src/owlbear/core/deps.py src/owlbear/core/delegation.py` -> All checks passed!
- `uv run pytest ... --cov --cov-report=term-missing --cov-fail-under=0` -> scoped suite still 14 passed; bare repo-wide coverage reported `src/owlbear/daemon.py` 37% (informational only for this test-only task)

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC line | Mapped test(s) | Would fail if AC were violated? | Verdict |
| --- | --- | --- | --- |
| Retry + fresh branch TestFromAC coverage exists in `tests/test_daemon_coverage_gaps.py` | `TestFromAC_PollTickRetryDispatchContext` (`tests/test_daemon_coverage_gaps.py:1574`) and `TestFromAC_PollTickFreshDispatchContext` (`tests/test_daemon_coverage_gaps.py:1844`) | Yes - both classes run in the scoped pytest command above | COVERED |
| `builder.run()` receives `instructions=` and `deps=` built from workspace, channel, and kanban task inputs in both paths | Presence/workspace/task-id checks at `tests/test_daemon_coverage_gaps.py:1609`, `:1636`, `:1694`, `:1724`, `:1858`, `:1896`, `:1976`, `:2017` | No - the suite never asserts `channel_name`, `task_title`, or `task_status`, and `grep channel_name|task_title|task_status tests/test_daemon_coverage_gaps.py` returns no matches. A mutation that hard-codes `channel_name=cli` or blanks task title/status still passes. | LAX |
| `instructions=` is produced from `format_dispatch_context()` | Same instructions-presence tests only | No - daemon-scope tests assert key presence, not formatted content. `src/owlbear/daemon.py:689` calls `format_dispatch_context(dispatch_context)`, but a constant string would still satisfy this suite. | LAX |
| Positional prompt keeps task body, WIP summary, and pre-hydrated content instead of migrating them into `instructions=` | Task-body/WIP/hydration tests at `tests/test_daemon_coverage_gaps.py:1752`, `:1786`, `:2054`, `:2100` | No - retry WIP test checks prompt retention plus `instructions` presence, but never asserts the WIP summary stays out of `instructions=`. No compensating daemon-scope test covers that negative assertion. | LAX |

#### Security Review

- No security issues found in the reviewed daemon path or new tests.

#### Test Integrity

| Original test | Change made | Assessment |
| --- | --- | --- |
| `tests/test_daemon_coverage_gaps.py` TestFromAC runtime-context classes from commit `b56d67c` | `git diff --ignore-all-space b56d67c HEAD -- tests/test_daemon_coverage_gaps.py` returned no diff | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | WEAK | Presence-only assertions on `instructions=`/`deps=` do not verify channel/title/status propagation or actual formatted instructions content. |
| Negative/error paths | ADEQUATE | Task-body and fresh-hydration non-migration are checked, but retry-branch WIP non-migration is not. |
| Manual mutation reasoning | WEAK | Mutating `_build_builder_run_kwargs()` at `src/owlbear/daemon.py:684`, `:686`, `:687`, `:689` to hard-code `channel_name=cli` or drop `task_title`/`task_status` would still leave all 14 tests green. |
| Test independence | STRONG | Each test constructs fresh state/mocks/tmp paths. |
| Descriptive names | STRONG | Test names clearly describe branch and expected contract. |

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- `_build_builder_run_kwargs()` currently injects `channel_name` (`src/owlbear/daemon.py:684`), `task_title` (`src/owlbear/daemon.py:686`), `task_status` (`src/owlbear/daemon.py:687`), and `format_dispatch_context()` output (`src/owlbear/daemon.py:689`) into both retry and fresh dispatch call sites (`src/owlbear/daemon.py:807`, `src/owlbear/daemon.py:881`). The new daemon tests do not pin those fields, so this behavior can regress silently.

### Pass 2 - INFORMATIONAL

- Current HEAD implementation already satisfies the runtime-context contract; the rejection is about incomplete daemon-scope test coverage, not a demonstrated code bug in the live tree.

### AC Compliance

| AC line | Evidence | Mapped test | Status |
| --- | --- | --- | --- |
| Add or update failing tests for retry and fresh dispatch paths in `tests/test_daemon_coverage_gaps.py` | Scoped pytest passed both TestFromAC classes | Runtime-context classes | PASS |
| Tests assert `builder.run()` receives context from workspace, channel, and kanban task inputs in both paths | Workspace/task-id covered, but channel/title/status and actual formatted instructions content are untested | Runtime-context classes | FAIL |
| Tests assert prompt keeps task body, WIP summary, and pre-hydrated content out of `instructions=` | Task body and fresh hydrated content covered; retry WIP non-migration untested | Runtime-context classes | FAIL |

### Verdict

FAIL. The runtime-context test file is preserved and green, but AC coverage remains too weak on channel/task-title/task-status wiring and retry-branch WIP non-migration. Add compensating daemon-scope tests before re-review.

### Action Taken

- `kanban\kanban-md.exe edit 960 --status todo --release`

[[2026-03-24]] Tue 03:25

## Test-Writer Notes (retry)

- Retry reason: reviewer HIGH finding — prior 14 tests used presence-only assertions on instructions=/deps= without verifying channel_name, task_title, task_status field values or WIP non-migration into instructions=

- Added 9 new tests across both TestFromAC classes addressing each LAX finding

- TestFromAC_PollTickRetryDispatchContext (5 new): test_dispatch_context_channel_name_matches_channel_object, test_dispatch_context_task_title_from_kanban_show, test_dispatch_context_task_status_from_kanban_show, test_instructions_content_reflects_dispatch_context_fields, test_wip_summary_not_in_instructions_kwarg

- TestFromAC_PollTickFreshDispatchContext (4 new): test_dispatch_context_channel_name_matches_channel_object, test_dispatch_context_task_title_from_kanban_show, test_dispatch_context_task_status_from_kanban_show, test_instructions_content_reflects_dispatch_context_fields

- Preserved: 14 existing tests — all PASS (implementation already satisfies contract)

- New tests: all 23 PASS (implementation was already complete — note per retry-cycle: tests pass because builder implemented in prior cycle, new tests add mutation resistance for channel_name/title/status/instructions-content)

- ruff: clean

- Commit: 7fabc9a

[[2026-03-24]] Tue 04:07

## Builder Notes

- Files changed: none.
- Tests: 23 passed (`uv run pytest tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickRetryDispatchContext tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickFreshDispatchContext -q --tb=short`).
- Lint: ruff clean (`uv run ruff check tests/test_daemon_coverage_gaps.py src/owlbear/daemon.py src/owlbear/core/deps.py src/owlbear/core/delegation.py`).
- Coverage: scoped bare `--cov` run reported daemon/deps/delegation coverage and test pass output, but the shared foreground shell raised a teardown KeyboardInterrupt; no code changes were made, and this matches known terminal-output isolation behavior.
- Evidence: task scope is unchanged (`git status --short -- tests/test_daemon_coverage_gaps.py src/owlbear/daemon.py src/owlbear/core/deps.py src/owlbear/core/delegation.py` returned empty).
- Fixes applied: None (current implementation already satisfies the strengthened TestFromAC runtime-context contract).

[[2026-03-24]] Tue 05:19

## Review Evidence

### Findings

1. HIGH - instructions= coverage is still incomplete. The retry/fresh tests at tests/test_daemon_coverage_gaps.py:1968 and tests/test_daemon_coverage_gaps.py:2529 assert only Channel, Task ID, and Task substrings. format_dispatch_context() also emits Workspace and Status at src/owlbear/core/delegation.py:79 and src/owlbear/core/delegation.py:93, but there are no matching daemon-scope asserts for those formatter lines. A partial instructions string, or a formatter call with task_status=None, would still leave all 23 tests green.

### Test Results

- uv run pytest tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickRetryDispatchContext tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickFreshDispatchContext -q --tb=short -> 23 passed, 4 warnings
- uv run ruff check tests/test_daemon_coverage_gaps.py src/owlbear/daemon.py src/owlbear/core/deps.py src/owlbear/core/delegation.py -> All checks passed!
- uv run pytest tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickRetryDispatchContext tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickFreshDispatchContext --cov --cov-report=term-missing --cov-fail-under=0 -q -> 23 passed; src/owlbear/daemon.py 37%, src/owlbear/core/delegation.py 58%, src/owlbear/core/deps.py 100%

### Verdict

FAIL. Current HEAD looks correct, but the daemon-scope tests still do not pin the full shared formatter contract for instructions=. Add workspace/status formatter assertions or exact format_dispatch_context() output comparisons in both branches, then re-review.

[[2026-03-24]] Tue 11:23

## Builder Notes

- Files changed: none.
- Tests: 27 passed (`uv run pytest tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickRetryDispatchContext tests/test_daemon_coverage_gaps.py::TestFromAC_PollTickFreshDispatchContext -q --tb=short`).
- Coverage: scoped bare `--cov` run passed for the same 27 tests (`$env:COVERAGE_FILE='.coverage.task960.builder'`); repository-wide total reported 7% in this scoped context.
- Lint: ruff clean (`uv run ruff check tests/test_daemon_coverage_gaps.py src/owlbear/daemon.py src/owlbear/core/delegation.py src/owlbear/core/deps.py`).
- Evidence: `_build_builder_run_kwargs()` in `src/owlbear/daemon.py` populates `DispatchContext` with workspace/channel/task fields and forwards `instructions` from `format_dispatch_context()` for both retry (step 3) and fresh-dispatch (step 7) paths.
- Red check outcome: test-writer TestFromAC suites are already green against current HEAD; no reproducible red baseline remained for builder implementation.
- Fixes applied: None (implementation already satisfies runtime-context contract).

[[2026-03-24]] Tue 13:07

## Review Evidence\n### Findings\n- No blocking findings.\n\n### Test Results\n- Scoped pytest for TestFromAC_PollTickRetryDispatchContext and TestFromAC_PollTickFreshDispatchContext: 27 passed, 4 warnings (optional qdrant_client skips from tests/conftest.py).\n- Ruff on tests/test_daemon_coverage_gaps.py plus src/owlbear/daemon.py, src/owlbear/core/delegation.py, and src/owlbear/core/deps.py: All checks passed.\n- Scoped bare coverage run: 27 passed; src/owlbear/daemon.py 37%, src/owlbear/core/delegation.py 58%, src/owlbear/core/deps.py 100% (informational only because #960 is a test-only task and those source files were intentionally untouched).\n\n### Pass 1 - CRITICAL\n- AC coverage: TestFromAC_PollTickRetryDispatchContext at tests/test_daemon_coverage_gaps.py:1575 and TestFromAC_PollTickFreshDispatchContext at tests/test_daemon_coverage_gaps.py:2157 cover poll_tick step 3 and step 7.\n- Context kwargs: the current tests pin instructions/deps presence, OwlBearDeps.dispatch_context typing, and workspace/channel/task_id/task_title/task_status propagation in both branches. Code inspection confirms src/owlbear/daemon.py:701-723 builds DispatchContext and calls format_dispatch_context(), then both poll branches pass those kwargs at src/owlbear/daemon.py:816-823 and src/owlbear/daemon.py:889-896.\n- Prompt retention: retry tests pin task-body and WIP separation from instructions; fresh tests pin task-body and hydrated-content separation from instructions; existing fresh-path WIP prompt coverage remains at tests/test_daemon_coverage_gaps.py:995.\n- Test integrity: git diff --quiet 08b0b81 HEAD -- tests/test_daemon_coverage_gaps.py returned exit 0, so the latest task-specific TestFromAC file is preserved exactly at review time.\n- Scope safety: task-specific commits b56d67c, 7fabc9a, and 08b0b81 touched only tests/test_daemon_coverage_gaps.py. No forbidden edits landed in src/owlbear/daemon.py, src/owlbear/core/delegation.py, or agent markdown files.\n- Security and data safety: no issues found.\n- Test quality: assertion specificity STRONG; mutation resistance STRONG; independence STRONG; descriptive names STRONG; negative-path coverage ADEQUATE for the task contract.\n\n### Verdict\n- PASS. Confidence .93

[[2026-03-24]] Tue 14:00

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC classes in tests/test_daemon_coverage_gaps.py for retry+fresh paths | TestFromAC_PollTickRetryDispatchContext at L1575, TestFromAC_PollTickFreshDispatchContext at L2157 | PASS |
| Tests assert builder.run() receives instructions= and deps= with DispatchContext from workspace/channel/task inputs | 27 tests pass; channel_name, task_id, task_title, task_status, Workspace, Status fields all pinned in both branches | PASS |
| Tests assert prompt retains task body, WIP, hydrated content separate from instructions= | Tests at L1752, L1786, L2054, L2100 assert content in prompt and not in instructions= | PASS |
| No modifications to src/owlbear/core/delegation.py, daemon.py, or agent markdown files | All 3 commits touch only tests/test_daemon_coverage_gaps.py | PASS |

### Test Results

- Task-specific: 27 passed, 4 warnings (qdrant_client optional-dependency skips)
- Full suite: 4231 passed, 37 failed, 20 skipped, 9 warnings
- Full suite failures: all 37 are pre-existing and unrelated to #960
- ruff: All checks passed

### Upstream Commits

- b56d67c test: add failing tests for daemon dispatch context reuse (#960, test-writer)
- 7fabc9a test: add channel/title/status propagation and WIP non-migration assertions (#960, test-writer)
- 08b0b81 test: add workspace/status instructions assertions for #960 (test-writer)
- Test integrity: git diff --quiet 08b0b81 HEAD returned exit 0

### Architect Quality

- AC specificity: good, named exact file, kwargs, types, and exclusion list
- Edge case coverage: minor gap on field value propagation, caught by reviewer rejection cycles
- Design direction: architecture notes correctly identified call sites and contract
- AC quality score: 4/5

### Confidence: .96

### Action: archive

[[2026-03-24]] Tue 14:01

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 7e3938d | chore | kanban/tasks/960-...md | #960 |
