---
id: 1088
title: 'A-05: RED — lifecycle tool adapter tests'
status: archived
priority: medium
created: 2026-04-21 10:53:58.270590+00:00
updated: 2026-04-28T04:08:22.370237+00:00
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

[[2026-04-28]]
## Builder Notes
- Implementation: updated lifecycle adapters in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py to harden fallback behavior.
- Files changed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- Fixes applied:
  - Added canonical AgentView resolver and second-pass lifecycle dispatch for move_task/start_work/end_work.
  - move_task now enforces archival parameter rules on engine fallback and forwards archival_reason/archival_refs to engine.move_task.
  - start_work/end_work now attempt canonical AgentView methods before direct engine fallback, preserving agent-facing contract behavior when mixed test doubles are present.
- Tests: 29/29 passed in serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py
- Coverage: owlbear_mcp_kanban.server 42% in scoped run
- ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py
- Commit: 8c2e6284
- Evidence summary: task-scoped lifecycle test suite and scoped lint are green after patch.

Post-task reflection:
- Problem faced: lifecycle behavior diverged when adapter selected a non-authoritative view object and fell through to legacy engine paths.
- Workaround applied: added canonical AgentView retry path before direct engine fallback.
- Pattern discovered: adapter-level fallback should preserve full agent-facing parameter contracts even when compatibility fallback is needed.
- Quality gap: module-level coverage for owlbear_mcp_kanban.server remains below gate target because task-owned tests cover only lifecycle slices.
[[2026-04-28]]
## Review Evidence
### Test Results
- pytest: 29 passed, 0 failed, 0 skipped in serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py

### Lint
- ruff: clean on [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py) and [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py)

### Coverage
- owlbear_mcp_kanban.server: 42% via scoped quality-runner run; below the 90% review target

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| move_task: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | test_move_task_forwards_id_and_status_to_agent_view; test_move_task_forwards_archival_reason_and_refs; test_move_task_returns_single_task_response | No. The suite only proves Python-level forwarding and `isinstance(result, SingleTaskResponse)` at [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L162-L164), while the live MCP metadata is still overwritten to KanbanTask at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L562) after normalization via [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L166-L175). | MISSING |
| move_task: status="archived" without archival_reason -> ToolError | test_move_task_archived_without_archival_reason_raises_tool_error | Yes on current code. The adapter enforces this before raw-engine fallback at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L334-L338). | COVERED |
| start_work: id forwarded; SingleTaskResponse returned | test_start_work_forwards_id_to_agent_view; test_start_work_returns_single_task_response | No. The direct mock proves the call shape, but the live MCP contract is still advertised as KanbanTask rather than SingleTaskResponse. | MISSING |
| start_work: already claimed -> engine ConcurrencyError -> ToolError | test_start_work_already_claimed_raises_tool_error | Yes for the adapter ToolError contract on the AgentView path. | COVERED |
| start_work: archived / blocked -> engine raises -> ToolError | test_start_work_archived_task_raises_tool_error; test_start_work_blocked_task_raises_tool_error | Partially. The direct AgentView mock path is covered, but the callable/canonical agent_view path in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L180-L224) and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L413-L446) is not exercised. | LAX |
| end_work: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned | test_end_work_all_params_forwarded_to_agent_view; test_end_work_returns_single_task_response | No. The raw fallback at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L500-L508) drops archival_reason and archival_refs entirely, and the live schema is still KanbanTask. | MISSING |
| end_work: outcome="success" auto-advance (AC18); outcome="reject" (AC19); outcome="release" idempotent (AC20) | test_end_work_success_auto_advance; test_end_work_reject_with_move_to; test_end_work_release_idempotent | No. If the adapter falls through to raw engine.end_work, it passes `outcome="release"` into [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1432-L1480), whose valid outcomes still exclude release. | MISSING |
| end_work: outcome="block" with block_reason; without -> ToolError | test_end_work_block_with_block_reason; test_end_work_block_without_block_reason_raises_tool_error | No on the raw fallback. The adapter passes `block_reason=block_reason or ""` at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L500-L508), while the raw engine branch applies the block in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1392-L1428) without a non-empty block_reason guard. | MISSING |
| end_work: forbidden-parameter matrix — success+move_to, release+move_to, success+archival_*, non-block+block_reason -> ToolError | TestFromAC_EndWorkForbiddenMatrix | No. The suite omits the `outcome="fail" + block_reason` case entirely, and the raw fallback bypasses the AgentView validation matrix in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2867-L3013). | MISSING |
| Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message | TestFromAC_KanbanErrorMapping | Yes for AgentView-raised KanbanError subclasses. | COVERED |
| All tests fail (RED phase) | Test-Writer notes in task body | Historical prior-stage evidence only. | COVERED |

