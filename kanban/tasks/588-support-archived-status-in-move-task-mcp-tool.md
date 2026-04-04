---
id: 588
title: Support 'archived' status in move_task MCP tool
status: todo
priority: needed
created: 2026-04-04T07:08:49.8265186+02:00
updated: 2026-04-04T07:08:49.8265186+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
class: standard
---

## Objective
Allow `move_task` MCP tool to accept "archived" as a target status, using kanban-md's `archive` CLI command under the hood.

## Acceptance Criteria
- [ ] `move_task(task_id, status="archived")` archives the task (calls `kanban-md archive`)
- [ ] All other status values continue to use `kanban-md move` as before
- [ ] Error from `kanban-md archive` is surfaced via ToolError
- [ ] Unit tests cover the new archive path and the existing move paths still pass

## Context
Currently `move_task` only supports the 7 defined statuses (ideation through done). Archiving requires the separate `kanban-md archive` command. This gap means agents have no MCP tool to archive tasks — they must use `end_work(outcome="success")` repeatedly to advance through every status first, which is impractical for mass cleanup.
