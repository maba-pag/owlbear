---
id: 729
title: 'P3-17: RED — MCP server migration (replace _run_kanban with engine)'
status: backlog
priority: critical
created: 2026-04-09T03:28:35.8186809+02:00
updated: 2026-04-09T03:28:35.8186809+02:00
tags:
    - kanban
    - phase-3
    - type:test
parent: 712
depends_on:
    - 726
    - 728
class: standard
---

## Objective
Write/update tests that verify the MCP server uses KanbanEngine instead of subprocess calls.

Brief: see parent #712 — Phase 2: MCP server migration

CRITICAL: The existing subprocess-based server MUST continue working until this migration is complete. This is an atomic swap — old code works until the switch.

## AC
- [ ] Tests for updated AppContext (KanbanEngine instance instead of kanban_bin path)
- [ ] Tests for updated lifespan (instantiates KanbanEngine, no binary check)
- [ ] Tests for each MCP tool (list_tasks, show_task, create_task, edit_task, move_task, start_work, end_work, pick_tasks) using engine methods
- [ ] Existing MCP test contracts preserved — same inputs produce equivalent outputs
- [ ] All tests fail against current subprocess-based server

## Files
- `tests/test_kanban_mcp_migration.py` (new)
