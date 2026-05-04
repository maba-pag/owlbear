---
id: 1337
title: Validate MCP task IDs at every task endpoint trust boundary
status: in-progress
priority: critical
created: 2026-05-04T15:00:05.722955+00:00
updated: 2026-05-04T20:22:41.389259+00:00
tags:
- sync-blocker
- security
- mcp-kanban
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The MCP server accepts task IDs through several tool handlers and currently relies on loose `StrId` coercion or raw strings. `create_dr` is the highest-risk endpoint because the ID becomes part of a decision-request filename, but the same trust-boundary rule should apply to every MCP task-id endpoint before values reach engine glob lookup or filesystem-backed helpers.

## Acceptance Criteria

1. Add a shared MCP ID parser/coercer used by every task-id accepting endpoint: `show_task` fallback path, `move_task`, `edit_task`, `start_work`, `end_work`, and `create_dr`.
2. Accept JSON numbers and positive decimal strings for VS Code schema-cache compatibility.
3. Reject empty, zero, negative, non-decimal, path-like, shell-like, whitespace-padded, and mixed strings before calling the engine.
4. Rejections raise a clear `ToolError` mentioning the relevant id field and positive integer requirement.
5. Rejected IDs do not create DR files, mutate task state, or fall through to raw engine glob/path lookup.
6. Valid numeric values continue to work for all MCP task tools.
7. Existing `create_dr` coercion tests remain covered, but are broadened or complemented so the shared parser cannot regress on other endpoints.

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`
- `serve/kanban/src/owlbear_kanban/decisions.py`
- `tests/test_mcp_create_dr_coerce_1337.py`
- `tests/test_mcp_kanban.py`

## Audit Evidence

- `create_dr` accepts raw `task_id: str`; non-numeric input is not rejected at the MCP boundary.
- `StrId` only coerces ints to strings; it does not validate positive decimal task IDs.
- Raw engine lookup has glob fallback behavior, so malformed IDs must be stopped before engine calls.

## Test-Writer Notes

- Existing RED file: `tests/test_mcp_create_dr_coerce_1337.py`.
- Preserve the integration tests that assert malformed `create_dr` IDs leave `decisions/pending` unchanged.
- Add parser/table tests once, then at least one endpoint-level proof for each task tool family.

## Source

Deployment audit reconciliation, 2026-05-04.


## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: validate task IDs at MCP trust boundary |
| Interface clarity | PASS | Shared parser input (str\|int) → validated int; ToolError on reject |
| Dependency correctness | PASS | No external dependencies; self-contained within mcp-kanban |
| Module layering | PASS | Validation at MCP boundary layer, before engine calls — correct placement |
| TDD compliance | PASS | RED file exists: `tests/test_mcp_create_dr_coerce_1337.py` |
| KISS/YAGNI | PASS | Single shared function, minimal scope, no speculative features |
| Premise challenge | PASS | Real security gap: path traversal and shell injection reach filesystem |
| Pattern consistency | PASS | Extends existing `StrId` / `BeforeValidator` pattern in server.py |
| Security surface | PASS | This IS the security fix; AC3 enumerates all rejection categories |
| Single domain | PASS | MCP server boundary validation only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| Shared parser receives valid "42" | None (happy path) | — | — | Returns int 42 |
| Shared parser receives "../foo" | Path traversal attempt | ToolError | AC4 | Clear error message |
| Shared parser receives "0" / "-1" | Non-positive integer | ToolError | AC4 | Clear error message |
| Valid ID reaches engine, task not found | Normal not-found | KanbanError→ToolError | Existing | "Task not found" |

### Challenge Results
- Challenger: reconsider (confidence 0.47)
- Architect response: REBUTTED — concerns addressed by existing AC text (AC6/AC7 handle regression, test-writer notes handle proof breadth, list_tasks.ids already int-typed at schema level). See evaluation above.

### Test Depth
- AC1: shared parser used by all endpoints (td:2) — multiple integration points
- AC2: accept JSON numbers and positive decimal strings (td:1) — happy-path coercion
- AC3: reject invalid inputs (td:2) — many edge cases per category
- AC4: clear ToolError with field/requirement (td:2) — message format per rejection
- AC5: rejected IDs don't create files/mutate state (td:2) — side-effect verification
- AC6: valid numeric values continue to work (td:1) — regression happy-path
- AC7: existing tests preserved and broadened (td:1) — test structure
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Approved to todo. AC is verifiable, architecture sound (boundary validation with shared parser), RED tests exist. Security-critical sync-blocker with clean single-domain scope.
[[2026-05-04]]
Architecture review complete. All 10 criteria PASS. Challenger rebutted (concerns addressed by existing AC text). Test depth: max td:2, test-writer PROCEED. Approved to todo.
[[2026-05-04]]
## Test-Writer Notes
- Test file: tests/test_mcp_task_id_parser_1337.py
- Existing RED file preserved: tests/test_mcp_create_dr_coerce_1337.py (9 tests, all FAIL — unchanged)
- Classes: TestFromAC_SharedParserContract, TestFromAC_EndpointBoundaryProofs, TestFromAC_NoSideEffects, TestFromAC_ValidIdsRegression
- Tests per category: happy 8, edge 2, error 18, boundary 1 → 29 new tests
- Total new: 29 tests, all FAIL (ImportError at collection — parse_task_id not yet in server.py)
- ruff: clean

AC coverage table:
| AC | Tests |
|----|-------|
| AC1 shared parser importable | TestFromAC_SharedParserContract (all — import fails = RED proof) |
| AC1 wired to all endpoints | TestFromAC_EndpointBoundaryProofs (6 tests, one per endpoint family) |
| AC2 accept int + decimal string | test_accepts_positive_int, test_accepts_positive_decimal_string |
| AC3 reject all invalid categories | test_rejects_* (10 tests: empty, zero×2, neg×2, alpha, path×2, shell, whitespace, mixed) |
| AC4 clear ToolError message | test_error_message_mentions_field_name_default, test_error_message_mentions_custom_field_name; all endpoint tests also assert match pattern |
| AC5 no side effects | TestFromAC_NoSideEffects (move_task, edit_task, start_work each verified) |
| AC6 valid IDs regression | TestFromAC_ValidIdsRegression (5 tests — one per endpoint) |
| AC7 breadth beyond create_dr | All TestFromAC_EndpointBoundaryProofs + SharedParserContract tests |
[[2026-05-04]]
## Builder Notes
- Files changed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Implementation applied: added shared `parse_task_id` and wired it into `show_task`, `create_dr`, `move_task`, `edit_task`, `start_work`, and `end_work` to reject invalid IDs before engine/filesystem calls.
- RED verification (before edits): quality-runner reported 8 failed tests + 1 collection error (`parse_task_id` import missing) across:
  - tests/test_mcp_task_id_parser_1337.py
  - tests/test_mcp_create_dr_coerce_1337.py
- GREEN verification (after edits): quality-runner scoped run results:
  - 37 passed
  - 1 failed: `tests/test_mcp_task_id_parser_1337.py::TestFromAC_NoSideEffects::test_rejected_start_work_does_not_claim_any_task`
  - ruff clean
  - coverage (scoped module): `owlbear_mcp_kanban.server` 56%
- Failure analysis: remaining failure is test interface mismatch, not endpoint behavior:
  - Test asserts `post_task.claimed` on `app_ctx.engine.show_task(...)` return value.
  - Engine `Task` model does not expose `.claimed`; canonical field is `.claimed_at`.
  - Raised error: `AttributeError: 'Task' object has no attribute 'claimed'. Did you mean: 'claimed_at'?`

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update `test_rejected_start_work_does_not_claim_any_task` to assert unclaimed state via the engine `Task` contract (`claimed_at is None`) instead of non-existent `.claimed`. | tests/test_mcp_task_id_parser_1337.py | quality-runner scoped run failure: `AttributeError: 'Task' object has no attribute 'claimed'` |

- No commit performed because task is rejected back to test-writer for interface-contract correction.
[[2026-05-04]]
## Test-Writer Notes
- Retry: fixed `test_rejected_start_work_does_not_claim_any_task` to assert unclaimed state via `post_task.claimed_at is None` instead of non-existent `.claimed` attribute (builder Required Follow-up #1).
- All 38 tests PASS against current implementation (builder's parse_task_id already handles the corrected assertion).
- ruff: clean
- Builder skip: test-only retry, all tests green — advancing directly to review.