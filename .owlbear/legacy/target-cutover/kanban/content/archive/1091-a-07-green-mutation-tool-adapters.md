---
id: 1091
title: 'A-07: GREEN — mutation tool adapters'
status: archived
priority: medium
created: 2026-04-21 10:54:28.949075+00:00
updated: 2026-04-28T11:09:39.985315+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:green
parent: 1045
depends_on:
- 1087
- 1090
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.4–§5.5, paper-integration.md §1.4–§1.5
Module: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

Implement the 2 mutation MCP tool handlers in server.py: `create_task`, `edit_task`. Same mechanical adapter pattern as read tools: deserialize → AgentView call → serialize response → catch KanbanError → ToolError. Serialized after read tools on server.py to avoid merge conflicts.

## Acceptance Criteria

- [ ] All RED tests from A-04 (#1087) pass
- [ ] `create_task` tool registered, forwards title, body, priority, tags, parent, depends_on to AgentView.create_task
- [ ] `create_task` does NOT accept `status` param (D50 — engine controls entry status)
- [ ] `edit_task` tool registered, forwards all 13 params to AgentView.edit_task
- [ ] `edit_task` does NOT accept `status` param — must be asserted with an `inspect.signature` test symmetric with `test_create_task_has_no_status_parameter` in the 1087 suite
- [ ] Error mapping reuses the helper established in A-06 (#1090)
- [ ] No business logic in adapter

## Architect Guidance

### Coverage scoping (authoritative)
This module (`server.py`) is monolithic (~500 lines, ~10 tool handlers). Task 1091 touches only 2 error-handling paths in `create_task` and `edit_task`. Following the precedent established in `.owlbear/research/1078-cockpitview-coverage-gate-blocker.md`: **the reviewer should evaluate coverage scoped to the task-changed lines (create_task and edit_task handlers), not the entire server.py module.** Module-wide coverage is a cross-task concern, not a gate for this 2-line fix.

### Registration proof
MCP registration for both `create_task` and `edit_task` is already covered by durable suite `serve/mcp-kanban/tests/test_tool_annotations_494.py` (tests `test_create_task_destructive_hint_false` and `test_edit_task_destructive_hint_false`). The reviewer may cross-reference these for AC2/AC4 registration proof.

### AC5 test requirement
The test-writer must add `test_edit_task_has_no_status_parameter` in the task-owned suite (`tests/test_mcp_kanban_1091.py`), using `inspect.signature(edit_task).parameters` to assert `"status" not in params`. This mirrors the existing `test_create_task_has_no_status_parameter` in the 1087 suite.
[[2026-04-28]]
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_1091.py
- Classes: TestFromAC_MutationToolErrorHelper
- Tests per category: happy 0, edge 0, error 2, boundary 0
- Total: 2 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test | Status |
|----|------|--------|
| AC1: 1087 tests pass | builder responsibility | n/a |
| AC2: create_task forwards params | 1087 suite (TestFromAC_CreateTaskAdapter) | covered |
| AC3: create_task no status param | 1087 suite (test_create_task_has_no_status_parameter) | covered |
| AC4: edit_task forwards all 13 params | 1087 suite (TestFromAC_EditTaskAdapter) | covered |
| AC5: edit_task no status param | already true, inspect confirms | passes immediately |
| AC6: error mapping uses _map_kanban_error | test_create_task_calls_map_kanban_error_helper, test_edit_task_calls_map_kanban_error_helper | FAIL ✓ |
| AC7: no business logic | 1087 forwarding tests | covered |

Failure mechanism: monkeypatch replaces _map_kanban_error with a tracking shim;
current inline `raise ToolError(exc.user_message)` bypasses the shim → helper_calls == 0 → assert fails.
[[2026-04-28]]
## Builder Notes
- Implementation: updated serve/mcp-kanban/src/owlbear_mcp_kanban/server.py to route KanbanError handling in both mutation adapters through _map_kanban_error(exc) (create_task and edit_task).
- Tests: 26 passed, 0 failed, 0 skipped (scoped quality-runner run on tests/test_mcp_kanban_1091.py + serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py).
- Coverage: 37% on owlbear_mcp_kanban.server in scoped run; broad full run showed existing unrelated suite failures (115) with module coverage 61%.
- ruff: clean (scoped and full quality-runner runs).
- Approach: surgical adapter-only fix; no business-logic changes, no interface changes.

- Reflection: Failure cause was duplicated inline ToolError mapping in mutation handlers instead of shared helper usage.
- Reflection: Minimal fix was safe because read tools already use the same _map_kanban_error pattern.
- Reflection: Scoped quality evidence isolated task correctness from baseline full-suite regressions.
- Reflection: No additional edge-case test gaps blocked implementation; existing TestFromAC coverage was sufficient.
[[2026-04-28]]
## Review Evidence
### Test Results
- quality-runner scoped run: 26 passed, 0 failed, 0 skipped across [tests/test_mcp_kanban_1091.py](tests/test_mcp_kanban_1091.py) and [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py)

### Lint
- clean: true

### Coverage
- [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py): 37% on the touched module
- Reviewer gate result: FAIL. The workflow requires at least 90% coverage on touched modules.

### Pass 1 — Critical
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: All RED tests from A-04 pass | quality-runner reported 26 passed, 0 failed across the 1087 and 1091 suites | [tests/test_mcp_kanban_1091.py](tests/test_mcp_kanban_1091.py), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py) | PASS |
| AC2: create_task tool registered and forwards title, body, priority, tags, parent, depends_on | decorator and handler exist at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L343](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L343), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344); forwarding path at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L357](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L357), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L362](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L362); exact forwarding assertions at [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L175](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L175), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L184](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L184), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L197](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L197), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L210](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L210), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L223](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L223), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L236](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L236), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L249](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L249) | TestFromAC_CreateTaskAdapter | PASS |
| AC3: create_task does not accept status | signature omission asserted at [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L268](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L268), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L271](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L271), with production signature at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344) | TestFromAC_CreateTaskAdapter.test_create_task_has_no_status_parameter | PASS |
| AC4: edit_task tool registered and forwards all 13 params | decorator and handler exist at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L430](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L430), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431); all-13-param forwarding assertion at [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L316](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L316), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L340](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L340), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L351](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L351) | TestFromAC_EditTaskAdapter.test_edit_task_forwards_all_13_params | PASS |
| AC5: edit_task does not accept status | production signature omits status at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431), but the task-owned suites do not executably assert that contract. [tests/test_mcp_kanban_1091.py#L16](tests/test_mcp_kanban_1091.py#L16) says it was only confirmed by inspect, and [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L462](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L462) inspects only block_reason default. | none | FAIL |
| AC6: error mapping reuses the helper from A-06 | helper defined at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L75](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L75); handlers call it at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L366](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L366) and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L478](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L478); exact one-call assertions at [tests/test_mcp_kanban_1091.py#L157](tests/test_mcp_kanban_1091.py#L157), [tests/test_mcp_kanban_1091.py#L190](tests/test_mcp_kanban_1091.py#L190), [tests/test_mcp_kanban_1091.py#L197](tests/test_mcp_kanban_1091.py#L197), [tests/test_mcp_kanban_1091.py#L230](tests/test_mcp_kanban_1091.py#L230) | TestFromAC_MutationToolErrorHelper | PASS |
| AC7: no business logic in adapter | code remains mechanical marshaling only at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L357](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L357), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L362](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L362), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L451](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L451), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L469](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L469), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L476](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L476) | direct code inspection | PASS |

