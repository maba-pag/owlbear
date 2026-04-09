---
id: 722
title: 'P3-10: GREEN — task CRUD operations'
status: backlog
priority: critical
created: 2026-04-09T03:26:03.5311612+02:00
updated: 2026-04-09T03:26:03.5311612+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 721
class: standard
---

## Objective
Implement create_task, edit_task, move_task on KanbanEngine.

Brief: see parent #712

## AC
- [ ] `create_task(title, ...)` allocates next_id from config, writes task file, increments config next_id
- [ ] `edit_task(task_id, ...)` modifies task fields, writes back, updates `updated` timestamp
- [ ] `edit_task` append_body with optional `[[YYYY-MM-DD]]` timestamp prefix
- [ ] `move_task(task_id, status)` changes status, handles archive
- [ ] Slug frozen at creation — edit title does not rename file
- [ ] All #721 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (edit — add CRUD methods)
