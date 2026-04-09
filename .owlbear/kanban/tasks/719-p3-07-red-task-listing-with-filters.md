---
id: 719
title: 'P3-07: RED — task listing with filters'
status: backlog
priority: needed
created: 2026-04-09T03:25:39.267676+02:00
updated: 2026-04-09T03:25:39.267676+02:00
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
Write failing tests for listing tasks with filtering, sorting, and pagination.

Brief: see parent #712

## AC
- [ ] Test list all tasks from tasks_dir
- [ ] Test filter by status, tag, priority, blocked (tri-state), unclaimed
- [ ] Test full-text search in titles and bodies
- [ ] Test sort by priority, updated, id, title, status, created
- [ ] Test reverse ordering
- [ ] Test limit (pagination cap)
- [ ] Test archived task listing
- [ ] All tests fail

## Files
- `tests/test_kanban_engine_listing.py` (new)