#### Security Review
- No issues found. The touched code only forwards arguments into existing AgentView calls and maps KanbanError through the shared helper.

#### Test Integrity
- No weakened or removed TestFromAC assertions found in [tests/test_mcp_kanban_1091.py](tests/test_mcp_kanban_1091.py) or [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py).

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | forwarding checks use exact equality assertions in [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L184](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L184), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L197](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L197), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L210](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L210), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L223](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L223), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L236](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L236), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L249](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L249); helper routing uses exact one-call assertions in [tests/test_mcp_kanban_1091.py#L190](tests/test_mcp_kanban_1091.py#L190) and [tests/test_mcp_kanban_1091.py#L230](tests/test_mcp_kanban_1091.py#L230) |
| Negative and error paths | ADEQUATE | helper-routing failures are exercised at [tests/test_mcp_kanban_1091.py#L157](tests/test_mcp_kanban_1091.py#L157) and [tests/test_mcp_kanban_1091.py#L197](tests/test_mcp_kanban_1091.py#L197); edit_task validation and generic error mapping are exercised at [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L383](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L383), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L401](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L401), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L419](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L419), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L437](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L437), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L502](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L502), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L556](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L556) |
| Manual mutation reasoning | WEAK | adding a status parameter to edit_task would evade the current suites because [tests/test_mcp_kanban_1091.py#L16](tests/test_mcp_kanban_1091.py#L16) records only inspect confirmation and [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L462](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L462) inspects only block_reason. Registration is also not intentionally exercised because both suites import the functions directly at [tests/test_mcp_kanban_1091.py#L29](tests/test_mcp_kanban_1091.py#L29) and [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L41](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L41), then call them directly at [tests/test_mcp_kanban_1091.py#L188](tests/test_mcp_kanban_1091.py#L188), [tests/test_mcp_kanban_1091.py#L228](tests/test_mcp_kanban_1091.py#L228), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L171](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L171), and [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L312](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L312) |
| Test independence | STRONG | both suites build fresh fixtures under tmp_path |
| Descriptive names | STRONG | test names state the exact adapter contract under review |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- create_task omission normalization for parent is only positively covered. Production normalizes zero and negative parent values at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L362](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L362), but the suite covers only the positive path at [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L236](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L236).
- edit_task omission paths are only partially pinned. Field omission logic lives at [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L451](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L451), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L453](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L453), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L459](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L459), [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L469](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L469), and [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L471](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L471); the suite proves the forwarded-values path at [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L316](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L316) and the empty-string unblock special case at [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L473](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L473), [serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L481](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L481), but not the general omission branches.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Deductions
- touched-module coverage is 37%, below the 90% reviewer gate
- AC5 lacks executable proof
- manual mutation resistance is WEAK because an edit_task status regression or registration regression would evade the current suites

