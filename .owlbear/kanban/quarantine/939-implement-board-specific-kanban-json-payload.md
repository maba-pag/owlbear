---
id: 939
title: Implement board-specific kanban JSON payload helper for BearClaw board CLI tests
status: archived
priority: nice-to-have
created: 2026-03-22T04:41:33.6631287+01:00
updated: 2026-03-25T07:15:41.3967342+01:00
started: 2026-03-25T07:14:58.5492584+01:00
completed: 2026-03-25T07:14:58.5492584+01:00
tags:
    - cli
    - test
    - tooling
    - phase-14
    - type:test
    - scope:cli
depends_on:
    - 910
    - 936
class: standard
---

Research follow-up from docs/research/bearclaw-board-kanban-json-fixtures.md. Build the board-only helper approved by #923 and exercised by #936. AC: (1) add a tests/cli_board_fixtures.py module exposing pure helpers for board_task(), board_move(), and board_payloads() or equivalent names that keep list/log JSON synchronized from shared semantic inputs; (2) update tests/test_cli_board.py to reuse the helper across happy-path and age-in-status cases without changing CLI-boundary assertions or local subprocess routing; (3) keep scope under tests/ only and do not modify tests/conftest.py, src/, or #926's generic subprocess-result helper lane; (4) helper output remains json.dumps-based and requires no live kanban binary or new dependency; (5) tests from #936 pass once implemented. See docs/research/bearclaw-board-kanban-json-fixtures.md.

[[2026-03-25]] Wed 01:55

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. cli_board_fixtures.py with board_task/board_move/board_payloads | Precise â€” RED tests in test_cli_board_fixtures.py define exact contract with field presence, kwargs, JSON round-trip, empty/multi cases | Keep |
| 2. Update test_cli_board.py happy-path and age cases | Clear â€” targets TestFromAC_BoardRendering, TestFromAC_AssigneeDisplay, TestFromAC_AgeInStatus; constraint ''without changing CLI-boundary assertions or local subprocess routing'' is precise | Keep |
| 3. Scope under tests/ only, no conftest/src/#926 | Concrete boundary, verifiable via git diff | Keep |
| 4. json.dumps-based, no live kanban binary or new dep | Clear, verifiable | Keep |
| 5. #936 tests pass once implemented | Clear, verifiable by running test_cli_board_fixtures.py | Keep |

### Architecture Notes

- Import path confirmed: pyproject.toml sets pythonpath = [''tests''], so from cli_board_fixtures import board_task resolves without conftest changes.
- Existing local helpers _task/_move in test_cli_board.py (lines 32-70) have near-identical signatures to the proposed board_task/board_move. Builder replaces usages in happy-path/assignee/age test classes and can optionally remove the now-unused local helpers.
- _subproc stays local to test_cli_board.py per AC2 constraint (subprocess routing is local).
- Failure-path helpers (_subproc_fail_list/_subproc_fail_log at lines 399-432) compose _task and make_completed_process from conftest. These are out of scope for AC2 (not happy-path or age cases), but builder may update them opportunistically if_task is removed. No requirement either way.
- No production code changes, no new dependencies, no security surface.
- No failure mode map needed (test-only task).

### Dependencies

- Verified: #910 (board command) archived
- Verified: #936 (RED tests) archived
- #926 (subprocess-result helpers) archived, scope boundary respected by AC3

[[2026-03-25]] Wed 02:18

## Test-Writer Notes

- Test file: tests/test_939_cli_board_migrate.py
- Classes: TestFromAC_HappyPathMigration, TestFromAC_AgeInStatusMigration, TestFromAC_HelpersArePure
- Total: 10 tests, all FAIL - ruff: clean
- AC2 happy-path: 4 tests (cli_board_fixtures import + BoardRendering + AssigneeDisplay uses board_task)
- AC2 age-in-status: 3 tests (AgeInStatus uses board_task + board_move)
- AC4 pure helpers: 3 tests (board_task/move/payloads callable without subprocess mock, fail with ImportError)
- AC1/AC5 fully covered by tests/test_cli_board_fixtures.py from #936
- AC3 scope constraint is a do-not-touch rule, verified by git diff only

