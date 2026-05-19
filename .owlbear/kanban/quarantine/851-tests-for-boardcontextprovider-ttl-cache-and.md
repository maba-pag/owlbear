---
id: 851
title: Tests for BoardContextProvider TTL cache and graceful degradation (TDD RED)
status: archived
priority: important
created: 2026-03-18T12:56:33.4884502+01:00
updated: 2026-03-20T11:18:11.2709749+01:00
started: 2026-03-20T11:18:01.6864645+01:00
completed: 2026-03-20T11:18:01.6864645+01:00
tags:
    - agent
    - knowledge
    - scope:core
    - type:test
class: standard
---

Goal: Write failing tests for BoardContextProvider before implementation in #770. AC: test file tests/test_board_context.py; default get_context() runs kanban/kanban-md.exe list --compact --status in-progress --status review --status todo --no-color --dir kanban; success returns decoded stdout; second call within 60s TTL uses cache; expired TTL reruns subprocess; invalidate() forces refresh; constructor accepts kanban_cmd, ttl_seconds, timer; OSError returns empty string and logs WARNING; non-zero exit returns empty string and logs WARNING with return code; tests mock asyncio.create_subprocess_exec; all tests RED against current src/owlbear/core/board_context.py stub. Pattern refs: src/owlbear/core/context_hook.py::_run_kanban; src/owlbear/tools/kanban.py::_run_kanban; docs/research/board-context-provider.md.

[[2026-03-19]] Thu 14:32

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Add tests/test_board_context.py covering the current stub | Precise single-file RED scope | Kept |
| Constructor tests verify zero-arg construction plus injected kanban_cmd, ttl_seconds, timer | Matches existing consumer contract and testable inputs | Kept |
| Default command expectation is the full list command with --no-color and --dir kanban | Removes ambiguity about subprocess args | Kept |
| Success-path test patches owlbear.core.board_context.asyncio.create_subprocess_exec and asserts decoded stdout | Correct mocking boundary for the core module | Kept |
| Warm-cache test proves second call within 60s TTL avoids a second subprocess | Verifiable cache-hit behavior | Kept |
| Expired-cache test advances timer beyond ttl_seconds and asserts refresh | Verifiable cache-expiry behavior without sleep | Kept |
| invalidate() test forces refresh before TTL expiry | Verifiable manual invalidation behavior | Kept |
| OSError path returns empty string and logs WARNING without propagating | Covers graceful degradation on spawn failure | Kept |
| Non-zero exit path returns empty string and logs WARNING with return code | Covers graceful degradation on subprocess failure | Kept |
| Tests use async doubles and avoid real subprocess/sleep calls | Keeps the task unit-scoped and deterministic | Kept |
| All tests fail against the current stub implementation | Makes RED-phase completion mechanically checkable | Kept |

### Architecture Notes

