---
id: 313
title: KanbanToolset unit tests (TDD first)
status: archived
priority: critical
created: 2026-03-01T06:23:20.6503985+01:00
updated: 2026-03-01T17:09:37.3661675+01:00
started: 2026-03-01T07:06:37.5586832+01:00
completed: 2026-03-01T17:09:37.3661675+01:00
tags:
    - phase-12
    - agent
    - orchestrator
    - test
depends_on:
    - 296
class: standard
---

TDD test task for #301. Write failing tests for KanbanToolset before implementation.

## Acceptance Criteria

- [ ] `tests/test_kanban_tools.py` created with `TestKanbanToolset` test classes
- [ ] Mock `asyncio.create_subprocess_exec` — same `_make_proc` / `_patch_exec` pattern as `test_git_local.py`
- [ ] `TestConstructor`: `kanban_dir` stored, `kanban_bin` stored/auto-detected, `hooks` stored (default None), inherits `FunctionToolset`
- [ ] `TestToolRegistration`: all 7 tools registered — `kanban_list`, `kanban_show`, `kanban_create`, `kanban_move`, `kanban_edit`, `kanban_pick`, `kanban_context`
- [ ] `TestKanbanList`: calls `kanban-md list --compact --no-color --dir {dir}`, returns stdout; optional `--status`, `--tag`, `--priority`, `--blocked`/`--not-blocked`/`--unblocked` filters passed through
- [ ] `TestKanbanShow`: calls `kanban-md show {id} --json --no-color --dir {dir}`, returns stdout
- [ ] `TestKanbanCreate`: calls `kanban-md create {title} --no-color --dir {dir}` with optional `--priority`, `--tags`, `--body`, `--depends-on` flags; returns stdout
- [ ] `TestKanbanMove`: calls `kanban-md move {id} {status} --no-color --dir {dir}`, returns stdout
- [ ] `TestKanbanEdit`: calls `kanban-md edit {id} --no-color --dir {dir}` with optional `--body`, `--block`, `--unblock`, `--tags`, `--priority`, `--append-body` flags; returns stdout
- [ ] `TestKanbanPick`: calls `kanban-md pick --no-color --dir {dir}` with optional `--status`, `--claim`, `--move` flags; returns stdout
- [ ] `TestKanbanContext`: calls `kanban-md context --no-color --dir {dir}`, returns stdout
- [ ] `TestErrorHandling`: non-zero exit code returns `error: {stderr.strip()}` for each tool (never raises)
- [ ] `TestHookEmission`: mutating ops (create, move, edit, pick) emit `HookEvent.PRE_TOOL_USE`; read-only ops (list, show, context) do not
- [ ] All tests import from `owlbear.tools.kanban` (will fail red until impl task)
- [ ] ruff clean

## Architecture Notes

Follow `test_git_local.py` pattern exactly. Use `unittest.mock.AsyncMock` for subprocess, `pytest.mark.asyncio` for async tests. The `_patch_exec` helper should patch `owlbear.tools.kanban.asyncio.create_subprocess_exec`.