[[2026-03-25]] Wed 02:47

## Builder Notes

- Files changed: tests/cli_board_fixtures.py, tests/test_cli_board.py
- Tests: 55 passed in task-specific RED/GREEN suite and 73 passed in scoped migration verification
- Coverage: Scoped coverage run completed successfully with repository total 18 percent; no src files changed in this task
- Lint: ruff clean on changed files
- Evidence: Scoped pytest and scoped coverage commands exited 0 after clearing stale pytest plugin autoload shell state; ruff check exited 0
- Fixes applied: implemented pure board fixture helpers (board_task, board_move, board_payloads) and migrated BoardRendering, AssigneeDisplay, and AgeInStatus tests to use imported helpers from cli_board_fixtures

[[2026-03-25]] Wed 03:28

## Review Evidence

### Review: #939 - Implement board-specific kanban JSON payload helper for BearClaw board CLI tests

### Test Results

- Targeted AC-owned pytest slice across TestFromAC_BoardRendering, TestFromAC_AssigneeDisplay, TestFromAC_AgeInStatus, tests/test_cli_board_fixtures.py, and tests/test_939_cli_board_migrate.py reported 73 passed in 3.38s.
- Broader tests/test_cli_board.py slice in the current workspace reported 3 failures outside #939 scope at tests/test_cli_board.py:690, :729, and :743. These were not used as the blocking criterion because they are outside the migrated classes and the workspace currently has unrelated src drift.

### Lint Results

- ruff: All checks passed on tests/cli_board_fixtures.py, tests/test_cli_board.py, tests/test_939_cli_board_migrate.py, and tests/test_cli_board_fixtures.py.

### Coverage

- N/A for pass/fail. #939 is a tests-only task; no src module changed, so bare coverage percentages are not meaningful for this gate.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| AC1 helper module exposes board_task, board_move, and board_payloads with synchronized JSON fixtures | tests/test_cli_board_fixtures.py:28, :128, :193, :350, :489 | Yes for the implemented contract: helper field presence, JSON serialization, move-age fixture shapes, and exact move detail formatting are asserted directly. | COVERED |
| AC2 migrated happy-path and age classes reuse shared helpers without relying on local helpers | tests/test_939_cli_board_migrate.py:50, :57, :67, :101, :111 | No. These checks only prove board_task or board_move appears somewhere in each class body. A partial migration leaving most _task or_move calls in place would still pass. | LAX |
| AC3 scope stays under tests only; no tests/conftest.py, src, or #926 helper lane edits | none; structural diff check | Yes by direct diff review: git diff between 788d1ba and 6e1bf3e lists only tests/cli_board_fixtures.py and tests/test_cli_board.py. | COVERED |
| AC4 helpers stay pure and json based with no live binary call | tests/test_939_cli_board_migrate.py:143, :150, :157 plus code review at tests/cli_board_fixtures.py:9 and :51 | Yes for purity, and current code review confirms stdlib json.dumps usage with no new dependency. | COVERED |
| AC5 #936 tests pass once implemented | tests/test_cli_board_fixtures.py full module in the 73-pass slice | Yes | COVERED |

#### Security Review

- No security issues found. Scope is tests-only helper construction and AST/file inspection.

#### Test Integrity

