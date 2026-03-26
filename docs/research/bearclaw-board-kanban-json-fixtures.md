# BearClaw Board Kanban JSON Fixture Helpers

Task: #923
Question: What helper shape keeps board-test JSON arrangements DRY without widening OwlBear's global test-helper surface or overlapping #926's subprocess-helper scope?

## Sources Studied

| ID | Source | What it established |
|----|--------|---------------------|
| S1 | `tests/test_cli_board.py` | Board tests already use local `_task`, `_move`, and `_subproc` helpers, but many cases still repeat paired list/log setup. |
| S2 | `tests/conftest.py`; `tests/test_conftest_helpers.py` | Shared test helpers live in `conftest.py` only when intended for multiple files and are guarded explicitly against duplicate local copies. |
| S3 | `kanban/tasks/924-test-bearclaw-board-failure-handling-and-json.md`; `kanban/tasks/925-test-bearclaw-board-age-threshold-styling-contract.md`; `kanban/tasks/926-create-reusable-subprocess-result-helpers-for.md`; `docs/research/bearclaw-cli-subprocess-result-helper.md` | Board work keeps subprocess routing local, while generic `CompletedProcess` reuse is already a separate lane. |
| S4 | pytest fixtures reference | `conftest.py` fixtures are automatically shared across multiple files, so moving a board-only helper there widens scope immediately. |
| S5 | pytest how-to fixtures | Factory-style helpers are a normal way to reuse test arrangement data without changing the tested boundary. |
| S6 | Python `json` docs | `json.dumps()` is the correct way to serialize Python task and move structures into string payloads for tests. |
| S7 | Typer testing docs | BearClaw CLI behavior should stay tested at the `CliRunner` app boundary while arrangement helpers move underneath it. |

## Current State

- `tests/test_cli_board.py` already separates semantic task data (`_task`, `_move`) from subprocess routing (`_subproc`), but it still repeats the same paired `[_task()], []` and manual task-plus-log combinations across many cases. [S1, S6]
- `tests/conftest.py` is the repo's broad helper surface, and `tests/test_conftest_helpers.py` exists to lock that shared API down. Putting a board-only JSON builder there would create a global contract before OwlBear has a second non-board consumer. [S2, S4]
- The generic subprocess-result lane is already covered by #926. #923 should stay about board JSON payloads, not `CompletedProcess` or spawn-failure abstractions. [S2, S3]

## Option Comparison

| Option | Confidence | Pros | Costs | Verdict |
|--------|------------|------|-------|---------|
| A. Keep current `_task` / `_move` / `_subproc` locals only | .48 | No new files, zero coordination | Repetition remains, paired list/log fixtures can drift apart, no reusable board-specific contract | Reject |
| B. Add `tests/cli_board_fixtures.py` with `board_task()`, `board_move()`, and `board_payloads()`; keep `_subproc` local | .93 | Smallest reusable board-only surface, explicit contract file possible, keeps list/log JSON synchronized, no overlap with #926 | Adds one tests-only module | Recommend |
| C. Move board JSON builders into `tests/conftest.py` | .41 | Broad reuse if more consumers appear later | Widens global helper scope too early and duplicates the shared-helper lane already being shaped elsewhere | Reject |

## Recommendation (.93 confidence)

Use option B.

- Add `tests/cli_board_fixtures.py` with pure helpers for `board_task(...)`, `board_move(...)`, and `board_payloads(...)` that return paired `list_json` and `log_json` strings via `json.dumps()`. [S1, S5, S6]
- Keep the board command's subprocess router in `tests/test_cli_board.py`; only the semantic data builders move. That preserves the public `CliRunner` boundary and stays compatible with #926's separate `CompletedProcess` cleanup. [S1, S3, S7]
- If a second non-board consumer appears later, revisit `tests/conftest.py`; today there is not enough verified reuse to justify a global helper contract. [S2, S3, S4]

## Why This Fits OwlBear

- It solves the real duplication point: synchronized kanban task and move payload data, not subprocess result objects. [S1, S3]
- It keeps scope tight under `tests/` and avoids new production seams or test dependencies. [S2, S3, S5]
- It leaves board CLI assertions unchanged at the Typer boundary, so the refactor changes arrangement only, not behavior coverage. [S1, S7]

## Follow-up Tasks

1. #936 — Test board-specific kanban JSON payload helper for BearClaw board CLI tests (RED)

Dependencies: `#910`.

One-line AC: add failing tests for `tests/cli_board_fixtures.py` and update at least two existing board CLI tests to consume the helper while keeping subprocess routing local.

Created: `kanban\kanban-md.exe create --title "Test board-specific kanban JSON payload helper for BearClaw board CLI tests (RED)" ...` -> `#936`

2. #939 — Implement board-specific kanban JSON payload helper for BearClaw board CLI tests

Dependencies: `#910`, `#936`.

One-line AC: implement the board-only helper module and reuse it across current board happy-path and age tests without touching `tests/conftest.py`, `src/`, or #926's generic subprocess-helper lane.

Created: `kanban\kanban-md.exe create --title "Implement board-specific kanban JSON payload helper for BearClaw board CLI tests" ...` -> `#939`