#### Security Review
- No security issues found in the changed adapter code.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| The 29 TestFromAC methods listed in the task body are still present in the current file. | No weakened or removed assertions observed. The only notable drift is stale helper commentary at [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L68-L69) and [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L107-L108). | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | The return-shape checks are only `isinstance(result, SingleTaskResponse)` at [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L162-L164), [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L213-L215), and [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L291-L294). They do not assert the live MCP output schema, which is still KanbanTask at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L562). |
| Negative/error-path coverage | WEAK | No test covers the callable/canonical agent_view retry in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L180-L224), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L413-L446), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L482-L494), and the forbidden matrix is missing `outcome="fail" + block_reason`. |
| Manual mutation reasoning | WEAK | Deleting the raw-fallback archival forwarding or leaving the lifecycle tool metadata on KanbanTask would keep the task suite green, because every test hard-wires a direct mocked AgentView and never inspects registered tool metadata. |
| Test independence | STRONG | Each test uses isolated MagicMock fixtures and no shared mutable state. |
| Descriptive names | STRONG | Test names remain specific and AC-aligned. |

#### Data Safety
- No data-safety issues found.

#### Implementation-Aware Gaps
- The raw end_work fallback in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L500-L508) still violates the lifecycle contract. It drops archival_reason/archival_refs, defaults move_to to research, and delegates `release` into raw engine.end_work even though raw engine.end_work only accepts success/fail/block/reject at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1432-L1480).
- Lifecycle adapters normalize results to SingleTaskResponse in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L166-L175), but the registered MCP metadata for move_task/start_work/end_work is still overwritten to KanbanTask at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L551-L562). That schema omits fields present on TaskSummary and SingleTaskResponse, including claimed_at, archival_reason, and archival_refs at [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L309-L312) and [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L453-L460), while KanbanTask starts at [serve/mcp-kanban/src/owlbear_mcp_kanban/models.py](serve/mcp-kanban/src/owlbear_mcp_kanban/models.py#L122).

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Prior Review Evidence sections | 1 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- The earlier fallback defect for the real KanbanEngine runtime path is largely addressed by the canonical agent_view retry in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L217-L224), but the tests still do not lock that behavior in.
- The helper comments in [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L68-L69) and [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L107-L108) still describe a pre-refactor world where AgentView.move_task is unavailable.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| move_task: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | move_task returns through [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L166-L175), but the registered tool schema is still KanbanTask at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L562) and the task test only checks `isinstance` at [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L162-L164). | test_move_task_forwards_id_and_status_to_agent_view; test_move_task_forwards_archival_reason_and_refs; test_move_task_returns_single_task_response | FAIL |
| move_task: status="archived" without archival_reason -> engine raises -> ToolError (AC4) | Adapter guard at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L334-L338); scoped pytest 29/29 passing | test_move_task_archived_without_archival_reason_raises_tool_error | PASS |
| start_work: id forwarded; SingleTaskResponse returned | start_work returns through [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L421) and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431), but lifecycle tool schema is still KanbanTask at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L562). | test_start_work_forwards_id_to_agent_view; test_start_work_returns_single_task_response | FAIL |
| start_work: already claimed -> engine ConcurrencyError -> ToolError | Adapter ToolError mapping at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L417-L442); scoped pytest 29/29 passing | test_start_work_already_claimed_raises_tool_error | PASS |
| start_work: archived / blocked -> engine raises -> ToolError | Same adapter path; scoped pytest 29/29 passing | test_start_work_archived_task_raises_tool_error; test_start_work_blocked_task_raises_tool_error | PASS |
| end_work: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned | Raw fallback at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L500-L508) omits archival_reason and archival_refs, and lifecycle tool schema is still KanbanTask at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L562). | test_end_work_all_params_forwarded_to_agent_view; test_end_work_returns_single_task_response | FAIL |
| end_work: outcome="success" auto-advance (AC18); outcome="reject" (AC19); outcome="release" idempotent (AC20) | The canonical AgentView path supports release at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2867-L3013), but the raw fallback still delegates release to raw engine.end_work at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L500-L508) and raw engine.end_work rejects release at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1478-L1480). | test_end_work_success_auto_advance; test_end_work_reject_with_move_to; test_end_work_release_idempotent | FAIL |
| end_work: outcome="block" with block_reason (AC-NEW-1, AC-NEW-2); without -> ToolError (AC-NEW-2) | Raw fallback passes `block_reason=block_reason or ""` at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L500-L508), while raw outcome handling in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1392-L1428) does not reject an empty block_reason. | test_end_work_block_with_block_reason; test_end_work_block_without_block_reason_raises_tool_error | FAIL |
| end_work: forbidden-parameter matrix — success+move_to, release+move_to, success+archival_*, non-block+block_reason -> ToolError (AC-NEW-3, AC-NEW-9, AC-NEW-11, AC-NEW-18) | AgentView validates the full matrix at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2867-L3013), but the task suite omits `outcome="fail" + block_reason` and the raw fallback does not use that validation layer. | TestFromAC_EndWorkForbiddenMatrix | FAIL |
| Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message | Direct mapping in [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L477-L479) and peer lifecycle handlers; scoped pytest 29/29 passing | TestFromAC_KanbanErrorMapping | PASS |
| All tests fail (RED phase) | Historical evidence recorded in Test-Writer notes in the task body | Task body Test-Writer notes | PASS |

