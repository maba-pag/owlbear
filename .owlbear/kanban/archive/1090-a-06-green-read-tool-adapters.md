---
id: 1090
title: 'A-06: GREEN — read tool adapters'
status: archived
priority: critical
created: 2026-04-21 10:54:20.345618+00:00
updated: 2026-04-28T09:53:04.266879+00:00
tags:
- phase:mcp
- brief:a
- scope:mcp-kanban
- tdd:green
parent: 1045
depends_on:
- 1086
blocked: false
block_reason:
claimed_by: quiet-shade
claimed_at: 2026-04-28T09:53:04.266879+00:00
archival_reason:
archival_refs: []
---
## Brief
Brief A (#1045) — kanban-mcp-surface-v2/brief.md §5.1–§5.3, paper-integration.md §1.1–§1.3
Module: `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`

Implement the 3 read-only MCP tool handlers in server.py: `list_tasks`, `show_task`, `pick_tasks`. Each handler: (1) deserializes MCP call args into the input model, (2) calls the corresponding AgentView method with a 1:1 passthrough, (3) serializes the engine response envelope to MCP response, (4) catches KanbanError and maps to MCP ToolError(user_message). The adapter is mechanical — no business logic.

First GREEN impl task on server.py — establishes the adapter pattern (error mapping helper, AgentView injection) that mutation and lifecycle tasks build on.

## Acceptance Criteria

- [ ] AC1: `list_tasks` tool accepts the 12 Brief A §5.1 params matching `ListTasksParams` fields from `owlbear_mcp_kanban.models` (status, priority, tag, archival_reason, ids, unclaimed, blocked, parent, search, sort, reverse, limit) — no legacy `archived: bool` on MCP surface
- [ ] AC2: `show_task` adapter translates MCP `id` → engine `task_id`. Single unconditional call: `view.show_task(task_id=params.id, section=params.section)`. No branching on section value or view type. Engine accepts `section=None` natively (returns full body).
- [ ] AC3: `pick_tasks` tool accepts `wave_size` + `max_waves` matching `PickTasksParams` fields and forwards to `AgentView.pick_tasks`
- [ ] AC4: Boundary validation via `model_validate` (not `model_construct`) proven by executable test in `serve/mcp-kanban/tests/`: pass type-invalid input (e.g., `id="not_an_int"` for show_task) and assert `ToolError` raised — proves `model_validate` rejects invalid types (which `model_construct` would silently accept)
- [ ] AC5: `KanbanError` → `ToolError` mapping via `_map_kanban_error` helper in all three handlers
- [ ] AC6: `list_tasks` sets `output_schema` from `ListTasksResponse.model_json_schema()` — executable equality assertion in `serve/mcp-kanban/tests/` (not comment-only)
- [ ] AC7: No `isinstance(*, Mock)` checks in `show_task` handler. Remove the Mock-specific section-handling branch at server.py:337-338. (The top-level `Mock` import stays — used by `_agent_view_for()`, a separate concern not in this task's scope.)
- [ ] AC8: All adjacent test suites updated to match Brief A kwarg contracts: (a) `test_mcp_guidance_1089.py` 3 callers: `show_task(task_id=…)` → `show_task(id=…)`, (b) `test_mcp_read_tools.py` ~L807: `kw.get("id")` → `kw.get("task_id")` when asserting engine-call kwargs. Task-local tests in `test_mcp_server_1090.py` that encode Mock-branch behavior (e.g., `section=""` assertion when `None` was passed) must also be corrected.

## Coverage Note
`owlbear_mcp_kanban.server` has 10+ tool handlers. This task covers 3 read handlers + error helper. Module-level coverage below 90% is architecturally expected and is not a defect — the reviewer gate applies to task-scoped proof, not module-wide percentage.
[[2026-04-28]]
## Architecture Review (cycle 5 — loop-breaker re-evaluation)

### Root-cause Analysis
The 4 prior failures share a common root cause: the `isinstance(view, Mock)` branch at server.py:337 created a circular dependency between production code and test expectations. Mock-based tests exercised the Mock-specific codepath (`section=None` → `""`) instead of the production path (`section=None` → omit kwarg or pass None). Every cycle either: (a) left the Mock branch in place (AC7 violation), or (b) fixed the adapter but left test assertions encoding Mock-branch behavior (contradictory proofs). Breaking the cycle requires fixing all three layers simultaneously: adapter code, durable test assertions, and task-local test assertions.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Read adapter for 3 tools — one domain (MCP boundary) |
| Interface clarity | PASS | AC2 now specifies exact call: `view.show_task(task_id=params.id, section=params.section)` — no ambiguity |
| Dependency correctness | PASS | Parent #1045, dependency #1086 — both archived |
| Module layering | PASS | Adapter → AgentView → Engine, no upward imports |
| TDD compliance | PASS | Test-writer processes at `todo`; task-local suite exists at tests/test_mcp_server_1090.py |
| KISS/YAGNI | PASS | Single unconditional call replaces 4-line branching construct |
| Premise challenge | PASS | Brief A mandates these adapters; boundary models exist in models.py |
| Pattern consistency | PASS | Uses `_map_kanban_error` + AgentView injection; AC6 follows output_schema pattern |
| Security surface | PASS | Read-only tools, input validated by boundary models (`extra="forbid"`) |
| Single domain | PASS | MCP adapter domain only |

### Key Refinements (cycle 5)
1. **AC2 simplified**: Single unconditional call `view.show_task(task_id=params.id, section=params.section)`. Engine.show_task(section: str | None = None) accepts None natively — no need for branching.
2. **AC4/AC6 proof location**: Explicitly requires executable tests in `serve/mcp-kanban/tests/` (not comment-only, not cross-package).
3. **AC7 explicit**: Names the exact line (server.py:337-338) to remove. Scopes Mock import retention to `_agent_view_for()`.
4. **AC8 widened**: Includes `test_mcp_read_tools.py` ~L807 (durable kwarg contradiction) and task-local Mock-branch assertions alongside the existing guidance caller rollout.
5. **Coverage note**: Explicit architecture statement that <90% module coverage is expected for 3-of-10 handler slice.

### Challenger Response
Challenger: reconsider (confidence 0.56). Four concerns raised:
1. Rollout boundary incomplete — ACCEPTED: AC8 now includes task-local test corrections.
2. Proof location unspecified — ACCEPTED: AC4/AC6 now specify `serve/mcp-kanban/tests/`.
3. AC4 breadth (only show_task) — PARTIALLY ACCEPTED: show_task is the focal handler and sufficient to prove `model_validate` is in use. list_tasks/pick_tasks boundary validation is already proven by durable error-mapping tests.
4. Coverage gate mismatch — REBUTTED: Coverage Note in task body provides explicit architectural rationale. Module-level 51% is a 3-of-10 handler artifact.

Blind spot on `id` defaulting to 0 in handler signature: `ShowTaskParams.model_validate({"id": 0})` succeeds at boundary; engine raises NotFoundError for non-existent task → ToolError. Correct separation of concerns.

Protocol instruction drift (`show_task(task_id="{id}")`) noted by challenger — already documented as out-of-scope docs concern in prior cycle. Not a code regression.

### Verdict: REFINE → APPROVE
### Action Taken: Rewrote full task body with 8 refined AC lines + coverage note. All 4 prior-failure root causes addressed in AC text. Advancing to `todo`.
[[2026-04-28]]
## Test-Writer Notes
- Test file: tests/test_mcp_server_1090.py
- Classes: TestFromAC_ShowTaskUnconditionalCall, TestFromAC_DurableSuiteRollout
- Tests per category: happy 0, edge 0, error 0, boundary 3
- Total: 3 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Test | Status |
|----|------|--------|
| AC1 | 12-param list_tasks surface | already verified by durable suite — pass-through |
| AC2 | section=None passes through as None (not "") | test_section_none_passes_through_as_none_not_empty_string — FAILS |
| AC3 | pick_tasks delegates to AgentView | already implemented — pass-through |
| AC4 | model_validate rejects type-invalid input | already implemented — pass-through |
| AC5 | KanbanError → ToolError via _map_kanban_error | already implemented — pass-through |
| AC6 | list_tasks output_schema set | already implemented — pass-through |
| AC7 | No isinstance(view, Mock) in show_task | test_show_task_source_has_no_isinstance_mock_check — FAILS |
| AC8(a) | guidance test uses id= not task_id= | already fixed — pass-through |
| AC8(b) | test_mcp_read_tools.py L807 kw.get("task_id") | test_read_tools_suite_show_task_id_assertion_uses_task_id_kwarg — FAILS |

Previous cycle note: All 4 prior-cycle tests were PASSING (they tested already-implemented behavior or wrong/Mock-branch behavior). Replaced with 3 tests targeting unimplemented AC2/AC7/AC8(b) gaps. The Mock branch (isinstance(view, Mock) → section="") is the root cause of AC2+AC7 failures; AC8(b) is a durable suite kwarg assertion mismatch.
[[2026-04-28]]
## Builder Notes
- Implementation: Updated `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` and `serve/mcp-kanban/tests/test_mcp_read_tools.py`.
- Fixes applied:
  - Removed Mock-specific branching from `show_task` and switched to the AC-mandated single unconditional call: `view.show_task(task_id=params.id, section=params.section)`.
  - Corrected durable-suite assertion in `test_show_task_id_forwarded_exact` to assert `kw.get("task_id")` instead of `kw.get("id")`.
- Tests: 52 passed, 0 failed (scoped quality-runner run over `tests/test_mcp_server_1090.py` and `serve/mcp-kanban/tests/test_mcp_read_tools.py`).
- ruff: clean (`server.py`, `test_mcp_read_tools.py`, `test_mcp_server_1090.py`).
- Coverage evidence: `owlbear_mcp_kanban.server` 33% in scoped run; this task intentionally validates the read-adapter slice only, consistent with task coverage note.

Post-task reflection:
- Problem faced: prior Mock-specific behavior in adapter created a mismatch between production contract and test expectations.
- Workaround applied: enforced direct passthrough call path with no view-type branching.
- Pattern discovered: adapter durability checks should assert engine kwarg names (`task_id`) rather than boundary model field names (`id`).
- Time sink: contradictory durable assertion masked completion despite correct adapter intent.
- Quality gap closed: aligned task-local structural assertion and durable behavioral assertion with the same engine-call contract.
[[2026-04-28]]
## Review Evidence
### Test Results
- pytest: 63 passed, 0 failed (`tests/test_mcp_server_1090.py`, `serve/mcp-kanban/tests/test_mcp_read_tools.py`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py` via quality-runner)
- Divergence: execution is green, but contract-proof review found missing executable evidence for AC4 and AC6.

### Lint
- ruff: clean on `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`, `serve/mcp-kanban/tests/test_mcp_read_tools.py`, `tests/test_mcp_server_1090.py`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`

### Coverage
- `owlbear_mcp_kanban.server`: 53%
- Coverage is not the gating defect here. The task body explicitly allows sub-90% module coverage for this 3-handler slice.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | `test_list_tasks_forwards_all_twelve_params_exact` + `test_list_tasks_forwards_ids_param` | Partly. The 11 non-`ids` params are exact at `serve/mcp-kanban/tests/test_mcp_read_tools.py:515` and `:548`; `ids` forwarding is only checked by stringifying `call_args` at `serve/mcp-kanban/tests/test_mcp_read_tools.py:264` and `:279`, so a wrong kwarg shape could slip through. | LAX |
| AC2 | `test_section_none_passes_through_as_none_not_empty_string`, `test_show_task_id_forwarded_exact`, adjacent guidance callers | Yes. The live adapter uses `ShowTaskParams.model_validate(...)` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:334` and the unconditional call at `:336`; task-local and durable tests would fail if `section=None` were normalized or `task_id` were not forwarded. | COVERED |
| AC3 | `test_pick_tasks_forwards_wave_size_exact`, `test_pick_tasks_forwards_max_waves_exact`, `test_pick_tasks_wave_size_none_forwarded_exact` | Yes. Exact kwarg forwarding is asserted at `serve/mcp-kanban/tests/test_mcp_read_tools.py:974`, `:992`, and `:1010`. | COVERED |
| AC4 | None. The task-local file explicitly says AC4 was treated as “already implemented” at `tests/test_mcp_server_1090.py:14`. Existing negative tests at `serve/mcp-kanban/tests/test_mcp_read_tools.py:729` and `:930` mock downstream `ValidationError`; they do not pass type-invalid MCP input through the boundary validator. | No. Replacing `model_validate` with `model_construct` could leave the scoped suite green. | MISSING |
| AC5 | Durable ToolError mapping tests plus live helper usage | Yes for behavior. `_map_kanban_error` is used in all three handlers at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:177`, `:338`, and `:623`, and the outward ToolError behavior is exercised by the read/guidance suites. | COVERED |
| AC6 | None. The task-local file explicitly says AC6 was treated as “already set” at `tests/test_mcp_server_1090.py:16` and `:240`. The live assignment exists at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:188`, but there is no executable equality assertion for `ListTasksResponse.model_json_schema()` in the scoped MCP test package. | No. Changing the registered schema could still leave the scoped suite green. | MISSING |
| AC7 | `test_section_none_passes_through_as_none_not_empty_string` + `test_show_task_source_has_no_isinstance_mock_check` | Yes. The `show_task` body at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:326-338` contains no Mock branch, and the structural/task-local assertions would fail if it returned. | COVERED |
| AC8 | `test_read_tools_suite_show_task_id_assertion_uses_task_id_kwarg` + adjacent guidance callers | Yes. Guidance callers use `id=` at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:226`, `:254`, and `:444`; the durable kwarg assertion uses `task_id` at `serve/mcp-kanban/tests/test_mcp_read_tools.py:794` and `:807`; the task-local rollout guard is at `tests/test_mcp_server_1090.py:207`. | COVERED |

#### Security Review
- No issues found. The changed handlers only validate input and delegate to `AgentView`; no new I/O, subprocess, SQL, template, dependency, or secret surface was added.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_ShowTaskUnconditionalCall.test_section_none_passes_through_as_none_not_empty_string` | Live assertion still checks exact `section is None` in the engine call. | PRESERVED |
| `TestFromAC_ShowTaskUnconditionalCall.test_show_task_source_has_no_isinstance_mock_check` | Structural assertion remains intact. | PRESERVED |
| `TestFromAC_DurableSuiteRollout.test_read_tools_suite_show_task_id_assertion_uses_task_id_kwarg` | Live assertion target now matches `task_id`; no weakening found. | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most task-owned assertions are exact, but `ids` forwarding still relies on `str(call_args)` at `serve/mcp-kanban/tests/test_mcp_read_tools.py:279`. |
| Negative/error-path coverage | WEAK | AC4 requires a boundary invalid-type test and none exists; current negative tests at `serve/mcp-kanban/tests/test_mcp_read_tools.py:729` and `:930` inject downstream `ValidationError` instead. |
| Manual mutation reasoning | WEAK | Replacing `model_validate` with `model_construct`, or changing the registered `list_tasks` schema at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:188`, would not be caught by the current scoped suite. |
| Test independence | ADEQUATE | Fresh tmp-path fixtures and isolated mocks are used in the scoped suites. |
| Descriptive names | STRONG | Task-owned and durable tests are specific and behavior-oriented. |

#### Data Safety
- No issues found. This is a read-only adapter slice with no persistence or multi-step mutation path.

#### Implementation-Aware Gaps
- `model_validate` is present in `list_tasks`, `show_task`, and `pick_tasks` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:146`, `:334`, and `:612`, but no scoped MCP test proves type-invalid input is rejected at the boundary.
- `list_tasks` registers `output_schema` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:188`, but no scoped MCP test asserts equality with `ListTasksResponse.model_json_schema()`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Prior `## Review Evidence` sections | 0 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `tests/test_mcp_server_1090.py:11-16` and `:237-240` still frame AC4 and AC6 as “already implemented” rather than requiring executable proof. That prose now conflicts with the explicit AC text in the task body.
- The scoped coverage result is acceptable for this task; the rejection is about missing proof, not coverage percentage.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `ListTasksParams.model_validate(...)` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:146`; exact 11-param forwarding at `serve/mcp-kanban/tests/test_mcp_read_tools.py:515`; `ids` forwarded but only laxly asserted at `:264` / `:279` | `test_list_tasks_forwards_all_twelve_params_exact`, `test_list_tasks_forwards_ids_param` | PASS |
| AC2 | Unconditional `view.show_task(task_id=params.id, section=params.section)` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:336`; exact passthrough checks at `tests/test_mcp_server_1090.py:143` and `serve/mcp-kanban/tests/test_mcp_read_tools.py:794` | `test_section_none_passes_through_as_none_not_empty_string`, `test_show_task_id_forwarded_exact` | PASS |
| AC3 | `PickTasksParams.model_validate(...)` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:612`; exact kwarg tests at `serve/mcp-kanban/tests/test_mcp_read_tools.py:974`, `:992`, `:1010` | `test_pick_tasks_forwards_wave_size_exact`, `test_pick_tasks_forwards_max_waves_exact`, `test_pick_tasks_wave_size_none_forwarded_exact` | PASS |
| AC4 | No scoped MCP test passes type-invalid input such as `id="not_an_int"`; task-local file omits it at `tests/test_mcp_server_1090.py:14`; existing validation tests at `serve/mcp-kanban/tests/test_mcp_read_tools.py:729` and `:930` only mock downstream `ValidationError` | None | FAIL |
| AC5 | `_map_kanban_error` helper exists at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:75` and is used at `:177`, `:338`, `:623`; ToolError mapping behavior is exercised by the read/guidance suites | durable ToolError mapping tests | PASS |
| AC6 | `list_tasks` schema assignment exists at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:188`; task-local file omits executable proof at `tests/test_mcp_server_1090.py:16` and `:240`; no equality assertion exists in the scoped MCP suites | None | FAIL |
| AC7 | No Mock branch remains in `show_task` at `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:326-338`; structural guard at `tests/test_mcp_server_1090.py:174` | `test_show_task_source_has_no_isinstance_mock_check` | PASS |
| AC8 | Adjacent callers updated to `id=` at `serve/mcp-kanban/tests/test_mcp_guidance_1089.py:226`, `:254`, `:444`; durable kwarg assertion updated at `serve/mcp-kanban/tests/test_mcp_read_tools.py:807`; rollout guard at `tests/test_mcp_server_1090.py:207` | rollout guard + adjacent durable suites | PASS |

### Deductions
- `-0.12` AC4 missing the required boundary invalid-type executable proof.
- `-0.08` AC6 missing the required `output_schema` equality proof.
- `-0.02` AC1 `ids` forwarding remains only laxly asserted via `str(call_args)`.

### Confidence: 0.78
### Verdict: FAIL
### Action
- Reject to `todo`. Implementation is correct enough to preserve, but the test suite does not prove AC4 or AC6. Next cycle should be test-writer-owned: add direct boundary invalid-type MCP tests for the read handlers and add an executable `list_tasks.output_schema == ListTasksResponse.model_json_schema()` assertion in `serve/mcp-kanban/tests/`.

### Post-task Reflection
- Green scoped execution can still be a false pass when explicit AC proof was deferred into prose.
- Adapter tasks need direct wire-contract tests for boundary validation and registered schema, not only behavior through mocks.
- Task-local `TestFromAC_*` coverage was improved for AC2/AC7/AC8, but AC4/AC6 were incorrectly treated as “already implemented.”
- The right route here is `todo`: preserve the builder’s correct code and send the missing proof back to test-writing.
[[2026-04-28]]
## Test-Writer Notes
- Test file: serve/mcp-kanban/tests/test_mcp_server_1090.py (new — proof tests for retry cycle)
- Classes: TestFromAC_BoundaryValidation, TestFromAC_OutputSchema
- Tests per category: happy 0, edge 0, error 2 (boundary invalid-type), boundary 1 (schema equality)
- Total: 3 tests
- ruff: clean

Retry cycle note: All 3 tests PASS immediately — implementation was already correct for AC4/AC6. Tests are mutation-resistant contractual proof added in the required location (serve/mcp-kanban/tests/).

AC coverage:
| AC | Test | Status |
|----|------|--------|
| AC4 | test_show_task_type_invalid_id_raises_tool_error | PROOF: model_validate boundary; model_construct would let string reach engine → no ToolError → test fails |
| AC4 | test_list_tasks_type_invalid_ids_element_raises_tool_error | PROOF: list[int] boundary; same mutation logic |
| AC6 | test_list_tasks_output_schema_equals_model_json_schema | PROOF: exact equality assertion for registered schema |

Mutation resistance: replacing model_validate with model_construct in either handler would cause (a) no ToolError raised and (b) engine called with invalid types — both pytest.raises and assert_not_called assertions fail. Changing or removing the output_schema registration breaks AC6 equality assert.

Prior test file (tests/test_mcp_server_1090.py) preserved unchanged per retry protocol.
[[2026-04-28]]
## Builder Notes
- Implementation: no code changes in this cycle; existing adapter implementation and proof tests already satisfy AC1-AC8.
- Files changed: none.
- Tests: 66 passed, 0 failed, 0 skipped (scoped quality-runner run over `tests/test_mcp_server_1090.py`, `serve/mcp-kanban/tests/test_mcp_server_1090.py`, `serve/mcp-kanban/tests/test_mcp_read_tools.py`, `serve/mcp-kanban/tests/test_mcp_guidance_1089.py`).
- Coverage: `owlbear_mcp_kanban.server` 54% in scoped run (expected for 3-handler slice per task coverage note).
- ruff: clean on scoped lint paths.
- Evidence summary: AC4/AC6 executable proof now exists in `serve/mcp-kanban/tests/test_mcp_server_1090.py`; AC2/AC7/AC8 durable rollout checks remain green.

Post-task reflection:
- Problem faced: prior cycles failed on missing executable AC4/AC6 proof despite adapter code being correct.
- Workaround applied: accepted retry-cycle proof tests and verified through quality-runner rather than reworking already-correct source.
- Pattern discovered: contract-proof gaps can require test-layer completion while source remains unchanged.
- Time sink: repeated code-oriented loops on a test-proof deficit.
- Quality gap closed: AC4/AC6 are now backed by executable tests in the required MCP test package.
[[2026-04-28]]
## Review Evidence
### Test Results
- pytest: 66 passed, 0 failed, 0 skipped (quality-runner scoped run over tests/test_mcp_server_1090.py, serve/mcp-kanban/tests/test_mcp_server_1090.py, serve/mcp-kanban/tests/test_mcp_read_tools.py, serve/mcp-kanban/tests/test_mcp_guidance_1089.py)

### Lint
- ruff: clean on serve/mcp-kanban/src/owlbear_mcp_kanban/server.py and the four scoped test files

### Coverage
- owlbear_mcp_kanban.server: 54%
- quality-runner scoped_note: module-scoped --cov is unavailable here because it crashes on a pydantic MRO path; the run used bare --cov and still reported the target module percentage.
- Gate decision: PASS. The task body explicitly scopes this task to a 3-handler slice and states that sub-90% module coverage is expected for this module.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | serve/mcp-kanban/tests/test_mcp_read_tools.py:515 and :279 | Yes for the 11 non-ids params; ids proof is still lax because it stringifies call_args instead of asserting the exact kwarg name. | LAX |
| AC2 | tests/test_mcp_server_1090.py:143, :174 and serve/mcp-kanban/tests/test_mcp_read_tools.py:794 | Yes. Reintroducing section normalization or dropping task_id forwarding would fail these assertions. | COVERED |
| AC3 | serve/mcp-kanban/tests/test_mcp_read_tools.py:974, :992, :1010 | Yes. Exact wave_size/max_waves passthrough is pinned by direct kwarg assertions. | COVERED |
| AC4 | serve/mcp-kanban/tests/test_mcp_server_1090.py:147 and :173 | Yes. Replacing model_validate with model_construct would skip ToolError and violate assert_not_called() on the mocked view. | COVERED |
| AC5 | serve/mcp-kanban/tests/test_mcp_read_tools.py:1118, :1139, :1160, :1181 and serve/mcp-kanban/tests/test_mcp_guidance_1089.py:444 | Yes for user-visible ToolError behavior; helper usage itself is primarily pinned by live code at server.py:177, :338, :623 rather than a helper-specific executable assertion. | LAX |
| AC6 | serve/mcp-kanban/tests/test_mcp_server_1090.py:208 | Yes. Removing or drifting the registered schema breaks the direct equality assertion. | COVERED |
| AC7 | tests/test_mcp_server_1090.py:143 and :174 | Yes. The task-local tests would fail if show_task reintroduced a Mock branch or coerced None to an empty string. | COVERED |
| AC8 | tests/test_mcp_server_1090.py:207, serve/mcp-kanban/tests/test_mcp_read_tools.py:807, serve/mcp-kanban/tests/test_mcp_guidance_1089.py:226, :254, :444 | Yes. The rollout guards pin id= at the MCP boundary and task_id= at the engine call boundary. | COVERED |

#### Security Review
- No issues found. The reviewed handlers only validate MCP input, delegate to AgentView, and map KanbanError to ToolError. No new I/O, subprocess, template, secret, or dependency surface was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| tests/test_mcp_server_1090.py TestFromAC_ShowTaskUnconditionalCall | Live assertions still require exact section=None passthrough and structural absence of isinstance(view, Mock). | PRESERVED |
| tests/test_mcp_server_1090.py TestFromAC_DurableSuiteRollout | Live assertion still rejects kw.get("id") and requires task_id in the durable suite. | PRESERVED |
| serve/mcp-kanban/tests/test_mcp_server_1090.py retry-cycle proof tests | New executable AC4/AC6 proof added in the required MCP test package. | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Exact contract proofs exist for AC2/AC3/AC4/AC6/AC8. Residual weak spots are limited to ids forwarding at serve/mcp-kanban/tests/test_mcp_read_tools.py:279 and the helper-specific clause of AC5, both documented below as non-blocking. |
| Negative/error-path coverage | ADEQUATE | Invalid-type boundary failures are exercised at serve/mcp-kanban/tests/test_mcp_server_1090.py:147 and :173; exact not-found ToolError text is pinned at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:444-445. |
| Manual mutation reasoning | ADEQUATE | model_validate -> model_construct in list_tasks/show_task, schema drift at server.py:188, or reintroducing the Mock branch in show_task would all break the scoped suite. |
| Test independence | STRONG | The scoped tests use isolated mocks and fixtures with no shared mutable state. |
| Descriptive names | STRONG | Test names remain behavior-specific and map cleanly to the AC lines. |

#### Data Safety
- No issues found. The reviewed scope is a read-only adapter slice with no persistence or multi-step mutation path.

#### Implementation-Aware Gaps
- Non-blocking residual: pick_tasks has no dedicated type-invalid boundary test. I am not failing on this because the latest Architecture Review refinement explicitly narrowed AC4 to the show_task focal proof path, and the retry cycle already strengthened coverage by adding list_tasks invalid-type proof as well.
- Non-blocking residual: ids passthrough proof in serve/mcp-kanban/tests/test_mcp_read_tools.py:279 still relies on stringified mock call args.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Prior Review Evidence sections | 1 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- share/skills/r-pipeline-protocol/SKILL.md:161 still shows show_task(task_id="{id}") in documentation. The task body already marked this as out-of-scope protocol-doc drift rather than a code regression.
- The adjacent durable suite still contains a few legacy weaker assertions, but stronger exact assertions in the scoped files now pin every gating behavior required by AC1-AC8.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:146 validates ListTasksParams and forwards the Brief A surface; exact 11-param proof at serve/mcp-kanban/tests/test_mcp_read_tools.py:515, ids proof at :279 | test_list_tasks_forwards_all_twelve_params_exact, test_list_tasks_forwards_ids_param | PASS |
| AC2 | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:334 and :336; task-local None passthrough/source checks at tests/test_mcp_server_1090.py:168 and :190; exact task_id assertion at serve/mcp-kanban/tests/test_mcp_read_tools.py:807 | test_section_none_passes_through_as_none_not_empty_string, test_show_task_source_has_no_isinstance_mock_check, test_show_task_id_forwarded_exact | PASS |
| AC3 | serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:612; exact pick_tasks kwarg assertions at serve/mcp-kanban/tests/test_mcp_read_tools.py:974, :992, :1024 | test_pick_tasks_forwards_wave_size_exact, test_pick_tasks_forwards_max_waves_exact, test_pick_tasks_wave_size_none_forwarded_exact | PASS |
| AC4 | Boundary invalid-type ToolError proofs at serve/mcp-kanban/tests/test_mcp_server_1090.py:167, :170, :192, :195 | test_show_task_type_invalid_id_raises_tool_error, test_list_tasks_type_invalid_ids_element_raises_tool_error | PASS |
| AC5 | _map_kanban_error definition at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:75-77 and handler use at :177, :338, :623; exact outward message proof at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:444-445 plus user_message-preservation tests at serve/mcp-kanban/tests/test_mcp_read_tools.py:1118, :1139, :1160, :1181 | scoped error-mapping tests + live code read | PASS |
| AC6 | list_tasks output_schema registration at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:188 and direct equality assertion at serve/mcp-kanban/tests/test_mcp_server_1090.py:227 | test_list_tasks_output_schema_equals_model_json_schema | PASS |
| AC7 | show_task body at serve/mcp-kanban/src/owlbear_mcp_kanban/server.py:326-338 contains no Mock-specific branch; structural/source guard at tests/test_mcp_server_1090.py:190 | test_show_task_source_has_no_isinstance_mock_check | PASS |
| AC8 | Guidance callers use id= at serve/mcp-kanban/tests/test_mcp_guidance_1089.py:226, :254, :444; durable engine-kwarg assertion uses task_id at serve/mcp-kanban/tests/test_mcp_read_tools.py:807; rollout guard at tests/test_mcp_server_1090.py:226 | rollout guard + adjacent durable suites | PASS |

### Deductions
- -0.03 AC1 ids forwarding proof still relies on stringified call_args.
- -0.02 AC5 helper-specific clause is primarily code-backed rather than helper-specific test-backed.
- -0.01 pick_tasks boundary invalid-type path is unpinned, but latest architecture refinement makes this residual non-gating for task 1090.

### Confidence: 0.94
### Verdict: PASS
### Action
- Advance to docs. The implementation and scoped proof now satisfy AC1-AC8, and the remaining weaker adjacent assertions are documented as non-blocking quality debt rather than gate failures.
[[2026-04-28]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A — no update needed | serve/mcp-kanban/README.md Tools table lists list_tasks/show_task/pick_tasks with accurate descriptions; task removed an internal Mock branch — no user-facing API or behavior change introduced. Pre-existing brief tool-param description in README is not task-introduced drift. |
| 2 | Module docstrings | Yes | Verified / no update | All 3 changed public handlers have accurate docstrings: list_tasks "List kanban tasks with optional filters.", show_task "Show a single task by ID with full details.", pick_tasks multi-line docstring. _map_kanban_error also has a docstring. No inaccuracies introduced by this task. |
| 3 | External attribution | No | N/A | Task body references Brief A only; no external patterns, articles, or repos used. |
| 4 | Research doc | No | N/A | No research doc produced or referenced. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | kanban.excalidraw (describes: serve/mcp-kanban/src/**) and mcp-topology.excalidraw (describes: serve/mcp-*/src/**) both match the changed server.py path. Footers updated: 2a7c6deb → eb38fd86 (2026-04-28). |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. Second builder cycle explicitly states "Files changed: none." |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/mcp-kanban/src/owlbear_mcp_kanban/server.py | IN (Python docstrings) | Verified — no update needed |
| serve/mcp-kanban/tests/test_mcp_read_tools.py | OUT (test file) | N/A |
| tests/test_mcp_server_1090.py | OUT (test file) | N/A |
| serve/mcp-kanban/tests/test_mcp_server_1090.py | OUT (test file) | N/A |

### Files Updated
- share/diagrams/kanban.excalidraw (footer)
- share/diagrams/mcp-topology.excalidraw (footer)

### Child Tasks Created
- None

### Scratch Files Cleaned
- .owlbear/scratch/1090-quality-pass-pytest.txt
- .owlbear/scratch/1090-quality-pass-ruff.txt