---
id: 924
title: Test bearclaw board failure handling and JSON parse errors (RED)
status: archived
priority: important
created: 2026-03-21T17:17:16.5195627+01:00
updated: 2026-03-22T17:54:20.101409+01:00
started: 2026-03-22T17:54:15.5140257+01:00
completed: 2026-03-22T17:54:15.5140257+01:00
tags:
    - cli
    - tooling
    - phase-14
    - test
    - type:test
    - scope:cli
class: standard
---

Research follow-up from docs/research/bearclaw-board-command-failure-handling.md.

Extend tests/test_cli_board.py with failing CLI-boundary tests for the board command failure contract.

AC:

1. In tests/test_cli_board.py, add failure-path tests that invoke the root bearclaw.cli.app via Typer CliRunner and cover missing-binary, non-zero task-list exit, non-zero move-log exit, invalid task-list JSON, and invalid move-log JSON.
2. Tests patch only bearclaw.commands.board.subprocess.run; they do not spawn a real kanban-md process or patch _cli_error or other helper seams.
3. Each failure-path case asserts exit code 1 and an Error: message that mentions kanban-md, distinguishes task-list failures from move-log failures, and distinguishes command failures from JSON parse failures.
4. Existing happy-path board assertions remain in tests/test_cli_board.py and stay green once implementation lands in #920.
5. All newly added failure-path tests fail before GREEN task #920.
6. Scope stays in tests/test_cli_board.py; do not add new shared test helpers or production abstractions for this card.

[[2026-03-21]] Sat 17:57

## Research

See docs/scratch/924-researcher.md for full findings, follow-up #926, and the linked doc docs/research/bearclaw-board-command-failure-tests-red-gate.md.

[[2026-03-21]] Sat 23:15

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1 | The five failure classes were explicit, but the public CLI entrypoint and seam were only implied. | Rewrote it to require Typer CliRunner against bearclaw.cli.app. |
| 2 | The subprocess seam was directionally right, but helper patching was still a loophole. | Tightened it to allow only bearclaw.commands.board.subprocess.run patching and to forbid real kanban-md execution or _cli_error patching. |
| 3 | The user-facing failure contract needed observable assertions, not an internal implementation guess. | Rewrote it to require exit code 1 plus Error: output that mentions kanban-md and distinguishes stage failures from JSON parse failures. |
| 4 | The coexistence requirement with the existing happy-path tests was sound. | Kept it and made the file boundary explicit. |
| 5 | The RED-before-GREEN gate was already verifiable. | Kept it as-is. |
| 6 | Scope control was missing. | Added a no-new-helper and no-production-abstraction boundary so cleanup stays in follow-up #926. |

### Architecture Notes

