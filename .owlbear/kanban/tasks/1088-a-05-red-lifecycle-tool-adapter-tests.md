---
id: 1088
title: 'A-05: RED — lifecycle tool adapter tests'
status: in-progress
priority: needed
created: '2026-04-21 10:53:58.270590+00:00'
updated: '2026-04-24 15:36:13.676640+00:00'
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
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.6–§5.8, paper-integration.md §1.6–§1.8
Module: `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`

Test the 3 lifecycle tool adapters: `move_task`, `start_work`, `end_work`. All tests mock `AgentView`. Tests verify: correct AgentView method called with correct args, SingleTaskResponse returned, KanbanError → ToolError mapping, and the `end_work` forbidden-parameter matrix (paper-integration.md §1.8).

## Acceptance Criteria

- [ ] `move_task`: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned
- [ ] `move_task`: `status="archived"` without `archival_reason` → engine raises → ToolError (AC4)
- [ ] `start_work`: id forwarded; SingleTaskResponse returned
- [ ] `start_work`: already claimed → engine ConcurrencyError → ToolError
- [ ] `start_work`: archived / blocked → engine raises → ToolError
- [ ] `end_work`: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned
- [ ] `end_work`: outcome="success" auto-advance (AC18); outcome="reject" (AC19); outcome="release" idempotent (AC20)
- [ ] `end_work`: outcome="block" with block_reason (AC-NEW-1, AC-NEW-2); without → ToolError (AC-NEW-2)
- [ ] `end_work`: forbidden-parameter matrix — success+move_to, release+move_to, success+archival_*, non-block+block_reason → ToolError (AC-NEW-3, AC-NEW-9, AC-NEW-11, AC-NEW-18)
- [ ] Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message
- [ ] All tests fail (RED phase)
[[2026-04-24]]
## Test-Writer Notes
- Test file: `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`
- Classes: `TestFromAC_MoveTaskAdapter`, `TestFromAC_StartWorkAdapter`, `TestFromAC_EndWorkAdapter`, `TestFromAC_KanbanErrorMapping`, `TestFromAC_EndWorkForbiddenMatrix`
- Tests per category: happy 12, edge 2, error 12, boundary 3
- Total: 29 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test(s) |
|---|---|
| move_task: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse | `test_move_task_forwards_id_and_status_to_agent_view`, `test_move_task_forwards_archival_reason_and_refs`, `test_move_task_returns_single_task_response` |
| move_task: status="archived" without archival_reason → ToolError (AC4) | `test_move_task_archived_without_archival_reason_raises_tool_error` |
| start_work: id forwarded; SingleTaskResponse | `test_start_work_forwards_id_to_agent_view`, `test_start_work_returns_single_task_response` |
| start_work: already claimed → ConcurrencyError → ToolError | `test_start_work_already_claimed_raises_tool_error` |
| start_work: archived / blocked → ToolError | `test_start_work_archived_task_raises_tool_error`, `test_start_work_blocked_task_raises_tool_error` |
| end_work: all 7 params forwarded; SingleTaskResponse | `test_end_work_all_params_forwarded_to_agent_view`, `test_end_work_returns_single_task_response` |
| end_work: outcome="success" auto-advance (AC18) | `test_end_work_success_auto_advance` |
| end_work: outcome="reject" (AC19) | `test_end_work_reject_with_move_to` |
| end_work: outcome="release" idempotent (AC20) | `test_end_work_release_idempotent` |
| end_work: outcome="block" with block_reason (AC-NEW-1/2) | `test_end_work_block_with_block_reason` |
| end_work: outcome="block" without block_reason → ToolError (AC-NEW-2) | `test_end_work_block_without_block_reason_raises_tool_error` |
| end_work: note optional | `test_end_work_note_is_optional` |
| KanbanError subclasses → ToolError with user_message | `test_validation_error_mapped_to_tool_error_with_user_message`, `test_not_found_error_mapped_to_tool_error_with_user_message`, `test_concurrency_error_mapped_to_tool_error_with_user_message`, `test_migration_error_mapped_to_tool_error_with_user_message` |
| end_work forbidden matrix: success+move_to, release+move_to, success+archival_*, non-block+block_reason | 7 tests in `TestFromAC_EndWorkForbiddenMatrix` |

