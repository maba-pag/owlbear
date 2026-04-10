---
id: 314
title: KanbanToolset implementation — 7 async subprocess tools
status: archived
priority: critical
created: 2026-03-01T06:23:35.1135777+01:00
updated: 2026-03-01T17:09:38.3451037+01:00
started: 2026-03-01T07:06:42.5881481+01:00
completed: 2026-03-01T17:09:38.3451037+01:00
tags:
    - phase-12
    - agent
    - orchestrator
depends_on:
    - 313
class: standard
---

Implementation task for #301. Make tests from #313 pass.

## Acceptance Criteria

- [ ] `src/owlbear/tools/kanban.py` created
- [ ] `KanbanToolset(FunctionToolset)` class with `__init__(kanban_dir: Path, kanban_bin: Path | None = None, hooks: HookRegistry | None = None)`
- [ ] `_run_kanban(*args: str) -> tuple[str, str, int]` async helper via `asyncio.create_subprocess_exec`
- [ ] `--no-color` and `--dir {kanban_dir}` appended to every command automatically
- [ ] Binary auto-detection: `kanban_dir / 'kanban-md.exe'` (Windows) or `kanban_dir / 'kanban-md'` (Unix), fall back to `shutil.which('kanban-md')`
- [ ] `kanban_list(*, status: str | None, tag: str | None, priority: str | None, blocked: bool | None, not_blocked: bool | None, unblocked: bool | None) -> str` — runs `list --compact`
- [ ] `kanban_show(task_id: int) -> str` — runs `show {id} --json`
- [ ] `kanban_create(title: str, *, priority: str | None, tags: str | None, body: str | None, depends_on: str | None) -> str`
- [ ] `kanban_move(task_id: int, status: str) -> str`
- [ ] `kanban_edit(task_id: int, *, body: str | None, block: str | None, unblock: bool | None, tags: str | None, priority: str | None, append_body: str | None) -> str`
- [ ] `kanban_pick(*, status: str | None, claim: str | None, move: str | None) -> str`
- [ ] `kanban_context() -> str`
- [ ] Mutating ops (create, move, edit, pick) emit `HookEvent.PRE_TOOL_USE` via `_emit_hook` (pattern from `GitLocalToolset`)
- [ ] Non-zero exit → `'error: {stderr.strip()}'` (never raises exceptions)
- [ ] All tests from #313 pass
- [ ] ruff clean
- [ ] Module docstring following `git_local.py` docstring style, `__all__` exported

## Architecture Notes

Follow `GitLocalToolset` pattern exactly. Same `_run_kanban` / `_emit_hook` / `_register_tools` structure. Optional parameters passed as CLI flags only when not None. `kanban_dir` is resolved to absolute path in constructor.
