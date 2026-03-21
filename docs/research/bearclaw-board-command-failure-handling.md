# BearClaw Board Failure-Handling Gate

> **Owning task:** #920 — Harden bearclaw board command failures and JSON parsing
> **Date:** 2026-03-21 **Status:** Complete

## 1. Context and Question

Task #910 intentionally kept `bearclaw board` on the happy path only. Task #920
decides the post-MVP failure contract: should missing `kanban-md`, non-zero
`list` / `log` exits, and invalid JSON bubble out as Rich tracebacks, degrade to
empty or partial board output, or be translated into the established BearClaw
`_cli_error` contract with distinct messages for the task list and move log
stages [S1, S2, S3].

## 2. Sources Studied

| ID | Source | Relevance | What |
|----|--------|:---------:|------|
| S1 | `docs/research/bearclaw-board-command.md` | .95 | Existing board seam, age fallback rule, and CLI boundary |
| S2 | `docs/research/bearclaw-board-command-implementation-gate.md` | .95 | MVP scope and the explicit deferral of failure hardening to #920 |
| S3 | `src/bearclaw/cli.py`, `src/bearclaw/commands/__init__.py`, `tests/test_cli_error_helper.py` | .95 | BearClaw CLI error contract and Rich traceback wiring |
| S4 | `src/owlbear/core/board_context.py`, `src/owlbear/core/context_hook.py`, `src/owlbear/tools/kanban.py`, `src/owlbear/core/lint_gate.py` | .90 | Existing subprocess error-handling patterns in OwlBear |
| S5 | Python `subprocess` docs | .90 | `run(..., check=False, capture_output=True, text=True)` behavior plus `OSError` for missing executables |
| S6 | Python `json` docs | .90 | `JSONDecodeError` semantics and parse-failure details |
| S7 | Click exception handling docs | .80 | User-facing CLI errors should render to stderr with explicit exit codes |
| S8 | Typer exception docs | .75 | Uncaught exceptions surface as Rich traceback output, which is useful for debugging but wrong for expected CLI failures |
| S9 | `docs/research/bearclaw-board-command-red-gate.md` | .85 | CLI-boundary test seam for board command behavior |

## 3. Options

| Option | Confidence | Behavior | Pros | Risks | Verdict |
|--------|:----------:|----------|------|-------|---------|
| A. Let exceptions bubble | .20 | Raw `FileNotFoundError` / `JSONDecodeError` / traceback | Lowest code | Breaks `_cli_error` contract; exposes debug output to users | Reject |
| B. Degrade to empty or partial board | .40 | Swallow failures and keep rendering | Keeps command alive | Hides broken `kanban-md`; move-log failure would produce wrong ages | Reject |
| C. Local stage-aware `_cli_error` helper | .95 | Catch spawn, exit, and parse errors per subprocess stage | Matches BearClaw contract; precise messages; minimal diff | Requires explicit test coverage for each failure class | Recommend |

## 4. Findings

1. `bearclaw` already installs Rich tracebacks at the root CLI, but existing
   command modules route predictable user-facing failures through `_cli_error`,
   which writes `Error: ...` to stderr and exits with code 1. Letting board
   subprocess or JSON exceptions escape would regress that contract and expose
   debug-style output for routine operator failures [S3, S7, S8].

2. The board command should keep the happy-path subprocess shape from #910:
   `subprocess.run(..., capture_output=True, text=True, check=False, cwd=...)`,
   then branch explicitly on spawn error, non-zero exit, and JSON parse error.
   `check=False` keeps stdout and stderr available so the command can produce
   stage-specific `_cli_error` messages instead of a generic
   `CalledProcessError` [S2, S4, S5].

3. Task-list and move-log failures must stay distinct because they guard
   different invariants. The list call defines the visible task rows; the move
   log only supports age-in-status. The earlier `created` fallback is valid only
   when a successfully loaded move log has no matching entry for a task, not
   when the move-log command or JSON parse fails entirely. On move-log failure,
   the command should abort instead of silently rendering incorrect ages [S1,
   S2, S6].

4. The smallest correct implementation is a private helper inside
   `src/bearclaw/commands/board.py`, parameterized by a human label such as
   `task list` or `move log`. That preserves #910's task-local-helper boundary
   and avoids inventing a shared kanban wrapper for one CLI command [S2, S3,
   S4].

5. Failure-path verification should stay at the CLI boundary. Extend
   `tests/test_cli_board.py` with patched `subprocess.run` cases for missing
   binary, non-zero task-list exit, non-zero move-log exit, invalid task-list
   JSON, and invalid move-log JSON, while keeping the happy-path assertions from
   #909 intact. Because #920 currently mixes RED and GREEN work, a paired RED
   task is warranted before implementation [S3, S9].

## 5. Recommendation (.95 confidence)

Implement option C.

Recommended behavior:

- Missing executable: `_cli_error("kanban-md is not available while loading the board {stage}.")`
- Non-zero exit: `_cli_error("Failed to load kanban-md task list: ...")` and `_cli_error("Failed to load kanban-md move log: ...")`
- Invalid JSON: `_cli_error("Failed to parse kanban-md task list JSON: ...")` and `_cli_error("Failed to parse kanban-md move log JSON: ...")`

Keep those branches in one local helper in `src/bearclaw/commands/board.py`.
Do not fall back to `created` when the move log itself failed to load or parse.

## 6. Follow-up Tasks

1. #924 — Test bearclaw board failure handling and JSON parse errors (RED)
   Priority rationale: #920 is a GREEN task but its AC still includes new CLI
   failure-path tests, so the contract should be pinned first.
   Dependencies: intended predecessor to #920; the architect should add the
   dependency before approving #920 to `todo`.
   One-line AC: failing CLI tests cover missing binary, non-zero list/log exits,
   invalid list/log JSON, and stage-specific `_cli_error` messages.
   Created: `kanban\kanban-md.exe create "Test bearclaw board failure handling and JSON parse errors (RED)" ...` -> #924

2. Existing #920 — Harden bearclaw board command failures and JSON parsing
   Priority rationale: GREEN half of the board hardening split.
   Dependencies: should follow #924 once the architect keeps the RED/GREEN pair.
   One-line AC: implement the local stage-aware `_cli_error` helper in
   `src/bearclaw/commands/board.py` and keep scope in that file plus
   `tests/test_cli_board.py`.