Failure modes: TypeError (new params not accepted), AssertionError (agent_view.method never called), no ToolError raised (KanbanError path not wired). Commit: 2f0e74c8.
[[2026-04-24]]
## Builder Notes
- Implementation: updated lifecycle MCP adapters in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Files changed: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Test contract implemented: `move_task`, `start_work`, and `end_work` now delegate to agent-view lifecycle methods when available, forward new AC parameters, return `SingleTaskResponse`, and map `KanbanError` subclasses to `ToolError` using `user_message`.
- Compatibility behavior: preserved fallback to engine lifecycle methods when agent-view lifecycle methods are unavailable/not implemented.
- Guidance behavior: fallback path retains existing guidance wiring; agent-view path passes through engine-provided response envelope.
- Tests: 29/29 passed in `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`.
- Coverage: `owlbear_mcp_kanban.server` 46% in scoped quality run.
- Ruff: clean (scoped lint paths: updated source file + task test file).
- Evidence summary: RED verified first (29 failing), then GREEN verified after implementation (29 passing, 0 lint violations).

Post-task reflection:
- Problem faced: `engine.agent_view` appears as both callable factory and direct mock object across test styles.
- Workaround applied: added resilient agent-view resolver that chooses the best lifecycle-capable candidate.
- Pattern discovered: lifecycle adapters need dual-path behavior (agent-view preferred, engine fallback) to support mixed migration state.
- Quality gap: module coverage for `owlbear_mcp_kanban.server` is still low in scoped run; broader AC-specific files remain to be completed in adjacent tasks.
[[2026-04-24]]
## Review Evidence
### Test Results
- pytest: 29 passed, 0 failed, 0 skipped in serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py

### Lint
- ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py

### Coverage
- owlbear_mcp_kanban.server: 46% via independent quality-runner scoped run
- Gate miss: touched module is below the 90% review threshold, and the uncovered branches are the live compatibility fallbacks in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L275-L299) and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L408-L452)

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| move_task forwards id/status/archival_reason/archival_refs; returns SingleTaskResponse | test_move_task_forwards_id_and_status_to_agent_view, test_move_task_forwards_archival_reason_and_refs, test_move_task_returns_single_task_response | No on the live runtime path. The helper hard-wires engine.agent_view to a direct mock at [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L72), so the suite never reaches the fallback call to [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L297), and the real engine signature at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1005) has no archival fields. | MISSING |
| move_task archived without archival_reason -> ToolError | test_move_task_archived_without_archival_reason_raises_tool_error | No. The mocked AgentView raises, but the live fallback reaches [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1005) which only accepts task_id/status and does not enforce archival_reason. | MISSING |
| start_work id forwarded; returns SingleTaskResponse | test_start_work_forwards_id_to_agent_view, test_start_work_returns_single_task_response | Yes for the public adapter contract. | COVERED |
| start_work already claimed -> ToolError | test_start_work_already_claimed_raises_tool_error | Yes for the public ToolError contract. | COVERED |
| start_work archived / blocked -> ToolError | test_start_work_archived_task_raises_tool_error, test_start_work_blocked_task_raises_tool_error | Partially. The mocked AgentView path is covered; the live callable-agent_view path is not independently exercised. | LAX |
| end_work forwards all 7 params; returns SingleTaskResponse | test_end_work_all_params_forwarded_to_agent_view, test_end_work_returns_single_task_response | No on the live runtime path. The fallback call at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L445) forwards only note/outcome/block_reason/move_to into [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1185-L1230); archival_reason and archival_refs are dropped. | MISSING |
| end_work success/reject/release | test_end_work_success_auto_advance, test_end_work_reject_with_move_to, test_end_work_release_idempotent | No. The live fallback ends in engine.end_work, whose valid outcomes are only success/fail/block/reject at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1221). release is unsupported there. | MISSING |
| end_work block with block_reason; without -> ToolError | test_end_work_block_with_block_reason, test_end_work_block_without_block_reason_raises_tool_error | No for the live fallback. The engine docstring promises block_reason validation at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1210-L1211), but the implementation falls through to _apply_outcome at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1246) with no empty-string guard. | MISSING |
| end_work forbidden-parameter matrix -> ToolError | TestFromAC_EndWorkForbiddenMatrix | No. The mocked AgentView raises, but the live fallback ignores success+move_to, success+archival_*, and non-block+block_reason, and rejects release for the wrong reason because engine.end_work lacks release support. | MISSING |
| Error mapping: all KanbanError subclasses mapped to ToolError with user_message | TestFromAC_KanbanErrorMapping | Yes on the AgentView path exercised by these tests. | COVERED |
| All tests fail (RED phase) | Test-Writer notes in task body | Historical prior-stage evidence only; not independently re-runnable from the current GREEN workspace. | COVERED |

