---
id: 975
title: Add make_completed_process duplicate-guard to test_conftest_helpers.py
status: archived
priority: nice-to-have
created: 2026-03-24T03:00:36.0996016+01:00
updated: 2026-03-25T05:11:14.1150357+01:00
started: 2026-03-25T05:10:51.3393746+01:00
completed: 2026-03-25T05:10:51.3393746+01:00
tags:
    - cli
    - test
    - tooling
    - type:test
    - scope:cli
class: standard
---

Research follow-up from docs/research/completedprocess-factory-implementation-gate.md.

## AC

- [ ] Add a parametrized test in TestFromAC_ZeroDuplicates (tests/test_conftest_helpers.py) that asserts test_cli_chat.py and test_cli_board.py do not define their own make_completed_process function.
- [ ] Follows existing duplicate-guard pattern (see MockChannel, _make_mock_toolset,_make_settings guards).
- [ ] Existing tests stay green.
- [ ] Scope: tests/test_conftest_helpers.py only.

[[2026-03-24]] Tue 13:19

## Research

- Scope: validate AC feasibility and alignment with existing duplicate-guard pattern.
- Finding: _has_func_def helper already exists; 3 identical guards already in TestFromAC_ZeroDuplicates. Implementation is ~10 LOC parametrized method. No blockers.
- Consumers: test_cli_chat.py (4 import sites) and test_cli_board.py (2 import sites) — neither redefines the function.
- Confidence: .92 — single clear approach, no trade-offs.
- Research doc: docs/research/make-completed-process-duplicate-guard.md
- No new external sources (all internal codebase evidence).

[[2026-03-24]] Tue 15:25

## Architecture Review

**Verdict:** Approve

### AC Assessment