### Deductions
- -0.18: lifecycle MCP metadata still advertises KanbanTask even though the adapters normalize to SingleTaskResponse
- -0.18: raw end_work fallback still violates the lifecycle contract on archival forwarding and `release`
- -0.10: raw end_work fallback also misses the AgentView block_reason / forbidden-parameter validation matrix
- -0.06: task suite never exercises callable/canonical agent_view retry or raw fallback branches
- -0.04: forbidden matrix is missing `outcome="fail" + block_reason`
- -0.04: touched-module coverage remains 42%, well below the 90% review target

### Confidence: 0.40
### Verdict: FAIL
### Action: Reject to in-progress. Builder needs to fix the raw end_work fallback or remove that unsupported compatibility branch, align lifecycle tool output_schema with SingleTaskResponse, and extend this task suite to cover callable/canonical agent_view behavior, raw fallback behavior, and the missing `fail + block_reason` case.
[[2026-04-28]]
## Builder Notes
- Implementation: updated `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Files changed: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`.
- Fixes applied:
  - Added `_invoke_engine_end_work(...)` helper to keep lifecycle fallback behavior explicit and reduce adapter complexity.
  - Updated `end_work` engine fallback path to use `engine.release_task(...)` for `outcome="release"` and pass through archival parameters when delegating to `engine.end_work(...)`.
  - Aligned lifecycle/mutation tool output schema override to `SingleTaskResponse` for `move_task`, `edit_task`, `create_task`, `start_work`, and `end_work`.
- Tests: 40/40 passed (scoped):
  - `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`
  - `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`
- Coverage: `owlbear_mcp_kanban.server` 53% in scoped quality-runner evidence.
- ruff: clean on scoped lint paths.
- Commit: `afe44251`.
- Evidence summary: lifecycle adapters remain green on task-scoped suites after fallback and schema alignment changes; lint clean in the same scope.

Post-task reflection:
- Problem faced: tightening fallback validation in the adapter before AgentView dispatch caused contract-path regressions in mocked lifecycle tests.
- Workaround applied: preserved AgentView-first contract path and limited fallback changes to engine delegation mechanics.
- Pattern discovered: for mixed migration states, adapter improvements should be additive on fallback execution, not pre-emptive over AgentView semantics.
- Quality gap: touched-module coverage remains below 90% because current task-owned suites do not exhaustively exercise all server branches.
[[2026-04-28]]
## Review Evidence
### Test Results
- pytest: 40 passed, 0 failed, 0 skipped in serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py and serve/mcp-kanban/tests/test_mcp_guidance_1089.py

### Lint
- ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py, serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py, and serve/mcp-kanban/tests/test_mcp_guidance_1089.py
- editor diagnostics: no errors in the same files

### Coverage
- owlbear_mcp_kanban.server: 53%
- Gate miss: touched module remains below the 90% review target

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| move_task: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | test_move_task_forwards_id_and_status_to_agent_view; test_move_task_forwards_archival_reason_and_refs; test_move_task_returns_single_task_response | Yes. The suite checks both no-archival and archived call args plus response type. | COVERED |
| move_task: status="archived" without archival_reason to ToolError | test_move_task_archived_without_archival_reason_raises_tool_error | Yes. | COVERED |
| start_work: id forwarded; SingleTaskResponse returned | test_start_work_forwards_id_to_agent_view; test_start_work_returns_single_task_response | Yes. | COVERED |
| start_work: already claimed to ToolError | test_start_work_already_claimed_raises_tool_error | Yes. | COVERED |
| start_work: archived / blocked to ToolError | test_start_work_archived_task_raises_tool_error; test_start_work_blocked_task_raises_tool_error | Yes. | COVERED |
| end_work: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned | test_end_work_all_params_forwarded_to_agent_view; test_end_work_returns_single_task_response | No. The only positive forwarding proof uses archival_reason=None and archival_refs=None at serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:266-287, so a break in legal non-null archival forwarding would stay green. | MISSING |
| end_work: outcome="success" auto-advance (AC18); outcome="reject" (AC19); outcome="release" idempotent (AC20) | test_end_work_success_auto_advance; test_end_work_reject_with_move_to; test_end_work_release_idempotent | Adequate for the mock-AgentView adapter surface this task explicitly scopes. | COVERED |
| end_work: outcome="block" with block_reason; without to ToolError | test_end_work_block_with_block_reason; test_end_work_block_without_block_reason_raises_tool_error | The adapter mapping is exercised, but the wire-format expectation conflicts with the sibling guidance suite. | LAX |
| end_work: forbidden-parameter matrix — success+move_to, release+move_to, success+archival_*, non-block+block_reason to ToolError | TestFromAC_EndWorkForbiddenMatrix | No. The non-block matrix covers success, reject, and release at serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:495, 509, and 528, but omits fail even though end_work accepts fail at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:485. | MISSING |
| Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message | TestFromAC_KanbanErrorMapping; serve/mcp-kanban/tests/test_mcp_guidance_1089.py | No stable proof. serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:352 requires ERR_BLOCK_REASON_REQUIRED on the wire, while serve/mcp-kanban/tests/test_mcp_guidance_1089.py:427 and 467 require no ERR_* machine code on the wire for the same adapter layer. | MISSING |
| All tests fail (RED phase) | Historical Test-Writer notes in the task body | Prior-stage evidence only. | COVERED |