- Existing consumer contract is already live: src/owlbear/core/agent.py awaits provider.get_context(), and src/owlbear/bootstrap/**init**.py constructs BoardContextProvider() with zero arguments.
- The implementation pattern should stay aligned with src/owlbear/core/context_hook.py::_run_kanban for warning-plus-empty-string degradation and with src/owlbear/tools/kanban.py::_run_kanban for the command shape.
- Single domain verified: this is a core-unit-test task only. It does not expand into bootstrap, config, or agent rewiring.
- TDD sequencing verified: implementation task #770 already depends on #851.

### Changes Made

- Rewrote #851 into explicit Goal, Scope, AC, and Pattern References sections.
- Verified the consumer contract in src/owlbear/core/agent.py and src/owlbear/bootstrap/**init**.py.
- Verified #770 is the paired implementation task and already depends on #851.

### Dependencies

- Verified: #770 depends on #851.
- Verified: archived task #771 already established the zero-arg async provider contract.

[[2026-03-19]] Thu 15:08

## Test-Writer Notes

- Test file: tests/test_board_context.py
- Classes: TestFromAC_Constructor, TestFromAC_GetContextHappyPath, TestFromAC_TTLCache, TestFromAC_GracefulDegradation
- Tests per category: happy 2, edge 3, error 4, boundary 1, constructor 5
- Total: 15 tests, all FAIL (AttributeError/TypeError — stub has no **init** params, no asyncio import, no invalidate())
- ruff: clean
- Patch path: owlbear.core.board_context.asyncio.create_subprocess_exec (builder must add import asyncio to stub)
- AC coverage:
  - default command args -> test_runs_default_command_via_create_subprocess_exec
  - success returns decoded stdout -> test_returns_decoded_stdout
  - second call within TTL uses cache -> test_second_call_within_ttl_skips_subprocess
  - expired TTL reruns subprocess -> test_expired_ttl_reruns_subprocess
  - invalidate() forces refresh -> test_invalidate_forces_refresh_before_ttl, test_invalidate_before_any_call_does_not_raise
  - constructor kanban_cmd/ttl_seconds/timer -> test_custom_*, test_default_*
  - OSError -> test_os_error_returns_empty_string, test_os_error_logs_warning
  - non-zero exit -> test_nonzero_exit_returns_empty_string, test_nonzero_exit_logs_warning_with_return_code

[[2026-03-19]] Thu 16:09

## Builder Notes

- Files changed: src/owlbear/core/board_context.py
- Tests: 15 passed, coverage 100% on board_context.py
- Lint: ruff clean (check + format)
- Evidence: 15 passed in 0.22s; board_context.py 36/36 stmts covered
- Fixes applied: moved Callable import into TYPE_CHECKING block (TC003)

[[2026-03-19]] Thu 16:54

## Review Evidence

### Test Results

- `uv run pytest tests/test_board_context.py -q --tb=short` -> 15 passed, 2 warnings.
- `uv run ruff check src/owlbear/core/board_context.py tests/test_board_context.py` -> All checks passed.
- `uv run pytest tests/test_board_context.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` -> `src/owlbear/core/board_context.py` 36/36 (100%).

### Pass 1 - CRITICAL

- Security: no hardcoded secrets, no eval/exec, and subprocess uses `create_subprocess_exec` arg list (no shell) in `src/owlbear/core/board_context.py`.
- Test integrity: all 15 `TestFromAC_*` tests are present in `tests/test_board_context.py`; builder commit `0eb597d` modified only `src/owlbear/core/board_context.py`.
- Test quality ratings: assertion specificity `ADEQUATE`; negative/error paths `STRONG`; mutation resistance `ADEQUATE`; independence `STRONG`; naming `STRONG`.
- Data safety: no data-integrity risks found in AC scope.

### AC Compliance

- Default command args (`--status in-progress/review/todo --no-color --dir kanban`) implemented in `src/owlbear/core/board_context.py` and asserted by `test_runs_default_command_via_create_subprocess_exec`.
- Decoded stdout validated by `test_returns_decoded_stdout`.
- TTL cache hit/expiry validated by `test_second_call_within_ttl_skips_subprocess` and `test_expired_ttl_reruns_subprocess`.
- `invalidate()` refresh validated by `test_invalidate_forces_refresh_before_ttl`.
- Constructor injection validated by custom constructor tests.
- OSError/non-zero graceful degradation validated by dedicated error-path tests.
- Historical RED evidence captured in test-writer note: 15 tests failed against stub before implementation.

### Verdict

PASS (confidence .93)

[[2026-03-19]] Thu 16:54

## Review Evidence

### Test Results

- `uv run pytest tests/test_board_context.py -q --tb=short` -> 15 passed, 2 warnings.
- `uv run ruff check src/owlbear/core/board_context.py tests/test_board_context.py` -> All checks passed.
- `uv run pytest tests/test_board_context.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` -> `src/owlbear/core/board_context.py` 36/36 (100%).

### Pass 1 - CRITICAL

- Security: no hardcoded secrets, no eval/exec, and subprocess uses `create_subprocess_exec` arg list (no shell) in `src/owlbear/core/board_context.py`.
- Test integrity: all 15 `TestFromAC_*` tests are present in `tests/test_board_context.py`; builder commit `0eb597d` modified only `src/owlbear/core/board_context.py`.
- Test quality ratings: assertion specificity `ADEQUATE`; negative/error paths `STRONG`; mutation resistance `ADEQUATE`; independence `STRONG`; naming `STRONG`.
- Data safety: no data-integrity risks found in AC scope.

### AC Compliance

- Default command args (`--status in-progress/review/todo --no-color --dir kanban`) implemented in `src/owlbear/core/board_context.py` and asserted by `test_runs_default_command_via_create_subprocess_exec`.
- Decoded stdout validated by `test_returns_decoded_stdout`.
- TTL cache hit/expiry validated by `test_second_call_within_ttl_skips_subprocess` and `test_expired_ttl_reruns_subprocess`.
- `invalidate()` refresh validated by `test_invalidate_forces_refresh_before_ttl`.
- Constructor injection validated by custom constructor tests.
- OSError/non-zero graceful degradation validated by dedicated error-path tests.
- Historical RED evidence captured in test-writer note: 15 tests failed against stub before implementation.

### Verdict

PASS (confidence .93)

[[2026-03-19]] Thu 17:27

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal core module; no conventions, API, or tech-stack entry changed |
| 2 | Docstrings | Yes | Pass | BoardContextProvider class, get_context(), invalidate() all have accurate docstrings in board_context.py |
| 3 | docs/sources/overview.md | No | N/A | Sources for board-context patterns already logged under Task #770 entry (lines 109-114); #851 adds only tests |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/board-context-provider.md exists; referenced in task body Pattern refs |

### Files Updated

- None

### Scratch Files Cleaned

- None (no docs/scratch/851-* files found)

[[2026-03-20]] Fri 11:17

## Audit\n### AC Verification\n| AC Line | Evidence | Status |\n|---------|----------|--------|\n| test file tests/test_board_context.py | File exists, 277 lines, 15 tests across 4 classes | PASS |\n| default get_context() runs full kanban list command |_DEFAULT_CMD in board_context.py L16-28 matches AC; test_runs_default_command_via_create_subprocess_exec verifies | PASS |\n| success returns decoded stdout |_run() returns stdout_bytes.decode(); test_returns_decoded_stdout verifies | PASS |\n| second call within 60s TTL uses cache | get_context() L68-73 checks timer delta; test_second_call_within_ttl_skips_subprocess verifies call_count==1 | PASS |\n| expired TTL reruns subprocess | get_context() timer check; test_expired_ttl_reruns_subprocess verifies call_count==2 | PASS |\n| invalidate() forces refresh | invalidate() sets _cached=None; test_invalidate_forces_refresh_before_ttl verifies | PASS |\n| constructor accepts kanban_cmd, ttl_seconds, timer | **init** L51-54; 5 constructor tests verify defaults and custom values | PASS |\n| OSError returns empty string and logs WARNING | _run() except OSError block L93-95; test_os_error_returns_empty_string + test_os_error_logs_warning verify | PASS |\n| non-zero exit returns empty string and logs WARNING with rc | _run() L97-102; test_nonzero_exit_returns_empty_string + test_nonzero_exit_logs_warning_with_return_code verify | PASS |\n| tests mock asyncio.create_subprocess_exec | All subprocess tests patch owlbear.core.board_context.asyncio.create_subprocess_exec | PASS |\n| all tests RED against stub | Test-writer notes confirm 15 tests failed (AttributeError/TypeError) against stub | PASS |\n\n### Test Results\n- pytest tests/test_board_context.py: 15 passed, 0 failed (0.12s)\n- pytest full suite (excl. unrelated broken test_security_audit_log.py): 3640 passed, 104 failed (all failures pre-existing/unrelated)\n- ruff check src/owlbear/core/board_context.py tests/test_board_context.py: All checks passed\n\n### Quality Gaps\n- test-writer did not commit tests/test_board_context.py; committed by auditor as orphaned deliverable\n\n### Commits\n| Commit | Type | Files | Tasks |\n|--------|------|-------|-------|\n| 0eb597d | feat | src/owlbear/core/board_context.py | #851 |\n| d8af9f4 | test | tests/test_board_context.py | #851 |\n\n### Confidence: .97\n### Action: archive
