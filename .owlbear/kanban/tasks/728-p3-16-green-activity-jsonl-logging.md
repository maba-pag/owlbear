---
id: 728
title: 'P3-16: GREEN — activity.jsonl logging'
status: backlog
priority: needed
created: 2026-04-09T03:28:26.0758289+02:00
updated: 2026-04-09T03:28:26.0758289+02:00
tags:
    - kanban
    - phase-3
    - scope:mcp-kanban
parent: 712
depends_on:
    - 727
class: standard
---

## Objective
Implement activity.jsonl logging and wire it into CRUD and compound operations.

Brief: see parent #712

## AC
- [ ] `log_activity(action, task_id, detail)` appends JSON line to activity.jsonl
- [ ] Wired into create_task, edit_task, move_task, claim, release, block, unblock, archive operations
- [ ] Log file created on first write if missing
- [ ] All #727 tests pass

## Files
- `serve/mcp-kanban/src/owlbear_mcp_kanban/activity_log.py` (new)
- `serve/mcp-kanban/src/owlbear_mcp_kanban/engine.py` (edit — wire activity logging)