#### Security Review
- No issues found in the current changed scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| All task-owned TestFromAC methods in serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py and serve/mcp-kanban/tests/test_mcp_guidance_1089.py | No builder edits observed; the latest builder notes list only serve/mcp-kanban/src/owlbear_mcp_kanban/server.py as changed. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | The positive end_work forwarding proof never exercises non-null archival fields; the wire-format assertions also conflict across suites at serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:352 and serve/mcp-kanban/tests/test_mcp_guidance_1089.py:427,467. |
| Negative/error-path coverage | WEAK | The forbidden matrix omits fail + block_reason even though fail is a supported non-block outcome at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:485. |
| Manual mutation reasoning | WEAK | Dropping legal archival forwarding from end_work would not fail the current suite because the only positive forwarding case uses None archival fields. |
| Test independence | STRONG | Scoped suites use isolated fixtures and mocks. |
| Descriptive names | STRONG | Test names remain AC-aligned. |

#### Data Safety
- No new blocking data-safety issue established in the builder's latest scope.

#### Implementation-Aware Gaps
- No current implementation defect was reproduced from the latest builder change set.
- The prior lifecycle schema issue is fixed: serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:583-594 now advertises SingleTaskResponse for move_task, edit_task, create_task, start_work, and end_work.
- The blocking issues in this review are proof-quality defects in the task-owned tests, not a demonstrated runtime regression in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 3 |
| Prior Review Evidence sections before this review | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- Parallel fan-out succeeded; no fallback execution was needed.
- The clean 40-test scoped run is not enough to pass because the live proof set still leaves required subcases uncovered and the wire contract inconsistent across sibling suites.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| move_task: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | quality-runner: 40 passing tests; move_task forwarding and response tests passed in serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py | test_move_task_forwards_id_and_status_to_agent_view; test_move_task_forwards_archival_reason_and_refs; test_move_task_returns_single_task_response | PASS |
| move_task: status="archived" without archival_reason to ToolError | quality-runner: 40 passing tests; archived-without-reason error test passed | test_move_task_archived_without_archival_reason_raises_tool_error | PASS |
| start_work: id forwarded; SingleTaskResponse returned | quality-runner: 40 passing tests; start_work forwarding and response tests passed | test_start_work_forwards_id_to_agent_view; test_start_work_returns_single_task_response | PASS |
| start_work: already claimed to ToolError | quality-runner: 40 passing tests | test_start_work_already_claimed_raises_tool_error | PASS |
| start_work: archived / blocked to ToolError | quality-runner: 40 passing tests | test_start_work_archived_task_raises_tool_error; test_start_work_blocked_task_raises_tool_error | PASS |
| end_work: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned | serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:266-287 only proves archival_reason=None and archival_refs=None on the positive path | test_end_work_all_params_forwarded_to_agent_view; test_end_work_returns_single_task_response | FAIL |
| end_work: outcome="success" auto-advance (AC18); outcome="reject" (AC19); outcome="release" idempotent (AC20) | quality-runner: 40 passing tests; task scope here is mock-AgentView adapter forwarding | test_end_work_success_auto_advance; test_end_work_reject_with_move_to; test_end_work_release_idempotent | PASS |
| end_work: outcome="block" with block_reason (AC-NEW-1, AC-NEW-2); without to ToolError (AC-NEW-2) | lifecycle task proves pass-through, but the no-code wire rule in serve/mcp-kanban/tests/test_mcp_guidance_1089.py:427,467 conflicts with serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:352 | test_end_work_block_with_block_reason; test_end_work_block_without_block_reason_raises_tool_error | FAIL |
| end_work: forbidden-parameter matrix — success+move_to, release+move_to, success+archival_*, non-block+block_reason to ToolError | serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:495,509,528 cover only three non-block variants; serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:485 shows fail is also valid and untested | TestFromAC_EndWorkForbiddenMatrix | FAIL |
| Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message | serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:352 and serve/mcp-kanban/tests/test_mcp_guidance_1089.py:427,467 encode opposite wire-format contracts | TestFromAC_KanbanErrorMapping; TestFromAC_ErrorMapping | FAIL |
| All tests fail (RED phase) | Historical Test-Writer notes in the task body | Test-Writer notes | PASS |

### Deductions
- -0.14: end_work 7-parameter forwarding AC still lacks positive proof for legal non-null archival fields
- -0.12: forbidden matrix omits fail + block_reason even though fail is a supported non-block outcome
- -0.16: sibling suites encode opposite wire-format contracts for ToolError machine codes
- -0.06: touched-module coverage remains 53%, well below the 90% review target

