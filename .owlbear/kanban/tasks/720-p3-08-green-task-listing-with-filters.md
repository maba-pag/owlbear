---
id: 720
title: 'P3-08: GREEN — task listing with filters'
status: backlog
priority: needed
created: 2026-04-09T03:25:47.5994845+02:00
updated: 2026-04-09T03:25:47.5994845+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 719
class: standard
---

## Objective
Implement `list_tasks()` on KanbanEngine with full filter/sort/limit support.

Brief: see parent #712

## AC
- [ ] `list_tasks(status, tag, priority, search, sort, unclaimed, archived, limit, reverse, blocked)` returns filtered list[TaskRecord]
- [ ] Reads all task files from tasks_dir via task_io module
- [ ] Filter logic matches kanban-md behavioral contracts
- [ ] Sort by each supported field
- [ ] All #719 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (new — KanbanEngine class, list_tasks method)
