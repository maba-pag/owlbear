---
id: 1087
title: 'A-04: RED — mutation tool adapter tests'
status: review
priority: needed
created: 2026-04-21T10:53:48.099115+00:00
updated: 2026-04-24T18:00:08.159390+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:red
parent: 1045
depends_on:
- 1083
- 1085
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.4–§5.5, paper-integration.md §1.4–§1.5
Module: `serve/mcp-kanban/tests/test_mcp_mutation_tools.py`

Test the 2 mutation tool adapters: `create_task`, `edit_task`. All tests mock `AgentView`. Tests verify: correct AgentView method called with correct args, SingleTaskResponse returned, KanbanError → ToolError mapping.

## Acceptance Criteria

- [ ] `create_task`: title, body, priority, tags, parent, depends_on forwarded; SingleTaskResponse returned (AC24 — dep validation delegated to engine)
- [ ] `create_task`: no `status` param accepted (engine controls entry status per D50)
- [ ] `edit_task`: all 13 params forwarded; SingleTaskResponse returned
- [ ] `edit_task`: `body` + `append_body` both set → engine raises ValidationError → adapter maps to ToolError (AC14)
- [ ] `edit_task`: `archival_reason` / `archival_refs` on non-archived → engine raises → ToolError
- [ ] `edit_task`: no-op call → engine raises → ToolError
- [ ] Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message
- [ ] All tests fail (RED phase)
[[2026-04-24]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Classes: TestFromAC_CreateTaskAdapter, TestFromAC_EditTaskAdapter, TestFromAC_KanbanErrorMapping
- Tests per category: happy 10, edge 3, error 9, boundary 0
- Total: 22 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| create_task: all 6 params forwarded to AgentView | test_calls_agent_view_create_task, test_forwards_title, test_forwards_body, test_forwards_priority, test_forwards_tags_as_list, test_forwards_parent, test_forwards_depends_on_as_list |
| create_task: no status param (D50) | test_create_task_has_no_status_parameter |
| create_task: SingleTaskResponse returned | test_create_task_returns_single_task_response |
| create_task: dep validation → ToolError (AC24) | test_create_task_dep_not_found_raises_tool_error |
| edit_task: all 13 params forwarded | test_edit_task_forwards_all_13_params, test_edit_task_forwards_id_as_int |
| edit_task: SingleTaskResponse returned | test_edit_task_returns_single_task_response |
| edit_task: body+append_body → ToolError (AC14) | test_edit_task_body_and_append_body_raises_tool_error |
| edit_task: archival_reason on non-archived → ToolError | test_edit_task_archival_reason_on_non_archived_raises_tool_error |
| edit_task: archival_refs on non-archived → ToolError | test_edit_task_archival_refs_on_non_archived_raises_tool_error |
| edit_task: no-op → ToolError | test_edit_task_no_op_raises_tool_error |
| KanbanError → ToolError with user_message | test_validation_error_user_message_in_tool_error, test_not_found_error_maps_to_tool_error, test_concurrency_error_maps_to_tool_error, test_all_kanban_error_subclasses_map_to_tool_error_not_raw_exception |

### Failure analysis (selected)
- adapter calls `engine.create_task()` not `engine.agent_view().create_task()` → 7 assertion failures
- `status` param still present on `create_task` → 1 assertion failure
- returns `KanbanTask` not `SingleTaskResponse` → 2 assertion failures
- `edit_task` missing `block_reason`/`archival_reason`/`archival_refs` params → TypeError → 3 failures
- `KanbanError` not caught; only `ValueError`/`FileNotFoundError` → 4 "Did not raise" failures

Commit: `8ddd2bb9` — serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py (512 lines)
[[2026-04-24]]
## Builder Notes
- Scope reviewed: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py and serve/mcp-kanban/src/owlbear_mcp_kanban/server.py.
- RED verification rerun via quality-runner did not reach adapter assertions. Fixture setup fails at KanbanEngine init with ConfigError: agent_map missing status entries for all board statuses.
- Evidence: failure occurs in app_ctx_with_mock_agent_view when loading _CONFIG_YAML lacking required agent_map keys.
- Result: Test assumptions are currently infeasible against the active engine config contract, so GREEN verification cannot be completed.
- test-writer: update fixture config in test_mcp_mutation_tools_1087.py to include a valid agent_map for all statuses, then rerun RED and requeue builder.
[[2026-04-24]]
## Test-Writer Notes (revision)
- Test file: serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py
- Commit: 1c85a4ed — fixture fix + test bug fix

### Changes made
1. **Fixture fix**: Added `agent_map` for all 7 statuses to `_CONFIG_YAML` in both `test_mcp_mutation_tools_1087.py` and `test_mcp_read_tools.py`. `_validate_engine_config` (added since original RED write) requires every status in `agent_map`; blank `{}` caused `ConfigError` at `KanbanEngine.__init__`.
2. **Test bug fix**: `test_create_task_forwards_title` was raising `IndexError` because `args[0]` was accessed on an empty tuple (adapter passes `title` as keyword, not positional). Fixed to `call.args[0] if call.args else call.kwargs.get("title")`.

### Current state: 22/22 PASS (adapter pre-implemented)
After fixing the fixture, all 22 tests pass. The adapter in `server.py` was updated (in a different task/session, prior to this builder attempt) to:
- Call `engine.agent_view().create_task()` (not `engine.create_task()` directly)
- Call `engine.agent_view().edit_task()` with all 13 params
- Map `KanbanError` → `ToolError` with `user_message`
- Exclude `status` from `create_task` signature (D50)
All AC lines are satisfied by the current adapter implementation.

### For builder
Tests are GREEN — verify all 22 pass and advance to review. No code changes needed to `server.py`.

### AC Coverage
| AC | Status |
|----|--------|
| create_task: 6 params forwarded to AgentView | 7 tests PASS |
| create_task: no status param (D50) | 1 test PASS |
| create_task: SingleTaskResponse returned | 1 test PASS |
| create_task: dep validation → ToolError (AC24) | 1 test PASS |
| edit_task: all 13 params forwarded | 2 tests PASS |
| edit_task: SingleTaskResponse returned | 1 test PASS |
| edit_task: body+append_body → ToolError (AC14) | 1 test PASS |
| edit_task: archival_reason on non-archived → ToolError | 1 test PASS |
| edit_task: archival_refs on non-archived → ToolError | 1 test PASS |
| edit_task: no-op → ToolError | 1 test PASS |
| KanbanError → ToolError with user_message | 4 tests PASS |

[[2026-04-24]]
## Builder Notes
- Validation only: no source edits required; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` already satisfies AC per revised Test-Writer notes.
- Tests: 22/22 passed in `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py` (quality-runner scoped).
- Lint: ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`.
- Coverage: 41% on `owlbear_mcp_kanban.server` in scoped run; no builder code changes in this pass.
- Evidence summary: adapter contract behaviors and KanbanError→ToolError mapping are verified by the 22 AC-linked tests, all green.
