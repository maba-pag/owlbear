---
id: 1089
title: 'A-09: RED — guidance + error mapping tests'
status: review
priority: needed
created: '2026-04-21 10:54:09.278833+00:00'
updated: '2026-04-24 19:34:10.309435+00:00'
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
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §7 "guidance field", paper-integration.md §3.6–§3.7
Module: `serve/mcp-kanban/tests/test_mcp_guidance.py`

Test guidance field passthrough and the KanbanError → MCP ToolError error-mapping layer. Guidance is an engine-generated `list[str]` on every response envelope — the adapter must pass it through unmodified. Error mapping: every KanbanError subclass (ValidationError, NotFoundError, ConcurrencyError) maps to MCP `ToolError(user_message)`. Tests mock AgentView.

## Acceptance Criteria

- [ ] Guidance passthrough: engine returns guidance strings → adapter includes them in MCP response unmodified
- [ ] show_task section occurrence count guidance (AC12) passes through
- [ ] pick_tasks dispatch hints pass through
- [ ] create_task/edit_task body size warning (>100 KB) passes through
- [ ] move_task / end_work skip-transition warning passes through (AC-NEW-5)
- [ ] end_work(outcome="block") Action-Request/Decision-Request hint passes through (AC-NEW-4)
- [ ] Error mapping: ValidationError → ToolError (user_message only, no code on wire per §7)
- [ ] Error mapping: NotFoundError → ToolError
- [ ] Error mapping: ConcurrencyError → ToolError (e.g. already-claimed)
- [ ] All tests fail (RED phase)
[[2026-04-24]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_guidance_1089.py
- Classes: TestFromAC_GuidancePassthrough, TestFromAC_ErrorMapping
- Tests per category: happy 2, edge 3, error 3, boundary 3
- Total: 11 tests, all FAIL
- ruff: clean

**AC coverage table:**

| AC | Test |
|---|---|
| Guidance passthrough (base) | test_show_task_guidance_passes_through_unmodified |
| show_task section occurrence count (AC12) | test_show_task_section_occurrence_count_guidance |
| pick_tasks dispatch hints | test_pick_tasks_dispatch_hints_guidance |
| create_task body size warning >100 KB | test_create_task_body_size_warning_guidance |
| edit_task body size warning >100 KB | test_edit_task_body_size_warning_guidance |
| move_task skip-transition warning (AC-NEW-5) | test_move_task_skip_transition_warning_guidance |
| end_work(reject) skip-transition warning (AC-NEW-5) | test_end_work_reject_skip_transition_warning_guidance |
| end_work(block) AR/DR hint (AC-NEW-4) | test_end_work_block_action_request_hint_guidance |
| ValidationError → ToolError (user_message only) | test_validation_error_maps_to_tool_error |
| NotFoundError → ToolError | test_not_found_error_maps_to_tool_error |
| ConcurrencyError → ToolError, no code on wire | test_concurrency_error_maps_to_tool_error_user_message_only |

**Failure modes:**
- Guidance tests: server calls engine.show_task/create_task/etc. directly; never calls engine.agent_view(); returns guidance=[] instead of AgentView envelope guidance
- Error mapping tests: KanbanError subclasses (ValidationError, NotFoundError, ConcurrencyError) propagate uncaught — adapter only catches ValueError and FileNotFoundError

**Commit:** f02635ee
[[2026-04-24]]
## Builder Notes
- Verdict: REJECT to test-writer due interface-contract mismatch in TestFromAC suite.
- RED evidence: quality-runner reports all 11 tests in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` fail at fixture setup with `ConfigError: agent_map missing status entries` during `KanbanEngine(...)` init.
- Blocking mismatch #1 (interface): `test_validation_error_maps_to_tool_error` invokes `create_task(ctx, title="Test task", status="flying")`, but MCP `create_task` intentionally has no `status` parameter (D50).
- Corroborating contract evidence:
  - `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py` asserts `create_task` must not accept `status`.
  - `serve/mcp-kanban/tests/test_mcp_models_1084.py` asserts `CreateTaskParams` has no `status` field.
  - `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` defines `create_task(title, body, depends_on, parent, priority, tags)` only.
- Blocking mismatch #2 (test setup): inline legacy config in `test_mcp_guidance_1089.py` omits `agent_map`; current engine/model validation rejects this at initialization, so guidance/error assertions never execute.
- Test-writer: please rewrite RED tests to align with the approved MCP contract:
  - Remove any `create_task(..., status=...)` expectation.
  - Avoid fixture setup paths that fail before assertions (either provide an engine-initializable config or use a pure mocked context when engine behavior is not under test).
  - Keep scope on AC #1089: guidance passthrough from AgentView envelopes and `KanbanError -> ToolError(user_message)` mapping without changing create_task surface.

[[2026-04-24]]
## Test-Writer Notes (retry)
- Test file: `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`
- Classes: `TestFromAC_GuidancePassthrough`, `TestFromAC_ErrorMapping`
- Total: **11 tests, all FAIL** ✓
- ruff: clean ✓
- Commit: 1ce9d252

**Builder rejection fixes applied:**
1. Added full `agent_map` to inline config (all 7 statuses) — resolves `ConfigError: agent_map missing status entries`
2. Replaced `create_task(ctx, title="Test task", status="flying")` with `create_task(ctx, title="")` — no `status` param, aligns with MCP contract (D50)

**AC coverage table:**

| AC | Test |
|---|---|
| Guidance passthrough (base) | test_show_task_guidance_passes_through_unmodified |
| show_task section occurrence count (AC12) | test_show_task_section_occurrence_count_guidance |
| pick_tasks dispatch hints | test_pick_tasks_dispatch_hints_guidance |
| create_task body size warning >100 KB | test_create_task_body_size_warning_guidance |
| edit_task body size warning >100 KB | test_edit_task_body_size_warning_guidance |
| move_task skip-transition warning (AC-NEW-5) | test_move_task_skip_transition_warning_guidance |
| end_work(reject) skip-transition warning (AC-NEW-5) | test_end_work_reject_skip_transition_warning_guidance |
| end_work(block) AR/DR hint (AC-NEW-4) | test_end_work_block_action_request_hint_guidance |
| ValidationError → ToolError (user_message only) | test_validation_error_maps_to_tool_error |
| NotFoundError → ToolError | test_not_found_error_maps_to_tool_error |
| ConcurrencyError → ToolError, no code on wire | test_concurrency_error_maps_to_tool_error_user_message_only |

**Failure modes (correct RED reasons):**
- Guidance tests: `AgentView` methods not yet implemented (TypeError on unexpected kwargs `section`, `body`, wave params); adapter fallback sentinel detected instead of AgentView-sourced strings
- Error mapping tests: `ConcurrencyError` not yet raised (engine raises `ValueError("Task '1' is already claimed")` — no "by another agent" fragment); `ValidationError`/`NotFoundError` not mapped to `ToolError` by adapter
[[2026-04-24]]
## Builder Notes
- Implementation: `serve/kanban/src/owlbear_kanban/engine.py` (implemented `AgentView` methods for MCP-facing envelopes, guidance passthrough, and KanbanError mapping)
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`
- Tests: 11 TestFromAC tests passed in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`
- Coverage: not run in final scoped verification pass
- ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`
- Evidence summary: fixed guidance passthrough for show/create/edit/move/end_work/pick and mapped not-found/validation/concurrency paths to `KanbanError` subclasses so MCP adapter emits `ToolError(user_message)`.
- Fixes applied:
  - Replaced `AgentView` stubs with concrete methods returning `ShowTaskResponse`, `SingleTaskResponse`, `PickTasksResponse`, and `ListTasksResponse`
  - Added section-aware `show_task(..., section=...)` behavior with duplicate-section occurrence guidance
  - Added oversized-body guidance (>100 KB) for create/edit flows
  - Added skip-transition guidance for move/reject transitions and block DR hint guidance for end_work(block)
  - Converted engine `FileNotFoundError`/`ValueError` branches into `NotFoundError`/`ValidationError`/`ConcurrencyError` in AgentView
- Reflection:
  - Problem faced: reject skip-count guidance expected different semantics than move guidance.
  - Workaround applied: used a dedicated `include_target_column` mode for reject guidance to match AC/test contract.
  - Pattern discovered: MCP adapter tests depend on AgentView being the guidance source; fallback guidance is intentionally patch-detectable.
  - Quality gap prevented: normalized ValueError pathways to typed `KanbanError` subclasses to avoid raw exception leakage at adapter boundaries.
[[2026-04-24]]
## Review Evidence
### Test Results
- Scoped pytest on `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`: 11 passed, 0 failed.
- Broader engine rerun used only to correct module coverage scope: 478 passed, 36 failed, 220 errors. Those broader failures are background drift and config debt, not the gating evidence for this task.

### Lint
- Scoped ruff on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`: clean.

### Coverage
- Task-only coverage against the 1089 suite measured 49% for `owlbear_kanban.engine` and undercounted the shared module.
- Corrected broader engine coverage measured `owlbear_kanban.engine` at 93%, so module coverage is not the blocker.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would fail if AC were violated? | Verdict |
|---------|-------------|----------------------------------|---------|
| Guidance passthrough unmodified | `test_show_task_guidance_passes_through_unmodified` | No. The docstring at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:231` says unmodified passthrough, but the assertion at `:241` checks only that guidance is a list. | FAIL |
| show_task section occurrence count guidance | `test_show_task_section_occurrence_count_guidance` | No. The engine emits a concrete count message at `serve/kanban/src/owlbear_kanban/engine.py:1640`, but the assertion at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:223` only checks for any guidance element containing `2`. | FAIL |
| pick_tasks dispatch hints | `test_pick_tasks_dispatch_hints_guidance` | No. The engine emits a specific dispatch hint at `serve/kanban/src/owlbear_kanban/engine.py:1686`, but the assertion at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:259` only checks that guidance is non-empty. | FAIL |
| create_task/edit_task body-size warning | `test_create_task_body_size_warning_guidance`, `test_edit_task_body_size_warning_guidance` | No. Assertions at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:278` and `:297` use substring containment against the warning constant at `serve/kanban/src/owlbear_kanban/engine.py:1522`, so transformed wire strings would still pass. | FAIL |
| move_task / end_work skip-transition warning | `test_move_task_skip_transition_warning_guidance`, `test_end_work_reject_skip_transition_warning_guidance` | Yes. Exact equality is asserted at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:321` and `:348`. | PASS |
| end_work(block) DR hint | `test_end_work_block_action_request_hint_guidance` | Yes. Exact equality at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:379` plus the fallback-sentinel patch proves the AgentView path is the source. | PASS |
| ValidationError maps to ToolError with user_message only | `test_validation_error_maps_to_tool_error` | No. The test checks ToolError at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:405` and generic text at `:408`, but never enforces the no-code-on-wire part of the AC. | FAIL |
| NotFoundError maps to ToolError | `test_not_found_error_maps_to_tool_error` | No. Only the `show_task` missing-task path is exercised at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:425`; `move_task` and `start_work` missing-task handling are broken in the implementation at `serve/kanban/src/owlbear_kanban/engine.py:1788` and `:1803`. | FAIL |
| ConcurrencyError maps to ToolError | `test_concurrency_error_maps_to_tool_error_user_message_only` | Yes for the already-claimed path. Assertions at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:450`, `:453`, and `:457` prove user-message-only wire text. | PASS |
| RED proof recorded before GREEN | Test-Writer retry note in the task body | Historical only. The retry note records 11 failing tests before builder work. | PASS |

#### Security Review
- No task-specific security issues found.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` | Builder notes report only `serve/kanban/src/owlbear_kanban/engine.py` changed; I found no evidence of builder weakening the TestFromAC file. | PRESERVED |
| `test_show_task_guidance_passes_through_unmodified` | Current assertion is weaker than its own stated intent. | CURRENT PROOF WEAK |
| `test_pick_tasks_dispatch_hints_guidance` | Current assertion is weaker than its own stated intent. | CURRENT PROOF WEAK |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:223`, `:241`, `:259`, `:278`, `:297`, `:408` |
| Negative/error-path coverage | WEAK | Generic not-found mapping is not proven beyond `show_task`; the hidden bug at `serve/kanban/src/owlbear_kanban/engine.py:1788` and `:1803` survives. |
| Manual mutation reasoning | WEAK | Any non-empty dispatch hint still passes at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:259`; machine-code leakage on the validation path still passes at `:408`. |
| Test independence | STRONG | Fresh `tmp_path`-backed `AppContext` fixtures per test. |
| Descriptive names | STRONG | Test names map clearly to AC clauses. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- Real implementation defect: `_wrap_not_found` accepts only `task_id` at `serve/kanban/src/owlbear_kanban/engine.py:1563`, but `move_task` and `start_work` call it with an extra exception object at `:1788` and `:1803`. On those missing-task paths the intended `NotFoundError` mapping becomes a `TypeError`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- Broader engine coverage is 93%, but the broader rerun also surfaced unrelated drift such as legacy `agent_name=` constructor callers and stale AgentView-stub expectations. I used the scoped 1089 run for task-specific pass/fail and the broader rerun only to correct coverage scope.
- Divergence note: code-reader treated the weak TestFromAC assertions as an integrity concern. I am scoring that as a test-quality/proof problem, not a builder-immutability violation, because the task body reports only `engine.py` changed in the builder pass.
- Non-blocking taxonomy issue: empty-title validation uses `ERR_INVALID_STATUS` at `serve/kanban/src/owlbear_kanban/engine.py:1701` for a title problem; the wire contract still hides the code.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Guidance passthrough unmodified | `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:231`, `:241` prove only list type, not unmodified wire value. | `test_show_task_guidance_passes_through_unmodified` | FAIL |
| show_task section occurrence count guidance | Exact message exists at `serve/kanban/src/owlbear_kanban/engine.py:1640`; test at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:223` checks only digit presence. | `test_show_task_section_occurrence_count_guidance` | FAIL |
| pick_tasks dispatch hints | Exact message exists at `serve/kanban/src/owlbear_kanban/engine.py:1686`; test at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:259` checks only non-empty guidance. | `test_pick_tasks_dispatch_hints_guidance` | FAIL |
| create_task/edit_task body-size warning | Warning constant at `serve/kanban/src/owlbear_kanban/engine.py:1522`; tests at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:278` and `:297` use substring containment only. | `test_create_task_body_size_warning_guidance`, `test_edit_task_body_size_warning_guidance` | FAIL |
| move_task / end_work skip-transition warning | Exact equality at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:321` and `:348`. | `test_move_task_skip_transition_warning_guidance`, `test_end_work_reject_skip_transition_warning_guidance` | PASS |
| end_work(block) DR hint | Exact equality at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:379`. | `test_end_work_block_action_request_hint_guidance` | PASS |
| ValidationError maps to ToolError with user_message only | Adapter maps `KanbanError` to `ToolError(exc.user_message)` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:452-453`, but the task test never proves no-code wire behavior on the validation path. | `test_validation_error_maps_to_tool_error` | FAIL |
| NotFoundError maps to ToolError | Generic not-found contract is broken for `move_task` and `start_work` by `serve/kanban/src/owlbear_kanban/engine.py:1788` and `:1803`. | `test_not_found_error_maps_to_tool_error` | FAIL |
| ConcurrencyError maps to ToolError | Adapter mapping at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:438-439`; no-code assertion at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:457`. | `test_concurrency_error_maps_to_tool_error_user_message_only` | PASS |
| All tests fail in RED phase | Historical Test-Writer evidence in task body shows 11 failing tests before builder work. | Test-Writer retry note | PASS |

### Confidence: 0.62
### Verdict: FAIL
[[2026-04-24]]
## Builder Notes
- Implementation: fixed AgentView not-found mapping arity in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1788) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1803) so `move_task`/`start_work` raise `NotFoundError` instead of `TypeError` on missing IDs.
- Files changed: [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py)
- Tests (task-gating scoped): 40 passed, 0 failed
  - [serve/mcp-kanban/tests/test_mcp_guidance_1089.py](serve/mcp-kanban/tests/test_mcp_guidance_1089.py)
  - [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py)
- Coverage:
  - Scoped run: 49% on `owlbear_kanban.engine` (expected undercount from narrow test slice)
  - Broader package-scoped contextual run: 92% on `owlbear_kanban.engine`
- Lint: clean (ruff) on touched source and scoped test paths
- Evidence summary: missing-task branches now consistently map to `NotFoundError` for MCP adapter `ToolError(user_message)` conversion; regression paths covered by lifecycle tool tests remain green.

- Reflection:
  - Problem faced: task `TestFromAC` suite already passed at entry (false-green), while review reported a real uncovered runtime defect.
  - Workaround applied: patched only the two erroneous arity call sites instead of broad AgentView changes.
  - Pattern discovered: adapter-level mapping defects can hide behind green task suites when assertion strictness is low.
  - Quality gap noted: broader package run still has unrelated legacy drift (`KanbanEngine(..., agent_name=...)` fixture usage); treated as non-gating background debt for this builder scope.
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on serve/mcp-kanban/tests/test_mcp_guidance_1089.py and serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py: 40 passed, 0 failed, 0 skipped.
- quality-runner broad run for module coverage: 1788 passed, 205 failed, 2 skipped, 220 setup errors from unrelated background drift. Used only for module coverage context.

### Lint
- clean on serve/kanban/src/owlbear_kanban/engine.py plus the two review-scoped test files.

### Coverage
- scoped slice: owlbear_kanban.engine 49%.
- broad module-level run: owlbear_kanban.engine 92%.
- coverage is not the blocker.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would fail if AC were violated? | Verdict |
|---|---|---|---|
| Guidance passthrough unmodified | test_show_task_guidance_passes_through_unmodified | No. serve/mcp-kanban/tests/test_mcp_guidance_1089.py:241 only checks list type. | FAIL |
| show_task section occurrence count guidance | test_show_task_section_occurrence_count_guidance | No. serve/mcp-kanban/tests/test_mcp_guidance_1089.py:223 only checks that some guidance contains `2`; serve/kanban/src/owlbear_kanban/engine.py:1640 builds a concrete message. | FAIL |
| pick_tasks dispatch hints pass through | test_pick_tasks_dispatch_hints_guidance | No. serve/mcp-kanban/tests/test_mcp_guidance_1089.py:259 only checks non-empty guidance; serve/kanban/src/owlbear_kanban/engine.py:1686 builds a concrete message. | FAIL |
| create_task/edit_task body-size warning passes through | test_create_task_body_size_warning_guidance; test_edit_task_body_size_warning_guidance | No. serve/mcp-kanban/tests/test_mcp_guidance_1089.py:278 and :297 use substring membership against serve/kanban/src/owlbear_kanban/engine.py:1522. Wrapped or transformed wire text would still pass. | FAIL |
| move_task/end_work skip-transition warning passes through | test_move_task_skip_transition_warning_guidance; test_end_work_reject_skip_transition_warning_guidance | Yes. Exact equality at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:321 and :348. | PASS |
| end_work(block) DR hint passes through | test_end_work_block_action_request_hint_guidance | Yes. Exact equality at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:379 against serve/kanban/src/owlbear_kanban/engine.py:1524. | PASS |
| ValidationError maps to ToolError with user_message only and no code on wire | test_validation_error_maps_to_tool_error | No. serve/mcp-kanban/tests/test_mcp_guidance_1089.py:408 checks only loose wording, while serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:352 still expects ERR_BLOCK_REASON_REQUIRED on wire. | FAIL |
| NotFoundError maps to ToolError | test_not_found_error_maps_to_tool_error | Yes. Live missing-task path is exercised at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:413 and :428; user message is built at serve/kanban/src/owlbear_kanban/engine.py:1566. | PASS |
| ConcurrencyError maps to ToolError | test_concurrency_error_maps_to_tool_error_user_message_only | Yes. serve/mcp-kanban/tests/test_mcp_guidance_1089.py:457 proves code absence; user message is built at serve/kanban/src/owlbear_kanban/engine.py:1809. | PASS |
| All tests fail in RED phase | task body history only | No executable artifact remains in scope beyond task prose. | FAIL |

#### Security Review
- No task-specific security issues found in AgentView response shaping or MCP ToolError mapping paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| serve/mcp-kanban/tests/test_mcp_guidance_1089.py | No in-scope evidence of builder edits to TestFromAC assertions. Current builder scope was serve/kanban/src/owlbear_kanban/engine.py only. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | serve/mcp-kanban/tests/test_mcp_guidance_1089.py:241, :259, :278, :297, :408 |
| Negative/error-path coverage | ADEQUATE | validation, not-found, and concurrency paths exist, but the validation wire contract is not proven precisely |
| Manual mutation resistance | WEAK | duplicate-section, dispatch-hint, and body-warning strings can change materially without failing the task-owned assertions |
| Test independence | STRONG | tmp_path-backed app_ctx fixtures and isolated mock fixtures in the lifecycle suite |
| Descriptive names | STRONG | names track AC clauses clearly |
| Contract consistency | WEAK | serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:352 expects an error code on wire, conflicting with this task's no-code-on-wire contract |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No implementation blocker found in current scope. The prior missing-task mapping defect was fixed, the scoped regression suite is green, and module-level engine coverage is 92.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- Full-suite failures and setup errors in the broad run are existing background drift, not task 1089 gating evidence.
- The remaining blocker is proof quality: the implementation now appears aligned with the written AC, but several TestFromAC assertions are too loose to enforce that contract.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Guidance passthrough unmodified | serve/mcp-kanban/tests/test_mcp_guidance_1089.py:241 proves only list type, not unmodified wire content | test_show_task_guidance_passes_through_unmodified | FAIL |
| show_task section occurrence count guidance | serve/mcp-kanban/tests/test_mcp_guidance_1089.py:223 checks only digit presence; serve/kanban/src/owlbear_kanban/engine.py:1640 constructs the exact message | test_show_task_section_occurrence_count_guidance | FAIL |
| pick_tasks dispatch hints pass through | serve/mcp-kanban/tests/test_mcp_guidance_1089.py:259 checks only non-empty guidance; serve/kanban/src/owlbear_kanban/engine.py:1686 constructs the exact message | test_pick_tasks_dispatch_hints_guidance | FAIL |
| create_task/edit_task body size warning passes through | serve/mcp-kanban/tests/test_mcp_guidance_1089.py:278 and :297 use substring matches against serve/kanban/src/owlbear_kanban/engine.py:1522 | test_create_task_body_size_warning_guidance; test_edit_task_body_size_warning_guidance | FAIL |
| move_task/end_work skip-transition warning passes through | exact equality at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:321 and :348 | test_move_task_skip_transition_warning_guidance; test_end_work_reject_skip_transition_warning_guidance | PASS |
| end_work(block) DR hint passes through | exact equality at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:379 | test_end_work_block_action_request_hint_guidance | PASS |
| ValidationError maps to ToolError with user_message only and no code on wire | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:453 maps KanbanError.user_message, but serve/mcp-kanban/tests/test_mcp_guidance_1089.py:408 does not prove code absence and serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:352 contradicts the AC | test_validation_error_maps_to_tool_error | FAIL |
| NotFoundError maps to ToolError | live ToolError expectation at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:425 and message check at :428 | test_not_found_error_maps_to_tool_error | PASS |
| ConcurrencyError maps to ToolError | user phrase check and code absence at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:450 and :457 | test_concurrency_error_maps_to_tool_error_user_message_only | PASS |
| All tests fail in RED phase | task body contains only historical prose, not a retained failing run artifact | historical Test-Writer notes | FAIL |

### Confidence: 0.78
### Verdict: FAIL

Action: return to todo. The implementation appears corrected, but the TestFromAC proof still does not enforce multiple AC lines strongly enough.
[[2026-04-24]]
## Test-Writer Notes (retry 2)
- Test file: `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`
- Classes: `TestFromAC_GuidancePassthrough`, `TestFromAC_ErrorMapping`
- Total: **11 tests, all PASS** (implementation is green; assertions now prove AC exactly)
- ruff: clean ✓

**Changes from reviewer FAIL (retry 2):**
Reviewer cited 5 weak-assertion AC lines and returned to todo. All 5 tightened:

1. `test_show_task_section_occurrence_count_guidance`: `any("2" in g...)` → exact equality `["Section 'Audit' matched 2 occurrences; returning the first section."]`
2. `test_show_task_guidance_passes_through_unmodified`: `isinstance(list)` → `patch.object(AgentView, "show_task", return_value=sentinel)` + exact equality proving no adapter transformation
3. `test_pick_tasks_dispatch_hints_guidance`: `len > 0` → exact equality `["Dispatch hints: 3 task(s) across 1 wave(s)."]`
4. `test_create/edit_task_body_size_warning_guidance`: `any(warning in g...)` → exact equality `[_BODY_SIZE_WARNING]`
5. `test_validation_error_maps_to_tool_error`: added `assert not any(word.startswith("ERR_") for word in error_text.split())` — proves no machine code on wire per §7

**New imports added:** `AgentView` from `owlbear_kanban.engine`, `ShowTaskResponse` from `owlbear_kanban.models`
**New module-level constants:** `_SECTION_OCCURRENCE_MSG`, `_PICK_DISPATCH_HINT`

**AC coverage table:**

| AC | Test | Assertion strength |
|---|---|---|
| Guidance passthrough unmodified | test_show_task_guidance_passes_through_unmodified | sentinel mock + exact equality |
| show_task section occurrence count (AC12) | test_show_task_section_occurrence_count_guidance | exact string equality |
| pick_tasks dispatch hints | test_pick_tasks_dispatch_hints_guidance | exact string equality |
| create_task body size warning >100 KB | test_create_task_body_size_warning_guidance | exact list equality |
| edit_task body size warning >100 KB | test_edit_task_body_size_warning_guidance | exact list equality |
| move_task skip-transition warning (AC-NEW-5) | test_move_task_skip_transition_warning_guidance | exact equality (unchanged) |
| end_work(reject) skip-transition warning | test_end_work_reject_skip_transition_warning_guidance | exact equality (unchanged) |
| end_work(block) AR/DR hint (AC-NEW-4) | test_end_work_block_action_request_hint_guidance | exact equality (unchanged) |
| ValidationError → ToolError (user_message only, no ERR_ code) | test_validation_error_maps_to_tool_error | phrase check + ERR_* absence |
| NotFoundError → ToolError | test_not_found_error_maps_to_tool_error | ToolError raised + message check |
| ConcurrencyError → ToolError, no code on wire | test_concurrency_error_maps_to_tool_error_user_message_only | phrase + code absence |
[[2026-04-24]]
## Builder Notes
- Implementation: no code changes required in this retry; verification-only pass after test-writer tightened assertions.
- Files changed: none.
- Tests (quality-runner, scoped):
  - `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`: 11 passed, 0 failed
  - Additional regression scope: `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` + `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py` + `serve/kanban/tests/test_engine_activity.py`: 67 passed, 0 failed
- Lint: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`, and `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`.
- Coverage evidence:
  - Narrow task-only slice undercounts shared module coverage (`owlbear_kanban.engine` 49% in single-file run; 64% in 3-file scoped regression run).
  - Prior module-level contextual evidence recorded in task history remains `owlbear_kanban.engine` 92% for broader package scope.
- Evidence summary: tightened assertions (exact equality and ERR_* absence checks) hold on current implementation; no regressions observed in the related lifecycle/activity slices.

- Reflection:
  - Problem faced: task-owned assertion hardening improved proof quality but narrowed slice still under-represents shared-module coverage.
  - Workaround applied: ran a second scoped regression batch on adjacent lifecycle/activity suites for stronger GREEN confidence.
  - Pattern discovered: adapter-contract tasks often require dual evidence (strict task tests + broader contextual coverage) to avoid false confidence from narrow slices.
  - Quality gap noted: full-suite background drift remains outside this task scope and should stay non-gating for scoped builder verification.
