---
id: 926
title: Create reusable subprocess result helpers for BearClaw CLI tests
status: archived
priority: nice-to-have
created: 2026-03-21T17:54:00.8115772+01:00
updated: 2026-03-23T15:44:13.1208893+01:00
started: 2026-03-23T15:43:08.8918885+01:00
completed: 2026-03-23T15:43:08.8918885+01:00
tags:
    - cli
    - test
    - tooling
    - phase-14
    - type:test
    - scope:cli
depends_on:
    - 920
    - 924
class: standard
---

Research follow-up from docs/research/bearclaw-board-command-failure-tests-red-gate.md and docs/research/bearclaw-cli-subprocess-result-helper.md.

Optional RED cleanup after #920 and #924 land.

AC:

1. In tests/test_conftest_helpers.py, add failing contract tests for an importable shared subprocess-result helper in tests/conftest.py that returns real text-mode subprocess.CompletedProcess values and covers success, non-zero exit, malformed stdout, and malformed stderr payloads.
2. In tests/test_cli_chat.py, replace at least one duplicated local CompletedProcess mock setup with helper-based usage so the shared helper becomes the executable contract for an existing BearClaw CLI subprocess test.
3. In tests/test_cli_board.py, keep subprocess argument routing local to the file but update the failure-path routers to compose the shared helper instead of hand-built result mocks, without changing the current CLI assertions.
4. Missing-binary coverage stays explicit through a named FileNotFoundError or OSError seam under tests/; do not introduce any src/ abstraction for spawn failures.
5. Scope stays under tests/ only, adds no new dependency, and leaves src/ unchanged.
6. All newly added assertions fail before the follow-on helper-implementation task that reuses them.

[[2026-03-21]] Sat 23:37

## Research

Doc: docs/research/bearclaw-cli-subprocess-result-helper.md

Summary:

- tests/conftest.py is the established home for shared test helpers.
- tests/test_conftest_helpers.py is the contract and duplicate-guard file for shared helper extraction.
- tests/test_cli_chat.py already shows duplicated CompletedProcess mock setup worth extracting.
- tests/test_cli_board.py should keep its command-routing helpers local even if result construction becomes shared.

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

- AC 1: The original helper requirement was directionally right but ambiguous on contract location and result shape. Rewritten to require contract coverage in tests/test_conftest_helpers.py for a real text-mode subprocess.CompletedProcess helper in tests/conftest.py.
- AC 2: The spawn-failure seam was acceptable but vague about exception type and scope. Tightened to a named FileNotFoundError or OSError seam under tests/ only, with no src/ abstraction.
- AC 3: At least one existing test and board failure-path tests were too loose to verify mechanically. Rewritten to make tests/test_cli_chat.py and tests/test_cli_board.py explicit and to keep board routers local while composing the shared helper.
- AC 4: The tests-only boundary was sound but needed a RED gate. Preserved the tests-only scope and added an explicit requirement that new assertions fail before the follow-on implementation.

### Architecture Notes

- tests/conftest.py already hosts shared extracted helpers, and tests/test_conftest_helpers.py is the established contract plus duplicate-guard location.
- tests/test_cli_chat.py currently repeats MagicMock(spec=subprocess.CompletedProcess) setup around bearclaw.commands.chat._detect_github_remote, so it is the clearest existing reuse target.
- tests/test_cli_board.py needs command-specific subprocess routing for list vs log responses, so only result construction should become shared; routing must stay local to that file.
- src/bearclaw/commands/chat.py and src/bearclaw/commands/board.py both consume subprocess.run(..., capture_output=True, text=True, check=False) through returncode, stdout, and stderr, so a real text-mode CompletedProcess matches the current production contract without adding a production seam.
- Single-domain check passed: this card stays inside CLI test support under tests/ only.

### Changes Made

- Rewrote the body into numbered, mechanically verifiable RED acceptance criteria.
- Added depends_on: #920 and #924.
- Advanced the task from backlog to todo.

### Dependencies

- Added: #920 and #924.
- Verified patterns: tests/conftest.py, tests/test_conftest_helpers.py, tests/test_cli_chat.py, tests/test_cli_board.py, src/bearclaw/commands/chat.py, and src/bearclaw/commands/board.py.
- Observed duplicate follow-up cards: #927 and #928 carry the same scope but were not modified because this review was scoped to #926 only.

[[2026-03-23]] Mon 06:23

