---
id: 923
title: Create reusable kanban JSON fixture helpers for BearClaw CLI board tests
status: archived
priority: nice-to-have
created: 2026-03-21T16:56:29.2134882+01:00
updated: 2026-03-26T16:07:48.6881365+01:00
tags:
    - cli
    - test
    - tooling
    - phase-14
    - type:test
    - scope:cli
depends_on:
    - 909
blocked: true
block_reason: 'Split into #936, #939 - work tracked there'
class: standard
---

Research follow-up from docs/research/bearclaw-board-command-red-gate.md. AC: (1) add a test-only helper that builds paired kanban-md list/log JSON payloads for board-style CLI tests; (2) helper covers assignee fallback and latest-move age fixtures without live subprocesses; (3) tests stay readable and do not require the real kanban binary.

## Research

Doc: docs/research/bearclaw-board-kanban-json-fixtures.md

Summary:

- Board JSON fixture cleanup should stay board-specific; do not widen tests/conftest.py.
- Recommended shape: tests/cli_board_fixtures.py with board_task(), board_move(), and board_payloads(); keep subprocess routing local to tests/test_cli_board.py.
- Scope boundary: #923 should not absorb #926's generic CompletedProcess helper lane.

Follow-up tasks created:

- #936 Test board-specific kanban JSON payload helper for BearClaw board CLI tests (RED)
- #939 Implement board-specific kanban JSON payload helper for BearClaw board CLI tests

Commands executed:

- kanban\kanban-md.exe create --title "Test board-specific kanban JSON payload helper for BearClaw board CLI tests (RED)" ...
- kanban\kanban-md.exe create --title "Implement board-specific kanban JSON payload helper for BearClaw board CLI tests" ...

Attribution:

- Added pytest fixtures reference, pytest how-to fixtures, Python json docs, and Typer Testing docs to docs/sources/overview.md.

[[2026-03-22]] Sun 17:07

## Architecture Review

**Verdict:** Split

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. add a test-only helper that builds paired kanban-md list/log JSON payloads for board-style CLI tests | Mixed builder concern that belongs on the dedicated GREEN child. Current repo state still has only local `_task()`, `_move()`, and `_subproc()` helpers in `tests/test_cli_board.py`, and `tests/cli_board_fixtures.py` does not exist yet. | Execute through `#936 -> #939`; do not advance this parent directly. |
| 2. helper covers assignee fallback and latest-move age fixtures without live subprocesses | Verifiable behavior contract, but it belongs in the RED child because those behaviors are already exercised in `tests/test_cli_board.py` with patched `bearclaw.commands.board.subprocess.run` against the CLI boundary. | Keep the behavioral contract on `#936` and require `#939` to preserve the local subprocess seam. |
| 3. tests stay readable and do not require the real kanban binary | Scope/readability constraint, not a separate implementation slice. Research and local patterns both say board-only JSON builders should stay under `tests/` and must not widen `tests/conftest.py` or overlap `#926`'s generic subprocess-result helper lane. | Keep this on `#936` and `#939`; parent remains a backlog tracker only. |

### Architecture Notes

- `tests/test_cli_board.py` currently uses local `_task()`, `_move()`, and `_subproc()` helpers; the duplication seam is board-specific arrangement data, not runtime CLI code.
- `src/bearclaw/commands/board.py` already consumes paired `list --json` and `log --action move --json` payloads through a patched subprocess boundary, so this helper work should stay fully under `tests/` and not touch `src/`.
- `tests/test_conftest_helpers.py` shows `tests/conftest.py` is the repo-wide helper surface. The research recommendation to avoid widening that surface for a single board consumer is consistent with current patterns.
- TDD compliance requires the dedicated RED predecessor. That path already exists as `#936` before `#939`; approving `#923` directly would create a second ambiguous GREEN lane.
- Observed duplicate RED card `#935` mirrors `#936` but is not part of the research-noted execution path. Leaving it untouched here respects the single-task boundary.
- Downstream dependency note: `#936` and `#939` currently depend on `#910`, whose code seam already exists in `src/bearclaw/commands/board.py` even though the board status is still blocked in `todo`. Keep this parent in `backlog` until the split path is advanced cleanly.

### Changes Made

- Claimed task `#923` as `architect-923`.
- Reviewed `docs/research/bearclaw-board-kanban-json-fixtures.md`, `tests/test_cli_board.py`, `src/bearclaw/commands/board.py`, `tests/test_conftest_helpers.py`, and child tasks `#936` and `#939`.
- Appended this architecture review and kept the parent in `backlog`.
- No new kanban tasks created.

### Dependencies

- Verified: `#909` is archived, so the original board CLI test seam exists.
- Verified: the intended execution path is `#936` (RED) -> `#939` (GREEN).
- Verified: `tests/cli_board_fixtures.py` does not exist yet, so the split child tasks remain necessary.
- Verified: no new runtime dependency or production-code change is required; scope stays under `tests/`.

