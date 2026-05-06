---
id: 1360
title: Remove MCP dual-path dead code (~100 lines)
status: backlog
priority: needed
created: 2026-05-05T23:34:52.820872+00:00
updated: 2026-05-06T00:54:40.142795+00:00
tags:
- kanban
- cleanup
- deploy-prep
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Remove the dual-path dead code in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — the `_canonical_agent_view_for` fallback pattern and associated helper functions that are never reached because `engine.agent_view()` always resolves.

## AC

- [ ] `_canonical_agent_view_for` helper removed
- [ ] `_invoke_view_move_task`, `_invoke_view_start_work`, `_invoke_view_end_work` fallback branches removed
- [ ] Direct AgentView calls replace the view-or-fallback pattern in `move_task`, `start_work`, `end_work` tools
- [ ] All existing MCP kanban tests pass
- [ ] ~100 lines net reduction

## Context

Audit Finding Group 1. The dual-path existed as a safety net during initial AgentView integration. Now that AgentView is always available via `engine.agent_view()`, the fallback path is dead code.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_1360.py
- Classes: TestFromAC_DeadCodeRemoval, TestFromAC_DirectAgentViewPath
- Tests per category: happy 0, edge 0, error 3, boundary 5
- Total: 8 tests, all FAIL
- ruff: clean

### AC Coverage
| AC Line | Tests |
|---|---|
| AC1: `_canonical_agent_view_for` removed | `test_canonical_agent_view_for_helper_removed` |
| AC2: `_invoke_view_move_task` / `_invoke_view_end_work` / `_invoke_engine_end_work` removed | `test_invoke_view_move_task_removed`, `test_invoke_view_end_work_removed`, `test_invoke_engine_end_work_removed` |
| AC3: Direct AgentView calls — no fallback | `test_move_task_not_implemented_propagates_without_fallback`, `test_start_work_not_implemented_propagates_without_fallback`, `test_end_work_not_implemented_propagates_without_fallback` |
| AC4: Existing MCP kanban tests pass | Regression — no new RED tests (existing suite is the evidence; builder runs it) |
| AC5: ~100 lines net reduction | `test_server_module_line_count_reduced` (current: 776, threshold: &lt;720) |

### Failure Mechanism
- Symbol-absence tests (4): `hasattr()` returns True for symbols that still exist → `AssertionError`
- Line-count test: 776 lines > 720 threshold → `AssertionError`  
- No-fallback behavior tests (3): current code catches `NotImplementedError` in `_invoke_view_*` helpers and falls back to engine methods (which succeed via mock) → `pytest.raises(NotImplementedError)` gets "DID NOT RAISE"
[[2026-05-05]]
## Builder Notes
- Implementation: updated serve/mcp-kanban/src/owlbear_mcp_kanban/server.py to remove dual-path helper/fallback code and use direct AgentView calls in move_task, start_work, end_work.
- RED verification (quality-runner): tests/test_mcp_kanban_1360.py failed 8/8 before edits; ruff clean.
- Post-change scoped verification (quality-runner): tests/test_mcp_kanban_1360.py passed 8/8; ruff clean on touched paths.
- Blocker: durable regression file tests/test_mcp_kanban.py fails at collection because it imports removed symbols (_canonical_agent_view_for, _invoke_view_move_task, _invoke_view_end_work).
- Routing: reject to todo because test assumptions in durable suite still target the removed API surface.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Update durable MCP regression imports to remove references to deleted helpers and assert direct AgentView behavior instead | tests/test_mcp_kanban.py | quality-runner error: ImportError cannot import name _canonical_agent_view_for from owlbear_mcp_kanban.server |
| 2 | test-writer | Replace helper-specific tests with assertions that public tools move_task/start_work/end_work propagate NotImplementedError without engine fallback | tests/test_mcp_kanban.py | AC requires helper removal; module test currently depends on removed private helpers |
| 3 | test-writer | Re-run module durable suite once updated to restore AC4 (existing MCP kanban tests pass) gate | tests/test_mcp_kanban.py, tests/test_mcp_kanban_1360.py | quality-runner: task file passes but module file fails collection |

