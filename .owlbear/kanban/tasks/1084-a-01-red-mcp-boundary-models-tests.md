---
id: 1084
title: 'A-01: RED — MCP boundary models tests'
status: todo
priority: needed
created: 2026-04-21T10:53:19.162858+00:00
updated: 2026-04-21T10:53:19.162858+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:red
parent: 1045
depends_on:
- 1066
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5–§6, paper-integration.md §2
Module: `serve/mcp-kanban/tests/test_mcp_models.py`

Test MCP-layer Pydantic input schemas (tool parameter models for all 8 tools) and verify response envelope re-exports from engine projection types. The MCP adapter is a mechanical translator — these models define the wire contract between calling agents and the adapter.

Cross-brief: depends on #1066 (Brief B models GREEN) because MCP input schemas and response envelopes import/reuse engine projection types (TaskSummary, TaskFull, DispatchEntry, Wave, response envelopes).

## Acceptance Criteria

- [ ] Input schema for each of the 8 tools: list_tasks, show_task, pick_tasks, create_task, edit_task, move_task, start_work, end_work
- [ ] AC13: edit_task input schema does NOT accept `status` parameter (adapter-layer rejection)
- [ ] AC15: list_tasks input schema enforces `ids` exclusivity with other filter params at schema level where possible
- [ ] AC16: No projection includes `file` field
- [ ] AC17: No `claimed_by` field in any projection
- [ ] Response envelopes (ListTasksResponse, ShowTaskResponse, PickTasksResponse, SingleTaskResponse) importable from engine models
- [ ] All tests fail (RED phase)