## Test-Writer Notes

- Test files: tests/test_conftest_helpers.py, tests/test_cli_chat.py, tests/test_cli_board.py
- Classes: TestFromAC_MakeCompletedProcess (new in test_conftest_helpers.py); modified TestDetectGitHubRemote (test_cli_chat.py); modified_subproc_fail_list/_subproc_fail_log helpers (test_cli_board.py)
- Tests per category: happy 6, edge 4, error 4, boundary 8
- Total: 22 tests, all FAIL ✓ (14 ImportError in test_conftest_helpers, 4 ImportError in test_cli_chat, 4 ImportError in test_cli_board)
- ruff: clean
- AC coverage:
  AC1 — TestFromAC_MakeCompletedProcess (14 tests): importable, real CompletedProcess, default returncode=0, nonzero roundtrip, text-mode stdout/stderr, default empty string, custom payload roundtrip, malformed stdout/stderr, JSON success payload, signature check
  AC2 — TestDetectGitHubRemote (4 tests): all 4 duplicated MagicMock setups replaced with make_completed_process; fail ImportError
  AC3 — TestFromAC_BoardFailurePaths (4 tests): _subproc_fail_list/_subproc_fail_log now compose make_completed_process; fail ImportError
  AC4 — test_missing_binary_exits_1_with_error_referencing_kanban_md stays explicit FileNotFoundError seam (passes — existing coverage, no src abstraction)
  AC5 — no src/ files touched; import subprocess removed from test_cli_chat.py (was only used for spec=CompletedProcess); no new deps
  AC6 — all 22 tests fail before builder adds make_completed_process to conftest.py ✓

[[2026-03-23]] Mon 08:55

## Builder Notes

- Files changed: tests/conftest.py (+16 lines)
- Tests: 23 passed (22 TestFromAC + 1 pre-existing), 0 failed
- Lint: ruff clean (tests/conftest.py)
- Evidence: uv run pytest tests/test_conftest_helpers.py::TestFromAC_MakeCompletedProcess tests/test_cli_chat.py::TestDetectGitHubRemote tests/test_cli_board.py::TestFromAC_BoardFailurePaths -q --no-cov -> 23 passed, 4 warnings in 1.88s
- Commit: 5d23467
- Fixes applied: Added import subprocess + make_completed_process(*, returncode=0, stdout='', stderr='') -> subprocess.CompletedProcess[str] to tests/conftest.py

[[2026-03-23]] Mon 12:07

## Review Evidence

### Review: #926 - Create reusable subprocess result helpers for BearClaw CLI tests

### Test Results

- `uv run pytest tests/test_conftest_helpers.py::TestFromAC_MakeCompletedProcess tests/test_cli_chat.py::TestDetectGitHubRemote tests/test_cli_board.py::TestFromAC_BoardFailurePaths -q --tb=short` -> 23 passed, 0 failed (4 optional-dependency warnings from `tests/conftest.py`).
- `uv run pytest tests/test_cli_board.py::TestFromAC_BoardFailurePaths::test_missing_binary_exits_1_with_error_referencing_kanban_md -q --tb=short` -> 1 passed, 0 failed (2 optional-dependency warnings).
- Wider scope sanity run: `uv run pytest tests/test_conftest_helpers.py tests/test_cli_chat.py tests/test_cli_board.py -q --tb=short` -> 90 passed, 0 failed (4 optional-dependency warnings).

### Lint Results