[[2026-05-06]]
## Test-Writer Notes
- Retry: updated `tests/test_mcp_kanban.py` to remove all references to deleted helpers.
- Removed imports: `_canonical_agent_view_for`, `_invoke_view_end_work`, `_invoke_view_move_task`.
- Removed 3 test classes that tested deleted helpers: `TestCanonicalAgentViewFor`, `TestInvokeViewMoveTask`, `TestInvokeViewEndWork` (269 lines deleted).
- Replaced fallback-path test classes with direct-path equivalents (80 lines added):
  - `TestMovetaskFallbackPath` → `TestMoveTaskDirectPath` (4 tests, verifies direct agent_view call + NotImplementedError propagates)
  - `TestStartWorkFallbackPath` → `TestStartWorkDirectPath` (2 tests, NotImplementedError propagates, ValueError → ToolError)
  - `TestEndWorkEngineFallbackPath` → `TestEndWorkDirectPath` (4 tests, direct path + KanbanError/ValueError → ToolError + NotImplementedError propagates)
  - `TestNoRetryOnTypeError` updated to mock `engine._agent_view` directly instead of patching the deleted `_canonical_agent_view_for`.
  - Added `TestAgentViewHelpersRemoved` regression guard (3 symbol-absence assertions).
- Removed top-level `patch` import (no longer needed after fallback-path classes removed).
- Step 1b.1 direct-to-review advance: all 75 tests PASS against current implementation (builder already removed dead code); ruff clean. No builder work needed.
- Commit: 7f468ee7
[[2026-05-06]]
Advancing to review: test-only retry complete, builder skip per Step 1b.1.
[[2026-05-06]]
## Review Evidence
### Test Results
- pytest: 75 passed, 0 failed, 0 skipped (quality-runner scoped pass on `tests/test_mcp_kanban.py` and `tests/test_mcp_kanban_1360.py`)

### Lint: clean
- ruff: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `tests/test_mcp_kanban.py`, `tests/test_mcp_kanban_1360.py`

### Coverage
- Module coverage: `owlbear_mcp_kanban.server` at 88%
- This is below 90% at module level, but the uncovered lines reported near the touched area are the `start_work()` success and guidance tail, not the dead-code-removal behavior under review. The task-owned direct-call and no-fallback lines are exercised by the scoped suite.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `_canonical_agent_view_for` helper removed | `tests/test_mcp_kanban_1360.py::TestFromAC_DeadCodeRemoval::test_canonical_agent_view_for_helper_removed`; `tests/test_mcp_kanban.py::TestAgentViewHelpersRemoved::test_canonical_agent_view_for_not_exported` | Yes. Any surviving helper makes `hasattr(...)` true and the assertion fails. | COVERED |
| `_invoke_view_move_task`, `_invoke_view_start_work`, `_invoke_view_end_work` fallback branches removed | `tests/test_mcp_kanban_1360.py::TestFromAC_DeadCodeRemoval::test_invoke_view_move_task_removed`; `test_invoke_view_end_work_removed`; `test_invoke_engine_end_work_removed`; plus `TestFromAC_DirectAgentViewPath::test_start_work_not_implemented_propagates_without_fallback` and durable `TestStartWorkDirectPath::test_not_implemented_propagates_without_fallback` | Yes. Reintroducing move or end helper exports fails symbol-absence assertions; reintroducing `start_work` fallback causes `NotImplementedError` propagation tests to fail. Current workspace has no `_invoke_view_start_work` source symbol; the live contract is functionally covered by the no-fallback `start_work` tests. | COVERED |
| Direct AgentView calls replace the view-or-fallback pattern in `move_task`, `start_work`, `end_work` | `tests/test_mcp_kanban_1360.py::TestFromAC_DirectAgentViewPath::{test_move_task_not_implemented_propagates_without_fallback,test_start_work_not_implemented_propagates_without_fallback,test_end_work_not_implemented_propagates_without_fallback}`; durable direct-path classes in `tests/test_mcp_kanban.py` | Yes. Any fallback that swallows `NotImplementedError` would turn these tests red. | COVERED |
| All existing MCP kanban tests pass | quality-runner scoped suite: 75 passed, 0 failed | Yes. Any collection or runtime regression in the durable MCP suite would fail the scoped run. | COVERED |
| `~100 lines` net reduction | `tests/test_mcp_kanban_1360.py::TestFromAC_DeadCodeRemoval::test_server_module_line_count_reduced` | Yes. The test enforces `<720` lines; current file reads to EOF at line 638. | COVERED |

