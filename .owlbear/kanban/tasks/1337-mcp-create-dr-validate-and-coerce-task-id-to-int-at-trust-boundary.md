---
id: 1337
title: 'MCP create_dr: validate and coerce task_id to int at trust boundary'
status: in-progress
priority: critical
created: 2026-05-04T15:00:05.722955+00:00
updated: 2026-05-04T15:48:07.899996+00:00
tags:
- sync-blocker
- security
- mcp-kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-04T15:48:07.899996+00:00
archival_reason:
archival_refs: []
---

## Context

`serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` (L369–387) accepts task_id as raw string. `serve/kanban/src/owlbear_kanban/decisions.py` expects int and uses it in filename construction. Non-numeric input is never rejected — path traversal possible.

## Acceptance Criteria

1. MCP create_dr handler coerces task_id to int; non-numeric raises ValueError with clear message
2. Integration test proves path-traversal payloads are rejected (e.g., "../etc/passwd", "1; rm -rf", "abc")
3. All red tests in test_mcp_kanban_1196 and test_mcp_create_dr_1182 pass
4. Existing valid integer task_ids continue to work

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/kanban/src/owlbear_kanban/decisions.py`

## Source

Finding 2 in `.owlbear/research/kanban-mcp-deployment-audit.md`
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_mcp_create_dr_coerce_1337.py
- Classes: TestFromAC_ErrorMessageClarity, TestFromAC_IntegrationRejection, TestFromAC_RegressionValidIds
- Tests per category: happy 1, edge 0, error 6, boundary 1
- Total: 8 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Test(s) |
|----|---------|
| AC1: non-numeric raises ToolError with clear message | test_non_numeric_string_error_message_is_clear, test_shell_injection_error_message_is_clear, test_path_traversal_error_message_is_clear |
| AC2: integration — path-traversal payloads rejected (no mock) | test_integration_etc_passwd_traversal_rejected, test_integration_shell_injection_rejected, test_integration_alpha_string_rejected, test_integration_decisions_pending_unchanged_after_traversal |
| AC3: existing tests pass — covered by test_mcp_kanban_1196 and test_mcp_create_dr_1182 (no new tests needed) | — |
| AC4: valid numeric string forwarded as int | test_valid_numeric_string_forwarded_as_int |

### RED Failure Summary

- AC1 tests: no validation in current code → `pytest.raises(ToolError, match=...)` fails with DID NOT RAISE
- Integration tests (`../etc/passwd`): os.open raises FileNotFoundError (not ToolError) → test ERRORS
- Integration tests (`1; rm -rf`, `abc`): ToolError IS raised (via engine NotFoundError path) but message says "not found", not matching `integer|numeric|task_id` → match fails → RED FAIL
- AC4 regression guard: task_id='99' forwarded as str '99', not int 99 → `isinstance(..., int)` fails → RED FAIL

One test (literal int regression guard) passed in RED — removed per TDD RED rules.
Commit: 45b626a9