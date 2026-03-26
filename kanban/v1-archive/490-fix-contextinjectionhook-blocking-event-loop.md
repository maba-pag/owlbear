---
id: 490
title: Fix ContextInjectionHook blocking event loop
status: archived
priority: important
created: 2026-03-04T07:38:06.1851597+01:00
updated: 2026-03-06T19:28:27.5136813+01:00
started: 2026-03-06T17:43:47.1413063+01:00
completed: 2026-03-06T19:28:27.5136813+01:00
tags:
    - audit
    - bugfix
    - scope:core
class: standard
---

ARC-19: `ContextInjectionHook` blocks the event loop in two places.

## Bug

`__call__()` is async but delegates to two sync methods:

1. `_read_instructions()`  `Path.read_text()` (blocking file I/O)
2. `_run_kanban()`  `subprocess.run()` (blocking subprocess)

Since `HookRegistry.emit()` awaits async handlers, both block the event loop
for the duration of the operation.

## Fix (established codebase patterns)

| Method | Current (blocking) | Fix | Precedent |
|---|---|---|---|
| `_run_kanban()` | `subprocess.run()` | `asyncio.create_subprocess_exec()` | `KanbanToolset._run_kanban()` (kanban.py L74) |
| `_read_instructions()` | `Path.read_text()` | `asyncio.to_thread(path.read_text, ...)` | `WebSearchToolset` (web_search.py L149), `TTSEngine` (tts.py L61) |

Both methods become `async`. `__call__` already is async, so just `await` them.

## Files to change

- `src/owlbear/core/context_hook.py`  make both helpers async, drop `import subprocess`
- `tests/test_context_hook.py`  update mocks from `subprocess.run` to `asyncio.create_subprocess_exec`; add mock for `asyncio.to_thread` on the file read path

## Acceptance Criteria

- [ ] `_run_kanban()` uses `asyncio.create_subprocess_exec()` (no sync subprocess calls)
- [ ] `_read_instructions()` uses `asyncio.to_thread()` (no blocking file I/O)
- [ ] Both methods are `async def`
- [ ] `import subprocess` removed from context_hook.py
- [ ] All existing tests pass with updated mocks
- [ ] No ruff violations