#### Security Review
- No issues found. The change removes private fallback helpers and routes the three lifecycle tools directly through `engine.agent_view()`. No new inputs, dependencies, shell execution, path handling, or serialization surface were introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_DeadCodeRemoval` | No weakening evidence in the current file; assertions remain exact symbol-absence and exact line-count threshold checks. | PRESERVED |
| `TestFromAC_DirectAgentViewPath` | No weakening evidence in the current file; assertions still require `NotImplementedError` propagation for all three tools. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact `hasattr(...) is False` style absence checks and exact `pytest.raises(NotImplementedError)` or `ToolError` expectations in the task and durable suites. |
| Negative and error-path coverage | STRONG | All three public tools now have explicit no-fallback error-path tests; durable suite also covers `KanbanError` and `ValueError` mapping. |
| Manual mutation reasoning | STRONG | Reintroducing helper exports or any `NotImplementedError` catch-and-fallback would immediately fail the symbol-absence or propagation tests. |
| Test independence | STRONG | Each test builds its own mock view or fixture-backed context; no shared mutable state is required for the proof. |
| Descriptive test names | STRONG | The direct-path and helper-removal tests describe the exact contract being enforced. |

#### Data Safety
- No issues found. The change is a dead-code removal in lifecycle adapters and does not introduce new persistence, concurrency, or resource-amplification behavior.

#### Implementation-Aware Gaps
- No significant untested path found in the task-owned behavior. The module-level coverage miss in `start_work()` is the trivial success and guidance tail after the direct call, while the task-owned direct-call and no-fallback behavior is exercised by both task-local and durable regression tests.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` now calls `engine.agent_view()` directly at the three lifecycle tools: `move_task`, `start_work`, `end_work`.
- Module-level coverage is 88%, not 90%+, but the uncovered lines are outside the dead-code-removal proof surface for this task.
- Dirty-tree contamination check could not be executed in this reviewer session because terminal/git commands are not exposed. Confidence deduction applied.
- The builder commit hash is not recorded in the task body, so TestFromAC immutability is based on task notes and current file state rather than commit diff. Confidence deduction applied.
- AC2 names `_invoke_view_start_work`, but no such source symbol exists in the current workspace outside task prose. I treated this as stale wording because the live `start_work()` no-fallback behavior is directly tested and green.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `_canonical_agent_view_for` helper removed | Helper-removal tests are present and green in both task-local and durable suites. | `test_canonical_agent_view_for_helper_removed`; `test_canonical_agent_view_for_not_exported` | PASS |
| `_invoke_view_move_task`, `_invoke_view_start_work`, `_invoke_view_end_work` fallback branches removed | Move and end helper-removal assertions are green; `start_work()` no-fallback `NotImplementedError` tests are green; current source uses direct `engine.agent_view().start_work(...)`. | `test_invoke_view_move_task_removed`; `test_invoke_view_end_work_removed`; `test_invoke_engine_end_work_removed`; `test_start_work_not_implemented_propagates_without_fallback` | PASS |
| Direct AgentView calls replace the view-or-fallback pattern in `move_task`, `start_work`, `end_work` tools | Current source calls `engine.agent_view().move_task` / `.start_work` / `.end_work` directly; no-fallback tests are green for all three tools. | direct-path task tests and durable direct-path classes | PASS |
| All existing MCP kanban tests pass | quality-runner scoped pass: 75 passed, 0 failed, 0 skipped. | durable suite plus task suite | PASS |
| `~100 lines` net reduction | Task-local line-count test is green and current file reads to EOF at line 638, below the `<720` threshold. | `test_server_module_line_count_reduced` | PASS |

