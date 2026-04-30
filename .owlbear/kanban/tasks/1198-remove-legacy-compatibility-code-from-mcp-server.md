---
id: 1198
title: Remove legacy compatibility code from MCP server
status: review
priority: needed
created: '2026-04-30 15:28:54.145200+00:00'
updated: '2026-04-30 21:47:50.360548+00:00'
tags:
- audit-kanban
- mcp-server
- debt-cleanup
parent:
depends_on:
- 1199
blocked: false
block_reason:
claimed_at: '2026-04-30 21:47:50.360548+00:00'
archival_reason:
archival_refs: []
---

## Objective
Remove legacy compatibility shims from MCP server.

## Files
- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py

## Change
Remove `_extract_task_id_compat()`, `_resolve_tool_id()`, legacy kwargs mapping. All active consumers (Copilot agents) use current API.

## AC
- [ ] No compat functions remain in server.py
- [ ] No legacy kwargs mapping code
- [ ] MCP server responds correctly to current tool calls
- [ ] Tests pass

## Finding: 4.6

[[2026-04-30]]

## Architecture Review
### AC (refined)
- [ ] `_extract_task_id_compat()` and `_resolve_tool_id()` deleted from server.py (td:0)
- [ ] `**legacy` catch-all kwargs removed from `move_task`, `edit_task`, `start_work`, `end_work` signatures (td:0)
- [ ] Legacy `title` kwarg handling removed from `edit_task` (td:0)
- [ ] Tool functions use `id: StrId` directly — no resolution indirection (td:1)
- [ ] Tests for removed functions (`test_server_1170.py` compat tests) deleted (td:0)
- [ ] Existing non-compat test suite passes (td:0)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: remove compat layer |
| Interface clarity | PASS | After refinement, scope is explicit — 3 functions + 4 signatures + title shim |
| Dependency correctness | PASS | 1199 (Remove KANBAN_TOOLS_EXCLUDE) archived/done |
| Module layering | PASS | All changes in server.py + associated test cleanup |
| TDD compliance | PASS | Test-writer will produce assertion confirming new signatures |
| KISS/YAGNI | PASS | Removing dead code |
| Premise challenge | PASS | VS Code Copilot agents use `id` parameter exclusively; legacy `task_id` path unused |
| Pattern consistency | PASS | Simplification toward clean signatures |
| Security surface | PASS | No new boundaries — reducing attack surface |
| Single domain | PASS | mcp-server only |

### Test Depth
- Max depth: td:1 (AC line 4 — verify signatures accept `id` without legacy fallback)
- Test-writer: PROCEED

### Challenge Results
- Challenger: SKIPPED — deletion task, max td:1, single-file scope, no design decisions
- Rationale: No architectural trade-offs to challenge; scope is mechanically verifiable

### Verdict: APPROVE
### Action Taken: Refined AC with explicit scope (title shim, test cleanup), annotated test depth, advancing to todo

[[2026-04-30]]
Architecture review complete. AC refined with explicit deletion scope: 2 compat functions, 4 **legacy signatures, title shim in edit_task, and associated test cleanup. Max td:1. Challenger skipped (mechanical deletion, no design decisions). Approved → todo.
[[2026-04-30]]
## Test-Writer Notes
- Test file: tests/test_server_1198.py
- Classes: TestFromAC_LegacyCompatRemoval
- Tests per category: happy 4, edge 0, error 0, boundary 0
- Total: 4 tests, all FAIL
- ruff: clean

### AC Coverage
| AC line | Test(s) |
|---------|---------|
| `_extract_task_id_compat()` and `_resolve_tool_id()` deleted (td:0) | skip |
| `**legacy` kwargs removed from 4 tool signatures (td:0) | skip |
| Legacy `title` kwarg handling removed from `edit_task` (td:0) | skip |
| Tool functions use `id: StrId` directly — no resolution indirection (td:1) | `test_move_task_uses_id_directly_no_legacy_kwargs`, `test_edit_task_uses_id_directly_no_legacy_kwargs`, `test_start_work_uses_id_directly_no_legacy_kwargs`, `test_end_work_uses_id_directly_no_legacy_kwargs` |
| compat tests in `test_server_1170.py` deleted (td:0) | skip |
| Existing non-compat suite passes (td:0) | skip |