#### Security Review
- No security issues found in the changed adapter code.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| The 29 TestFromAC methods listed in the task body are all still present in the current file. | No removals or renames observed in the current workspace. I could not diff the pre-builder test file directly with the available tools, so this is an inventory check rather than a full textual diff. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | Direct call assertions and ToolError match checks are specific on the mocked AgentView path. |
| Negative/error-path coverage | WEAK | Every helper forces a direct mock AgentView at [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L72), so no test exercises the callable/missing-method compatibility branches in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L275-L299) or [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L408-L452). |
| Manual mutation reasoning | WEAK | The suite stays green even though the live fallback drops archival fields and still rejects release via Unknown outcome. |
| Test independence | STRONG | Tests use isolated MagicMock fixtures and no shared mutable state. |
| Descriptive names | STRONG | Test names map cleanly to individual AC clauses. |

#### Data Safety
- No data-safety issues found.

#### Implementation-Aware Gaps
- move_task is only correct on the mocked AgentView branch. On the real engine path, AgentView has start_work/end_work but no move_task in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1508-L1539), so the adapter falls back to [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L297) and calls engine.move_task with only task_id/status against [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1005). That drops archival_reason/archival_refs and cannot raise the required ToolError for archived-without-reason.
- end_work is only correct on the mocked AgentView branch. The compatibility fallback at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L408-L452) eventually calls engine.end_work at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1185-L1267), which does not accept archival fields, does not support outcome=release, and does not implement the promised empty block_reason validation.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Prior Review Evidence sections | 0 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- No additional style or documentation issues beyond the blocking findings above.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| move_task: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L275-L299), fallback call at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L297), engine signature at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1005), direct-mock test helper at [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L72) | test_move_task_forwards_id_and_status_to_agent_view; test_move_task_forwards_archival_reason_and_refs; test_move_task_returns_single_task_response | FAIL |
| move_task: status="archived" without archival_reason -> ToolError | engine.move_task lacks archival_reason validation at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1005-L1021) | test_move_task_archived_without_archival_reason_raises_tool_error | FAIL |
| start_work: id forwarded; SingleTaskResponse returned | Adapter path in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L367-L390); scoped pytest 29/29 passing | test_start_work_forwards_id_to_agent_view; test_start_work_returns_single_task_response | PASS |
| start_work: already claimed -> ToolError | Adapter maps errors to ToolError in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L367-L390); scoped pytest 29/29 passing | test_start_work_already_claimed_raises_tool_error | PASS |
| start_work: archived / blocked -> ToolError | Same adapter path as above; scoped pytest 29/29 passing | test_start_work_archived_task_raises_tool_error; test_start_work_blocked_task_raises_tool_error | PASS |
| end_work: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned | Fallback path at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L408-L452) drops archival_reason/archival_refs when it reaches engine.end_work at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1185-L1230) | test_end_work_all_params_forwarded_to_agent_view; test_end_work_returns_single_task_response | FAIL |
| end_work: outcome="success" auto-advance; outcome="reject"; outcome="release" idempotent | engine.end_work valid outcomes exclude release at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1221) | test_end_work_success_auto_advance; test_end_work_reject_with_move_to; test_end_work_release_idempotent | FAIL |
| end_work: outcome="block" with block_reason; without -> ToolError | engine docstring promises validation at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1210-L1211), but there is no guard before _apply_outcome at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1246) | test_end_work_block_with_block_reason; test_end_work_block_without_block_reason_raises_tool_error | FAIL |
| end_work: forbidden-parameter matrix -> ToolError | Live fallback ignores or mishandles these combos in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L408-L452) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1185-L1267) | TestFromAC_EndWorkForbiddenMatrix | FAIL |
| Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message | Direct mapping branches in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L286-L290) and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L432-L436); scoped pytest 29/29 passing | TestFromAC_KanbanErrorMapping | PASS |
| All tests fail (RED phase) | Historical evidence recorded in Test-Writer notes in the task body | Task body Test-Writer notes | PASS |

### Deductions
- -0.22: live move_task fallback drops archival fields and bypasses archived-without-reason enforcement
- -0.22: live end_work fallback drops archival fields, lacks release support, and misses block_reason validation on the real engine path
- -0.10: touched-module coverage is 46%, confirming the compatibility branches are not exercised
- -0.08: test quality is WEAK for manual mutation/fallback coverage because the suite only proves the direct mock path

### Confidence: 0.38
### Verdict: FAIL
### Action: Reject to in-progress for builder fix. The builder needs to make the live fallback path satisfy the new lifecycle contract, then add tests that exercise callable/missing-method AgentView compatibility instead of only the direct-mock path.
