---
id: 489
title: 'Build: move/pick JSON output, drop board_context'
status: ideation
priority: needed
created: 2026-03-31T06:21:33.245938+02:00
updated: 2026-03-31T06:21:55.9504463+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
depends_on:
    - 485
class: standard
---

## Acceptance Criteria

- [ ] move_task passes --json to _run_kanban (1-line change)
- [ ] pick_task passes --json to _run_kanban (1-line change)
- [ ] board_context function and @mcp.tool() decorator removed from server.py
- [ ] board_context removed from __all__
- [ ] All mcp-kanban tests pass (unit + integration)
- [ ] ruff clean

## Context
GREEN phase for #477. Pattern: copy show_task's --json usage.

## Design Notes
- show_task already uses: _run_kanban(app_ctx, 'show', task_id, '--json')
- move_task change: add '--json' after status arg
- pick_task change: add '--json' after all other args
- Remove board_context function (7 lines) + __all__ entry
