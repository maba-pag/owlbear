---
id: 538
title: Verify structuredContent behavior for KanbanTask MCP tools
status: archived
priority: medium
created: 2026-04-02 05:25:08.426284+02:00
updated: 2026-04-02 17:46:06.040935+02:00
started: 2026-04-02 17:45:56.763996+02:00
completed: 2026-04-02 17:45:56.763996+02:00
tags:
- scope:mcp
- type:test
- phase-2
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria

- [ ] Add a `TestFromAC_StructuredContent` test class in `packages/mcp-kanban/tests/test_integration.py`
- [ ] `show_task` test: create a task, call `show_task` through MCP client, assert `CallToolResult.structuredContent` is a non-None dict containing at minimum keys `id` (int), `title` (str), `status` (str), and `class` (alias key, NOT `class_`)
- [ ] `move_task` test: create a task, call `move_task` through MCP client, assert `CallToolResult.structuredContent` is a non-None dict with `status` matching the target status
- [ ] `pick_task` test: add `pick_task` to `_make_test_server` add_tool calls; create an unclaimed task; call `pick_task` with no filters; assert `CallToolResult.structuredContent` is a non-None dict with `id` and `title` keys
- [ ] All tests use `@pytest.mark.integration` and `@pytest.mark.asyncio(loop_scope="function")`
- [ ] All tests follow existing `_make_test_server` + `create_connected_server_and_client_session` fixture pattern

## Notes for builder

- `research` tag removed: prior research confirms FastMCP auto-populates `structuredContent` for Pydantic model returns (see `docs/research/mcp-kanban-outputschema-annotations.md` L110). No new research needed.
- These tests verify end-to-end MCP protocol behavior (structuredContent in CallToolResult), NOT outputSchema registration (already covered by `tests/test_mcp_kanban_kanbantask_model_495.py`).
- `_make_test_server` creates a fresh FastMCP instance. The production `outputSchema` override at `server.py` L506-509 does NOT propagate. FastMCP auto-derives schema from KanbanTask return type (also uses `by_alias=True` internally). If structuredContent assertions fail, this divergence is the likely root cause: document it and create a follow-up.
- `pick_task` defaults to the first unclaimed task across all statuses. Test setup: create one task (lands in `ideation` per minimal config). `pick_task` with no filters should find it.

## Context
Gap identified during #477 arch review. The original task's Update section included "Return structuredContent alongside text content" as an AC item. This was never explicitly verified or tested. server.py tools return KanbanTask Pydantic models with outputSchema set (L502-509), but no test validates that the MCP protocol response includes structuredContent.

[[2026-04-02]] Thu 08:09
## Architecture Review
**Verdict:** APPROVED
**DR Verification:** N/A. Task tagged research but originated from #477 arch review gap, not from a T3 research workflow. Prior research docs (mcp-kanban-outputschema-annotations.md, create-task-status-parent-json.md) confirm FastMCP behavior. No DR required.

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add TestFromAC_StructuredContent class | Clear, specific location | Keep |
| show_task structuredContent assertion | Precise keys and types specified | Keep |
| move_task structuredContent assertion | Status match condition clear | Keep |
| pick_task structuredContent assertion | Setup specified in builder notes | Keep |
| Integration markers | Standard pattern | Keep |
| Fixture pattern | References existing code | Keep |

### Architecture Notes
- Tests belong in packages/mcp-kanban/tests/test_integration.py alongside existing integration tests
- Uses existing create_connected_server_and_client_session pattern (mcp.shared.memory)
- Test server created by _make_test_server is a fresh FastMCP instance. Production outputSchema override (server.py L506-509) does NOT propagate. FastMCP auto-derives schema from KanbanTask return type using by_alias=True internally, so structuredContent should match. If it doesn't, document the divergence.
- No new module or interface introduced. Pure test addition.
- Existing unit-level outputSchema tests (test_mcp_kanban_kanbantask_model_495.py) cover registration. This task covers protocol-level structuredContent in CallToolResult. No overlap.

### Changes Made
- Refined AC from vague research+conditional structure to concrete test assertions
- Removed research tag (research already done in prior docs)
- Added builder notes explaining test-server schema divergence risk and pick_task setup

### Dependencies
- None. Task #495 (KanbanTask model) and #477 (outputSchema) are already done.

### Challenge Results
- Challenger: reconsider
- Confidence in original: .70
- Key challenges: (1) _make_test_server schema divergence from production (production outputSchema override doesn't propagate); (2) pick_task test setup not specified; (3) existing test overlap concern
- Architect response: (1) Accepted, added builder note about divergence risk and fallback path; (2) Accepted, specified pick_task setup in AC notes; (3) Rebutted: existing tests cover outputSchema registration, not protocol-level structuredContent. Different verification layer.

[[2026-04-02]] Thu 10:40
## Test-Writer Notes
- Non-implementation task (tagged type:test) - no tests applicable.
- Passing through to builder.

[[2026-04-02]] Thu 15:39
## Builder Notes\n- Files changed: packages/mcp-kanban/tests/test_integration.py\n- Tests: 9 passed (3 new TestFromAC_StructuredContent + 6 existing)\n- Lint: ruff clean\n- Evidence: 9 passed in 7.34s; commit 543bb66, +71 lines\n- Changes: Added pick_task to imports and _make_test_server; TestFromAC_StructuredContent with 3 tests (show_task, move_task, pick_task structuredContent assertions)\n- Note: pick_task requires claim parameter (kanban-md pick returns error if --claim not set)

[[2026-04-02]] Thu 16:24
## Review Evidence

### Test Results

- TestFromAC_StructuredContent: 3 passed (2.45s)
- TestFromAC_Integration: 6 passed (4.16s)
- TestFromAC_Configuration: 1 passed (0.62s)
- Total: 10/10 passed, 0 failed

### Lint Results

- ruff check packages/mcp-kanban/tests/test_integration.py: All checks passed!

### Security

No issues. Pure test code: no secrets, no injection surface, no new dependencies.

### TestFromAC Coverage (Step 6.0)

type:test task -- builder wrote TestFromAC_StructuredContent from AC directly. Test-writer passed through.

AC: Add TestFromAC_StructuredContent class -- class exists at L270 -- COVERED
AC: show_task structuredContent id(int) title(str) status(str) class key -- test_show_task_structured_content, type checks on all 4 keys -- COVERED/STRONG
AC: move_task structuredContent status==target -- test_move_task_structured_content, exact match -- COVERED/STRONG
AC: pick_task add to _make_test_server, assert id and title keys -- test_pick_task_structured_content, key presence -- COVERED/ADEQUATE
AC: All tests integration marker + asyncio(loop_scope=function) -- all 3 tests have both markers -- COVERED
AC: All tests follow _make_test_server + create_connected_server_and_client_session -- verified -- COVERED

### TestFromAC Comparison (Step 6.2)

Skipped. type:test task. Test-writer passed through. No pre-existing TestFromAC_StructuredContent.

### Test Quality (Step 6.3)

- Assertion specificity: STRONG for show/move (type checks + exact value match); ADEQUATE for pick (key presence per AC spec)
- Negative paths: N/A -- protocol behavior test
- Test independence: STRONG -- each test uses fresh board_dir(tmp_path) + fresh server

### Builder Process Quality (Step 6.7)

Single Builder Notes section. CLEAN.

### Notes

pick_task AC says call with no filters but test passes claim=test-agent. Claim is operational (required by kanban-md), not a selection filter. Builder explained this. Acceptable.

### Verdict: PASS

Confidence: .94
