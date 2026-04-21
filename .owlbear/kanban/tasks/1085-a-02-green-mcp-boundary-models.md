---
id: 1085
title: 'A-02: GREEN — MCP boundary models'
status: todo
priority: critical
created: 2026-04-21T10:53:28.584627+00:00
updated: 2026-04-21T10:53:28.584627+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:green
parent: 1045
depends_on:
- 1084
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5–§6, paper-integration.md §2
Module: `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`

Implement MCP-layer Pydantic input schemas for all 8 tool parameter sets. Re-export engine response envelopes. AC13 enforcement: edit_task schema must NOT include `status`. The adapter models are the wire contract — all validation beyond schema shape is delegated to the engine via AgentView.

## Acceptance Criteria

- [ ] All RED tests from A-01 (#1084) pass
- [ ] Input models: ListTasksInput, ShowTaskInput, PickTasksInput, CreateTaskInput, EditTaskInput, MoveTaskInput, StartWorkInput, EndWorkInput
- [ ] EditTaskInput excludes `status` field (AC13 — adapter-layer rejection)
- [ ] EndWorkInput includes `outcome`, `move_to`, `note`, `block_reason`, `archival_reason`, `archival_refs` per Brief A §5.8
- [ ] Response envelopes re-exported or directly importable from engine models package
- [ ] No `file` field, no `claimed_by` field in any schema (AC16, AC17)