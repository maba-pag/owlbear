---
id: 22
title: Build CLI trigger commands
status: todo
priority: needed
created: 2026-03-26T17:22:48.6175218+01:00
updated: 2026-03-30T07:56:41.8421812+02:00
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
