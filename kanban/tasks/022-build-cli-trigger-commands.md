---
id: 22
title: Build CLI trigger commands
status: review
priority: needed
created: 2026-03-26T17:22:48.6175218+01:00
updated: 2026-03-30T22:49:17.3493664+02:00
tags:
    - phase-2
    - scope:cli
    - type:build
depends_on:
    - 20
    - 202
class: standard
---

## Objective
Build the owlbear CLI commands that trigger orchestrator dispatch.

## Acceptance Criteria

### CLI App Structure
- [ ] Typer app defined in `packages/orchestrator/src/owlbear/cli.py` (single file)
- [ ] Entry point `owlbear = owlbear.cli:app` added to `packages/orchestrator/pyproject.toml` under `[project.scripts]`
- [ ] `uv run owlbear --help` lists dispatch, run, and status commands

### `owlbear dispatch <task_id>`
- [ ] Positional argument `task_id: int`
- [ ] Calls planner gate checks + agent mapper for the given task
- [ ] Dispatches to selected agent via AcpClient (async, wrapped with `asyncio.run()`)
- [ ] Stdout on success: `Dispatched #<id> to <agent>`
- [ ] Exit 0 on success, exit 1 on any error

### `owlbear run [--all]`
- [ ] No-arg: calls `read_board()` + gates + selector, dispatches the single top-priority task
- [ ] Stdout when no tasks: `No actionable tasks on the board.` with exit 0
- [ ] `--all` flag: loops (read_board, select, dispatch) until no actionable tasks remain, printing each result
- [ ] Each iteration re-reads the board (tasks change status mid-loop)

### `owlbear status`
- [ ] Reads board via `kanban-md list` subprocess (no planner dependency)
- [ ] Prints task count per status column (e.g., `backlog: 5 | todo: 3 | in-progress: 2`)
- [ ] Prints blocked tasks with reasons (if any)
- [ ] Exit 0

### Error Handling
- [ ] Copilot CLI missing (`shutil.which(copilot) is None`): stderr `Copilot CLI not found. Install: gh extension install github/gh-copilot` with exit 1
- [ ] Task not found: stderr `Task #<id> not found.` with exit 1
- [ ] Task already claimed: stderr `Task #<id> is already claimed by <agent>.` with exit 1
- [ ] AcpClientError: stderr with category-appropriate message, exit 1
- [ ] All errors via `typer.echo(..., err=True)` + `raise typer.Exit(code=1)`

### Constraints
- [ ] No business logic in CLI layer -- delegates to `owlbear.planner` and `owlbear_orchestrator` modules
- [ ] Async commands use `asyncio.run(_async_impl())` wrapper pattern (v1 precedent)

## Context
Depends on #20 (dispatch planner umbrella) and #202 (TDD RED â€” failing tests). See docs/research/cli-trigger-commands.md for framework choice (Typer, .85 confidence), module placement, async pattern, and error handling design.

-t

[[2026-03-30]] Mon 07:56
## Architecture Review
**Verdict:** APPROVED

### AC Assessment

- **Typer or click**: Ambiguous framework choice. Pinned to Typer per research (.85 confidence).
- **owlbear dispatch**: Missing output format and exit codes. Specified stdout format + exit codes.
- **owlbear run**: Missing board re-read requirement. Added re-read-per-iteration constraint.
- **owlbear status**: Vague "board summary". Specified count-per-status + blocked task display.
- **CLI entry point**: Clear but no module path. Pinned to owlbear/cli.py + [project.scripts].
- **Clear output**: Untestable as phrased. Replaced with specific stdout/stderr formats.
- **Error handling**: Listed scenarios but no behavior. Specified exact messages + exit codes.
- **Unit tests**: TDD violation (tests bundled in impl task). Extracted to #202 (Test: CLI trigger commands).

### Architecture Notes

Module placement: owlbear/cli.py in domain package, consistent with research recommendation and voice package pattern (owlbear_voice/main.py). Single file for 4 commands per KISS (v1 needed split at 1200 LOC; v2 is ~150 LOC).