| Original Test | Change Made | Assessment |
| --- | --- | --- |
| Pre-existing TestFromAC_BoardRendering methods in tests/test_cli_board.py | 788d1ba to 6e1bf3e swaps _task calls to board_task and leaves assertions intact. | PRESERVED |
| Pre-existing TestFromAC_AssigneeDisplay methods in tests/test_cli_board.py | 788d1ba to 6e1bf3e swaps _task calls to board_task and leaves assertions intact. | PRESERVED |
| Pre-existing TestFromAC_AgeInStatus methods in tests/test_cli_board.py | 788d1ba to 6e1bf3e swaps _task and_move calls to board_task and board_move, with assertions intact. | PRESERVED |
| TestFromAC classes in tests/test_939_cli_board_migrate.py | No builder changes; 788d1ba to 6e1bf3e does not touch the file. | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | WEAK | tests/test_939_cli_board_migrate.py:57, :67, :101, and :111 only search for board_task or board_move substrings in ast.unparse(cls). They do not assert that legacy _task or_move calls were fully removed from the migrated classes. |
| Negative or error paths | ADEQUATE | tests/test_cli_board_fixtures.py covers empty lists, wrong-destination age fixtures, created fallback, and exact move-detail formatting. |
| Mutation reasoning | WEAK | If only one method per migrated class were rewritten to use board_task or board_move while the rest still used _task or_move, the migration tests would still pass. |
| Test independence | STRONG | The helper-contract tests are pure function calls; the migration tests are AST and file reads with no shared mutable state. |
| Descriptive names | STRONG | Method names clearly state the required migration and helper-contract scenarios. |

#### Data Safety

- No data safety issues found. The task adds pure test helpers and test-only imports.

#### Implementation-Aware Test Gaps

- The implementation currently satisfies AC2, but the migration tests do not lock that in robustly. They never assert absence of _task or_move inside TestFromAC_BoardRendering, TestFromAC_AssigneeDisplay, or TestFromAC_AgeInStatus, and they do not check that every migrated method uses the shared helpers. That leaves a real regression hole for future partial rewrites.

### Pass 2 - INFORMATIONAL

- The current workspace has unrelated in-flight src changes. A broader tests/test_cli_board.py run currently fails in threshold-style tests at lines 690, 729, and 743, outside the classes touched by #939.
- tests/test_939_cli_board_migrate.py also has current full-file working-tree churn that reads as non-semantic line-ending normalization; the builder commit did not touch that file.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
| --- | --- | --- | --- |
| AC1 add tests/cli_board_fixtures.py with board_task, board_move, and board_payloads | tests/cli_board_fixtures.py:12, :36, :51, :59 | tests/test_cli_board_fixtures.py:28, :128, :193, :350, :489 | PASS |
| AC2 migrate happy-path and age-in-status cases in tests/test_cli_board.py | tests/test_cli_board.py:20, :119, :221, :258 and direct diff review | tests/test_939_cli_board_migrate.py:50, :57, :67, :101, :111 | PASS |
| AC3 keep scope under tests only and do not touch tests/conftest.py, src, or #926 helper lane | git diff between 788d1ba and 6e1bf3e lists only tests/cli_board_fixtures.py and tests/test_cli_board.py | structural diff review | PASS |
| AC4 helper output remains json based and requires no live binary or new dependency | tests/cli_board_fixtures.py:9 and :51 plus direct helper calls at tests/test_939_cli_board_migrate.py:143, :150, :157 | tests/test_939_cli_board_migrate.py helper-purity tests | PASS |
| AC5 tests from #936 pass once implemented | targeted pytest slice included tests/test_cli_board_fixtures.py and passed 73 total | tests/test_cli_board_fixtures.py full module | PASS |

### Verdict: FAIL

- The current implementation meets the AC, but the review gate still fails because the new migration tests are too lax. They would allow partial helper migration in the targeted TestFromAC classes without failing, which violates the reviewer bar for meaningful AC enforcement.

### Action Taken

- Appended review evidence.
- Returning task #939 to todo for stronger migration assertions.

[[2026-03-25]] Wed 05:28

## Builder Notes