- `uv run ruff check src/ tests/` -> FAIL with 232 pre-existing `RUF100` findings (repo baseline, mostly unused `noqa: N801` directives outside #926 scope).
- `uv run ruff check tests/conftest.py tests/test_conftest_helpers.py tests/test_cli_chat.py tests/test_cli_board.py` -> All checks passed.

### Coverage

- `uv run pytest tests/test_conftest_helpers.py::TestFromAC_MakeCompletedProcess tests/test_cli_chat.py::TestDetectGitHubRemote tests/test_cli_board.py::TestFromAC_BoardFailurePaths --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` -> 23 passed.
- Coverage report uses project-wide `source = src/...`; #926 modifies tests-only files, so per-file coverage gating on touched code is not directly measurable via pytest-cov in this repo configuration.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: contract tests for importable shared helper returning real text-mode `CompletedProcess` incl. success/non-zero/malformed payloads | `TestFromAC_MakeCompletedProcess` (14 tests in `tests/test_conftest_helpers.py`) | Yes - importability, type checks, exact round-trip assertions, malformed payload preservation all fail if helper contract is broken | COVERED |
| AC2: replace duplicated local setup in chat tests with shared helper usage | `TestDetectGitHubRemote::{test_ssh_remote_parsed,test_https_remote_parsed,test_git_failure_returns_none,test_invalid_remote_returns_none}` in `tests/test_cli_chat.py` | Yes - tests import/use `make_completed_process`; helper removal or incompatible return shape breaks patched subprocess path and assertions | COVERED |
| AC3: keep board subprocess routing local but compose shared helper in failure routers | `_subproc_fail_list`, `_subproc_fail_log` + `TestFromAC_BoardFailurePaths` in `tests/test_cli_board.py` | Yes - routers remain local functions and now return helper-built `CompletedProcess`; wrong composition or routing breaks stage-specific assertions | COVERED |
| AC4: missing-binary coverage explicit via FileNotFoundError/OSError seam under tests, no src abstraction | `TestFromAC_BoardFailurePaths::test_missing_binary_exits_1_with_error_referencing_kanban_md` | Yes - explicit `FileNotFoundError` side effect is asserted through CLI error output contract | COVERED |
| AC5: scope only under `tests/`, no new dependency, `src/` unchanged | Commit diffs `8c26993` and `5d23467` | Yes - changed files are `tests/test_conftest_helpers.py`, `tests/test_cli_chat.py`, `tests/test_cli_board.py`, `tests/conftest.py` only; no dependency-manifest edits | COVERED |
| AC6: newly added assertions fail pre-helper implementation | Pre-builder state (`git show 5d23467^:tests/conftest.py`) + RED tests import helper from conftest | Yes - pre-builder `tests/conftest.py` had no `make_completed_process`; RED tests import it directly, so they fail until builder adds helper | COVERED |

#### Security Review

- No security issues found. Changes are tests-only helper construction and test-side subprocess mock composition; no credential handling, dynamic code execution, or command-construction changes in `src/`.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_MakeCompletedProcess::*` | No changes in builder commit (`git diff 5d23467^..5d23467 -- tests/test_conftest_helpers.py` empty) | PRESERVED |
| `TestFromAC_BoardFailurePaths::*` | No changes in builder commit (`git diff 5d23467^..5d23467 -- tests/test_cli_board.py` empty) | PRESERVED |
| `TestDetectGitHubRemote::*` AC-linked subprocess tests | No changes in builder commit (`git diff 5d23467^..5d23467 -- tests/test_cli_chat.py` empty) | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact equality/type assertions on `returncode/stdout/stderr`, explicit output-content checks for board failure stages |
| Negative/error paths | STRONG | Non-zero exits, invalid JSON payloads, invalid remote parsing, missing binary seam all covered |
| Mutation reasoning | STRONG | Altering helper defaults/types or removing helper-based composition breaks multiple AC tests immediately |
| Test independence | STRONG | Each test constructs its own helper result / patch context with no shared mutable fixture coupling |
| Descriptive names | STRONG | Method names encode scenario and expected outcome (e.g., `test_movelog_invalid_json_exits_1_with_json_parse_error`) |

#### Data Safety

- No data safety issues found. No persistence or shared-state mutation was introduced by #926.

#### Implementation-Aware Test Gaps

- No significant untested paths introduced by the builder implementation. `make_completed_process` is a single constructor wrapper; tests cover defaults, non-defaults, malformed payload passthrough, and signature shape.

### Pass 2 - INFORMATIONAL

- Repo-wide ruff debt (`RUF100`) remains and is unrelated to #926; scoped files are lint-clean.
- Foreground terminal intermittently showed `KeyboardInterrupt` artifacts; isolated/background reruns produced stable passing results and were used as source evidence.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. Add failing contract tests in `tests/test_conftest_helpers.py` for shared helper behavior | `TestFromAC_MakeCompletedProcess` at `tests/test_conftest_helpers.py` (class begins line 188), all assertions pass after helper added | `TestFromAC_MakeCompletedProcess::*` | PASS |
| 2. Replace at least one duplicated local setup in `tests/test_cli_chat.py` with helper usage | `tests/test_cli_chat.py` lines 305/318/333/346 import helper; lines 309/322/337/350 construct results via helper | `TestDetectGitHubRemote::*` | PASS |
| 3. Keep board routing local while composing shared helper | Local routers remain in `tests/test_cli_board.py` lines 401 and 419; helper composed inside both routers (lines 413/414/434/435) | `TestFromAC_BoardFailurePaths::*` | PASS |
| 4. Keep missing-binary seam explicit under tests (FileNotFoundError/OSError), no src abstraction | `tests/test_cli_board.py` line 465 test + line 469 `FileNotFoundError` side effect; targeted pytest run passed | `test_missing_binary_exits_1_with_error_referencing_kanban_md` | PASS |
| 5. Tests-only scope, no new dependency, src unchanged | `git show --stat 8c26993` + `git show --stat 5d23467` (changed files under `tests/` only); dependency-manifest unchanged | N/A | PASS |
| 6. New assertions fail before follow-on helper implementation | `git show 5d23467^:tests/conftest.py` contains no helper; RED tests already import `make_completed_process` from conftest in commit `8c26993` | `TestFromAC_MakeCompletedProcess::*`, AC-linked chat/board tests | PASS |

### Verdict: PASS

- Confidence: .93

### Action Taken

- `kanban\kanban-md.exe edit 926 --status docs --release`

[[2026-03-23]] Mon 13:01

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Tests-only helper addition; no behavior, API, or convention change |
| 2 | Docstrings complete | Yes | Pass | make_completed_process has docstring at tests/conftest.py:132; src/ unchanged (AC5 confirmed) |
| 3 | docs/sources/overview.md | No | N/A | No external patterns or attribution required |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/bearclaw-cli-subprocess-result-helper.md exists; linked in task body Research section; this task IS the follow-up |
| 6 | No impact (fallback) | No | N/A | Items 2 and 5 applied |

### Files Updated

- None

### Scratch Files Cleaned

- docs/scratch/926-architect.tmp
- docs/scratch/926-cov.txt
- docs/scratch/926-list.tmp

[[2026-03-23]] Mon 13:01

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Tests-only helper addition; no behavior, API, or convention change |
| 2 | Docstrings complete | Yes | Pass | make_completed_process has docstring at tests/conftest.py:132; src/ unchanged (AC5 confirmed) |
| 3 | docs/sources/overview.md | No | N/A | No external patterns or attribution required |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/bearclaw-cli-subprocess-result-helper.md exists; linked in task body Research section; this task IS the follow-up |

### Files Updated

- None

### Scratch Files Cleaned

- docs/scratch/926-architect.tmp
- docs/scratch/926-cov.txt
- docs/scratch/926-list.tmp

[[2026-03-23]] Mon 13:02

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Tests-only helper addition; no behavior, API, or convention change |
| 2 | Docstrings complete | Yes | Pass | make_completed_process has docstring at tests/conftest.py:132; src/ unchanged (AC5 confirmed) |
| 3 | docs/sources/overview.md | No | N/A | No external patterns or attribution required |
| 4 | README.md | No | N/A | No CLI commands added or changed |
| 5 | Research doc linked | Yes | Pass | docs/research/bearclaw-cli-subprocess-result-helper.md exists; linked in task body Research section; this task IS the follow-up |

### Files Updated

- None

### Scratch Files Cleaned

- docs/scratch/926-architect.tmp
- docs/scratch/926-cov.txt
- docs/scratch/926-list.tmp

[[2026-03-23]] Mon 15:43

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: Contract tests in test_conftest_helpers.py | TestFromAC_MakeCompletedProcess (14 tests), all pass | PASS |
| AC2: Replace duplicated setup in test_cli_chat.py | 4 TestDetectGitHubRemote tests use make_completed_process | PASS |
| AC3: Board routing local, compose shared helper | _subproc_fail_list/_subproc_fail_log local, compose helper | PASS |
| AC4: Missing-binary via FileNotFoundError seam | test present, no src/ abstraction | PASS |
| AC5: Scope tests/ only, src/ unchanged | Commits 8c26993 + 5d23467 touch only tests/ | PASS |
| AC6: Assertions fail before implementation | RED commit imports before helper exists | PASS |

### Test Results

- Scoped: 90 passed, 0 failed
- Full suite: 3921 passed, 92 failed (all pre-existing, none in #926 files)
- ruff: clean

### Architect Quality: 4/5

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 15:44

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4f66f15 | chore | kanban/tasks/926-*.md | #926 |