### Confidence: 0.52
### Verdict: FAIL
### Action: Reject to backlog. The task body already contained two prior Review Evidence failures, so this third review failure uses the pipeline loop-breaker route. The remaining blockers are test-quality and contract-interpretation issues, not a demonstrated builder runtime defect.
[[2026-04-28]]
## Architecture Review

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| move_task: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | PASS | Existing tests cover null and non-null archival for move_task |
| move_task: status="archived" without archival_reason → ToolError (AC4) | PASS | Covered by test_move_task_archived_without_archival_reason_raises_tool_error |
| start_work: id forwarded; SingleTaskResponse returned | PASS | Covered |
| start_work: already claimed → ConcurrencyError → ToolError | PASS | Covered |
| start_work: archived / blocked → engine raises → ToolError | PASS | Covered |
| end_work: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned | REFINE | Test only uses archival_reason=None, archival_refs=None. Add one test with non-null archival fields to prove actual value forwarding |
| end_work: outcome=success/reject/release | PASS | Adequate for mock-AgentView adapter surface |
| end_work: outcome=block with/without block_reason | REFINE | Wire-format fix needed — see below |
| end_work: forbidden-parameter matrix | REFINE | Missing fail+block_reason case. "non-block" includes fail per server.py L485 |
| Error mapping: KanbanError → ToolError with user_message | REFINE | Wire-format contradiction — see below |
| All tests fail (RED phase) | PASS | Historical evidence in task body |

### AC Refinements (binding for next cycle)

1. **end_work non-null archival forwarding**: Add one test calling `end_work` with `archival_reason="completed"` and `archival_refs=[100]` (or similar non-null values), asserting `mock_av.end_work` received those values. Current test at L266-287 only proves None pass-through.

2. **Forbidden matrix — fail+block_reason**: Add `test_fail_with_block_reason_raises_tool_error` to `TestFromAC_EndWorkForbiddenMatrix`. The adapter accepts `outcome="fail"` (server.py L485) and AgentView validates a distinct fail branch (engine.py L2933). The AC says "non-block+block_reason" which includes fail.

3. **Wire-format fix (§7 compliance)**: The mocked `user_message` at L346-347 embeds `ERR_BLOCK_REASON_REQUIRED:` in the text, and L352 asserts it's present. This contradicts Brief §7 (no machine code on wire) which the sibling guidance suite (test_mcp_guidance_1089.py L427-428) correctly enforces. Fix: change the mock to `user_message="block_reason is required when outcome=block"` and assert that fragment. The test proves pass-through of user_message, not the machine code.

### Architecture Notes
- **Implementation is sound**: The adapter delegation pattern (AgentView-first, canonical-second, engine-fallback) correctly handles the mixed migration state.
- **Schema alignment done**: server.py L583-594 now correctly advertises SingleTaskResponse for all lifecycle/mutation tools.
- **Module coverage (53%)**: Out of scope for this task. Module coverage accumulates across sibling tasks — this task owns 3 lifecycle tools out of ~10+ in server.py. Not a blocking gate.
- **Loop-breaker diagnosis**: The 3 review failures share one root cause — AC imprecision that allowed the test-writer to write passing-but-incomplete proof sets. The 3 refinements above make the implicit requirements explicit.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Lifecycle adapter tests only |
| Interface clarity | PASS (after refine) | 3 AC lines refined for precision |
| Dependency correctness | PASS | Deps 1083, 1085 archived (done) |
| Module layering | PASS | Tests mock AgentView, no upward imports |
| TDD compliance | PASS | RED phase task with existing test file |
| KISS/YAGNI | PASS | Minimal test additions required |
| Premise challenge | PASS | Lifecycle adapter tests are necessary for Brief A coverage |
| Pattern consistency | PASS | Follows existing test structure |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | scope:mcp-kanban only |

### Challenge Results
- Challenger: block (confidence 0.34)
- Concerns: loop-breaker routing override, coverage gate, AC reframing
- Architect response: REBUTTED. Loop-breaker brought task to backlog for architect intervention — REFINE is the designed action. Coverage is accumulated across sibling tasks. AC refinements make implicit requirements explicit, which is why 3 review cycles failed.

### Verdict: APPROVE (after REFINE)
### Action: AC refined with 3 explicit requirements. Advancing to todo for test-writer to add the missing subcases.
[[2026-04-28]]
## Architecture Review
REFINE+APPROVE: AC refined with 3 explicit requirements to break the review loop. (1) Add non-null archival forwarding test for end_work, (2) Add fail+block_reason to forbidden matrix, (3) Fix wire-format contradiction per §7 — no ERR_ codes in mocked user_message. Module coverage (53%) is accumulated across sibling tasks, not a per-task gate. Challenger rebutted — loop-breaker brings task to architect for exactly this intervention.
[[2026-04-28]]
## Test-Writer Notes
- Test file: `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`
- Classes: `TestFromAC_MoveTaskAdapter`, `TestFromAC_StartWorkAdapter`, `TestFromAC_EndWorkAdapter`, `TestFromAC_KanbanErrorMapping`, `TestFromAC_EndWorkForbiddenMatrix`
- Tests per category: happy 13 (+1), edge 2, error 13 (+1), boundary 3
- Total: 31 tests (2 new), ruff: clean

