---
id: 726
title: 'P3-14: GREEN — compound ops (start_work, end_work)'
status: backlog
priority: critical
created: 2026-04-09T03:27:37.7135664+02:00
updated: 2026-04-09T03:27:37.7135664+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 725
class: standard
---

## Objective
Implement start_work and end_work as KanbanEngine methods.

Brief: see parent #712

## AC
- [ ] `start_work(task_id)`: blocked guard, claim, return TaskRecord
- [ ] `end_work(task_id, note, outcome, ...)`: append timestamped note, advance/stay/block/reject, release claim
- [ ] Status advancement: index current in config statuses, move to next; last status triggers archive
- [ ] block_reason required when outcome=block
- [ ] All #725 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (edit — add start_work, end_work)
