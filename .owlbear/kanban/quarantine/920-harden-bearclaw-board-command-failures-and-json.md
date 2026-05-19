---
id: 920
title: Harden bearclaw board command failures and JSON parsing
status: archived
priority: important
created: 2026-03-21T16:42:55.2571034+01:00
updated: 2026-03-23T05:46:44.3977784+01:00
started: 2026-03-23T05:46:17.1573373+01:00
completed: 2026-03-23T05:46:17.1573373+01:00
tags:
    - cli
    - tooling
    - phase-14
    - type:build
    - scope:cli
depends_on:
    - 910
    - 924
class: standard
---

Research follow-up from docs/research/bearclaw-board-command-implementation-gate.md. Harden bearclaw board failure handling after the MVP board command in #910 lands.

AC:
(1) in src/bearclaw/commands/board.py, keep the failure-handling seam as a task-local helper around subprocess.run(..., check=False, capture_output=True, text=True) for kanban-md JSON loading, and route missing kanban-md, non-zero task-list or move-log exits, and invalid JSON through bearclaw.commands._cli_error instead of uncaught exceptions or Rich tracebacks.
(2) user-facing errors must mention kanban-md and distinguish task-list failures from move-log failures; JSON parse failures must be reported as parse failures rather than as generic command failures.
(3) if move-log loading or parsing fails, bearclaw board aborts through_cli_error; created-timestamp fallback remains allowed only when a successfully loaded move log has no matching move into the current status.
(4) scope stays in src/bearclaw/commands/board.py and tests/test_cli_board.py, follows existing BearClaw Typer/_cli_error/subprocess patterns, and adds no new dependencies.
(5) happy-path board tests from #909 stay green and failure-path tests from #924 pass.

[[2026-03-21]] Sat 17:19

## Research

Doc: docs/research/bearclaw-board-command-failure-handling.md

Summary: keep a local board.py helper that runs kanban-md with check=False and maps missing-binary, non-zero task-list or move-log exits, and invalid JSON through _cli_error with stage-specific messages; do not treat move-log load failure as a created fallback.

Follow-up created:

- #924 Test bearclaw board failure handling and JSON parse errors (RED)

Attribution updated: docs/sources/overview.md

[[2026-03-21]] Sat 17:59

## Architecture Review

See docs/scratch/920-architect.md for full review.

[[2026-03-23]] Mon 01:31

## Test-Writer Notes