All 4 AC lines are already satisfied by commit 83c9fed (task #927).

- Parametrized test at tests/test_conftest_helpers.py lines 390-400 covers test_cli_chat.py and test_cli_board.py.
- Follows _has_func_def pattern identical to the 3 existing guards at lines 331-388.
- Existing tests pass (scoped run confirmed).
- Scope confined to tests/test_conftest_helpers.py.

### Architecture Notes

Green-on-arrival: the #927 test-writer implemented this guard before #975 was picked up. Downstream agents should verify and fast-track.
No TDD test task needed: this IS the test task, and the tests already exist.

### Changes Made

- None.

### Dependencies

- No depends_on. No blocking dependencies.

[[2026-03-24]] Tue 16:35

## Test-Writer Notes

- Green-on-arrival: all AC tests already exist in tests/test_conftest_helpers.py (committed in task #927).
- Test file: tests/test_conftest_helpers.py
- Class: TestFromAC_ZeroDuplicates
- New test: test_no_duplicate_make_completed_process (parametrized: test_cli_board.py, test_cli_chat.py)
- Follows _has_func_def pattern identical to 3 existing guards.
- pytest: 14 passed, 2 warnings.
- ruff: clean.
- Overtaken RED: no new test files needed; builder should verify and fast-track.

[[2026-03-25]] Wed 02:44

## Builder Notes

- Files changed: None. Green-on-arrival no-op; AC already satisfied in tests/test_conftest_helpers.py.
- Tests: 49 passed, 4 warnings on tests/test_conftest_helpers.py.
- Coverage: Scoped bare coverage run completed; project source total reported 2% because no source modules were exercised in this test-only task.
- Lint: ruff clean on tests/test_conftest_helpers.py.
- Evidence: pytest reported 49 passed in 0.46s; coverage run reported 49 passed in 2.32s; ruff reported All checks passed.
- Fixes applied: None.

[[2026-03-25]] Wed 03:00

## Review Evidence

### Review: #975 - Add make_completed_process duplicate-guard to test_conftest_helpers.py

### Test Results

- pytest: 49 passed, 4 warnings on tests/test_conftest_helpers.py.
- Evidence: Scoped run completed in 0.38s. Warnings are optional-dependency skip notices from tests/conftest.py:58 and are unrelated to this task.

### Lint Results

- ruff: All checks passed on tests/test_conftest_helpers.py.

### Coverage

- Bare scoped coverage run also passed with 49 passed, 4 warnings.
- Note: repo source total reported 2 percent, which is not meaningful for this tests-only task because the guarded behavior lives entirely in tests/test_conftest_helpers.py.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC: Add a parametrized test in TestFromAC_ZeroDuplicates that asserts test_cli_chat.py and test_cli_board.py do not define their own make_completed_process function.
  Mapped test: TestFromAC_ZeroDuplicates::test_no_duplicate_make_completed_process.
  Would fail if violated: Yes. tests/test_conftest_helpers.py:386-387 parameterize both filenames, line 390 defines the test, and line 395 asserts not_has_func_def(filepath, make_completed_process). Current consumer-file search found only imports or calls in tests/test_cli_chat.py:305,309,318,322,333,337,346,350 and tests/test_cli_board.py:413,417,418,434,438,439. No local def make_completed_process match was found in either file.
  Verdict: COVERED.
- AC: Existing tests stay green.
  Mapped test: Scoped pytest on tests/test_conftest_helpers.py.
  Would fail if violated: Yes. Current run is 49 passed.
  Verdict: COVERED.
- Note: Non-runtime AC lines for duplicate-guard pattern and scope confinement are verified in AC Compliance below.

#### Security Review

- No security issues found. Scope is AST-based duplicate detection in test code only; no secrets, shell execution, path traversal, or unsafe deserialization introduced.

#### Test Integrity

- Original test: TestFromAC_ZeroDuplicates::test_no_duplicate_make_completed_process.
  Change made: No change.
  Assessment: PRESERVED.
  Evidence: git blame for tests/test_conftest_helpers.py lines 390-400 attributes the method body to commit 83c9fed from the earlier test-writer work.

#### Test Quality

- Assertion specificity: STRONG. The assertion checks the exact prohibited symbol name and includes the offending filename in the failure message.
- Negative or error paths: ADEQUATE. The parametrized test covers both current consumer files. Missing-file skip behavior matches the established duplicate-guard pattern in the same class.
- Mutation reasoning: STRONG. Adding a top-level def make_completed_process to either consumer file would make _has_func_def return True and fail the test.
- Test independence: STRONG. The test only parses repository files; no shared mutable state or order dependence.
- Descriptive names: STRONG. test_no_duplicate_make_completed_process precisely states the guarded regression.

#### Data Safety

- No data safety issues found. The test reads tracked files and parses AST only; no persistence, concurrency, or unbounded input risk.

#### Implementation-Aware Test Gaps

- No significant untested paths. _has_func_def is intentionally top-level only per tests/test_conftest_helpers.py:317, and the new guard uses the same helper and structure as the neighboring duplicate guards for_make_mock_toolset and _make_settings.

### Pass 2 - INFORMATIONAL

- tests/test_cli_chat.py currently has an unstaged working-tree diff, but the current file still only imports or calls make_completed_process at lines 305, 309, 318, 322, 333, 337, 346, and 350. No local def was found, and the duplicate-guard test passes against the current workspace state.
- No other informational findings.

### AC Compliance

- AC: Add a parametrized test in TestFromAC_ZeroDuplicates (tests/test_conftest_helpers.py) that asserts test_cli_chat.py and test_cli_board.py do not define their own make_completed_process function.
  Evidence: tests/test_conftest_helpers.py:386-387 list both filenames, line 390 defines the parametrized test, and line 395 asserts not_has_func_def(filepath, make_completed_process).
  Mapped test: TestFromAC_ZeroDuplicates::test_no_duplicate_make_completed_process.
  Status: PASS.
- AC: Follows existing duplicate-guard pattern (see MockChannel, _make_mock_toolset,_make_settings guards).
  Evidence: tests/test_conftest_helpers.py:317 defines_has_func_def. The new method reuses the same filepath existence check and assert-not-_has_func_def shape used by the neighboring guards at lines 361 and 379.
  Mapped test: TestFromAC_ZeroDuplicates::test_no_duplicate_make_completed_process.
  Status: PASS.
- AC: Existing tests stay green.
  Evidence: Scoped pytest on tests/test_conftest_helpers.py returned 49 passed, 4 warnings in 0.38s. Ruff on tests/test_conftest_helpers.py returned All checks passed.
  Mapped test: tests/test_conftest_helpers.py slice.
  Status: PASS.
- AC: Scope: tests/test_conftest_helpers.py only.
  Evidence: The task-specific duplicate guard lives in tests/test_conftest_helpers.py, and the shared helper already lives in tests/conftest.py:126. Review found no local def make_completed_process in tests/test_cli_chat.py or tests/test_cli_board.py.
  Mapped test: Code review.
  Status: PASS.

### Verdict: PASS

### Action Taken

- Moved task to docs and released reviewer claim.

[[2026-03-25]] Wed 04:09

## Docs Gate: test-only task, no docs impact

[[2026-03-25]] Wed 04:09

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only task; no behavior or API change |
| 2 | Docstrings | No | N/A | Only tests/test_conftest_helpers.py modified; no application modules touched |
| 3 | sources/overview.md | No | N/A | No new external sources all internal evidence |
| 4 | README.md | No | N/A | No CLI commands changed |
| 5 | Research doc | Yes | Pass | docs/research/make-completed-process-duplicate-guard.md exists and linked in task body |
| 6 | Scratch files | N/A | Pass | No docs/scratch/975-* files found |

### Files Updated

- None

### Scratch Files Cleaned

- None

[[2026-03-25]] Wed 04:09

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only task no behavior or API change |
| 2 | Docstrings | No | N/A | Only test file modified no application modules touched |
| 3 | sources/overview.md | No | N/A | No new external sources internal evidence only |
| 4 | README.md | No | N/A | No CLI commands changed |
| 5 | Research doc | Yes | Pass | make-completed-process-duplicate-guard.md exists and linked |
| 6 | Scratch files | N/A | Pass | No docs/scratch/975-* files found |

### Files Updated

- None

### Scratch Files Cleaned

- None

[[2026-03-25]] Wed 04:09

## Docs Gate

No docs impact. Test-only task, no application changes.

[[2026-03-25]] Wed 05:10

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Parametrized test in TestFromAC_ZeroDuplicates for test_cli_chat.py and test_cli_board.py | tests/test_conftest_helpers.py:386-400, parametrized over both filenames, asserts not _has_func_def | PASS |
| Follows existing duplicate-guard pattern | Identical shape to MockChannel (L331), _make_mock_toolset (L361),_make_settings (L379) guards | PASS |
| Existing tests stay green | 4339 passed, 37 pre-existing RED-phase failures, 0 in test_conftest_helpers.py | PASS |
| Scope: tests/test_conftest_helpers.py only | Only deliverable file; upstream commit 83c9fed scoped to this file | PASS |

### Test Results

- pytest: 4339 passed, 37 failed (all pre-existing RED-phase), 2 skipped, 7 warnings
- ruff: All checks passed on tests/test_conftest_helpers.py

### Architect Quality

- AC specificity: 5/5 all lines concrete and verifiable
- Edge cases: N/A for duplicate-guard test task
- Design notes: Architect correctly identified green-on-arrival from #927

### Confidence: .97

### Action: archive

[[2026-03-25]] Wed 05:11

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1624f76 | chore | kanban/tasks/975-*.md | #975 |
