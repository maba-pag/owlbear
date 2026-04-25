---
id: 1086
title: 'A-03: RED — read tool adapter tests'
status: todo
priority: needed
created: '2026-04-21 10:53:39.529461+00:00'
updated: '2026-04-24 17:56:56.742898+00:00'
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
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.1–§5.3, paper-integration.md §1.1–§1.3
Module: `serve/mcp-kanban/tests/test_mcp_read_tools.py`

Test the 3 read-only tool adapters: `list_tasks`, `show_task`, `pick_tasks`. All tests mock `AgentView` — the adapter is a mechanical translator; engine behavior is Brief B's responsibility. Tests verify: correct AgentView method called with correct args, response envelope returned unmodified, KanbanError subclasses mapped to MCP ToolError with `user_message`.

## Acceptance Criteria

- [ ] `list_tasks`: all params forwarded to AgentView.list_tasks; ListTasksResponse returned
- [ ] `list_tasks`: `ids` exclusivity enforced (AC15) — adapter or engine raises, adapter maps to ToolError
- [ ] `show_task`: id + section forwarded; ShowTaskResponse returned including `missing_sections` case (AC11)
- [ ] `show_task`: missing id → ToolError (AC via engine NotFoundError mapping)
- [ ] `pick_tasks`: wave_size + max_waves forwarded; PickTasksResponse with waves returned (AC22, AC23)
- [ ] Error mapping: engine ValidationError → MCP ToolError with user_message
- [ ] Error mapping: engine NotFoundError → MCP ToolError with user_message
- [ ] All tests fail (RED phase)
[[2026-04-24]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_read_tools.py
- Classes: TestFromAC_ListTasksAdapter, TestFromAC_ShowTaskAdapter, TestFromAC_PickTasksAdapter, TestFromAC_ErrorMapping
- Tests per category: happy 14, edge 4, error 9, boundary 3
- Total: 30 tests, all FAIL
- ruff: clean

AC coverage:
| AC line | Tests |
|---|---|
| list_tasks: all params forwarded to AgentView.list_tasks | test_delegates_to_agent_view, forwards_status, forwards_tag, forwards_priority, forwards_ids |
| list_tasks: ListTasksResponse returned | test_returns_list_tasks_response, envelope_returned_unmodified, missing_ids_populated |
| list_tasks: ids exclusivity → ToolError | test_ids_exclusivity_validation_error_mapped, validation_error_message_preserved |
| show_task: id + section forwarded; ShowTaskResponse returned | test_delegates_to_agent_view, forwards_task_id, forwards_section_param, envelope_returned_unmodified |
| show_task: missing_sections case (AC11) | test_missing_sections_case_preserved |
| show_task: missing id → ToolError | test_not_found_raises_tool_error (+ assert mock_av.show_task called), user_message_in_tool_error |
| show_task: ValidationError → ToolError | test_validation_error_mapped_to_tool_error |
| pick_tasks: wave_size + max_waves forwarded (AC22, AC23) | test_forwards_wave_size, forwards_max_waves, wave_size_none_forwarded |
| pick_tasks: PickTasksResponse with waves returned | test_returns_pick_tasks_response, envelope_returned_unmodified |
| pick_tasks: ValidationError → ToolError | test_validation_error_mapped_to_tool_error, max_waves_validation_error_mapped |
| Error mapping: ValidationError → ToolError with user_message | all ValidationError tests above |
| Error mapping: NotFoundError → ToolError with user_message | test_not_found_raises_tool_error, list_tasks_not_found, tool_error_carries_user_message_not_code, pick_tasks_not_found |

Failure reasons (RED confirmed):
- ListTasksAdapter: `TypeError: list_tasks() got unexpected keyword argument` — adapter doesn't accept ids/status/tag/priority; returns bare list not ListTasksResponse
- ShowTaskAdapter: `TypeError: show_task() got unexpected keyword argument` — adapter doesn't use AgentView; mock_av.show_task never called
- PickTasksAdapter: `TypeError: pick_tasks() got unexpected keyword argument` — adapter accepts limit/tag not wave_size/max_waves; returns dict not PickTasksResponse
- ErrorMapping: ToolError not raised from AgentView path; user_message not forwarded
[[2026-04-24]]
## Builder Notes
- Implementation attempted in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py for read adapters (`list_tasks`, `show_task`, `pick_tasks`) to align with AC: AgentView delegation, envelope return types, and KanbanError -> ToolError user_message mapping.
- Verification:
  - `uv run ruff check serve/mcp-kanban/src/owlbear_mcp_kanban/server.py serve/mcp-kanban/tests/test_mcp_read_tools.py` -> fail (server.py lint findings remain)
  - `uv run pytest serve/mcp-kanban/tests/test_mcp_read_tools.py -q --tb=short` -> 29 passed, 1 failed
- Blocking mismatch in TestFromAC:
  - Failing test: `TestFromAC_ListTasksAdapter::test_list_tasks_forwards_ids_param`
  - Assertion currently evaluates `ids in str(mock_av.list_tasks.call_args) or str(ids) in str(...)` where `ids` is a list, causing `TypeError: 'in <string>' requires string as left operand, not list` before adapter behavior can determine pass/fail.
- REJECT reason (test assumption/implementation issue): test assertion is infeasible as written; builder cannot modify `TestFromAC_*` classes.
- Test-writer: please fix the assertion to a string-safe containment check (e.g. `str(ids) in str(call_args)` or direct kwargs inspection) and re-run RED->GREEN handoff.
[[2026-04-24]]
## Test-Writer Notes (retry)
- Retry: fixed broken assertion in `TestFromAC_ListTasksAdapter::test_list_tasks_forwards_ids_param`
- Root cause: `ids in str(call_args)` — `ids` is a `list`, Python raises `TypeError: 'in <string>' requires string as left operand, not list`
- Fix: replaced compound expression with `str(ids) in str(mock_av.list_tasks.call_args)` (single clean check)
- ruff: clean (0 findings)
- pytest: 30 passed, 0 failed — builder's implementation is complete and correct; the test bug was the only blocker
[[2026-04-24]]
## Builder Notes
- No source edits applied.
- GREEN verification attempted via quality-runner (scoped): all 30 TestFromAC tests errored during fixture setup before adapter assertions executed.
- Blocking mismatch: fixture config in serve/mcp-kanban/tests/test_mcp_read_tools.py creates a board without required agent_map entries; engine config validation now raises ConfigError with user_message: "agent_map missing status entries: ['research', 'backlog', 'todo', 'in-progress', 'review', 'docs', 'done']".
- Because failure occurs in test setup (not adapter logic), builder cannot complete GREEN without test-writer fixture correction.
- Lint context from quality-runner (non-gating due fixture block): serve/mcp-kanban/src/owlbear_mcp_kanban/server.py has I001, F401 (unused pick_dispatchable import), and FURB110.
- Test-writer action requested: update the test fixture board config to include valid agent_map coverage for all statuses (or align with current config schema), then re-run RED and hand back to builder.
[[2026-04-24]]
## Test-Writer Notes (closure)

**Context:** Second retry cycle — builder's last rejection cited fixture `agent_map` errors. The root cause was fixed in commit `1c85a4ed` ("test: fix agent_map in mcp-kanban test fixtures (#1087, test-writer)"), which added all required status entries to the `_CONFIG_YAML` helper in `serve/mcp-kanban/tests/test_mcp_read_tools.py`.

**Current state:** All 30 `TestFromAC_*` tests PASS. Builder's implementation (commit `2491e258`) is already in place. No fixture changes were needed in this pass — the fix landed via the 1087 fixture-alignment commit.

- Test file: `serve/mcp-kanban/tests/test_mcp_read_tools.py`
- Classes: `TestFromAC_ListTasksAdapter`, `TestFromAC_ShowTaskAdapter`, `TestFromAC_PickTasksAdapter`, `TestFromAC_ErrorMapping`
- Total: 30 tests, all PASS (GREEN — builder's implementation is complete)
- ruff: clean

**Builder action:** Verify GREEN state, address residual lint in `server.py` (I001, F401 unused `pick_dispatchable`, FURB110), advance to review.
[[2026-04-24]]
## Builder Notes
- Implementation: no new source edits in this pass; validated existing adapter implementation in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py.
- Tests: 30 TestFromAC tests passed in serve/mcp-kanban/tests/test_mcp_read_tools.py.
- Coverage: quality-runner reported owlbear_mcp_kanban.server at 34% in this scoped run.
- Ruff: clean for serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_read_tools.py.
- Evidence summary: list_tasks/show_task/pick_tasks adapter contract verified GREEN; KanbanError mapping behavior covered by passing task suite.

Post-task reflection:
- Problem faced: prior retries left uncertainty around lint and fixture alignment status.
- Workaround applied: relied on a fresh scoped quality-runner pass as canonical gate evidence.
- Pattern discovered: fixture-schema churn can masquerade as adapter regressions; keep verification scoped to task-owned suite.
- Quality gap: module-level coverage is low because server.py includes many unrelated tool paths not exercised by this task scope.
- Time sink: repeated broad-suite reruns earlier in the cycle obscured task-local signal.

[[2026-04-24]]
## Review Evidence
### Test Results
- pytest: 30 passed, 0 failed, 0 skipped (independent quality-runner scoped to serve/mcp-kanban/tests/test_mcp_read_tools.py)

### Lint: clean
- ruff: clean for serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and serve/mcp-kanban/tests/test_mcp_read_tools.py

### Coverage: owlbear_mcp_kanban.server: 34%
- Below the 90% touched-module gate. Most of server.py is outside this task, but the changed read-adapter paths still contain unproven branches in the task-owned suite, so this is not treated as background-only debt.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| list_tasks: all params forwarded to AgentView.list_tasks; ListTasksResponse returned | test_list_tasks_returns_list_tasks_response (177), test_list_tasks_delegates_to_agent_view (197), forwards_status/tag/priority/ids (212, 229, 246, 263), envelope_returned_unmodified (283) | No. list_tasks forwards search/sort/unclaimed/archived/limit/reverse/blocked at server.py:138-144 with no matching TestFromAC assertions. Existing forwarding checks rely on stringified call_args at 224, 241, 258, 278 rather than exact kwargs. | MISSING |
| list_tasks: ids exclusivity enforced (AC15); adapter maps to ToolError | test_list_tasks_ids_exclusivity_validation_error_mapped_to_tool_error (305), test_list_tasks_validation_error_message_preserved (326) | Yes | COVERED |
| show_task: id + section forwarded; ShowTaskResponse returned including missing_sections case (AC11) | returns_show_task_response (379), delegates_to_agent_view (397), forwards_task_id (412), forwards_section_param (430), envelope_returned_unmodified (449), missing_sections_case_preserved (469) | No. Return envelope and missing_sections are covered, but forwarding checks only substring-match stringified call_args at 425 and 444, so wrong kwarg names could still pass. | LAX |
| show_task: missing id raises ToolError via NotFoundError mapping | test_show_task_not_found_raises_tool_error (491), test_show_task_not_found_user_message_in_tool_error (511) | Yes | COVERED |
| pick_tasks: wave_size + max_waves forwarded; PickTasksResponse with waves returned | returns_pick_tasks_response (561), delegates_to_agent_view (579), forwards_wave_size (594), forwards_max_waves (611), envelope_returned_unmodified (628), wave_size_none_forwarded (650) | No. Forwarding checks only substring-match stringified call_args at 606 and 623, and wave_size_none_forwarded only proves a call happened, not kwarg shape. The passthrough test asserts wave count and first id only, not the full envelope. | LAX |
| Error mapping: ValidationError to MCP ToolError with user_message | list_tasks tests (305, 326), show_task validation mapping (532), pick_tasks validation mapping (669, 690) | Partially. Exact user_message preservation is only proved for list_tasks. show_task and pick_tasks assert fragments, not the full preserved message. | LAX |
| Error mapping: NotFoundError to MCP ToolError with user_message | show_task not found tests (491, 511), list_tasks_not_found (722), tool_error_carries_user_message_not_code (741), pick_tasks_not_found (765) | Partially. pick_tasks only asserts ToolError is raised, and list_tasks only checks a substring. Cross-adapter user_message preservation is under-proven. | LAX |
| All tests fail (RED phase) | Historical phase evidence only | Not independently reproducible after implementation exists | N/A |

#### Security Review
- No issues in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:115-147, 228-235, 472-489. The changed logic is in-process delegation and KanbanError to ToolError mapping only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------|-------------|------------|
| TestFromAC suite in serve/mcp-kanban/tests/test_mcp_read_tools.py | No builder weakening evidenced in current snapshot or task history. The current failures are about test strength, not builder-authored removal or relaxation. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---------|--------|---------|
| Assertion specificity | WEAK | status/tag/priority/ids/task_id/section/wave_size/max_waves checks use stringified mock call_args at 224, 241, 258, 278, 425, 444, 606, 623 |
| Negative/error-path coverage | ADEQUATE | ValidationError and NotFoundError paths are exercised at 305, 326, 491, 511, 669, 690, 722, 741, 765 |
| Manual mutation resistance | WEAK | Dropping or misnaming search/sort/unclaimed/archived/limit/reverse/blocked in server.py:138-144 would still pass the suite; omitting wave_size=None at server.py:485 would still pass line 650 |
| Test independence | STRONG | Fresh fixture and MagicMock AgentView per test at test_mcp_read_tools.py:154 |
| Descriptive naming | STRONG | Test names remain AC-oriented across the suite |

#### Data Safety
- No issues.

#### Implementation-Aware Gaps
- list_tasks forwards search, sort, unclaimed, archived, limit, reverse, and blocked at server.py:138-144 with no direct TestFromAC proof.
- show_task normalizes empty section to None at server.py:231 before forwarding at 233; test_show_task_validation_error_mapped_to_tool_error (532) does not assert delegated section shape and cannot prove the named scenario.
- pick_tasks forwards wave_size and max_waves at server.py:485-486; test_pick_tasks_wave_size_none_forwarded (650) only proves the method was called.

#### Builder Process Quality
| Metric | Value |
|---------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- Quality-runner and code-reading agree the production adapters are simple and currently green; the blocking issue is proof quality in the TestFromAC suite, not a verified adapter defect.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| list_tasks: all params forwarded to AgentView.list_tasks; ListTasksResponse returned | server.py:134-144 forwards 11 kwargs; test file only proves status/tag/priority/ids and return envelope at 177, 197, 212, 229, 246, 263, 283 | test_list_tasks_returns_list_tasks_response; test_list_tasks_delegates_to_agent_view; test_list_tasks_forwards_*; test_list_tasks_envelope_returned_unmodified | FAIL |
| list_tasks: ids exclusivity enforced (AC15); adapter maps to ToolError | ValidationError mapping path is exercised and user_message preservation is asserted at 305 and 326 | test_list_tasks_ids_exclusivity_validation_error_mapped_to_tool_error; test_list_tasks_validation_error_message_preserved | PASS |
| show_task: id + section forwarded; ShowTaskResponse returned including missing_sections case (AC11) | Return type/envelope/missing_sections are covered at 379, 449, 469, but task_id and section forwarding assertions at 425 and 444 only inspect stringified call_args | test_show_task_returns_show_task_response; test_show_task_forwards_task_id; test_show_task_forwards_section_param; test_show_task_envelope_returned_unmodified; test_show_task_missing_sections_case_preserved | FAIL |
| show_task: missing id raises ToolError via NotFoundError mapping | NotFoundError is mapped and user_message is preserved at 491 and 511 | test_show_task_not_found_raises_tool_error; test_show_task_not_found_user_message_in_tool_error | PASS |
| pick_tasks: wave_size + max_waves forwarded; PickTasksResponse with waves returned | server.py:485-486 forwards both kwargs, but forwarding proof at 606 and 623 is string-based and wave_size=None at 650 does not assert kwargs | test_pick_tasks_returns_pick_tasks_response; test_pick_tasks_forwards_wave_size; test_pick_tasks_forwards_max_waves; test_pick_tasks_envelope_returned_unmodified; test_pick_tasks_wave_size_none_forwarded | FAIL |
| Error mapping: ValidationError to MCP ToolError with user_message | Exact user_message proof is complete for list_tasks only; show_task and pick_tasks use fragment checks at 532, 669, 690 | test_list_tasks_validation_error_message_preserved; test_show_task_validation_error_mapped_to_tool_error; test_pick_tasks_validation_error_mapped_to_tool_error; test_pick_tasks_max_waves_validation_error_mapped | FAIL |
| Error mapping: NotFoundError to MCP ToolError with user_message | show_task proves exact user_message at 511, but list_tasks and pick_tasks do not fully assert the contract at 722 and 765 | test_show_task_not_found_user_message_in_tool_error; test_list_tasks_not_found_error_mapped_to_tool_error; test_pick_tasks_not_found_mapped_to_tool_error | FAIL |
| All tests fail (RED phase) | Historical phase note in task body only; not scored in review because the implementation now exists | Test-Writer Notes only | N/A |

### Deductions
- -0.08 AC1 missing proof for 7 forwarded list_tasks parameters.
- -0.04 AC3 lax forwarding proof for task_id and section.
- -0.04 AC5 lax forwarding proof for wave_size/max_waves and partial envelope passthrough.
- -0.03 AC6 partial user_message assertions.
- -0.03 AC7 partial user_message assertions.
- -0.02 touched-module coverage below gate, with task-scope gaps inside changed functions.

### Confidence: .76
### Verdict: FAIL
### Action
- Reject to todo. Implementation currently looks correct, but the TestFromAC suite does not yet provide strong AC proof for all forwarded kwargs and user_message contracts.