- Test file: tests/test_cli_board.py
- Classes: TestFromAC_BoardFailurePaths (from #924), TestFromAC_AgeInStatus (age/fallback coverage)
- Tests per category: happy 0 new, edge 0 new, error 5 existing, boundary 0 new
- Total: 30 tests all PASS (5 failure-path tests from #924 cover all AC lines)
- ruff: clean (no new test code added)
- Pipeline note: implementation (board.py _run_kanban) and failure-path tests
  (TestFromAC_BoardFailurePaths) were committed as part of #924 work before
  #920 advanced through the test-writer gate. All AC lines are already covered.
- AC coverage:
  AC#1 _run_kanban routes failures via _cli_error: test_missing_binary_exits_1, test_tasklist_nonzero_exit, test_movelog_nonzero_exit (error)
  AC#2 messages name kanban-md and distinguish stages/JSON: all 5 TestFromAC_BoardFailurePaths tests (error)
  AC#3 move-log failures abort; created fallback scoped correctly: test_movelog_* (abort), test_age_falls_back_to_created_* (allowed fallback) (error/boundary)
  AC#4 scope constraint: not directly testable
  AC#5 all 30 existing tests pass: confirmed

[[2026-03-23]] Mon 01:31

## Test-Writer Notes

- Test file: tests/test_cli_board.py
- Classes: TestFromAC_BoardFailurePaths (from #924), TestFromAC_AgeInStatus (age/fallback coverage)
- Tests per category: happy 0 new, edge 0 new, error 5 existing, boundary 0 new
- Total: 30 tests all PASS (5 failure-path tests from #924 cover all AC lines)
- ruff: clean (no new test code added)
- Pipeline note: implementation (board.py _run_kanban) and failure-path tests
  (TestFromAC_BoardFailurePaths) were committed as part of #924 work before
  #920 advanced through the test-writer gate. All AC lines are already covered.
- AC coverage:
  AC#1 _run_kanban routes failures via _cli_error: test_missing_binary_exits_1, test_tasklist_nonzero_exit, test_movelog_nonzero_exit (error)
  AC#2 messages name kanban-md and distinguish stages/JSON: all 5 TestFromAC_BoardFailurePaths tests (error)
  AC#3 move-log failures abort; created fallback scoped correctly: test_movelog_* (abort), test_age_falls_back_to_created_* (allowed fallback) (error/boundary)
  AC#4 scope constraint: not directly testable
  AC#5 all 30 existing tests pass: confirmed

[[2026-03-23]] Mon 01:31

## Test-Writer Notes

- Test file: tests/test_cli_board.py
- Classes: TestFromAC_BoardFailurePaths (from #924), TestFromAC_AgeInStatus (fallback coverage)
- All 30 tests PASS - implementation + failure-path tests committed as part of #924 before #920 entered test-writer gate
- AC coverage: AC1 (missing-binary/nonzero/JSON routing via _cli_error): test_missing_binary_exits_1, test_tasklist_nonzero_exit, test_movelog_nonzero_exit; AC2 (kanban-md named, stages distinguished, JSON vs command): all 5 TestFromAC_BoardFailurePaths; AC3 (abort on log failure, allowed created fallback): test_movelog_*+ test_age_falls_back_to_created_*; AC4: not testable; AC5: 30/30 pass confirmed
- ruff: clean (no new test code written)

[[2026-03-23]] Mon 02:46

## Builder Notes

- Files changed: tests/test_cli_board.py (minor whitespace reformat only)
- Implementation in src/bearclaw/commands/board.py already committed in #924 (34d5bb7)
- Tests: 30 passed (TestFromAC_BoardFailurePaths x5, TestFromAC_BoardRendering x10, TestFromAC_AgeInStatus x4, TestFromAC_AssigneeDisplay x3, TestFromAC_EmptyBoard x3, TestFromAC_BoardRegistration x2, TestBuilderDiscovered x3)
- Lint: ruff clean on board.py + test_cli_board.py
- Evidence: 30 passed in 2.56s; ruff: All checks passed!
- Fixes applied: None (implementation complete from #924)

[[2026-03-23]] Mon 04:09

## Review Evidence

## Review: #920 — Harden bearclaw board command failures and JSON parsing

### Test Results

- pytest: 30 passed, 0 failed
- Command: `uv run pytest tests/test_cli_board.py -q --tb=short`
- Evidence: 30 passed in 2.89s (2 non-blocking optional-dependency warnings from tests/conftest.py)

### Lint Results

- ruff: clean
- Command: `uv run ruff check src/bearclaw/commands/board.py tests/test_cli_board.py`
- Evidence: All checks passed

### Coverage

- Command: `uv run pytest tests/test_cli_board.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- `src/bearclaw/commands/board.py`: 99% (missed line 66)

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage (TestFromAC present)

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|-----------------------------|---------|
| AC1: task-local helper around `subprocess.run(..., check=False, capture_output=True, text=True)` and route missing binary/non-zero/invalid JSON via `_cli_error` | `TestFromAC_BoardFailurePaths::{test_missing_binary_exits_1_with_error_referencing_kanban_md,test_tasklist_nonzero_exit_exits_1_with_stage_specific_command_error,test_movelog_nonzero_exit_exits_1_with_stage_specific_command_error,test_tasklist_invalid_json_exits_1_with_json_parse_error,test_movelog_invalid_json_exits_1_with_json_parse_error}` | Yes — assertions require `exit_code == 1`, `Error:` prefix, `kanban-md` mention, and parse-vs-command classification | COVERED |
| AC2: errors mention `kanban-md`, distinguish task-list vs move-log, parse failures reported as parse failures | Same 5 failure-path tests above | Yes — command-failure tests assert no `json`; parse tests assert `json`; stage-specific token asserted (`task` vs `log`) | COVERED |
| AC3: move-log load/parse failure aborts via `_cli_error`; created fallback only when move log loaded and no matching move | `test_movelog_nonzero_exit_exits_1_with_stage_specific_command_error`, `test_movelog_invalid_json_exits_1_with_json_parse_error`, `TestFromAC_AgeInStatus::{test_age_falls_back_to_created_when_no_matching_move,test_age_ignores_moves_to_different_status}` | Yes — move-log failures require exit 1 with error output; fallback tests verify created fallback only in no-match scenarios | COVERED |
| AC4: scope constrained to board command + board tests, no new dependencies | N/A (scope constraint) | N/A | COVERED (verified by commit file list and unchanged dependency files) |
| AC5: #909 happy-path tests remain green and #924 failure-path tests pass | Entire module run: `tests/test_cli_board.py` (30 tests) including `TestFromAC_BoardRendering` and `TestFromAC_BoardFailurePaths` | Yes — module would fail if either happy-path or failure-path contracts regressed | COVERED |

#### Security Review

- No hardcoded secrets detected in reviewed files.
- No command injection: `subprocess.run` is invoked with fixed argument lists and `shell=True` is not used (`src/bearclaw/commands/board.py:44`).
- No unsafe deserialization: JSON parsing uses `json.loads` with explicit `JSONDecodeError` handling and `_cli_error` routing (`src/bearclaw/commands/board.py:52-54`).
- No path traversal exposure: executable/config paths are fixed constants (`kanban/kanban-md.exe`, `kanban/config.yml`) in this module.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_BoardFailurePaths::*` | No assertion or method changes detected vs test-writer baseline; diff shows additions only in `TestBuilderDiscovered` area | PRESERVED |
| `TestFromAC_AgeInStatus::*` | No assertion or method changes detected | PRESERVED |
| `TestFromAC_BoardRendering::*` | No assertion or method changes detected | PRESERVED |
| `TestFromAC_AssigneeDisplay::*` | No assertion or method changes detected | PRESERVED |
| `TestFromAC_EmptyBoard::*` | No assertion or method changes detected | PRESERVED |
| `TestFromAC_BoardRegistration::*` | No assertion or method changes detected | PRESERVED |

Evidence: `git diff --unified=0 fe4a290 -- tests/test_cli_board.py` shows additions for `TestBuilderDiscovered` and no TestFromAC weakening/removal; #920 commit (`5da1f50`) changes only formatting in a builder-discovered method signature.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Failure-path tests assert exit code, error prefix, tool name, stage token, and parse/non-parse classification (`tests/test_cli_board.py:481-534`) |
| Negative/error paths | STRONG | Missing binary + non-zero list/log + invalid JSON list/log all covered (`tests/test_cli_board.py:473-534`) |
| Mutation reasoning | STRONG | Swapping command-failure/parse messages or stage labels would fail assertions (`tests/test_cli_board.py:496-510,520-534`) |
| Test independence | STRONG | Each test patches `bearclaw.commands.board.subprocess.run` and uses isolated fixtures/helpers |
| Descriptive names | STRONG | Test names describe scenario and expected behavior across AC and failure classes |

#### Data Safety

- No data safety issues found in reviewed scope.
- Command is read-only display logic; no multi-step persistence, no transactional integrity risk, no shared mutable concurrency path.

#### Implementation-Aware Test Gaps

- No significant untested behavioral path found for this task scope.
- Critical branches are exercised: missing binary, non-zero exits, JSON parse failures, no-task short-circuit, move-log fallback semantics, and subprocess call-count behavior.

### Pass 2 — INFORMATIONAL

- No informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `_run_kanban` helper and subprocess seam (`src/bearclaw/commands/board.py:32,44`); `_cli_error` routing for missing binary/non-zero/invalid JSON (`src/bearclaw/commands/board.py:46,49,54`) | `TestFromAC_BoardFailurePaths::{test_missing_binary_exits_1_with_error_referencing_kanban_md,test_tasklist_nonzero_exit_exits_1_with_stage_specific_command_error,test_movelog_nonzero_exit_exits_1_with_stage_specific_command_error,test_tasklist_invalid_json_exits_1_with_json_parse_error,test_movelog_invalid_json_exits_1_with_json_parse_error}` | PASS |
| AC2 | Stage-specific command and parse messages in implementation (`src/bearclaw/commands/board.py:49,54`) and stage/JSON assertions (`tests/test_cli_board.py:496,509,520,534`) | Same five `TestFromAC_BoardFailurePaths` tests | PASS |
| AC3 | Move-log loaded through `_run_kanban(move-log, ...)` before rendering (`src/bearclaw/commands/board.py:104`); fallback only when `matching` absent (`src/bearclaw/commands/board.py:85-89`) | `test_movelog_nonzero_exit_exits_1_with_stage_specific_command_error`, `test_movelog_invalid_json_exits_1_with_json_parse_error`, `test_age_falls_back_to_created_when_no_matching_move`, `test_age_ignores_moves_to_different_status` | PASS |
| AC4 | Scope verification from commit metadata: #920 touches only `tests/test_cli_board.py`; no dependency/config file changes (`git show --name-only 5da1f50`) | N/A (scope/dependency constraint) | PASS |
| AC5 | Scoped run passes all board tests (`30 passed`) including happy-path and failure-path classes; command output confirms full module green | `TestFromAC_BoardRendering` + `TestFromAC_BoardFailurePaths` (plus remaining module tests) | PASS |

### Verdict: PASS

- Confidence: .95

### Action Taken

- Appended review evidence to task body with reviewer claim retained.
- Advanced task to docs with claim release in follow-up command.

[[2026-03-23]] Mon 04:51

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | No behavior/API/convention change - hardened error handling in existing board command internals only |
| 2 | Docstrings complete | Yes | Pass | All public functions in board.py have docstrings: _read_status_order,_run_kanban,_assignee_display,_destination_status,_age_in_status, board |
| 3 | docs/sources/overview.md | Yes | Pass | Already updated in research phase with BearClaw Board Failure-Handling Gate (Task #920) section |
| 4 | README.md | No | N/A | No new CLI commands; bearclaw board already documented at README.md line 51 |
| 5 | Research doc linked | Yes | Pass | docs/research/bearclaw-board-command-failure-handling.md exists, references task #920, follow-up task #924 created |
| 6 | No impact (catch-all) | No | N/A | Items 2, 3, 5 apply |

### Files Updated

- None (docstrings already complete; sources.md updated in research phase)

### Scratch Files Cleaned

- docs/scratch/920-architect.md
- docs/scratch/920-cov.tmp
- docs/scratch/920-test-writer.tmp

[[2026-03-23]] Mon 04:51

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | No behavior change - hardened error handling in existing board cmd internals only |
| 2 | Docstrings | Yes | Pass | All public fns in board.py have docstrings: _read_status_order,_run_kanban,_assignee_display,_destination_status,_age_in_status, board |
| 3 | docs/sources/overview.md | Yes | Pass | Already updated in research phase - BearClaw Board Failure-Handling Gate (Task #920) section present |
| 4 | README.md | No | N/A | No new CLI commands; bearclaw board already documented at README.md L51 |
| 5 | Research doc linked | Yes | Pass | docs/research/bearclaw-board-command-failure-handling.md exists, references task #920, follow-up #924 created |
| 6 | No impact (catch-all) | No | N/A | Items 2/3/5 apply |

### Files Updated

- None (docstrings complete; sources.md updated in research phase)

### Scratch Files Cleaned

- docs/scratch/920-architect.md
- docs/scratch/920-cov.tmp
- docs/scratch/920-test-writer.tmp

[[2026-03-23]] Mon 05:46

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 831ec58 | chore | kanban/tasks/920-*.md | #920 |