[[2026-03-22]] Sun 17:27

## Architecture Review

**Verdict:** SPLIT -> #936, #939

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. add a test-only helper that builds paired kanban-md list/log JSON payloads for board-style CLI tests | Valid board-test arrangement seam, but the executable contract now lives on the RED/GREEN split tasks. `tests/test_cli_board.py` still keeps `_task()`, `_move()`, and `_subproc()` local, and `tests/cli_board_fixtures.py` does not exist yet. | Keep execution on `#936` then `#939`; block direct execution of `#923`. |
| 2. helper covers assignee fallback and latest-move age fixtures without live subprocesses | Verifiable behavior, but it belongs on the RED test contract because those behaviors are already asserted at the `CliRunner` boundary with patched `bearclaw.commands.board.subprocess.run`. | Preserve on `#936`; require `#939` to keep subprocess routing local to `tests/test_cli_board.py`. |
| 3. tests stay readable and do not require the real kanban binary | Correct scope constraint, not a standalone implementation slice. Research and current test structure both show this should stay under `tests/` and avoid `tests/conftest.py`, `src/`, and `#926`'s generic subprocess-helper lane. | Preserve on `#936` and `#939`; do not dispatch a builder from `#923`. |

### Architecture Notes

- `tests/test_cli_board.py` is the active board CLI seam: local `_task()`, `_move()`, and `_subproc()` helpers feed patched `bearclaw.commands.board.subprocess.run` while assertions stay at the `CliRunner` boundary.
- `src/bearclaw/commands/board.py` already consumes paired `list --json` and `log --action move --json` payloads, so this helper cleanup is arrangement reuse under `tests/` only, not production CLI work.
- `tests/test_conftest_helpers.py` makes `tests/conftest.py` the repo-wide shared helper surface. The research recommendation to keep this board-specific helper out of `conftest.py` matches current repo practice.
- TDD compliance is satisfied only through the dedicated RED/GREEN path: `#936` defines the failing contract and `#939` implements it. Advancing `#923` directly would duplicate that path and bypass the test-first split.
- Board precedent for split umbrellas is `#905`: keep the parent in `backlog`, add a split review, and set a `block_reason` so it stops redispatching while child tasks carry the executable work.

### Changes Made

- Claimed `#923` as `architect-923`.
- Re-reviewed `docs/research/bearclaw-board-kanban-json-fixtures.md`, `tests/test_cli_board.py`, `tests/test_conftest_helpers.py`, `src/bearclaw/commands/board.py`, and related tasks `#935`, `#936`, `#939`, `#905`, `#909`, and `#910`.
- Appended this architecture review and blocked direct execution of `#923` because work is tracked on the split child tasks.
- No new kanban tasks created.

### Dependencies

- Verified: `#909` remains the upstream board-command RED prerequisite for this board-test helper line.
- Verified: `#936` (RED) and `#939` (GREEN) already exist as the intended execution path.
- Verified: `tests/cli_board_fixtures.py` does not exist yet, so the child tasks are still necessary.
- Verified: no production-code dependency or new runtime boundary is required; scope stays under `tests/`.

[[2026-03-26]] Thu 16:07

## Architecture Review

**Verdict:** Approve (completed umbrella tracker)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. Add a test-only helper that builds paired kanban-md list/log JSON payloads for board-style CLI tests | SATISFIED. tests/cli_board_fixtures.py exports board_task(), board_move(), and board_payloads(). tests/test_cli_board.py imports and uses board_task and board_move across 20+ call sites. | No further work needed. |
| 2. Helper covers assignee fallback and latest-move age fixtures without live subprocesses | SATISFIED. board_task() accepts assignee and claimed_by kwargs; board_move() accepts timestamp for age fixtures. All assertions in test_cli_board.py use patched subprocess.run, not the real binary. | No further work needed. |
| 3. Tests stay readable and do not require the real kanban binary | SATISFIED. Helpers live in tests/cli_board_fixtures.py (board-specific, not widening tests/conftest.py). No runtime subprocess dependency; all tests use mock side-effects. | No further work needed. |

### Architecture Notes

- Both child tasks are archived: #936 (RED) and #939 (GREEN).
- Deliverables confirmed: tests/cli_board_fixtures.py exists with board_task(), board_move(), board_payloads().
- tests/test_cli_board.py actively imports and uses the helpers (20+ call sites).
- Scope boundary respected: board-specific helpers stayed out of tests/conftest.py and did not overlap with #926's generic subprocess-result helper lane.
- No production code touched; all changes are under tests/.
- This parent tracker is now ready to flow through the pipeline as a completed umbrella tracker. The builder should confirm deliverables and advance.

### Changes Made

- Claimed task #923 as architect-923.
- Verified deliverables exist and match all three AC lines.
- Approved to todo.

### Dependencies

- Verified: #936 (RED) is archived.
- Verified: #939 (GREEN) is archived.
- Verified: #909 (upstream board CLI tests) is archived.
- No new runtime or test dependency required.