- Files changed: none (green on arrival; existing task implementation already present).
- Tests: scoped AC slice passed 77 tests; migration file check passed 34 tests.
- Coverage: scoped coverage run passed; repository total reported 19 percent because this task touches tests only and no src modules changed.
- Lint: ruff check passed for tests/cli_board_fixtures.py, tests/test_cli_board.py, tests/test_939_cli_board_migrate.py, tests/test_cli_board_fixtures.py.
- Evidence: TestFromAC classes for board rendering, assignee display, and age in status all passed; strict local-helper absence assertions in test_939 file also passed.
- Fixes applied: none. No code changes required in builder phase.

[[2026-03-25]] Wed 06:10

## Review Evidence

### Review: #939 - Implement board-specific kanban JSON payload helper for BearClaw board CLI tests

### Test Results

- Isolated scoped pytest run passed 77 tests in 3.18s across tests/test_cli_board_fixtures.py, tests/test_939_cli_board_migrate.py, TestFromAC_BoardRendering, TestFromAC_AssigneeDisplay, and TestFromAC_AgeInStatus.
- A foreground pytest attempt died during pytest startup with a spurious KeyboardInterrupt before collection. Verdict uses the isolated rerun only.

### Lint Results

- Ruff passed for tests/cli_board_fixtures.py, tests/test_cli_board.py, tests/test_939_cli_board_migrate.py, and tests/test_cli_board_fixtures.py.

### Coverage

- Not used for pass or fail. This is a tests-only task with no src changes.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC1 covered: tests/cli_board_fixtures.py defines board_task at line 12, board_move at line 36, board_payloads at line 51, and exports them at line 59. Contract tests exist in tests/test_cli_board_fixtures.py at lines 25, 125, 190, 295, 347, 489, and 495.
- AC2 covered: tests/test_cli_board.py imports board_task and board_move at line 20 and the migrated classes use them throughout TestFromAC_BoardRendering starting at line 119, TestFromAC_AssigneeDisplay starting at line 221, and TestFromAC_AgeInStatus starting at line 258. tests/test_939_cli_board_migrate.py now adds strict AST absence checks for local_task and _move at lines 185 and 200 through 243, closing the prior partial-migration gap.
- AC3 covered: diff review against 788d1ba shows scope stayed under tests only. The builder baseline changed tests/test_cli_board.py; the current workspace additionally strengthens tests/test_939_cli_board_migrate.py. No src or tests/conftest.py changes were part of the task state I reviewed.
- AC4 covered: tests/cli_board_fixtures.py uses stdlib json and serializes through json.dumps in board_payloads at lines 51 through 56. Purity checks run in tests/test_939_cli_board_migrate.py starting at line 140.
- AC5 covered: the isolated pytest slice included the full tests/test_cli_board_fixtures.py module and passed.

#### Security Review

- No security findings. Scope is pure test fixture generation and test-only AST inspection.

#### Test Integrity

- tests/test_cli_board.py TestFromAC_BoardRendering: preserved. The diff from 788d1ba replaces local_task calls with board_task while keeping the CLI assertions intact.
- tests/test_cli_board.py TestFromAC_AssigneeDisplay: preserved. Local_task calls become board_task and the priority assertions are unchanged.
- tests/test_cli_board.py TestFromAC_AgeInStatus: preserved. Local_task and _move calls become board_task and board_move; age assertions remain intact.
- tests/test_939_cli_board_migrate.py existing TestFromAC_HappyPathMigration, TestFromAC_AgeInStatusMigration, and TestFromAC_HelpersArePure are preserved.
- tests/test_939_cli_board_migrate.py adds _local_name_calls at line 185 and TestFromAC_NoLocalHelpersInMigratedClasses at lines 200 through 243. This is a strengthening change, not a weakening or removal.

#### Test Quality

