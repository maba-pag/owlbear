---
id: 1093
title: 'A-10: GREEN — guidance + error mapping'
status: archived
priority: medium
created: 2026-04-21 10:54:47.282679+00:00
updated: 2026-04-29T02:15:24.054985+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:green
parent: 1045
depends_on:
- 1089
- 1092
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §7 "guidance field", paper-integration.md §3.6–§3.7
Module: `serve/mcp-kanban/src/owlbear_mcp_kanban/guidance.py` (if needed), `server.py` (integration)

Implement guidance passthrough and finalize the KanbanError → MCP ToolError error-mapping layer. By this point all 8 tool handlers exist — this task ensures guidance strings flow through every response and the error mapping is complete and consistent. May be a no-op if A-06 through A-08 already established the patterns correctly — in that case, this task validates the pattern holds across all tools.

## Acceptance Criteria

- [ ] All RED tests from A-09 (#1089) pass
- [ ] Every tool's MCP response includes `guidance: list[str]` from engine envelope
- [ ] Guidance strings are NOT modified, filtered, or truncated by the adapter
- [ ] Error mapping covers all KanbanError subclasses: ValidationError, NotFoundError, ConcurrencyError
- [ ] ToolError carries `user_message` only — no engine error `code` on the MCP wire (per Brief A §7)
- [ ] AC12: show_task section occurrence count guidance passes through
- [ ] AC-NEW-4: end_work(block) Action-Request hint passes through
- [ ] AC-NEW-5: skip-transition warning passes through
[[2026-04-28]]
## Test-Writer Notes
- Non-implementation pass-through: all AC items already satisfied by existing implementation.
- Test file written (`tests/test_mcp_kanban_1093.py`, 15 tests across all AC lines).
- Quality-Runner result: **15 passed, 0 failed** — implementation is complete.
- Test file deleted per `w-tdd-red` Step 5: "any test that passes means implementation exists — remove."

### AC Coverage Audit

| AC item | Status | Evidence |
|---------|--------|----------|
| All RED tests from A-09 (#1089) pass | ✅ Already satisfied | 11/11 tests pass in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` |
| Every tool response includes `guidance: list[str]` | ✅ Already satisfied | All 8 tool return types have `guidance` field; list_tasks + start_work tested, both return `list` |
| Guidance NOT modified/filtered/truncated | ✅ Already satisfied | Sentinel passthrough tests for create_task, edit_task, end_work, move_task — all returned sentinel unchanged |
| Error mapping: ValidationError, NotFoundError, ConcurrencyError | ✅ Already satisfied | edit_task + NotFoundError, move_task + ValidationError, end_work + ValidationError — all mapped correctly |
| ToolError user_message only — no code on wire | ✅ Already satisfied | No ERR_* code leaked for any tested error path |
| AC12: show_task section occurrence count guidance | ✅ Already satisfied | test_mcp_guidance_1089.py::test_show_task_section_occurrence_count_guidance PASSES |
| AC-NEW-4: end_work(block) AR hint passes through | ✅ Already satisfied | test_mcp_guidance_1089.py::test_end_work_block_action_request_hint_guidance PASSES |
| AC-NEW-5: skip-transition warning passes through | ✅ Already satisfied | test_mcp_guidance_1089.py::test_move_task_skip_transition_warning_guidance + test_end_work_reject_skip_transition_warning_guidance PASS |

### Why "may be a no-op" applies here
The implementation was completed in tasks #1089 (AgentView with guidance), #1091 (create/edit _map_kanban_error), #1092 (move/start/end _map_kanban_error), #1126 (TypeError fallback removal). All patterns are established consistently. Task #1093 is a validation gate — the builder should verify all #1089 tests still pass and advance without code changes.
[[2026-04-28]]
## Builder Notes
- Non-implementation task — no code changes required.
- Implementation: none (pass-through per Test-Writer Notes).
- Tests: reused test-writer evidence (15 task tests passed, 0 failed).
- Coverage: not rerun by builder (pass-through path).
- ruff: not rerun by builder (pass-through path).
- Approach: validated non-implementation pass-through marker and advanced directly to review per `w-tdd-green` Step 0a.
[[2026-04-28]]
## Review Evidence
### Test Results
- Quality-Runner scoped authority (task-owned suites): 238 passed, 0 failed, 0 skipped.
- Scoped files: serve/mcp-kanban/tests/test_mcp_guidance_1089.py, serve/mcp-kanban/tests/test_mcp_read_tools.py, serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py, serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py, serve/mcp-kanban/tests/test_mcp_models_1084.py.
- Broader regression context: 280 passed, 7 failed in older guidance suites. Per reviewer scoping rule, used as context only after scoped rerun isolated task-owned evidence.

### Lint
- Ruff clean on serve/mcp-kanban/src/owlbear_mcp_kanban/ and the scoped task-owned suites.

### Coverage
- Scoped coverage overall: 45%
- owlbear_mcp_kanban.server: 62%
- owlbear_mcp_kanban.models: 97%
- Coverage is not the sole gate here because the builder reported no code changes, but the low server coverage supports that the retained proof does not fully exercise the current adapter surface.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Evidence | Would Fail If AC Violated? | Verdict |
| --- | --- | --- | --- |
| All RED tests from A-09 (#1089) pass | Quality-Runner scoped run: serve/mcp-kanban/tests/test_mcp_guidance_1089.py passed inside the 238/0 scoped result | Yes | COVERED |
| Every tool's MCP response includes guidance: list[str] from engine envelope | Field presence is covered in serve/mcp-kanban/tests/test_mcp_models_1084.py lines 549-589, but exact runtime proof is missing for list_tasks, start_work, and end_work(success) | No | MISSING |
| Guidance strings are NOT modified, filtered, or truncated by the adapter | Strong exact equality exists for show_task/create_task/edit_task/move_task/end_work(block)/end_work(reject) in serve/mcp-kanban/tests/test_mcp_guidance_1089.py lines 213-396; list_tasks uses an identity-or-equality assertion in serve/mcp-kanban/tests/test_mcp_read_tools.py lines 282-301 that can false-green on in-place mutation, and start_work has no guidance assertion | No | MISSING |
| Error mapping covers ValidationError, NotFoundError, ConcurrencyError | _map_kanban_error raises ToolError(exc.user_message) in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py lines 75-77; subclass coverage exists in serve/mcp-kanban/tests/test_mcp_guidance_1089.py lines 405-476, serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py lines 498-546, and serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py lines 393-441 | Yes | COVERED |
| ToolError carries user_message only — no engine error code on the MCP wire | Exact no-code assertions in serve/mcp-kanban/tests/test_mcp_guidance_1089.py lines 423-426 and 468-471 | Yes | COVERED |
| AC12: show_task section occurrence count guidance passes through | Exact equality in serve/mcp-kanban/tests/test_mcp_guidance_1089.py lines 213-229 | Yes | COVERED |
| AC-NEW-4: end_work(block) Action-Request hint passes through | Exact equality plus adapter-fallback sentinel guard in serve/mcp-kanban/tests/test_mcp_guidance_1089.py lines 370-396 | Yes | COVERED |
| AC-NEW-5: skip-transition warning passes through | Exact equality in serve/mcp-kanban/tests/test_mcp_guidance_1089.py lines 317-338 and 342-366 | Yes | COVERED |

#### Security Review
- No security findings in the reviewed adapter/model surface.

#### Test Integrity
| Original Test | Change Made | Assessment |
| --- | --- | --- |
| Live TestFromAC suites retained in current snapshot | No definitive weakened or removed assertion proven from current snapshot; strongest retained exact-equality checks remain in serve/mcp-kanban/tests/test_mcp_guidance_1089.py | PRESERVED (current snapshot only) |
| Historical diff / builder-side TestFromAC mutation check | Could not complete because the changed-files / SCM diff surface was not exposed in this session | UNVERIFIED |

#### Test Quality
| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | WEAK | serve/mcp-kanban/tests/test_mcp_read_tools.py lines 282-301 uses `result is expected or result == expected`, which can pass after in-place mutation of the returned envelope |
| Negative/error-path coverage | ADEQUATE | Error-mapping paths are exercised across read/mutation/lifecycle suites |
| Manual mutation reasoning | WEAK | serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py lines 212-215 only asserts `SingleTaskResponse` for start_work, so dropped or transformed guidance would still pass |
| Test independence | ADEQUATE | No shared mutable-state coupling observed in the scoped task-owned suites |
| Descriptive names | STRONG | Task-owned suites use explicit AC-oriented test names |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- list_tasks directly returns the AgentView envelope in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py lines 126-158, but the retained runtime proof is not binding on guidance preservation.
- start_work can return an AgentView response directly in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py lines 477-487 or synthesize fallback guidance at lines 499-501, yet the retained suite only checks return type in serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py lines 212-215.
- end_work(success) can return a direct AgentView response in serve/mcp-kanban/src/owlbear_mcp_kanban/server.py lines 530-550, but there is no retained sentinel-style passthrough proof for that path. Older broad-run suites that tried to cover surrounding behavior are stale or obsolete, including serve/mcp-kanban/tests/test_guidance_server_980.py lines 123-184.

#### Builder Process Quality
| Metric | Value |
| --- | --- |
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Broad regression run found 7 failures in older guidance suites, including obsolete `edit_task(title=...)` expectations in serve/mcp-kanban/tests/test_guidance_server_980.py lines 123-171 and outdated guidance-wiring expectations around end_work(success). Those failures were not used as the primary gate after the scoped rerun, but they reduce confidence in relying on legacy guidance suites as proof.

### Deductions
- 0.08 deducted: explicit AC proof missing for list_tasks/start_work/end_work(success) guidance passthrough.
- 0.04 deducted: live list_tasks passthrough assertion can false-green on in-place mutation.
- 0.03 deducted: changed-files / SCM diff surface unavailable, so historical TestFromAC immutability could not be fully audited.
- 0.02 deducted: scoped server coverage only 62%, consistent with the proof gap on the remaining adapter paths.

### Verdict
- FAIL with confidence 0.83.
- Root cause: current-snapshot proof is not strong enough for the all-tools guidance passthrough contract. The implementation appears intact, but the retained executable evidence is missing or lax for list_tasks, start_work, and end_work(success).
- Action: return to backlog for test/AC-quality repair. The next pass should restore current-snapshot, exact-value proof for those paths rather than relying on deleted task-local tests or stale legacy suites.
[[2026-04-28]]


## Architecture Review (Cycle 2)

### Reviewer Feedback (Cycle 1)
FAIL at 0.83. Implementation intact, proof gaps for 3 tools:
1. **list_tasks** — assertion uses `result is expected or result == expected` (can false-green on in-place mutation)
2. **start_work** — only `isinstance(result, SingleTaskResponse)` (no guidance content check)
3. **end_work(success)** — no guidance assertion at all

### AC Refinements

**AC line 2 refined:** "Every tool's MCP response includes `guidance: list[str]`" — removed "from engine envelope" because `start_work` and `end_work` fallback paths use adapter-generated guidance via `collect_guidance()`, not engine envelope.

**AC line 4 refined:** "Error mapping handles `KanbanError` base class (covering all subclasses including ConfigError and MigrationRequiredError, not just the 3 enumerated)"

**Added AC-FIX lines (proof-gap repair):**
- [ ] AC-FIX-1: Test asserts `list_tasks` response `guidance` field by exact value comparison on the field itself (not whole-envelope `is`/`==`)
- [ ] AC-FIX-2: Test asserts `start_work` response `guidance` field matches expected content — mock AgentView.start_work with known sentinel guidance and verify exact passthrough
- [ ] AC-FIX-3: Test asserts `end_work(outcome="success")` response `guidance` field matches expected content — mock AgentView.end_work with known sentinel guidance and verify exact passthrough

### Test Placement Directive
Add AC-FIX tests to the existing guidance suite (`serve/mcp-kanban/tests/test_mcp_guidance_1089.py`) alongside the other sentinel passthrough tests. Do NOT create a task-owned file — task-owned suites are subject to w-tdd-red Step 5 cleanup and this is exactly what caused the previous cycle's failure.

### Codebase Notes for Builder
The server has 3 branches per tool: AgentView → canonical AgentView → engine fallback. The AC-FIX tests should bind to the AgentView branch (primary path). The fallback branch uses `collect_guidance()` which returns:
- `start_work`: `[]` (no matching conditions)
- `end_work(success)`: `["Reminder: verify your changes are committed..."]`

Pattern to follow: existing sentinel tests in `test_mcp_guidance_1089.py` mock `_agent_view_for()` to return an AgentView with known guidance → call the tool → assert `result.guidance == expected`.

### Stale Suite Note
7 failures in older guidance suites (test_guidance_server_980, test_guidance_end_work_973) are from superseded task implementations — reviewer already discounted them as context, not gate evidence.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Guidance passthrough + error mapping for MCP adapter — one domain |
| Interface clarity | PASS | AC specifies behavior per tool; AC-FIX lines add exact assertion requirements |
| Dependency correctness | PASS | #1089 and #1092 done (archived) |
| Module layering | PASS | MCP adapter → engine, correct direction |
| TDD compliance | PASS | Paired with #1089 (RED), tdd:green tag present |
| KISS/YAGNI | PASS | Validation gate — minimal scope, 3 test additions |
| Premise challenge | PASS | Reviewer confirmed implementation intact; task repairs proof gaps |
| Pattern consistency | PASS | Follows existing sentinel-passthrough test pattern from test_mcp_guidance_1089.py |
| Security surface | PASS | No new system boundaries; guidance is internal pipeline data |
| Single domain | PASS | scope:mcp-kanban only |

### Design Diverge
Skipped: single approach (add 3 exact-value tests to existing guidance suite). No competing designs.

### Challenge Results
- Challenger: reconsider (0.44)
- Findings: (1) AC "from engine envelope" inaccurate for fallback paths — ACCEPTED, refined. (2) Error subclass enumeration incomplete — ACCEPTED, refined. (3) AC-FIX-2/3 underspecified — ACCEPTED, tightened to require exact-value sentinel tests. (4) Task-owned suite gets deleted by w-tdd-red — ACCEPTED, directed to shared suite. (5) Branch selection unspecified — ACCEPTED, added builder notes specifying AgentView branch.
- Architect response: All 5 challenges accepted and incorporated into refinement. No overrides.

### Verdict: REFINE → APPROVE
AC refined to address reviewer proof gaps and challenger concerns. Moving to todo.

### Action Taken
Refined AC with 3 AC-FIX lines for list_tasks/start_work/end_work(success) guidance proof. Fixed AC line 2 (removed inaccurate "from engine envelope"). Fixed AC line 4 (acknowledged full KanbanError hierarchy). Directed test placement to shared suite. Approving to todo.
[[2026-04-28]]
Architecture review complete (cycle 2). Refined AC with 3 AC-FIX lines for proof gaps identified by reviewer: list_tasks (exact-value guidance assertion), start_work (sentinel passthrough), end_work(success) (sentinel passthrough). Addressed all 5 challenger concerns: fixed "from engine envelope" inaccuracy, expanded error subclass enumeration, tightened AC-FIX specificity, directed test placement to shared suite, specified AgentView branch binding. All 10 Step 2 criteria PASS.
[[2026-04-28]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_guidance_1089.py (shared suite — per Architecture Review cycle-2 directive)
- Classes: TestFromAC_GuidanceProofRepair (3 new tests added to existing suite)
- Tests per category: happy 3, edge 0, error 0, boundary 0
- Total: 3 new tests added; all 14 tests in suite PASS (proof-repair, not RED phase)
- ruff: clean

### Retry cycle outcome
Reviewer cited missing proof for 3 tool paths (list_tasks, start_work, end_work(success)). Architecture Review cycle-2 directed adding sentinel tests to the **shared** guidance suite (not a task-owned file), because task-owned files are deleted when they pass (which caused the cycle-1 failure).

### AC-FIX coverage
| AC-FIX | Test | Result |
|--------|------|--------|
| AC-FIX-1: list_tasks exact guidance field comparison | `test_list_tasks_guidance_exact_field_value` | PASS — implementation correct |
| AC-FIX-2: start_work sentinel passthrough | `test_start_work_guidance_sentinel_passthrough` | PASS — implementation correct |
| AC-FIX-3: end_work(success) sentinel passthrough | `test_end_work_success_guidance_sentinel_passthrough` | PASS — implementation correct |

All 3 tests pass because the implementation has always been correct. Durable proof is now in the shared suite.
[[2026-04-28]]
## Builder Notes
- Implementation: no code changes required; existing adapter behavior already satisfies refined AC and AC-FIX proof requirements.
- Files changed: none.
- Tests: 14 passed, 0 failed, 0 skipped (`serve/mcp-kanban/tests/test_mcp_guidance_1089.py`).
- Coverage: `owlbear_mcp_kanban.server` 54% (scoped run context; no module edits in this pass).
- ruff: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`.
- Evidence summary: guidance passthrough and KanbanError->ToolError mapping assertions in the shared guidance suite are passing in current snapshot; no surgical intervention required.

### Post-task Reflection
- The key risk was treating earlier deleted task-local tests as authoritative; durable proof in shared suites is the right gate.
- Scoped quality-runner verification provided clear go/no-go evidence without rerunning unrelated stale suites.
- This task remains a validation/green gate: strongest outcome was confirming correctness with zero diff.
- Low scoped server coverage is a known context signal, but with no code changes it is not a regression introduced by this pass.
[[2026-04-28]]
## Review Evidence
### Test Results
- Quality-Runner scoped run on `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`: 14 passed, 0 failed, 0 skipped.
- Additional scoped verification on `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` + `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`: 45 passed, 0 failed, 0 skipped.

### Lint
- Ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`.

### Coverage
- Scoped coverage overall: 44%
- `owlbear_mcp_kanban.server`: 54%
- `owlbear_mcp_kanban.models`: 92%
- Coverage is contextual only in this retry because the builder reported no source edits.

### Pass 1 - CRITICAL
#### AC Compliance
| AC Line | Evidence | Status |
| --- | --- | --- |
| All RED tests from A-09 (#1089) pass | Quality-Runner scoped run on `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`: 14 passed, 0 failed, 0 skipped. | PASS |
| Every tool's MCP response includes `guidance: list[str]` | Shared guidance suite exercises all 8 tool paths with guidance assertions: `show_task` / `pick_tasks` / `create_task` / `edit_task` / `move_task` / `end_work(block)` / `end_work(reject)` in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:215-400`, plus exact-value `list_tasks` / `start_work` / `end_work(success)` proof-repair tests in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:450-504`. | PASS |
| Guidance strings are NOT modified, filtered, or truncated by the adapter | Exact equality assertions at the adapter return boundary in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:215-400` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:450-504`. | PASS |
| Error mapping handles KanbanError base class, covering ValidationError, NotFoundError, ConcurrencyError, ConfigError, and MigrationRequiredError | Generic mapping exists in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:75-77`. Validation / NotFound / Concurrency are covered in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:411-550`. MigrationRequiredError is covered and green in `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:433-449`. Direct search under `serve/mcp-kanban/tests/**` found no `ConfigError` matches, so the refined AC still lacks executable MCP-side proof for that subclass. | FAIL |
| ToolError carries `user_message` only, with no engine error code on the MCP wire | Exact `user_message` and no-code assertions in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:411-428` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:528-550`. | PASS |
| AC12: show_task section occurrence count guidance passes through | Exact equality in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:215-233`. | PASS |
| AC-NEW-4: end_work(block) Action-Request hint passes through | Exact equality plus fallback-sentinel guard in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:372-400`. | PASS |
| AC-NEW-5: skip-transition warning passes through | Exact equality in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:319-369`. | PASS |
| AC-FIX-1: list_tasks exact guidance field comparison | Exact field-level assertion in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:450-467`. | PASS |
| AC-FIX-2: start_work sentinel passthrough | Exact field-level assertion in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:470-487`. | PASS |
| AC-FIX-3: end_work(success) sentinel passthrough | Exact field-level assertion in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:490-504`. | PASS |

#### Security Review
- No security findings in the reviewed adapter and shared-suite surface.

#### Test Integrity
| Original Test Surface | Change Made | Assessment |
| --- | --- | --- |
| Prior weak proof for `list_tasks` / `start_work` / `end_work(success)` | Current snapshot adds direct field-equality assertions in `TestFromAC_GuidanceProofRepair`. | STRENGTHENED |
| Historical TestFromAC diff versus the prior snapshot | No builder commit hash or SCM diff was present in the task body, so historical comparison could only be checked on the current snapshot. | UNVERIFIED HISTORICALLY |

#### Test Quality
| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | STRONG | Proof-repair tests assert exact `result.guidance == sentinel` in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:450-504`. |
| Negative / error-path coverage | WEAK | The refined AC explicitly names `ConfigError`, but no MCP-side test covers that subclass anywhere under `serve/mcp-kanban/tests/**`. |
| Manual mutation reasoning | STRONG | The new exact-value assertions would fail if the adapter stripped, replaced, or transformed guidance on the three repaired paths. |
| Test independence | ADEQUATE | No shared mutable-state coupling observed in the scoped suites. |
| Descriptive names | STRONG | Current proof-repair and mapping tests are AC-specific and descriptive. |

#### Data Safety
- No issues found in the scoped adapter surface.

#### Implementation-Aware Gaps
- `_map_kanban_error` is generic and appears implementation-correct, but the refined AC still lacks executable MCP-side proof for `ConfigError`.
- `MigrationRequiredError` is covered in `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:433-449` and passed in the additional scoped run; `ConfigError` is the remaining gap.

#### Builder Process Quality
| Metric | Value |
| --- | --- |
| Builder Notes sections | 2 |
| Approach variation | Yes - retry scope changed after Architecture Review cycle 2 and shared-suite proof was added upstream |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- This retry successfully closed the cycle-1 proof gaps for `list_tasks`, `start_work`, and `end_work(success)`.
- Low scoped server coverage (54%) is not treated as the gate in this pass because the builder reported no source changes and the current fail is a specific missing test obligation.

### Deductions
- 0.11 deducted: refined AC still lacks executable MCP-side proof for `ConfigError` mapping.
- 0.02 deducted: no commit hash / diff in the task body, so TestFromAC immutability could only be audited on the current snapshot.

### Verdict
- FAIL with confidence 0.87.
- Root cause: the implementation looks correct and the proof-repair tests now bind the three previously missing guidance paths, but the latest refined AC still names `ConfigError` and there is no MCP-side test covering it.
- Action: return to `todo` for test coverage only. Add one MCP adapter test in the shared suite (or other durable MCP suite) that forces `AgentView` to raise `ConfigError` and asserts `ToolError` exposes the exact `user_message` with no engine error code on the wire.

### Post-task Reflection
- Exact-value field assertions were the right repair for passthrough contracts; the earlier identity-or-envelope assertions were correctly removed from the proof basis.
- Named subclass requirements can still fail even when a generic base-class mapper is implementation-correct; each named subclass needs executable proof.
- Adjacent durable suites can supply part of the evidence set, but they do not excuse a missing named path in the current AC.
[[2026-04-28]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_guidance_1089.py (shared suite — per Architecture Review cycle-2 directive)
- Classes: TestFromAC_GuidanceProofRepair (1 new test added)
- Tests per category: happy 1, edge 0, error 0, boundary 0
- Total: 1 new test added; all 15 tests in suite PASS (proof-repair retry, not RED phase)
- ruff: clean

### Retry cycle outcome (cycle 3)
Reviewer cited missing MCP-side proof for `ConfigError` subclass. Implementation already correct (`_map_kanban_error` catches `KanbanError` base class). Added `test_config_error_maps_to_tool_error_user_message_only` to `TestFromAC_GuidanceProofRepair` — mocks `AgentView.list_tasks` to raise `ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT", user_message=...)`, asserts `ToolError` exposes exact `user_message` and no `ERR_*` code on wire. Also added `from owlbear_kanban.errors import ConfigError` import.

### AC-FIX coverage (cycle 3)
| AC-FIX | Test | Result |
|--------|------|--------|
| ConfigError → ToolError, no code on wire | `test_config_error_maps_to_tool_error_user_message_only` | PASS — implementation correct |

Test passes because the implementation has always handled all `KanbanError` subclasses via the generic `_map_kanban_error` mapper. Durable proof is now in the shared suite.
[[2026-04-28]]
## Builder Notes
- Implementation: no source changes required; existing adapter behavior already satisfies AC after cycle-3 proof repair landed.
- Files changed: none.
- Tests: 15 passed, 0 failed, 0 skipped (`serve/mcp-kanban/tests/test_mcp_guidance_1089.py`).
- Coverage: `owlbear_mcp_kanban.server` 55% (scoped verification context; no module edits in this builder pass).
- ruff: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`.
- Evidence summary: ConfigError mapping proof is now present in the shared guidance suite and passes; guidance passthrough contract remains green across the retained AC proof tests.

### Post-task Reflection
- This remained a validation-gate cycle: strongest intervention was verification, not code change.
- Shared durable suite proof prevented the prior false-green risk from task-local test cleanup.
- Scoped quality-runner execution gave a clean gate signal without involving stale legacy suites.
[[2026-04-28]]
## Review Evidence
### Test Results
- Quality-Runner scoped run on `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`, `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py`, `serve/mcp-kanban/tests/test_mcp_read_tools.py`, `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py`, and `serve/mcp-kanban/tests/test_mcp_models_1084.py`: 242 passed, 0 failed, 0 skipped.

### Lint
- Ruff clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/` and the scoped MCP kanban suites above.

### Coverage
- `owlbear_mcp_kanban.server`: 62%
- `owlbear_mcp_kanban.models`: 97%
- Coverage is contextual only in this review cycle because the builder reported no source edits.

### Pass 1 - CRITICAL
#### AC Compliance
| AC Line | Evidence | Status |
| --- | --- | --- |
| All RED tests from A-09 (#1089) pass | Independent Quality-Runner scoped run passed 242/0 and included the shared A-09 guidance suite `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`. | PASS |
| Every tool's MCP response includes `guidance: list[str]` | Canonical response models declare `guidance: list[str]` on `ListTasksResponse`, `ShowTaskResponse`, `PickTasksResponse`, and `SingleTaskResponse` in `serve/kanban/src/owlbear_kanban/models.py:431-456`; runtime guidance assertions cover all 8 tool paths in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:216-398` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:451-505`. | PASS |
| Guidance strings are NOT modified, filtered, or truncated by the adapter | Exact equality assertions cover show/pick/create/edit/move/end_work(reject)/end_work(block) in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:216-398`; exact field-equality proof repairs cover list_tasks/start_work/end_work(success) in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:451-505`. The live adapter paths are direct-return/shared-normalizer paths in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:126-179` and `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:477-576`. | PASS |
| Error mapping handles `KanbanError` base class, covering ValidationError, NotFoundError, ConcurrencyError, ConfigError, and MigrationRequiredError | Shared mapper `_map_kanban_error` raises `ToolError(exc.user_message)` for any `KanbanError` in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:75-77`; base-class proof exists in `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:556-571`; subclass proof exists in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:412-576` and `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:393-444`. | PASS |
| ToolError carries `user_message` only — no engine error `code` on the MCP wire | Exact no-code assertions exist for ValidationError, ConcurrencyError, and ConfigError in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:419-428`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:537-553`, and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:555-576`; NotFoundError exact equality proof exists in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:510-527`; all subclasses use the same mapper in `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:75-77`. | PASS |
| AC12: show_task section occurrence count guidance passes through | Exact equality proof in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:216-233`. | PASS |
| AC-NEW-4: end_work(block) Action-Request hint passes through | Exact equality plus fallback-poisoning proof in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:373-398`. | PASS |
| AC-NEW-5: skip-transition warning passes through | Exact equality proof for move_task and end_work(reject) in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:320-369`. | PASS |
| AC-FIX-1: list_tasks exact guidance field comparison | Exact field-level assertion in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:451-469`. | PASS |
| AC-FIX-2: start_work sentinel passthrough | Exact field-level assertion in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:471-489`. | PASS |
| AC-FIX-3: end_work(success) sentinel passthrough | Exact field-level assertion in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:491-505`. | PASS |

#### Security Review
- No security findings in the reviewed adapter/model/test surface.

#### Test Integrity
| Original Test Surface | Change Made | Assessment |
| --- | --- | --- |
| Shared `TestFromAC_*` guidance suite | Current snapshot strengthens the earlier weak proof with exact field-equality assertions for list_tasks/start_work/end_work(success) and exact ConfigError mapping proof in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:451-576`. | STRENGTHENED |
| Historical diff vs prior snapshot | No builder commit hash / SCM diff was present in the task body, so immutability could only be audited on the current snapshot. No weakened assertion was found in the current bound proof set. | UNVERIFIED HISTORICALLY |

#### Test Quality
| Dimension | Rating | Evidence |
| --- | --- | --- |
| Assertion specificity | STRONG | Current binding proof uses exact equality / exact no-code assertions in `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:216-398` and `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:451-576`. |
| Negative / error-path coverage | ADEQUATE | Named subclass coverage plus base-class mapper proof exist across `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:412-576`, `serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py:393-444`, and `serve/mcp-kanban/tests/test_mcp_mutation_tools_1087.py:556-571`. |
| Manual mutation reasoning | STRONG | A regression that strips/transforms guidance or prepends machine error codes would fail the exact-value assertions in the shared guidance suite. |
| Test independence | ADEQUATE | Fixtures isolate engine/context state per test; no shared mutable-state coupling found in the scoped suites. |
| Descriptive names | STRONG | AC-oriented test names and docstrings make the proof surface auditable. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No significant adapter-path gaps remain in the current binding proof set. The cycle-1 list_tasks/start_work/end_work(success) gaps and the cycle-2 ConfigError gap are now closed in the shared guidance suite.

#### Builder Process Quality
| Metric | Value |
| --- | --- |
| Builder Notes sections | 2 |
| Approach variation | Yes - review feedback was addressed through Architecture Review cycle 2 and shared-suite proof repair |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- The latest binding authority is `## Architecture Review (Cycle 2)`, not the stale top-level wording. Review was anchored to that refinement and the post-refinement shared-suite proof.
- Adjacent durable suites still contain some permissive assertions, but they are not the binding proof surface for task 1093 after the shared guidance suite repair landed.
- Low server coverage remains contextual only here because the builder reported no source edits and the scoped runtime proof is green.

### Deductions
- 0.03 deducted: no builder commit hash / SCM diff in the task body, so historical TestFromAC immutability could only be checked on the current snapshot.
- 0.03 deducted: adjacent non-binding MCP suites still contain some permissive assertions, which is test debt but not a blocker for this task's repaired proof surface.

### Verdict
- PASS with confidence 0.94.
- The current snapshot satisfies the latest refined AC. The earlier proof gaps for list_tasks/start_work/end_work(success) and ConfigError are now closed by durable exact-value assertions in the shared guidance suite, and the shared `_map_kanban_error` implementation remains consistent with the wire contract.
- Action: advance to `docs`.

### Post-task Reflection
- Latest architecture refinements must override stale header AC when looped tasks accumulate old review sections.
- Shared response-model definitions were useful to settle the `guidance: list[str]` contract without inventing extra per-tool type checks.
- Adjacent permissive assertions are worth tracking as test debt, but they should not outweigh stronger task-owned proof once the task's binding gaps are repaired.
[[2026-04-28]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No behavioral changes to adapter API, CLI, config, or package structure. Builder confirmed no source edits in either builder pass. No IN-scope prose doc references this test-only change. |
| 2 | Module docstrings | No | N/A | No Python modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns cited in task body or builder notes. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | No | N/A | kanban.excalidraw and mcp-topology.excalidraw describe serve/mcp-kanban/src/**; no source files changed — test-only additions do not trigger diagram update. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-kanban/tests/test_mcp_guidance_1089.py | OUT (test file) | N/A |
| serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | OUT (source, no changes) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no scratch files existed for task 1093)
[[2026-04-29]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from A-09 (#1089) pass | 15/15 in test_mcp_guidance_1089.py (scoped run 312/5, 5 failures in legacy _973 suites only) | PASS |
| Every tool response includes guidance: list[str] | Exact assertions for all 8 tools in test_mcp_guidance_1089.py:216-505 | PASS |
| Guidance NOT modified/filtered/truncated | Exact sentinel equality assertions (spot-checked test_list_tasks_guidance_exact_field_value, test_start_work_guidance_sentinel_passthrough) | PASS |
| Error mapping handles KanbanError base + subclasses | _map_kanban_error in server.py:75-77 + subclass tests for Validation/NotFound/Concurrency/Config/MigrationRequired | PASS |
| ToolError user_message only — no code on wire | Explicit no-code assertions in test_mcp_guidance_1089.py:419-576 | PASS |
| AC12: show_task occurrence count guidance | Exact equality in test_mcp_guidance_1089.py:216-233 | PASS |
| AC-NEW-4: end_work(block) AR hint | Exact equality + fallback guard | PASS |
| AC-NEW-5: skip-transition warning | Exact equality for move_task + end_work(reject) | PASS |
| AC-FIX-1: list_tasks exact field comparison | test_list_tasks_guidance_exact_field_value — sentinel pattern, direct field assertion | PASS |
| AC-FIX-2: start_work sentinel passthrough | test_start_work_guidance_sentinel_passthrough — AgentView branch binding | PASS |
| AC-FIX-3: end_work(success) sentinel passthrough | test_end_work_success_guidance_sentinel_passthrough — AgentView branch binding | PASS |

### Test Results
- Full suite: 2827 passed, 124 failed, 4 skipped (no failures in task scope)
- Scoped mcp-kanban: 312 passed, 5 failed (all 5 in legacy _973 suites — pre-existing debt, not regressions)
- Task-specific (test_mcp_guidance_1089.py): 15/15 passed
- ruff: clean in mcp-kanban scope; 4 violations in unrelated packages (knowledge, orchestrator)

### Reviewer Evidence
- PASS at 0.94 (cycle 3). Thorough 3-cycle review with detailed AC compliance tables. All 11 AC lines mapped with file:line evidence. Deductions documented.

### Architect Quality: 3/5
Original AC missed ConfigError/MigrationRequiredError subclasses, had inaccurate "from engine envelope" framing, and didn't anticipate the task-owned test deletion lifecycle causing proof loss. Cycle-2 architecture review addressed all issues well with AC-FIX lines and shared-suite placement directive.

### Deduction Breakdown
- AC quality 3/5: -0.03
- No builder commit hash / SCM diff for historical TestFromAC immutability: -0.02

### Confidence: 0.95
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3d7bc7a5 | test | test_mcp_guidance_1089.py (ConfigError proof) | #1093 |
| 4c9831ab | test | test_mcp_guidance_1089.py (proof-repair sentinels) | #1093 |
| 635e7fc0 | chore | kanban task file | #1093 |