- tests/test_cli_board.py already defines the board contract at the root CLI boundary with CliRunner and module-local subprocess.run patching.
- src/bearclaw/cli.py installs Rich tracebacks at the root, so failure-path tests should assert the user-facing Error: contract instead of helper internals.
- src/bearclaw/commands/**init**.py and tests/test_cli_error_helper.py define the observable_cli_error behavior: stderr Error: prefix and exit code 1.
- src/bearclaw/commands/chat.py shows the existing BearClaw subprocess.run(check=False, capture_output=True, text=True) pattern the paired GREEN task should follow.
- Single-domain check passed: this card stays in CLI test coverage only.

### Changes Made

- Rewrote the task body into numbered, mechanically verifiable RED acceptance criteria.
- Preserved the research pointer and follow-up reference.
- Advanced the task from backlog to todo.

### Dependencies

- Verified paired GREEN task: #920.
- Verified research inputs: docs/research/bearclaw-board-command-failure-tests-red-gate.md and docs/research/bearclaw-board-command-failure-handling.md.
- Verified existing patterns: src/bearclaw/cli.py, src/bearclaw/commands/**init**.py, src/bearclaw/commands/chat.py, tests/test_cli_board.py, and tests/test_cli_error_helper.py.

[[2026-03-21]] Sat 23:55

## Test-Writer Notes

- Test file: tests/test_cli_board.py
- Class: TestFromAC_BoardFailurePaths
- Tests: happy 0, edge 0, error 5, boundary 0 | Total: 5 tests, all FAIL
- ruff: clean
- AC coverage:
  AC1: test_missing_binary_exits_1_with_error_referencing_kanban_md (error)
  AC1: test_tasklist_nonzero_exit_exits_1_with_stage_specific_command_error (error)
  AC1: test_movelog_nonzero_exit_exits_1_with_stage_specific_command_error (error)
  AC1: test_tasklist_invalid_json_exits_1_with_json_parse_error (error)
  AC1: test_movelog_invalid_json_exits_1_with_json_parse_error (error)
  AC2: all 5 tests patch only bearclaw.commands.board.subprocess.run
  AC3: exit_code==1 + Error: + kanban-md + stage + type asserted in all 5
  AC4: 23 existing happy-path tests all PASS
  AC5: all 5 new tests FAIL before GREEN task #920
  AC6: helpers added only in tests/test_cli_board.py, no shared fixtures
- Failure reasons: missing-binary -> empty output (no Error: prefix); nonzero exits -> exit 0 (impl returns []); invalid JSON -> empty output (JSONDecodeError caught by CliRunner)

[[2026-03-22]] Sun 04:28

## Builder Notes

- Files changed: none (failure handling was bundled in board.py when #910 landed)
- Tests: 28 passed (23 happy-path + 5 failure-path TestFromAC_BoardFailurePaths), coverage 99% on board.py
- Lint: ruff clean
- Evidence: uv run pytest tests/test_cli_board.py -- 28 passed; board.py 99% coverage
- Fixes applied: None — implementation was already in src/bearclaw/commands/board.py (_run_kanban handles FileNotFoundError, non-zero returncode, and JSONDecodeError via _cli_error with stage-specific messages)

[[2026-03-22]] Sun 17:14

## Review Evidence

Reviewer append smoke test

[[2026-03-22]] Sun 17:15

## Review Evidence

## Review: #924 - Test bearclaw board failure handling and JSON parse errors (RED)

### Test Results

- uv run pytest tests/test_cli_board.py -q --tb=short -> 28 passed, 2 warnings.
- uv run pytest tests/test_cli_board.py -q --tb=short -k BoardFailurePaths -> 5 passed, 23 deselected, 2 warnings.
- uv run pytest tests/test_cli_board.py -q --tb=short -k not BoardFailurePaths -> 23 passed, 5 deselected, 2 warnings.

### Lint Results

- uv run ruff check src/ tests/ -> 451 existing repository-wide errors (out of task scope).
- uv run ruff check tests/test_cli_board.py src/bearclaw/commands/board.py src/bearclaw/cli.py src/bearclaw/commands/**init**.py -> All checks passed.

### Coverage

- uv run pytest tests/test_cli_board.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- src/bearclaw/commands/board.py: 71 statements, 1 miss, 99%.

[[2026-03-22]] Sun 17:15

### Pass 1 - CRITICAL

- Test-Writer AC Coverage:
  - AC1 COVERED: TestFromAC_BoardFailurePaths and five failure methods present at tests/test_cli_board.py:453, 473, 487, 500, 513, 524; root app+CliRunner wiring at tests/test_cli_board.py:20, 22, 24.
  - AC2 COVERED: all failure tests patch only bearclaw.commands.board.subprocess.run at tests/test_cli_board.py:472, 486, 499, 512, 523.
  - AC3 COVERED: exit/error/kanban plus stage/type assertions at tests/test_cli_board.py:481-484, 493-497, 506-510, 517-521, 530-534.
  - AC4 COVERED: existing happy-path classes remain at tests/test_cli_board.py:100, 118, 220, 254, 372 and pass in isolated run (23 passed).
  - AC5 COVERED: task body Test-Writer Notes recorded all five tests failing pre-GREEN; same tests now pass (5 passed).
  - AC6 COVERED: scoped git status shows no task-scoped production-file changes (only tests/test_cli_board.py).
- Security Review: no hardcoded secrets, injection, path traversal, unsafe deserialization, or sensitive log leakage in task scope.
- Test Integrity: all five TestFromAC_BoardFailurePaths methods preserved vs Test-Writer Notes intent; no weakened or removed assertions observed.
- Integrity limitation: tests/test_cli_board.py is untracked in this workspace, so commit-to-commit diff evidence is unavailable.
- Test Quality: Assertion specificity ADEQUATE, Negative/error coverage STRONG, Mutation resistance ADEQUATE, Independence STRONG, Names STRONG.
- Data Safety: no issues found.
- Implementation-aware gaps: _run_kanban failure branches in src/bearclaw/commands/board.py:44-54 are covered; no significant untested high-risk path found.

[[2026-03-22]] Sun 17:15

### Pass 2 - INFORMATIONAL

- Repository-wide ruff currently has baseline findings unrelated to this task; scoped lint for task-relevant files is clean.

### AC Compliance

- AC1: PASS
- AC2: PASS
- AC3: PASS
- AC4: PASS
- AC5: PASS
- AC6: PASS

### Verdict: PASS

- Confidence: .91

### Action Taken

- Prepared to move task from review to docs.