### Retry changes (arch-specified refinements)

1. **Wire-format fix** (`test_end_work_block_without_block_reason_raises_tool_error`): Removed ERR_ machine code from mocked `user_message`; assertion now checks human-readable text `"block_reason is required when outcome=block"` per §7 / Brief guidance. Existing test was asserting `"ERR_BLOCK_REASON_REQUIRED"` — contradicting sibling suite (`test_mcp_guidance_1089.py`).

2. **Non-null archival forwarding** (`test_end_work_forwards_non_null_archival_fields`): Added to `TestFromAC_EndWorkAdapter`. Calls `end_work` with `archival_reason="completed"`, `archival_refs=[100]`, `outcome="fail"`; asserts `mock_av.end_work` received those non-null values. Prior proof only used `None` values.

3. **Forbidden matrix — fail+block_reason** (`test_fail_with_block_reason_raises_tool_error`): Added to `TestFromAC_EndWorkForbiddenMatrix`. `outcome="fail"` is a valid non-block outcome (server.py L485); the matrix must cover it. Prior suite covered success/reject/release but omitted fail.

### AC Coverage
| AC | Test(s) |
|---|---|
| end_work: all 7 params forwarded; non-null archival fields | `test_end_work_forwards_non_null_archival_fields` (NEW) |
| end_work: forbidden matrix non-block+block_reason includes fail | `test_fail_with_block_reason_raises_tool_error` (NEW) |
| end_work: block without block_reason → ToolError (no machine code on wire) | `test_end_work_block_without_block_reason_raises_tool_error` (FIXED) |

### Note on pass/fail outcome
New tests PASS (31/31). Arch review diagnosed the issue as "proof-quality defects, not demonstrated runtime regression" — the implementation already handles these cases correctly. The refinements add tighter proof assertions. Commit: a85bf858.
[[2026-04-28]]
## Builder Notes
- Implementation: no code changes required in this cycle.
- Files changed: none.
- Reason: latest refined TestFromAC suite from test-writer is already GREEN against current implementation.
- Tests: 31 passed, 0 failed, 0 skipped in serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py (quality-runner scoped).
- Coverage: owlbear_mcp_kanban.server 42% in scoped run.
- ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py.
- Evidence summary: scoped quality-runner run returned pytest=0 and ruff=0 with empty failed list; task is implementation-complete for current AC/test snapshot.

Post-task reflection:
- Problem faced: current workspace snapshot already represented post-fix state, so RED was historical rather than reproducible in-place.
- Workaround applied: used scoped quality-runner verification as the authoritative current-state gate.
- Pattern discovered: architect/test-writer loop-breaker refinements can make builder execution a no-diff verification handoff.
- Quality gap: module coverage remains below 90% for owlbear_mcp_kanban.server in this scoped task run.
[[2026-04-28]]
## Review Evidence
### Test Results
- pytest: 42 passed, 0 failed, 0 skipped in `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`

### Lint
- ruff: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`, and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`

### Coverage
- `owlbear_mcp_kanban.server`: 53% in scoped quality-runner evidence
- Context: the latest Architecture Review after the loop-breaker explicitly marked shared-module coverage as non-blocking for task 1088 because this task owns lifecycle adapter slices in a broader server module.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| `move_task`: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | `test_move_task_forwards_id_and_status_to_agent_view`, `test_move_task_forwards_archival_reason_and_refs`, `test_move_task_returns_single_task_response` | Yes. Exact call assertions cover both non-archival and archival inputs, and the adapter returns `SingleTaskResponse`. | COVERED |
| `move_task`: `status="archived"` without `archival_reason` -> ToolError | `test_move_task_archived_without_archival_reason_raises_tool_error` | Yes. The mocked AgentView raises `ValidationError`, and the adapter maps it to `ToolError`. | COVERED |
| `start_work`: id forwarded; SingleTaskResponse returned | `test_start_work_forwards_id_to_agent_view`, `test_start_work_returns_single_task_response` | Yes. Exact call assertion plus response-type assertion. | COVERED |
| `start_work`: already claimed -> ConcurrencyError -> ToolError | `test_start_work_already_claimed_raises_tool_error` | Yes. | COVERED |
| `start_work`: archived / blocked -> ToolError | `test_start_work_archived_task_raises_tool_error`, `test_start_work_blocked_task_raises_tool_error` | Yes. | COVERED |
| `end_work`: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned | `test_end_work_all_params_forwarded_to_agent_view`, `test_end_work_forwards_non_null_archival_fields`, `test_end_work_returns_single_task_response` | Yes. The first test proves id/outcome/move_to/note/block_reason plus null archival fields; the second proves non-null archival forwarding; the third proves response type. | COVERED |
| `end_work`: outcome=`success` auto-advance; outcome=`reject`; outcome=`release` idempotent | `test_end_work_success_auto_advance`, `test_end_work_reject_with_move_to`, `test_end_work_release_idempotent` | Yes. | COVERED |
| `end_work`: outcome=`block` with `block_reason`; without -> ToolError | `test_end_work_block_with_block_reason`, `test_end_work_block_without_block_reason_raises_tool_error` | Yes. The positive pass-through is explicit, and the missing-reason case now asserts the human-readable wire text instead of an `ERR_*` code. | COVERED |
| `end_work`: forbidden-parameter matrix — success+move_to, release+move_to, success+archival_*, non-block+block_reason -> ToolError | `TestFromAC_EndWorkForbiddenMatrix`, including `test_fail_with_block_reason_raises_tool_error` | Yes. The missing `fail + block_reason` gap from the prior review is now covered. | COVERED |
| Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message | `TestFromAC_KanbanErrorMapping`, `TestFromAC_ErrorMapping` in `test_mcp_guidance_1089.py` | Yes. Lifecycle tests cover move/start/end subclasses; the adjacent guidance suite asserts exact/no-code wire behavior for the same adapter layer. | COVERED |
| All tests fail (RED phase) | Historical Test-Writer notes in the task body | Historical prior-stage evidence only, but it satisfies the RED-phase provenance requirement for this TDD task. | COVERED |

