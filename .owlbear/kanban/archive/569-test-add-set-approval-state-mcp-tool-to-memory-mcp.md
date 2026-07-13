---
id: 569
title: 'Test: Add set_approval_state MCP tool to memory-mcp'
status: archived
priority: medium
created: 2026-04-03 10:57:25.825073+02:00
updated: 2026-04-03 15:37:05.690552+02:00
started: 2026-04-03 15:36:45.584782+02:00
completed: 2026-04-03 15:36:45.584782+02:00
tags:
- scope:agents
- phase-2
- test
depends_on:
- 525
class: standard
archival_reason: completed
archival_refs: []
---

TDD RED phase for #529. Write failing tests for set_approval_state tool before implementation.

## Acceptance Criteria

### File and structure
- [ ] Test file: tests/test_set_approval_state_569.py
- [ ] Reuses helper pattern from test_memory_tools_556.py (_make_conn, _make_app_ctx, _make_mcp_ctx, _insert_entry, _get_tool_annotations)
- [ ] All tests use in-memory SQLite (no disk files)
- [ ] All tests FAIL in RED phase (ImportError until builder implements set_approval_state in tools.py via #529)

### TestFromAC_ValidTransitions (3 tests)
- [ ] AC-T1: pending to approved succeeds (approval_state becomes 'approved' in DB)
- [ ] AC-T2: pending to deleted succeeds (approval_state becomes 'deleted' in DB)
- [ ] AC-T3: deleted to pending succeeds (approval_state becomes 'pending' in DB)

### TestFromAC_InvalidTransitions (6 tests, full 3x3 matrix minus 3 valid)
- [ ] AC-T4: approved to pending returns soft error starting with "error:"
- [ ] AC-T5: approved to deleted returns soft error starting with "error:"
- [ ] AC-T6: deleted to approved returns soft error starting with "error:"
- [ ] AC-T7: pending to pending (same-state) returns soft error starting with "error:"
- [ ] AC-T8: approved to approved (same-state) returns soft error starting with "error:"
- [ ] AC-T9: deleted to deleted (same-state) returns soft error starting with "error:"

### TestFromAC_ErrorFormat (1 test)
- [ ] AC-T10: soft error message contains "transition from" and "is not allowed" substrings

### TestFromAC_Timestamps (3 tests)
- [ ] AC-TS1: updated_at refreshed on every successful transition (differs from pre-existing value)
- [ ] AC-TS2: deleted_at set to non-null UTC ISO timestamp when transitioning to 'deleted'
- [ ] AC-TS3: deleted_at cleared to NULL when transitioning from deleted to pending

### TestFromAC_Errors (2 tests)
- [ ] AC-E1: ToolError raised for nonexistent entry_id (consistent with mark_for-deletion)
- [ ] AC-E2: Invalid new-state value (e.g., "archived") does not succeed silently (either ToolError or soft error)

### TestFromAC_ReturnValue (1 test)
- [ ] AC-R1: Successful transition returns non-empty str

### TestFromAC_ToolAnnotations (2 tests)
- [ ] AC-A1: set_approval_state discoverable via mcp._tool_manager.list_tools()
- [ ] AC-A2: Annotations: readOnlyHint=False, idempotentHint=False, destructiveHint=True

### TestFromAC_ValidTransitionsConstant (1 test)
- [ ] AC-V1: _VALID_TRANSITIONS is a frozenset containing exactly {("pending","approved"), ("pending","deleted"), ("deleted","pending")}

### TestFromAC_CrossCutting (1 test)
- [ ] AC-CC1: server.py __all__ includes "set_approval_state"

### TestFromAC_CrossToolInteraction (2 tests)
- [ ] AC-I1: mark_for-deletion then set_approval_state(entry_id, "pending") roundtrip: entry becomes pending, deleted_at cleared to NULL
- [ ] AC-I2: set_approval_state(entry_id, "deleted") then mark_for-deletion(entry_id): no error (mark_for-deletion is idempotent on already-deleted entries)

## Architecture Review
**Verdict:** APPROVE
**DR Verification:** N/A (test task for #529; DR #387 verified in #529 arch review)

### AC Assessment
AC was completely unscoped ("Write failing tests"). Rewrote with 22 specific test cases across 10 test classes covering: full 3x3 transition matrix, timestamps, error handling, cross-tool interaction, ToolAnnotations, and _VALID_TRANSITIONS constant.

### Architecture Notes
Follows test_memory_tools_556.py pattern (helpers, in-memory SQLite, TestFromAC_ class naming). Cross-tool interaction tests validate dual-path design (set_approval_state vs mark_for-deletion) per research doc sec 3B. Existing AST cross-cutting tests in test_memory_tools_525.py cover asyncio.to_thread structurally.

### Changes Made
- Rewrote task body with 22 specific test AC items across 10 test classes

### Dependencies
- Verified: #525 (archived)
- Downstream: #529 depends_on [525, 569]

### Challenge Results
- Challenger: reconsider (.68)
- Accepted: C1 cross-tool interaction, C2 invalid new-state, C3 message format, C5 full 3x3 matrix
- Rejected: C4 AST over-specification (existing tests cover it)
- Revised confidence: .88

[[2026-04-03]] Fri 11:44
## Test-Writer Notes
- Test file: tests/test_set_approval_state_569.py
- Classes: TestFromAC_ValidTransitions, TestFromAC_InvalidTransitions, TestFromAC_ErrorFormat, TestFromAC_Timestamps, TestFromAC_Errors, TestFromAC_ReturnValue, TestFromAC_ToolAnnotations, TestFromAC_ValidTransitionsConstant, TestFromAC_CrossCutting, TestFromAC_CrossToolInteraction
- Tests per category: valid transitions 3, invalid transitions 6, error format 1, timestamps 3, errors 2, return value 1, annotations 2, constant 1, cross-cutting 1, cross-tool interaction 2
- Total: 22 tests, all FAIL (ImportError on _VALID_TRANSITIONS and set_approval_state) checked
- ruff: clean
- AC coverage:
  AC-T1: test_pending_to_approved_succeeds (valid)
  AC-T2: test_pending_to_deleted_succeeds (valid)
  AC-T3: test_deleted_to_pending_succeeds (valid)
  AC-T4: test_approved_to_pending_returns_soft_error (invalid)
  AC-T5: test_approved_to_deleted_returns_soft_error (invalid)
  AC-T6: test_deleted_to_approved_returns_soft_error (invalid)
  AC-T7: test_pending_to_pending_returns_soft_error (invalid)
  AC-T8: test_approved_to_approved_returns_soft_error (invalid)
  AC-T9: test_deleted_to_deleted_returns_soft_error (invalid)
  AC-T10: test_invalid_transition_message_format (error format)
  AC-TS1: test_updated_at_refreshed_on_successful_transition (timestamps)
  AC-TS2: test_deleted_at_set_on_transition_to_deleted (timestamps)
  AC-TS3: test_deleted_at_cleared_on_transition_from_deleted_to_pending (timestamps)
  AC-E1: test_toolerror-raised_for-nonexistent_entry_id (errors)
  AC-E2: test_invalid_new-state_does_not_succeed_silently (errors)
  AC-R1: test_successful_transition_returns_non_empty_str (return value)
  AC-A1: test_set_approval_state_discoverable_via_tool_manager (annotations)
  AC-A2: test_set_approval_state_annotations (annotations)
  AC-V1: test_valid_transitions_is_frozenset_with-exactly_three_pairs (constant)
  AC-CC1: test_server-all_includes_set_approval_state (cross-cutting)
  AC-I1: test_mark_for-deletion_then_set_approval_state_pending_roundtrip (cross-tool)
  AC-I2: test_set_approval_state_deleted_then_mark_for-deletion_is_idempotent (cross-tool)

[[2026-04-03]] Fri 14:38
## Builder Notes
- Files changed: packages/mcp-memory/src/owlbear_mcp_memory/tools.py, server.py
- Added: _VALID_TRANSITIONS frozenset (3 pairs), set_approval_state tool
- Tests: 22 passed, ruff clean
- Fixes applied: None

[[2026-04-03]] Fri 14:44
## Review Evidence
See docs/scratch/569-reviewer.md for full evidence.

[[2026-04-03]] Fri 14:59
## Docs Gate test

[[2026-04-03]] Fri 14:59
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | New tool in mcp-memory; copilot-instructions.md covers package-level conventions only, not individual tool APIs |
| 2 | Docstrings | Yes | Pass | set_approval_state has complete docstring (tools.py lines 231-237); _VALID_TRANSITIONS is a typed constant -- no docstring needed |
| 3 | docs/sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | MCP tool addition, no CLI changes |
| 5 | Research doc | No | N/A | Test task; research doc scoped to parent feature #529 |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/569-reviewer.md

[[2026-04-03]] Fri 15:36
## Audit
### AC Verification
All 22 AC items verified via passing tests and code spot-check. Full AC table: test file at tests/test_set_approval_state_569.py has 10 test classes covering valid transitions (3), invalid transitions (6), error format (1), timestamps (3), errors (2), return value (1), annotations (2), constant (1), cross-cutting (1), cross-tool interaction (2).

### Test Results
- pytest (scoped): 22 passed, 0 failed
- pytest (full suite): 3297 passed, 239 failed (all failures in mcp-knowledge, unrelated to task)
- ruff: clean

### Upstream Commit Check
- Builder commit: b20b9ef
- Test file NOT committed by test-writer, committed by auditor as orphan: 598fa4c

### AC Quality Score: 5
Exceptional AC: 22 specific test cases across 10 classes with full 3x3 matrix. Zero improvisation.

### Deduction breakdown: none
### Confidence: 1.0
### Action: archive

[[2026-04-03]] Fri 15:37
## Commits
598fa4c test: add set_approval_state tests (#569, auditor) - orphaned test file
