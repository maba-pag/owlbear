---
id: 1084
title: 'A-01: RED — MCP boundary models tests'
status: in-progress
priority: needed
created: 2026-04-21T10:53:19.162858+00:00
updated: 2026-04-22T18:03:56.639718+00:00
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
archival_reason:
archival_refs: []
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
[[2026-04-22]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_models_1084.py
- Classes: TestFromAC_MCPInputSchemas, TestFromAC_EditTaskNoStatusParam, TestFromAC_ListTasksIdsExclusivity, TestFromAC_NoFileInProjections, TestFromAC_ClaimFieldContracts, TestFromAC_EngineSummaryProjectionFields, TestFromAC_TaskFullModel, TestFromAC_DispatchModels, TestFromAC_ResponseEnvelopes
- Tests per category: happy 18, edge 10, error 12, boundary 11
- Total: 51 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests |
|---|---|
| 8 MCP input schemas exist | test_*_params_importable (×8), instantiation tests (×7) |
| AC13: edit_task no status | test_edit_task_params_rejects_status_field, test_edit_task_params_no_status_in_model_fields + rejects depends_on/tags |
| AC15: ids exclusivity | test_list_tasks_ids_with_{status,tag,priority,search,unclaimed}_raises, test_ids_alone_valid |
| AC16: no file field | test_task_full_no_file_field, test_dispatch_entry_no_file_field |
| AC17: claimed_at + claimed, no claimed_by | test_task_summary_has_claimed_at_field, test_task_full_no_claimed_by_field |
| Engine §2.1 fields | archival_reason, archival_refs (list[int]), dep_status — 4 tests |
| TaskFull §2.2 | importable, has created/updated/body, body optional (None) — 3 tests |
| DispatchEntry §2.3 | importable, agent field, all 6 required fields — 3 tests |
| Wave §2.4 | importable, index + tasks — 2 tests |
| Response envelopes §2.5 | 4 import tests + 4 field tests |

### Failure modes
All 51 tests fail: ImportError (new schema classes/models not yet implemented), AttributeError/AssertionError (missing fields on existing TaskSummary). No syntax errors.