#### Security Review
- No security issues found in the reviewed scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| Task-owned `TestFromAC_*` lifecycle suite plus adjacent guidance error-mapping suite | The architect-requested refinements are present: human-readable `block_reason` wire assertion, non-null archival forwarding, and `fail + block_reason` in the forbidden matrix. Latest builder notes report no test-file edits in this cycle. | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | Forwarding tests use exact `assert_called_once_with(...)`; guidance tests assert exact `ToolError` text / no `ERR_*` code on wire. |
| Negative/error-path coverage | STRONG | Already-claimed, archived, blocked, forbidden-matrix, and error-mapping paths are covered, including the prior missing `fail + block_reason` case. |
| Manual mutation reasoning | ADEQUATE | Dropping non-null archival forwarding or allowing `fail + block_reason` would now fail task-owned tests. |
| Test independence | STRONG | The suite uses isolated `MagicMock` fixtures and per-test context setup. |
| Descriptive names | STRONG | Test names remain directly AC-aligned. |

#### Data Safety
- No data-safety issues found.

#### Implementation-Aware Gaps
- No current implementation defect was reproduced.
- Current source aligns with the refined AC and prior review concerns:
  - `_invoke_view_move_task(...)` forwards archival fields and maps `KanbanError` to `ToolError(user_message)`.
  - `_invoke_engine_end_work(...)` now routes `outcome="release"` to `engine.release_task(...)` and passes archival parameters through on engine fallback.
  - Lifecycle tool metadata now advertises `SingleTaskResponse` for `move_task`, `edit_task`, `create_task`, `start_work`, and `end_work`.
- Compatibility-branch coverage remains partial at the module level, but the latest Architecture Review bound that as cross-task context rather than a blocker for task 1088.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 4 |
| Prior Review Evidence sections before this review | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- Parallel fan-out partially failed because the `code-reader` subagent returned no response. I fell back to a direct sequential file review against the current source and test files.
- The broader module coverage figure remains low, but after the loop-breaker refinement it is context rather than a task-owned failure condition.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| `move_task`: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:132-164`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:234-257,336-356,587-600` | `test_move_task_forwards_id_and_status_to_agent_view`; `test_move_task_forwards_archival_reason_and_refs`; `test_move_task_returns_single_task_response` | PASS |
| `move_task`: `status="archived"` without `archival_reason` -> ToolError | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:166-178`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:357-365` | `test_move_task_archived_without_archival_reason_raises_tool_error` | PASS |
| `start_work`: id forwarded; SingleTaskResponse returned | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:202-215`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:447-482,587-600` | `test_start_work_forwards_id_to_agent_view`; `test_start_work_returns_single_task_response` | PASS |
| `start_work`: already claimed -> ConcurrencyError -> ToolError | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:217-227`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:452-469` | `test_start_work_already_claimed_raises_tool_error` | PASS |
| `start_work`: archived / blocked -> ToolError | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:229-247`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:452-469` | `test_start_work_archived_task_raises_tool_error`; `test_start_work_blocked_task_raises_tool_error` | PASS |
| `end_work`: all 7 params forwarded per Brief A §5.8; SingleTaskResponse returned | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:261-294,354-377`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:485-558,587-600` | `test_end_work_all_params_forwarded_to_agent_view`; `test_end_work_forwards_non_null_archival_fields`; `test_end_work_returns_single_task_response` | PASS |
| `end_work`: outcome=`success` auto-advance; outcome=`reject`; outcome=`release` idempotent | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:296-329`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:485-558`; `serve/kanban/src/owlbear_kanban/engine.py:1296-1371,2867-3015` | `test_end_work_success_auto_advance`; `test_end_work_reject_with_move_to`; `test_end_work_release_idempotent` | PASS |
| `end_work`: outcome=`block` with `block_reason`; without -> ToolError | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:331-352`; `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:408-428,449-473`; `serve/kanban/src/owlbear_kanban/engine.py:2945-2962` | `test_end_work_block_with_block_reason`; `test_end_work_block_without_block_reason_raises_tool_error` | PASS |
| `end_work`: forbidden-parameter matrix — success+move_to, release+move_to, success+archival_*, non-block+block_reason -> ToolError | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:440-580`; `serve/kanban/src/owlbear_kanban/engine.py:2882-3015` | `TestFromAC_EndWorkForbiddenMatrix` | PASS |
| Error mapping: all KanbanError subclasses mapped to MCP ToolError with user_message | `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:390-438`; `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:408-473`; `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:234-257,452-479,500-541` | `TestFromAC_KanbanErrorMapping`; `TestFromAC_ErrorMapping` | PASS |
| All tests fail (RED phase) | Historical Test-Writer notes in task body | Test-Writer notes | PASS |