Dependency direction: CLI (assembly-level) imports from owlbear.planner (domain) and owlbear_orchestrator (infrastructure). No layering violation.

Async pattern: asyncio.run() wrappers for dispatch/run commands. Standard pattern, v1 precedent confirmed in research.

owlbear status has zero dependency on planner module (reads kanban-md directly). This enables partial testability before #20 completes, but keeping all commands in one task is correct (shared Typer app, entry point, error handling).

Typer already in dependencies (typer>=0.24 added by #154, archived).

### Changes Made

- Rewrote AC: 9 vague lines replaced with 19 verifiable lines grouped by command
- Created #202 (Test: CLI trigger commands) at backlog with detailed test AC
- Added depends_on #202 to #22
- Pinned module path, entry point, framework choice, output formats, exit codes, error messages

### Dependencies

- Verified: #20 (dispatch planner umbrella) at todo, subtasks #144/#145/#146 in pipeline
- Verified: #154 (Typer dependency) archived, typer>=0.24 in pyproject.toml
- Added: #202 (TDD RED test task) at backlog

[[2026-03-30]] Mon 19:10
## Test-Writer Notes\n- Test file: tests/test_cli.py\n- Classes: TestFromAC_CLIAppStructure, TestFromAC_DispatchCommand, TestFromAC_RunCommand, TestFromAC_StatusCommand, TestFromAC_ErrorHandling\n- Tests per category: happy 5, edge 2, error 8, boundary 5\n- Total: 20 tests, all FAIL (ModuleNotFoundError on owlbear.cli) checked\n- ruff: clean\n- Mock strategy: patch at owlbear.cli.* namespace (name-import pattern expected)\n- AC coverage:\n  CLI app structure: test_help_lists_dispatch/run/status\n  dispatch success: test_dispatch_success_stdout_format\n  dispatch task_not_found: test_dispatch_task_not_found_exits_1_stderr\n  dispatch already_claimed: test_dispatch_already_claimed_exits_1_stderr\n  dispatch AcpClientError: test_dispatch_acp_client_error_exits_1_stderr\n  dispatch copilot_missing: test_dispatch_copilot_not_found_exact_message\n  dispatch int validation: test_dispatch_non_integer_task_id_rejected\n  run top-priority: test_run_no_args_dispatches_top_priority_task\n  run no tasks: test_run_no_actionable_tasks_message_exit_0\n  run --all loop: test_run_all_loops_dispatches_each_task\n  run board re-read: test_run_all_rereads_board_each_iteration\n  status counts: test_status_prints_count_per_status_column\n  status blocked: test_status_shows_blocked_tasks_with_block_reason\n  status exit 0: test_status_always_exits_0\n  stderr routing: test_copilot_not_found_install_hint_on_stderr, test_task_not_found_message_contains_id_and_phrase, test_already_claimed_message_contains_id_and_agent, test_error_message_not_on_stdout

[[2026-03-30]] Mon 22:49
## Builder Notes
- Files changed: packages/orchestrator/src/owlbear/cli.py (new), packages/orchestrator/src/owlbear_orchestrator/acp_client.py (+__aenter__/__aexit__), packages/orchestrator/pyproject.toml (+[project.scripts]), tests/test_cli.py (test infrastructure fixes)
- Tests: 20 passed, coverage 94% on owlbear/cli.py (above 90% threshold)
- Lint: ruff clean on both cli.py and acp_client.py
- Evidence: 20/20 tests green in 0.72s
- Fixes applied: (1) datetime.UTC used on class instead of module -- fixed by importing UTC directly; (2) CliRunner(mix_stderr=False) not supported in Click 8.2+ -- fixed with _SeparatedCliRunner subclass restoring pre-8.2 output semantics; (3) AcpClient needed __aenter__/__aexit__ for async context manager support -- added minimal implementation; (4) PYI034 __aenter__ return type -- changed to Self
