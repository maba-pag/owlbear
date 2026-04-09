---
id: 721
title: 'P3-09: RED — task CRUD (create with next_id, edit fields, move status)'
status: backlog
priority: critical
created: 2026-04-09T03:25:55.6660108+02:00
updated: 2026-04-09T03:25:55.6660108+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 718
class: standard
---

## Objective
Write failing tests for task creation (next_id allocation), field editing, and status movement.

Brief: see parent #712

## AC
- [ ] Test create_task: allocates next_id, creates file with slug, increments next_id in config
- [ ] Test create_task with all optional params (body, tags, priority, status, parent, depends_on)
- [ ] Test edit_task: update title, body, priority, status, tags (add/remove), deps (add/remove), parent, block/unblock
- [ ] Test edit_task append_body with timestamp prefix
- [ ] Test move_task to valid status
- [ ] Test move_task to archived
- [ ] Test move_task rejects invalid status
- [ ] All tests fail

## Files
- `tests/test_kanban_engine_crud.py` (new)