- Assertion specificity: ADEQUATE. The helper contract tests assert exact fields and JSON behavior, and the migration file now uses AST exact-match checks to reject local _task and_move calls in the migrated classes.
- Negative and error-path coverage: ADEQUATE. tests/test_cli_board_fixtures.py covers empty payloads, created fallback fixtures, wrong-destination fixtures, and exact move-detail formatting.
- Mutation reasoning: ADEQUATE. Reverting any migrated class back to local _task or_move would fail the new AST checks, and changing helper output shape or detail formatting would fail the contract tests.
- Test independence: STRONG. The helper tests are pure function calls and the migration tests read and parse source without shared mutable state.
- Descriptive names: STRONG. Test names map cleanly to the migration and fixture contracts.

#### Data Safety

- No data-safety findings.

#### Implementation-Aware Test Gaps

- No significant untested paths remain for the implemented scope. The helper module has three pure functions and current tests cover field omission, JSON serialization, multiple entries, assignee precedence fixtures, age-fixture scenarios, and strict no-local-helper migration checks.

### Pass 2 - INFORMATIONAL

- Review was performed against current working-tree state. git status showed task-local modifications in tests/test_939_cli_board_migrate.py in addition to the already-reviewed task files.
- The first foreground pytest invocation was discarded because it ended during pytest startup with a spurious KeyboardInterrupt. The isolated rerun completed cleanly and is the evidence basis for this verdict.

### AC Compliance

- AC1 PASS: helper definitions at tests/cli_board_fixtures.py lines 12, 36, 51, and 59, backed by tests/test_cli_board_fixtures.py starting at lines 25, 125, and 190.
- AC2 PASS: shared-helper import and usage at tests/test_cli_board.py lines 20, 119, 221, and 258, plus migration enforcement at tests/test_939_cli_board_migrate.py lines 47, 98, 185, and 200 through 243.
- AC3 PASS: structural diff review kept the task within tests only.
- AC4 PASS: json-based pure helpers in tests/cli_board_fixtures.py lines 8 and 51 through 56, backed by tests/test_939_cli_board_migrate.py starting at line 140.
- AC5 PASS: isolated scoped pytest run passed 77 tests including the full tests/test_cli_board_fixtures.py module.

### Verdict: PASS

- The prior FAIL condition is resolved in the current workspace state. No critical findings remain.

### Confidence

- .93

### Action Taken

- Appending review evidence and moving task to docs.

[[2026-03-25]] Wed 07:15

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 cli_board_fixtures.py with board_task/board_move/board_payloads | File exists at tests/cli_board_fixtures.py L12/L36/L51/L59; contract tests in test_cli_board_fixtures.py | PASS |
| AC2 Migrate happy-path and age-in-status in test_cli_board.py | Import at L20; BoardRendering L119, AssigneeDisplay L221, AgeInStatus L258 use shared helpers; strict AST absence checks in test_939 | PASS |
| AC3 Scope under tests/ only | git log 788d1ba..6e1bf3e touches only tests/ files | PASS |
| AC4 json.dumps-based, no live binary | cli_board_fixtures.py imports only stdlib json (L9); purity tests pass | PASS |
| AC5 #936 tests pass | 110 scoped tests pass including full test_cli_board_fixtures.py | PASS |

### Test Results

- scoped: 110 passed (test_cli_board_fixtures + test_939_cli_board_migrate + test_cli_board) in 3.50s
- full suite: 4339 passed, 38 pre-existing failures (none #939-related), 2 skipped
- ruff: all checks passed

### AC Quality Score: 4/5

AC was specific with named files, functions, and scope boundaries. Minor gap: AC2 said 'reuse' without specifying full migration (no local helpers remaining), which required reviewer to demand strict absence checks in cycle 1. Otherwise solid.

### Confidence: .95

### Action: archive

### Quality Gap

test_939_cli_board_migrate.py was modified with reviewer-requested strict AST absence checks but left uncommitted by the builder. Committed by auditor as aa33619.

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 788d1ba | test | test_939_cli_board_migrate.py | #939 |
| 6e1bf3e | test | cli_board_fixtures.py, test_cli_board.py | #939 |
| aa33619 | test | test_939_cli_board_migrate.py | #939 |