### Failure evidence
All 4 fail with `AssertionError: {fn} still has **legacy catch-all` — VAR_KEYWORD parameter present in current signatures.
[[2026-04-30]]
## Builder Notes
- Implementation attempt (not committed): removed legacy compatibility helpers `_extract_task_id_compat` / `_resolve_tool_id`, removed `**legacy` from `move_task`/`edit_task`/`start_work`/`end_work`, removed legacy `title` shim in `edit_task`.
- Task-scoped RED->GREEN evidence: `tests/test_server_1198.py` moved from 4 failing to 4 passing; lint clean.
- Blocking mismatch found in durable suites after compat removal:
  - `tests/test_server_1170.py` imports removed compat functions (collection ImportError).
  - `tests/test_server_1172.py` and `tests/test_mcp_lifecycle_1173.py` still call `move_task(..., task_id=...)`, now raising `TypeError` after compat removal.
- This is a test-interface mismatch (tests still encode removed legacy API), so task is rejected to test-writer for suite update before builder can finalize and commit.
- Requested test-writer updates:
  - Remove compat-function tests/imports tied to `_extract_task_id_compat` and `_resolve_tool_id`.
  - Migrate legacy `task_id=` calls to `id=` in remaining server lifecycle tests.
  - Re-run non-compat MCP server suite and hand back to builder when green.

[[2026-04-30]]
## Test-Writer Notes
- Retry: surgical suite repair so builder can commit the uncommitted compat-removal implementation.
- **Changes made (test files only):**
  - `tests/test_server_1170.py`: removed imports of `_extract_task_id_compat` and `_resolve_tool_id`; deleted `TestFromAC_ExtractTaskIdCompat` and `TestFromAC_ResolveToolId` classes; deleted `test_legacy_title_becomes_append_body_when_no_body` (tests removed legacy title shim); updated module docstring.
  - `tests/test_server_1172.py`: migrated 7× `move_task(ctx, task_id="1", ...)` → `move_task(ctx, id="1", ...)`.
  - `tests/test_mcp_lifecycle_1173.py`: migrated 3× `move_task(ctx, task_id="1", ...)` → `move_task(ctx, id="1", ...)`.
- **Result:** 72 passed, 0 failed (including `test_server_1198.py` 4 tests — all green against builder's uncommitted server.py).
- **ruff:** clean on all three files.
- **Builder action:** commit the uncommitted server.py changes.
[[2026-04-30]]
## Builder Notes
- Implementation: removed legacy compatibility layer from [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py).
- Fixes applied:
  - Deleted `_extract_task_id_compat()` and `_resolve_tool_id()`.
  - Removed `**legacy` catch-all kwargs from `move_task`, `edit_task`, `start_work`, `end_work` signatures.
  - Removed legacy `title` kwarg shim path in `edit_task`.
  - Switched lifecycle tool paths to use `id: StrId` directly (no task-id resolution indirection).
- Commit: `706cc2f7` with message `refactor: remove MCP legacy compatibility shims (#1198, builder)`.
- Test evidence (quality-runner, scoped): 114 passed, 0 failed, 0 skipped.
- Lint evidence (quality-runner): ruff clean (0 violations).
- Coverage evidence (quality-runner): `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` at 90%.
- Verification suite used:
  - [tests/test_server_1198.py](tests/test_server_1198.py)
  - [tests/test_server_1199.py](tests/test_server_1199.py)
  - [tests/test_server_1170.py](tests/test_server_1170.py)
  - [tests/test_server_1172.py](tests/test_server_1172.py)
  - [tests/test_mcp_lifecycle_1173.py](tests/test_mcp_lifecycle_1173.py)
  - [tests/test_mcp_server_1090.py](tests/test_mcp_server_1090.py)
  - [tests/test_mcp_kanban_1196.py](tests/test_mcp_kanban_1196.py)
  - [tests/test_engine_lazy_agent_map_1221.py](tests/test_engine_lazy_agent_map_1221.py)
  - [serve/mcp-kanban/tests/test_mcp_server_1090.py](serve/mcp-kanban/tests/test_mcp_server_1090.py)
  - [serve/mcp-kanban/tests/test_mcp_create_dr_1182.py](serve/mcp-kanban/tests/test_mcp_create_dr_1182.py)

## Post-task Reflection
- Initial scoped verification passed but only yielded 82% coverage on the touched module; expanding to additional existing server-focused suites was required to satisfy the gate.
- Keeping the commit scoped to the single builder-owned source file avoided mixing in unrelated dirty-tree changes.
- Existing test-writer updates in task body provided clear handoff context, which reduced implementation churn and allowed a direct closeout.