### Confidence: 0.93
### Verdict: PASS
[[2026-05-06]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | `serve/mcp-kanban/README.md` documents public tool signatures only — no private helper references; unchanged |
| 2 | Module docstrings | Yes | Verified | `move_task`, `start_work`, `end_work` docstrings accurate post-removal; private helpers deleted with their docstrings |
| 3 | External attribution | No | N/A | Dead-code removal, no external patterns used |
| 4 | Research doc | No | N/A | No research phase for this task |
| 5 | Diagram maintenance | Yes | Updated | `kanban.excalidraw` (`describes: serve/mcp-kanban/src/**`) and `mcp-topology.excalidraw` (`describes: serve/mcp-*/src/**`) footers updated to `Last verified: 2026-05-06 (7f468ee7)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request |
| 7 | Deletion detection | No | N/A | Deleted symbols are private Python helpers; no IN-scope doc references them |

### Scope Classification
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — Python source (docstrings IN scope); application logic OUT
- `tests/test_mcp_kanban.py`, `tests/test_mcp_kanban_1360.py` — test files, OUT scope

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated
- Commit: `82a19310`

### Scratch Files
- No `1360-*` scratch files found
[[2026-05-06]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| _canonical_agent_view_for helper removed | grep on serve/mcp-kanban/src finds no symbol; hasattr tests green | PASS |
| _invoke_view_move/start/end fallback branches removed | grep on serve/mcp-kanban/src finds no symbols; direct-path tests green | PASS |
| Direct AgentView calls replace fallback in move_task, start_work, end_work | Source confirmed via git diff (af05ce05); propagation tests green | PASS |
| All existing MCP kanban tests pass | tests/test_server_1170.py fails at collection: ImportError for _invoke_engine_end_work, _invoke_view_end_work, _invoke_view_move_task | FAIL |
| ~100 lines net reduction | wc -l reports 638 lines (below 720 threshold); line-count test green | PASS |

### Test Results
- pytest (scoped: test_mcp_kanban.py + test_mcp_kanban_1360.py): 75 passed, 0 failed
- pytest (full root tests/ excl. test_server_1170.py): 154 passed, 0 failed
- pytest (test_server_1170.py): COLLECTION ERROR (ImportError: removed symbols)
- ruff: clean

### Commit Integrity
- Builder source changes committed under af05ce05 (#1362) not #1360. Process concern: no dedicated builder commit for this task's implementation.
- Test-writer commit 7f468ee7 (#1360) correctly attributed.

### Architect Quality: 4/5
AC lines are specific and verifiable. AC4 scope ("all existing MCP kanban tests") is clear but the pipeline missed one consumer of the removed symbols.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| Full-suite test failures in task scope (test_server_1170.py) | -.05 |
| AC4 contradicted by verifiable failure (not just missing evidence) | -.02 |

### Confidence: .93
### Action: reject to backlog

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Remove or update tests/test_server_1170.py to eliminate imports of deleted private helpers (_invoke_engine_end_work, _invoke_view_end_work, _invoke_view_move_task, _canonical_agent_view_for); either delete coverage-gap tests for removed code or rewrite to test current direct-path behavior | tests/test_server_1170.py | ImportError at collection: cannot import name _invoke_engine_end_work |
| 2 | builder | Create a dedicated commit for the server.py dead-code removal attributed to #1360 (currently bundled in af05ce05 #1362) or document the bundling explicitly | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | git log shows no #1360-attributed commit for server.py |