### Verdict
- FAIL
- Confidence: 0.79

### Action
- Reject to backlog. The implementation itself looks correct, but the review gate fails on proof quality and a structurally misaligned coverage target for this monolithic module. Architect and test-writer should re-scope the evidence strategy before this returns to build.
[[2026-04-28]]
## Architecture Review (2nd cycle — post-reviewer rejection)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Task covers one concern: routing mutation error handling through shared helper |
| Interface clarity | PASS | AC lines map to specific function signatures and helper calls |
| Dependency correctness | PASS | Both deps (#1087, #1090) archived/done |
| Module layering | PASS | Adapter-only; no upward imports, no business logic |
| TDD compliance | PASS | RED tests from #1087 exist; task is tdd:green |
| KISS/YAGNI | PASS | 2-line fix replacing inline ToolError with _map_kanban_error calls |
| Premise challenge | PASS | Reviewer confirmed implementation is correct; rejection was on proof quality only |
| Pattern consistency | PASS | Follows read-tool adapter pattern established in A-06 (#1090) |
| Security surface | PASS | No new system boundaries; forwards through existing AgentView |
| Single domain | PASS | scope:mcp-kanban only |

### Reviewer Rejection Analysis
The reviewer rejected at confidence 0.79 with 3 deductions:
1. **AC5 lacks executable proof** — no `test_edit_task_has_no_status_parameter` symmetric with AC3's create_task test
2. **Coverage 37%** on monolithic server.py vs 90% gate — structural mismatch
3. **Mutation resistance WEAK** — status regression on edit_task would evade suites

### Refinements Applied
1. **AC5 tightened** — now explicitly requires `inspect.signature` test symmetric with `test_create_task_has_no_status_parameter`
2. **Coverage scoping authorized** — following 1078 precedent (`.owlbear/research/1078-cockpitview-coverage-gate-blocker.md`), reviewer should scope coverage to task-changed lines (create_task/edit_task handlers), not entire module
3. **Registration proof noted** — durable suite `test_tool_annotations_494.py` covers MCP registration for both tools; reviewer should cross-reference

### Challenge Results
- Challenger: reconsider (0.61)
- Concerns: coverage authority not yet binding, registration proof gap, AC5 narrowing
- Architect response: accepted all three — provided explicit coverage scoping authorization (matching 1078 precedent), tightened AC5 to require executable test, noted durable registration coverage

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC5 with explicit test requirement, added Architect Guidance section with coverage scoping authorization and registration proof pointers. Advancing to todo for test-writer to add the missing AC5 assertion.
[[2026-04-28]]
## Test-Writer Notes
- Retry cycle: reviewer cited missing AC5 executable proof (test_edit_task_has_no_status_parameter).
- Test file: tests/test_mcp_kanban_1091.py
- Classes: TestFromAC_MutationToolErrorHelper (2 tests, unchanged), TestFromAC_EditTaskSignature (1 test, added)
- New test: test_edit_task_has_no_status_parameter — uses inspect.signature(edit_task).parameters to assert "status" not in params; symmetric with test_create_task_has_no_status_parameter in 1087 suite.
- Tests per category: error 2 (unchanged), boundary 1 (new AC5 proof)
- Total: 3 tests in task-owned suite; 27 passed across scoped run (1091 + 1087), 0 failed
- Note: AC5 test passes immediately (implementation already correct — builder already excluded status param). This is expected: proof test added in retry cycle for existing behavior.
- ruff: clean
[[2026-04-28]]
## Builder Notes
- Implementation: no source edits in this cycle; existing `create_task`/`edit_task` adapters already route `KanbanError` through `_map_kanban_error` and already omit `status` from both signatures.
- Tests: 27 passed, 0 failed, 0 skipped (quality-runner scoped run on `tests/test_mcp_kanban_1091.py` + `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`).
- ruff: clean (scoped run).
- Coverage: `owlbear_mcp_kanban.server` = 37% in task-scoped run; architect guidance for this task authorizes line-scoped evaluation on the two touched mutation handlers instead of module-wide gate for monolithic `server.py`.
- Evidence summary: AC5 proof now exists as executable `inspect.signature` assertion in the task-owned suite; helper-routing assertions for AC6 pass; forwarding/no-business-logic behavior remains covered by the 1087 durable mutation suite.

- Reflection: This retry cycle was proof-completion, not implementation-change; preserving code avoided unnecessary churn.
- Reflection: Broad-context quality-runner run over `serve/mcp-kanban/tests/` surfaced unrelated legacy guidance-suite failures (13 failing tests) and 60% module coverage, confirming the need to keep task gating scoped to AC-owned lines.
- Reflection: Best signal for this task is combined scoped tests (1091 + 1087), which directly exercise the mutation adapter contract under review.
- Reflection: No missing blocking edge-case coverage remains for this task’s acceptance criteria.
[[2026-04-28]]
## Review Evidence
### Test Results
- quality-runner scoped run: 45 passed, 0 failed, 0 skipped across `tests/test_mcp_kanban_1091.py`, `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`, and `serve/mcp-kanban/tests/test_tool_annotations_494.py`

### Lint
- ruff: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `tests/test_mcp_kanban_1091.py`, `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`, and `serve/mcp-kanban/tests/test_tool_annotations_494.py`

### Coverage
- Raw module coverage: `owlbear_mcp_kanban.server` = 37%
- Task-authoritative gate: PASS. Architect guidance explicitly narrows coverage to the touched handler lines in `create_task` and `edit_task`, not the monolithic module-wide threshold.
- quality-runner `term-missing` output reported missing ranges `49, 89, 97-110, 116-120, 144-179, 195, 200-209, 214-246, 251-257, 269-282, 287-292, 307-313, 332-340, 378-427, 484-515, 531-591, 610-625`; those ranges do not include `create_task` `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344)` through `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L366](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L366)` or `edit_task` `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431)` through `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L478](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L478)`, so the task-changed lines were executed.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: All RED tests from A-04 (#1087) pass | quality-runner reported 45 passed, 0 failed, 0 skipped across the scoped 1091/1087/494 suites, including the full 1087 mutation suite | `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py` | PASS |
| AC2: `create_task` registered and forwards title/body/priority/tags/parent/depends_on | registration proved through tool-manager lookup at `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L29](serve/mcp-kanban/tests/test_tool_annotations_494.py#L29)`, `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L32](serve/mcp-kanban/tests/test_tool_annotations_494.py#L32)`, `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L33](serve/mcp-kanban/tests/test_tool_annotations_494.py#L33)`, and `test_create_task_destructive_hint_false` at `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L116](serve/mcp-kanban/tests/test_tool_annotations_494.py#L116)`; forwarding goes through `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L357](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L357)` and exact forwarded kwargs are asserted in the 1087 suite at `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L175](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L175)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L189](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L189)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L202](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L202)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L215](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L215)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L228](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L228)`, and `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L241](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L241)` | `TestFromAC_CreateTaskAdapter` + durable annotation suite | PASS |
| AC3: `create_task` does not accept `status` | production signature starts at `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344)` and the omission proof is executable at `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L268](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L268)` | `test_create_task_has_no_status_parameter` | PASS |
| AC4: `edit_task` registered and forwards all 13 params | registration proved through tool-manager lookup at `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L29](serve/mcp-kanban/tests/test_tool_annotations_494.py#L29)`, `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L32](serve/mcp-kanban/tests/test_tool_annotations_494.py#L32)`, `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L33](serve/mcp-kanban/tests/test_tool_annotations_494.py#L33)`, and `test_edit_task_destructive_hint_false` at `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L144](serve/mcp-kanban/tests/test_tool_annotations_494.py#L144)`; forwarding goes through `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L476](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L476)` and exact forwarded kwargs are asserted at `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L316](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L316)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L340](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L340)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L341](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L341)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L343](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L343)`, and `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L351](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L351)` | `TestFromAC_EditTaskAdapter.test_edit_task_forwards_all_13_params` + durable annotation suite | PASS |
| AC5: `edit_task` does not accept `status` and must be asserted with `inspect.signature` | the missing executable proof from the first review is now present at `[tests/test_mcp_kanban_1091.py#L251](tests/test_mcp_kanban_1091.py#L251)` and the assertion itself is at `[tests/test_mcp_kanban_1091.py#L254](tests/test_mcp_kanban_1091.py#L254)`; production signature starts at `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431)` | `TestFromAC_EditTaskSignature.test_edit_task_has_no_status_parameter` | PASS |
| AC6: error mapping reuses `_map_kanban_error` from A-06 | handlers call the shared helper at `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L366](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L366)` and `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L478](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L478)`; exact one-call helper assertions are at `[tests/test_mcp_kanban_1091.py#L158](tests/test_mcp_kanban_1091.py#L158)`, `[tests/test_mcp_kanban_1091.py#L191](tests/test_mcp_kanban_1091.py#L191)`, `[tests/test_mcp_kanban_1091.py#L198](tests/test_mcp_kanban_1091.py#L198)`, and `[tests/test_mcp_kanban_1091.py#L231](tests/test_mcp_kanban_1091.py#L231)` | `TestFromAC_MutationToolErrorHelper` | PASS |
| AC7: no business logic in adapter | reviewed adapter bodies remain mechanical delegation plus exception translation only across `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L344)` through `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L366](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L366)` and `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L431)` through `[serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L478](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L478)` | direct code inspection + 1087 forwarding tests | PASS |

#### Security Review
- No issues found. The touched handlers only marshal arguments into existing `AgentView` calls and map `KanbanError` through the shared helper; no shell, SQL, path, eval, or unsafe-deserialization sinks appear in scope.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions found in the scoped task suites.
- The new AC5 signature test in `tests/test_mcp_kanban_1091.py` is additive and resolves the prior reviewer finding rather than relaxing any earlier proof.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | exact kwargs, exact signature omission, exact helper-call counts, and exact tool-manager annotation lookup are asserted at `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L340](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L340)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L351](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L351)`, `[tests/test_mcp_kanban_1091.py#L191](tests/test_mcp_kanban_1091.py#L191)`, `[tests/test_mcp_kanban_1091.py#L231](tests/test_mcp_kanban_1091.py#L231)`, `[tests/test_mcp_kanban_1091.py#L254](tests/test_mcp_kanban_1091.py#L254)`, and `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L32](serve/mcp-kanban/tests/test_tool_annotations_494.py#L32)` |
| Negative/error-path coverage | STRONG | helper-routing error paths are exercised at `[tests/test_mcp_kanban_1091.py#L158](tests/test_mcp_kanban_1091.py#L158)` and `[tests/test_mcp_kanban_1091.py#L198](tests/test_mcp_kanban_1091.py#L198)`; mutation adapter error mapping remains covered in the 1087 suite at `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L383](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L383)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L401](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L401)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L419](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L419)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L437](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L437)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L502](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L502)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L520](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L520)`, `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L538](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L538)`, and `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L556](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L556)` |
| Manual mutation reasoning | STRONG | adding `status` to either signature, removing tool registration, or reverting helper reuse would now be caught by `[serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L268](serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py#L268)`, `[tests/test_mcp_kanban_1091.py#L251](tests/test_mcp_kanban_1091.py#L251)`, `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L116](serve/mcp-kanban/tests/test_tool_annotations_494.py#L116)`, `[serve/mcp-kanban/tests/test_tool_annotations_494.py#L144](serve/mcp-kanban/tests/test_tool_annotations_494.py#L144)`, `[tests/test_mcp_kanban_1091.py#L191](tests/test_mcp_kanban_1091.py#L191)`, and `[tests/test_mcp_kanban_1091.py#L231](tests/test_mcp_kanban_1091.py#L231) |
| Test independence | STRONG | both suites build isolated fixtures and mock AgentView per test |
| Descriptive names | STRONG | test names state the exact adapter contract under review |

#### Data Safety
- No issues found. The reviewed handlers are single-call adapters plus exception translation, with no multi-step persistence or shared mutable adapter state.

#### Implementation-Aware Gaps
- No significant untested paths found for this task’s adapter contract.
- Residual non-blocking gap: some general omission branches in `edit_task` and the `parent <= 0` normalization branch in `create_task` are not individually pinned, but those are pre-existing mechanical branches outside this task’s acceptance criteria and do not block the current contract.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Deductions
- None blocking.
- Raw whole-module coverage remains low, but that is not the governing gate for this task after the architect’s refinement; the touched handler lines were executed.

### Verdict
- PASS
- Confidence: 0.96

### Action
- Advance to docs.
- Residual risk is limited to out-of-scope omission branches in the monolithic adapter file; no follow-up is required to satisfy task 1091.
[[2026-04-28]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/mcp-kanban/README.md` tool table and descriptions remain accurate — no interface, parameter, or behavioral change; internal error-routing change only |
| 2 | Module docstrings | Yes | Verified | `_map_kanban_error` docstring accurate; `create_task` docstring accurate; `edit_task` docstring accurate — all public touched functions have docstrings |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research doc produced |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes `serve/mcp-kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes `serve/mcp-*/src/**`) footer updated to `Last verified: 2026-04-28 (5d3ecd42)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | IN (docstrings) | Verified — no docstring edits needed |
| tests/test_mcp_kanban_1091.py | OUT | N/A |
| serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py | OUT | N/A |
| serve/mcp-kanban/tests/test_tool_annotations_494.py | OUT | N/A |
| share/diagrams/kanban.excalidraw | IN (diagram) | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- share/diagrams/kanban.excalidraw — footer: `Last verified: 2026-04-28 (5d3ecd42)`
- share/diagrams/mcp-topology.excalidraw — footer: `Last verified: 2026-04-28 (5d3ecd42)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1091-* scratch files found)
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: All RED tests from A-04 pass | quality-runner: 30 passed across 1091+1087 suites | PASS |
| AC2: create_task registered, forwards params | 1087 suite forwarding assertions + durable annotation suite test_create_task_destructive_hint_false | PASS |
| AC3: create_task no status param | test_create_task_has_no_status_parameter (1087 suite L268) | PASS |
| AC4: edit_task registered, forwards 13 params | 1087 suite test_edit_task_forwards_all_13_params + durable annotation suite | PASS |
| AC5: edit_task no status param (inspect.signature) | test_edit_task_has_no_status_parameter (1091 suite L251-254) | PASS |
| AC6: error mapping reuses _map_kanban_error | server.py L366, L478; 1091 suite helper-call assertions L158,L191,L198,L231 | PASS |
| AC7: no business logic in adapter | code inspection: mechanical delegation + exception translation only | PASS |

### Test Results
- Full suite: 2792 passed, 115 failed (all pre-existing, documented by builder in both cycles), 4 skipped
- Task-scoped: 30 passed, 0 failed
- ruff: clean

### Architect Quality: 4/5
AC lines were specific and testable. One rework cycle needed for AC5 executable proof requirement and coverage scoping authorization. Refinements were appropriate and followed established precedent (1078 research).

### Deduction Breakdown
- 7 AC lines with evidence: 0
- Lint: clean: 0
- AC quality 4 (above 3): 0
- Reviewer evidence: present, detailed, PASS: 0
- Full-suite task-scope failures: 0

### Confidence: 0.98
### Action: archive