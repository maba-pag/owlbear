---
id: 620
title: 'Test: pick_tasks MCP tool gate logic and output format'
status: ideation
priority: needed
created: 2026-04-05T01:30:52.3984607+02:00
updated: 2026-04-05T01:58:34.5763653+02:00
tags:
    - scope:mcp
    - phase-2
    - test
parent: 619
class: standard
---

## Acceptance Criteria

- Tests cover `pick_tasks` MCP tool in owlbear-kanban server
- Test cases validate:
  - Basic pick: tasks in various statuses returned with task_id and status
  - Gate filtering: tasks failing atomicity/TDD/clarity gates are excluded
  - Limit: `limit=5` caps output at 5 entries
  - Default limit is 25
  - Sort order: critical+done-adjacent tasks appear before someday+ideation tasks
  - Empty board: returns empty dispatch list
  - Archived tasks excluded
  - Blocked/claimed tasks excluded (unblocked + unclaimed board read)
- Tests use the existing test patterns for MCP kanban tools (mock _run_kanban or use subprocess fixtures)
- Tests live in tests/test_pick_tasks_{task_id}.py