### Deductions
- -0.04: `code-reader` subagent returned no response, so the review used the sequential fallback path.
- -0.03: scoped module coverage remains 53%, though the latest Architecture Review scoped this out as non-blocking for task 1088.

### Confidence: 0.93
### Verdict: PASS
### Action: Advance to docs.
[[2026-04-28]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified/N/A | `serve/mcp-kanban/README.md` Tools table lists move_task/start_work/end_work with accurate descriptions; `end_work` already mentions `release` outcome. No edits needed. |
| 2 | Module docstrings | Yes | Verified/N/A | Checked `_invoke_view_move_task`, `_invoke_engine_end_work`, `move_task`, `start_work`, `end_work` — all have accurate, current docstrings. No edits needed. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body or builder notes. |
| 4 | Research doc | No | N/A | No research phase doc for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes `serve/mcp-kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes `serve/mcp-*/src/**`) both matched. Footers updated from `afe44251` → `d6e1c080`, commit `94160b4a`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` | IN (docstrings) | Verified — accurate, no edits |
| `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` | OUT (test file) | N/A |
| `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` | OUT (test file) | N/A |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer: `Last verified: 2026-04-28 (d6e1c080)`
- `share/diagrams/mcp-topology.excalidraw` — footer: `Last verified: 2026-04-28 (d6e1c080)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/1088-pytest.txt`
- `.owlbear/scratch/qr-1088-broader.txt`
- `.owlbear/scratch/qr-1088-pytest-scoped.txt`
- `.owlbear/scratch/qr-1088-pytest.txt`
- `.owlbear/scratch/qr-1088-ruff-scoped.txt`
- `.owlbear/scratch/qr-1088-ruff.txt`
- `.owlbear/scratch/qr-1088-scoped-pytest.txt`
- `.owlbear/scratch/qr-1088-scoped-ruff.txt`
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| move_task: id, status, archival_reason, archival_refs forwarded; SingleTaskResponse returned | Reviewer AC table PASS; tests at L132-164 | PASS |
| move_task: status=archived without archival_reason -> ToolError (AC4) | Reviewer PASS; adapter guard at server.py L334-338 | PASS |
| start_work: id forwarded; SingleTaskResponse returned | Reviewer PASS; tests at L202-215 | PASS |
| start_work: already claimed -> ConcurrencyError -> ToolError | Reviewer PASS; test at L217-227 | PASS |
| start_work: archived / blocked -> ToolError | Reviewer PASS; tests at L229-247 | PASS |
| end_work: all 7 params forwarded; SingleTaskResponse returned | Reviewer PASS; spot-checked non-null archival test at L355-377 confirms archival_reason="completed", archival_refs=[100] forwarded | PASS |
| end_work: outcome=success/reject/release | Reviewer PASS; tests at L296-329 | PASS |
| end_work: outcome=block with/without block_reason | Reviewer PASS; spot-checked wire-format fix at L340-353: human-readable user_message, no ERR_ code on wire per section 7 | PASS |
| end_work: forbidden-parameter matrix | Reviewer PASS; spot-checked fail+block_reason test at L566 confirms architect refinement present | PASS |
| Error mapping: KanbanError -> ToolError with user_message | Reviewer PASS; sibling guidance suite consistent | PASS |
| All tests fail (RED phase) | Historical test-writer notes in task body | PASS |

### Test Results
- Full suite: 2771 passed, 115 failed, 4 skipped
- 0 failures in task scope (test_mcp_lifecycle_tools.py and test_mcp_guidance_1089.py all green)
- 115 failures are pre-existing in other modules (corruption, storage, engine_init, react-compiler, mcp-knowledge, guidance_973/980)
- ruff: clean (8 advisory violations, none in task scope)

### Architect Quality: 3/5
Original AC had 11 lines, mostly specific. However, 3 precision gaps (missing fail+block_reason in forbidden matrix, wire-format ambiguity for error mapping, no non-null archival forwarding requirement) caused 3 review failures before architect intervention with targeted refinements. The architect's loop-breaker response was well-targeted and broke the cycle effectively.

### Deduction Breakdown
- AC quality 3/5: -0.03
- No other deductions (all AC lines have evidence, lint clean, reviewer evidence present and detailed, no task-scope failures)

### Confidence: 0.97
### Action: Archive