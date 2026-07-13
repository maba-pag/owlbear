---
id: 1082
title: 'B-17: RED — cockpit backend route tests'
status: archived
priority: medium
created: 2026-04-21 10:50:43.401807+00:00
updated: 2026-04-27T21:53:27.680048+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- scope:cockpit
- tdd:red
parent: 1044
depends_on:
- 1081
- 1144
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §5, AC-NEW-24
Module: `tests/test_cockpit_kanban_routes.py`

Test FastAPI cockpit backend routes that wrap CockpitView methods. Routes include: task reads (GET /api/tasks, GET /api/tasks/{id}), OCC mutations (POST /api/tasks/{id}/edit, POST /api/tasks/{id}/move), admin operations (POST /api/tasks/{id}/release, POST /api/tasks/sweep), activity/session reads (GET /api/activity, GET /api/sessions), and maintenance (POST /api/tasks/scan, POST /api/tasks/repair, POST /api/tasks/compact-activity).

## Acceptance Criteria

- [ ] AC-NEW-24: `POST /api/tasks/{id}/edit` with `status` in request body → HTTP 422 (Pydantic rejects before engine)
- [ ] OCC mutations pass `expected_updated` from request body to CockpitView
- [ ] ERR_STALE from CockpitView → HTTP 409 Conflict
- [ ] ERR_NOT_FOUND → HTTP 404
- [ ] ValidationError → HTTP 422
- [ ] ConfigError → HTTP 500
- [ ] GET /api/tasks returns ListTasksResponse envelope
- [ ] GET /api/tasks/{id} returns ShowTaskResponse envelope
- [ ] GET /api/activity returns filtered activity events
- [ ] GET /api/sessions returns SessionRecord list
- [ ] POST /api/tasks/{id}/release returns SingleTaskResponse
- [ ] POST /api/tasks/sweep returns list of released task IDs
- [ ] All tests fail (RED phase)
[[2026-04-27]]
## Test-Writer Notes

**Test file:** `tests/test_cockpit_kanban_routes_1082.py`
**Class:** `TestFromAC_CockpitRoutes`
**Total:** 18 tests, all FAIL (RED phase verified)
**Lint:** ruff clean

### Tests by category

| Category | Count | Tests |
|----------|-------|-------|
| happy (response envelope shape) | 8 | list_tasks guidance, list_tasks no-mtime, show_task guidance, show_task missing_sections, activity 200, activity list, sessions flat list, sessions task_status_at_start |
| happy (new routes) | 4 | get_activity 200, get_activity list, sweep 200, sweep list-of-int |
| happy (mutation envelope) | 2 | release guidance, move guidance |
| error (CockpitView delegation) | 5 | edit delegates (called_once), ERR_STALE→409, ERR_NOT_FOUND→404, ValidationError→422, ConfigError→500 |
| boundary | 1 | activity filter by task_id |

### AC coverage

| AC | Test(s) |
|----|---------|
| AC-NEW-24 (Pydantic rejects status before engine) | covered via `test_edit_delegates_to_cockpit_view_not_engine` (constraint: EditRequest.extra='forbid' unchanged) |
| OCC edit passes expected_updated to CockpitView | `test_edit_delegates_to_cockpit_view_not_engine` |
| ERR_STALE → 409 | `test_edit_stale_token_from_cockpit_view_returns_409` |
| ERR_NOT_FOUND → 404 | `test_edit_not_found_from_cockpit_view_returns_404` |
| ValidationError → 422 | `test_edit_validation_error_from_cockpit_view_returns_422` |
| ConfigError → 500 | `test_edit_config_error_from_cockpit_view_returns_500` |
| GET /api/tasks ListTasksResponse | `test_list_tasks_response_has_guidance_field`, `test_list_tasks_envelope_has_no_mtime_field` |
| GET /api/tasks/{id} ShowTaskResponse | `test_show_task_response_has_guidance_field`, `test_show_task_response_has_missing_sections_field` |
| GET /api/activity | `test_get_activity_endpoint_returns_200`, `test_get_activity_returns_list_of_event_objects`, `test_get_activity_filter_by_task_id_scopes_results` |
| GET /api/sessions SessionRecord | `test_sessions_response_is_flat_list_not_wrapped`, `test_sessions_record_has_task_status_at_start_field` |
| POST /api/tasks/{id}/release SingleTaskResponse | `test_release_response_has_guidance_field` |
| POST /api/tasks/{id}/move SingleTaskResponse | `test_move_response_has_guidance_field` |
| POST /api/tasks/sweep | `test_sweep_endpoint_returns_200`, `test_sweep_returns_list_of_integer_task_ids` |

### Why each test fails

- **guidance/missing_sections fields**: Current cockpit models (TaskListOut, TaskDetailOut) lack these fields from ListTasksResponse/ShowTaskResponse/SingleTaskResponse
- **GET /api/activity**: Route not registered → 404
- **GET /api/sessions flat list**: Current route returns SessionListOut `{"sessions": [...]}`, not a flat list
- **POST /api/tasks/sweep**: Route not registered → 405
- **CockpitView delegation tests**: Edit route uses `_Engine` (KanbanEngine) directly, not `_View` (CockpitView); mocked view is never consulted; engine edit with fresh token returns 200
[[2026-04-27]]
## Builder Notes
- Implementation:
  - Updated cockpit read routes to use CockpitView canonical envelopes and added missing endpoint `GET /api/activity`.
  - Updated cockpit mutation routes to return `SingleTaskResponse`, delegate edit to CockpitView, and added missing endpoint `POST /api/tasks/sweep`.
- Files changed:
  - `serve/cockpit/src/owlbear_cockpit/routes/read.py`
  - `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
- RED verification:
  - `tests/test_cockpit_kanban_routes_1082.py` was confirmed failing before implementation (18 failed).
- GREEN verification (quality-runner, scoped):
  - `tests/test_cockpit_kanban_routes_1082.py`: 18 passed, 0 failed.
  - `ruff` on touched files + task test: clean.
- Coverage evidence:
  - Scoped run with `coverage_modules=["owlbear_cockpit"]` reported:
    - `owlbear_cockpit.routes.read`: 83%
    - `owlbear_cockpit.routes.mutation`: 71%
  - Coverage tool output was inconsistent for direct module targeting; broader run also indicates cockpit routes are not currently tracked consistently by global coverage configuration.
- Evidence summary:
  - AC behaviors now implemented: edit delegates to CockpitView with mapped domain errors; stale/not-found/validation/config mappings; read envelopes now include guidance/missing_sections; sessions returns flat list; activity and sweep endpoints are available.

### Reflection
- Existing durable suites in `tests/test_cockpit_read_api.py` and `tests/test_cockpit_mutation_api.py` still assert legacy response shapes (`mtime`, wrapped sessions, `block:user` tag behavior), which now conflict with task-1082 contract.
- Main time sink was reconciling contract drift between task-scoped AC tests and legacy durable suites.
- Workaround applied: strict task-scoped GREEN verification plus explicit drift note for reviewer follow-up.
[[2026-04-27]]
## Review Evidence
### Test Results
- Quality-runner scoped plus adjacent durable suites: 87 passed, 18 failed, 0 skipped.
- Task-owned suite passed: tests/test_cockpit_kanban_routes_1082.py.
- Durable regressions failed in tests/test_cockpit_read_api.py and tests/test_cockpit_mutation_api.py.
- Representative failures:
  - tests/test_cockpit_read_api.py::TestFromAC_TaskList::test_tasks_response_has_mtime_integer
  - tests/test_cockpit_read_api.py::TestFromAC_Sessions::test_sessions_response_has_sessions_list
  - tests/test_cockpit_read_api.py::TestFromAC_TaskDetailClaimedFields::test_task_detail_response_has_claimed_by_field
  - tests/test_cockpit_mutation_api.py::TestFromAC_BlockUserTag::test_block_adds_block_user_tag
  - tests/test_cockpit_mutation_api.py::TestFromAC_BlockUserTag::test_unblock_removes_block_user_tag

### Lint
- Ruff clean on serve/cockpit/src/owlbear_cockpit/routes/read.py, serve/cockpit/src/owlbear_cockpit/routes/mutation.py, and tests/test_cockpit_kanban_routes_1082.py.

### Coverage
- Quality-runner did not produce usable scoped module percentages for owlbear_cockpit.routes.read or owlbear_cockpit.routes.mutation. Coverage evidence is incomplete and was not used for PASS.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Were Violated? | Verdict |
|---------|-------------|----------------------------------|---------|
| AC-NEW-24 before-engine 422 | tests/test_cockpit_mutation_api.py:291 and tests/test_cockpit_kanban_routes_1082.py:392 | No. One test only checks 422 for a status payload; the task suite only checks delegation on a title payload. No test proves the status payload dies before lower layers are called. | LAX |
| OCC mutations pass expected_updated to CockpitView | tests/test_cockpit_kanban_routes_1082.py:392 | No. The task suite uses assert_called_once only and never checks call arguments for edit, move, or release. | MISSING |
| ERR_STALE maps to 409 | tests/test_cockpit_kanban_routes_1082.py:414 | Partially. Edit is covered; delegated move and release stale branches are not. | LAX |
| ERR_NOT_FOUND maps to 404 | tests/test_cockpit_kanban_routes_1082.py:436 | Partially. Edit is covered; delegated move and release not-found branches are not. | LAX |
| ValidationError maps to 422 | tests/test_cockpit_kanban_routes_1082.py:458 | Partially. Edit is covered; delegated move validation branch is not. | LAX |
| ConfigError maps to 500 | tests/test_cockpit_kanban_routes_1082.py:480 | Yes. | COVERED |
| GET /api/tasks returns ListTasksResponse envelope | tests/test_cockpit_kanban_routes_1082.py:179 and tests/test_cockpit_kanban_routes_1082.py:195 | Partially. The task suite only checks guidance present and mtime absent; it does not reconcile the opposite live durable contract in tests/test_cockpit_read_api.py:258. | LAX |
| GET /api/tasks/{id} returns ShowTaskResponse envelope | tests/test_cockpit_kanban_routes_1082.py:210 and tests/test_cockpit_kanban_routes_1082.py:225 | Partially. The task suite checks guidance and missing_sections only; older durable tests still require claimed_by in tests/test_cockpit_read_api.py:606. | LAX |
| GET /api/activity returns filtered activity events | tests/test_cockpit_kanban_routes_1082.py:243, tests/test_cockpit_kanban_routes_1082.py:254, tests/test_cockpit_kanban_routes_1082.py:266 | Yes. | COVERED |
| GET /api/sessions returns SessionRecord list | tests/test_cockpit_kanban_routes_1082.py:286 and tests/test_cockpit_kanban_routes_1082.py:300 | Yes for the task AC, but it directly conflicts with the wrapped-envelope contract still asserted in tests/test_cockpit_read_api.py:405. | COVERED |
| POST /api/tasks/{id}/release returns SingleTaskResponse | tests/test_cockpit_kanban_routes_1082.py:350 and tests/test_cockpit_mutation_api.py:395 | Yes. | COVERED |
| POST /api/tasks/sweep returns list of released task IDs | tests/test_cockpit_kanban_routes_1082.py:321 and tests/test_cockpit_kanban_routes_1082.py:334 | Yes. | COVERED |
| All tests fail in RED phase | Test-Writer Notes in task body | Historical evidence only; not independently rerunnable after GREEN. | COVERED (historical) |

#### Security Review
- No security issues found in the touched route files. The handlers only validate request bodies and delegate to in-process engine/view methods.

#### Test Integrity
| Original Test / Contract | Change Made | Assessment |
|--------------------------|-------------|------------|
| TestFromAC classes in tests/test_cockpit_kanban_routes_1082.py | No builder edits detected in task-owned tests | PRESERVED |
| tests/test_cockpit_kanban_routes_1082.py:207 versus tests/test_cockpit_read_api.py:258 | Opposite contracts for GET /api/tasks mtime field | CONTRADICTION |
| tests/test_cockpit_kanban_routes_1082.py:298 versus tests/test_cockpit_read_api.py:405 | Opposite contracts for GET /api/sessions envelope shape | CONTRADICTION |
| serve/kanban/src/owlbear_kanban/models.py:274 and serve/kanban/src/owlbear_kanban/models.py:322 versus tests/test_cockpit_read_api.py:606 | Canonical Brief-B projections intentionally drop claimed_by, but durable cockpit tests still require it | CONTRADICTION |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | Envelope tests mostly assert field presence or absence only; they do not prove full response shape or field types. |
| Negative and error-path coverage | WEAK | Edit error mapping is exercised, but delegated move and release failure paths in serve/cockpit/src/owlbear_cockpit/routes/mutation.py:123-137 and :254-264 are untested. |
| Manual mutation reasoning | WEAK | Removing expected_updated forwarding at serve/cockpit/src/owlbear_cockpit/routes/mutation.py:126, :219, or :254 would still pass the task suite. |
| Test independence | ADEQUATE | Dependency overrides are cleared in fixtures; state remains local per test. |
| Descriptive names | STRONG | Test names are explicit and behavior-oriented. |

#### Data Safety
- No direct data safety issue proven. OCC token forwarding exists in code, but proof quality is insufficient.

#### Implementation-Aware Gaps
- No task-owned test checks the exact expected_updated value passed to view.move_task, view.edit_task, or view.release_task even though the code forwards req.updated at serve/cockpit/src/owlbear_cockpit/routes/mutation.py:126, :219, and :254.
- No task-owned test covers delegated move failure branches after the call site in serve/cockpit/src/owlbear_cockpit/routes/mutation.py:123-137.
- No task-owned test covers delegated release failure branches after the call site in serve/cockpit/src/owlbear_cockpit/routes/mutation.py:254-264.
- The edit route now breaks established block:user lifecycle behavior because _build_edit_kwargs only diffs list fields and passes block_reason through, with no block:user conflict handling in serve/cockpit/src/owlbear_cockpit/routes/mutation.py:156-188. Durable failures proving that regression are in tests/test_cockpit_mutation_api.py:642, :661, :684, :745, and :776.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- Brief authority is narrow for AC-NEW-24. The paper section only explicitly grounds the before-engine status rejection at .owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md:389; the broader response-envelope changes need the same level of architecture grounding to avoid more cross-suite drift.
- Canonical Brief-B projections intentionally derive claimed from claimed_at and drop claimed_by at serve/kanban/src/owlbear_kanban/models.py:274 and :322-327. That explains the durable claimed_by failures and confirms this is a live contract conflict, not a random route bug.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-NEW-24 status field rejected before engine | .owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md:389 and serve/cockpit/src/owlbear_cockpit/routes/mutation.py:35-50 require it, but no test proves lower layers are not called for the status payload | tests/test_cockpit_mutation_api.py:291 | FAIL |
| OCC expected_updated reaches CockpitView | Code forwards req.updated at serve/cockpit/src/owlbear_cockpit/routes/mutation.py:126, :219, and :254, but the suite never asserts call arguments | tests/test_cockpit_kanban_routes_1082.py:392 | FAIL |
| ERR_STALE maps to 409 | Edit path tested; move and release delegated stale branches not proven | tests/test_cockpit_kanban_routes_1082.py:414 | FAIL |
| ERR_NOT_FOUND maps to 404 | Edit path tested; move and release delegated not-found branches not proven | tests/test_cockpit_kanban_routes_1082.py:436 | FAIL |
| ValidationError maps to 422 | Edit path tested; delegated move validation branch not proven | tests/test_cockpit_kanban_routes_1082.py:458 | FAIL |
| ConfigError maps to 500 | Code and test agree for edit path | tests/test_cockpit_kanban_routes_1082.py:480 | PASS |
| GET /api/tasks ListTasksResponse envelope | Route now declares ListTasksResponse at serve/cockpit/src/owlbear_cockpit/routes/read.py:41, but live durable suite still fails on the removed mtime field | tests/test_cockpit_kanban_routes_1082.py:179 | FAIL |
| GET /api/tasks/{id} ShowTaskResponse envelope | Route now declares ShowTaskResponse at serve/cockpit/src/owlbear_cockpit/routes/read.py:59, but live durable suite still fails on claimed_by expectations | tests/test_cockpit_kanban_routes_1082.py:210 | FAIL |
| GET /api/activity filtered events | Route and tests agree | tests/test_cockpit_kanban_routes_1082.py:243 | PASS |
| GET /api/sessions SessionRecord list | Route and task-owned tests agree at serve/cockpit/src/owlbear_cockpit/routes/read.py:91, but the live durable suite still asserts a wrapped sessions envelope | tests/test_cockpit_kanban_routes_1082.py:286 | FAIL |
| POST /api/tasks/{id}/release SingleTaskResponse | Route and tests agree | tests/test_cockpit_kanban_routes_1082.py:350 | PASS |
| POST /api/tasks/sweep list of released ids | Route and tests agree | tests/test_cockpit_kanban_routes_1082.py:321 | PASS |
| RED phase evidence exists | Task body contains prior Test-Writer Notes confirming all 18 task tests failed before builder work | task body | PASS |

### Deductions
- 0.25: Task-owned and durable cockpit suites encode contradictory public contracts for GET /api/tasks, GET /api/tasks/{id}, and GET /api/sessions.
- 0.20: The task suite does not prove AC-NEW-24 before-engine semantics or exact expected_updated forwarding.
- 0.15: The edit-route rewrite regressed established block:user lifecycle behavior in durable mutation tests.
- 0.05: Scoped coverage evidence for touched route modules was unavailable.

### Verdict
- FAIL. Confidence: 0.35.
- Routing: backlog. The blocking issue is not a clean builder-only bug. The task-owned contract and the live durable cockpit contract disagree on the same public endpoints, so the gate is structurally infeasible until architecture/test authority is reconciled.

### Action
- Architect/test-writer must reconcile the public cockpit route contract for list/detail/sessions envelopes and claimed fields across live suites.
- Regenerate task-scoped proof for before-engine rejection and expected_updated forwarding once the single source of truth is settled.
- Preserve the existing block:user edit semantics or deliberately retire them in the authoritative contract before sending builder back to GREEN.

### Reflection
- Cross-suite HTTP contract drift, not just local route code, was the main blocker.
- Running adjacent durable suites surfaced regressions that a task-only green run hid.
- Canonical Brief-B projection changes such as dropping claimed_by must be rolled out with coordinated durable-suite updates, not isolated route rewrites.
- Boundary ACs need direct non-call or call-argument assertions; status-code-only checks are too weak for review confidence.
[[2026-04-27]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests CockpitView delegation and new endpoints for cockpit backend — one domain |
| Interface clarity | PASS after refinement | AC lines tightened below for test-proof requirements |
| Dependency correctness | PASS | Added #1144 (durable suite reconciliation) as dependency; 1081 done/archived |
| Module layering | PASS | Routes delegate to CockpitView (engine facade); no upward imports |
| TDD compliance | PASS | RED task; test-writer wrote 18 failing tests before builder |
| KISS/YAGNI | PASS | Tests what Brief B §5 requires for cockpit routes |
| Premise challenge | PASS | CockpitView delegation is necessary — cockpit routes must use the role-view facade per D9 |
| Pattern consistency | PASS | Follows existing FastAPI route + TestClient pattern |
| Security surface | PASS | Routes validate request bodies via Pydantic and delegate to in-process view methods |
| Single domain | PASS | scope:cockpit only |

### Challenger Results
- Challenger: reconsider (confidence 0.41)
- Challenges raised: (1) maintenance routes in Brief scope but not in AC, (2) release OCC authority split, (3) block:user is cross-brief not legacy drift, (4) AC-NEW-24 proof underspecified, (5) reconciliation task not yet wired
- Architect response: ACCEPTED challenges 2-5. Challenge 1 (maintenance routes) scoped out — they have no routes, no tests, no implementation. Follow-up task needed separately.

### Authority Decisions
- **Release OCC**: Live CockpitView.release_task() requires expected_updated (line 3277 of engine.py). This is authoritative over Brief B §5 "no OCC" statement — the implementation and task #1133 tests already enforce OCC on release. AC line for OCC mutations covers release.
- **block:user**: Normative cockpit adapter contract per D21 and the blocking brief. Separated into #1144 since the regression predates this task's AC.
- **mtime**: Brief B D21 says Cockpit adapter injects mtime from cache. The task-owned test asserting mtime ABSENCE contradicts Brief B. Test-writer: remove the no-mtime assertion or replace with mtime presence assertion (cache injection is #1144's responsibility).
- **Maintenance routes** (scan, repair, compact-activity): Not in AC, not implemented, not tested. Out of scope. Needs a separate follow-up task.

### Refined AC (supersedes original)
These refinements specify what test proofs must demonstrate. The test-writer should rewrite the task-owned suite to satisfy these:

1. AC-NEW-24: POST /api/tasks/{id}/edit with status in body → HTTP 422; test MUST assert CockpitView mock is NOT called (proves Pydantic rejects before engine)
2. OCC mutations pass expected_updated: test MUST assert exact expected_updated value in call_args for view.edit_task(), view.move_task(), and view.release_task()
3. ERR_STALE → 409: for ALL delegated routes (edit, move, release) — not just edit
4. ERR_NOT_FOUND → 404: for ALL delegated routes (edit, move, release) — not just edit
5. ValidationError → 422: for edit and move routes (where applicable)
6. ConfigError → 500: edit path (adequate as-is)
7. GET /api/tasks returns ListTasksResponse with tasks + guidance (do NOT assert mtime absence — that contradicts D21)
8. GET /api/tasks/{id} returns ShowTaskResponse with missing_sections + guidance
9. GET /api/activity returns filtered activity events as flat list
10. GET /api/sessions returns SessionRecord flat list
11. POST /api/tasks/{id}/release returns SingleTaskResponse with guidance
12. POST /api/tasks/sweep returns list of released task IDs
13. All tests fail (RED phase)
14. No durable cockpit test regressions in full suite run (depends on #1144 completing first)

### Dependency
- Added #1144 as dependency: "Reconcile durable cockpit suites with Brief-B contract migration" — restores mtime injection, block:user adapter logic, updates claimed_by/sessions durable tests. Must complete before #1082 builder phase.

### Verdict: REFINE → todo
### Action Taken: Tightened 6 AC lines for explicit test-proof requirements (argument assertions, multi-route error coverage, before-engine proof). Created dependency task #1144 for durable suite reconciliation. Scoped out maintenance routes as separate follow-up.
[[2026-04-27]]
## Test-Writer Notes (retry)

**Test file:** `tests/test_cockpit_kanban_routes_1082.py`
**Class:** `TestFromAC_CockpitRoutes`
**Total:** 27 tests (18 original + 9 new)
**Lint:** ruff clean

### Retry context
Architecture Review (final section of task body) refined the AC with 6 stronger proof requirements for before-engine rejection, exact OCC call_args, and multi-route error-path coverage. This retry adds 9 new tests for those gaps. The builder's previous implementation already satisfies all refined AC behaviors; all 27 tests pass.

### New tests (9) by category

| Category | Count | Tests |
|----------|-------|-------|
| AC-NEW-24 before-engine proof | 1 | test_edit_status_field_rejected_before_cockpit_view |
| OCC exact call_args | 3 | test_edit/move/release_passes_exact_expected_updated_to_cockpit_view |
| ERR_STALE → 409 (move, release) | 2 | test_move/release_stale_token_from_cockpit_view_returns_409 |
| ERR_NOT_FOUND → 404 (move, release) | 2 | test_move/release_not_found_from_cockpit_view_returns_404 |
| ValidationError → 422 (move) | 1 | test_move_validation_error_from_cockpit_view_returns_422 |

### Refined AC coverage

| Refined AC | Test |
|-----------|------|
| AC-NEW-24: view NOT called when status in body | test_edit_status_field_rejected_before_cockpit_view |
| OCC exact expected_updated for edit | test_edit_passes_exact_expected_updated_to_cockpit_view |
| OCC exact expected_updated for move | test_move_passes_exact_expected_updated_to_cockpit_view |
| OCC exact expected_updated for release | test_release_passes_exact_expected_updated_to_cockpit_view |
| ERR_STALE → 409 for move | test_move_stale_token_from_cockpit_view_returns_409 |
| ERR_STALE → 409 for release | test_release_stale_token_from_cockpit_view_returns_409 |
| ERR_NOT_FOUND → 404 for move | test_move_not_found_from_cockpit_view_returns_404 |
| ERR_NOT_FOUND → 404 for release | test_release_not_found_from_cockpit_view_returns_404 |
| ValidationError → 422 for move | test_move_validation_error_from_cockpit_view_returns_422 |

### Process note
All 27 tests pass because the builder's prior implementation correctly handles all refined AC behaviors. New tests provide the explicit proof assertions the reviewer and architect required. Move delegation tests use `view_mock.engine = engine` to bypass local pre-delegation OCC/transition checks. Release delegation tests rely on `view_mock.show_task.return_value.claimed = True` to pass the claimed guard. Builder phase is a verification pass-through.
[[2026-04-27]]
## Builder Notes
- Implementation: no additional source changes in this retry cycle; prior builder implementation already satisfies refined functional AC assertions.
- Verification (quality-runner, scoped): 27 passed, 0 failed in tests/test_cockpit_kanban_routes_1082.py; ruff clean on route modules and task-owned test file.
- Coverage: owlbear_cockpit.routes.mutation = 71%, owlbear_cockpit.routes.read = 78%.
- Gate result: builder completion gate not met because required coverage >= 90% on touched modules was not achieved.
- Routing reason: rejecting to test-writer for additional task-owned TestFromAC coverage to raise route-module coverage to >= 90% without changing functional contract.

### Test-writer follow-up needed
- Add targeted TestFromAC cases for currently uncovered branches in route handlers (especially mutation route error/guard branches and read route non-happy paths) until both modules reach >= 90% in scoped quality-runner output for this task.
- Keep existing refined AC assertions intact; this is a coverage-completeness delta, not a contract change.

### Reflection
- Retry cycle was pass-through on functionality: strengthened tests now prove refined AC behavior.
- Remaining blocker is quantitative coverage threshold, not failing behavior.
- Fastest path is expanding task-owned tests for uncovered route branches rather than modifying already-correct source paths.
[[2026-04-27]]
## Test-Writer Notes (coverage retry)

**Test file:** `tests/test_cockpit_kanban_routes_1082.py`
**Classes:** `TestFromAC_CockpitRoutes` (27 tests), `TestFromAC_RouteGuardBranches` (21 tests)
**Total:** 48 tests — all PASS (coverage retry; implementation was already complete)
**Lint:** ruff clean

### Coverage achieved (scoped pytest run)
| Module | Before | After |
|--------|--------|-------|
| `owlbear_cockpit.routes.mutation` | 71% | **98%** |
| `owlbear_cockpit.routes.read` | 78% | **95%** |

### New tests added (21) by category
| Category | Tests |
|----------|-------|
| error (move pre-delegation guards) | not-found/stale-token/invalid-transition → 404/409/422 |
| error (edit guards) | no-editable-fields → 422, tags-path show_task NotFoundError → 404 |
| error (release guards) | unclaimed → 409, show_task NotFoundError → 404 |
| happy (_build_edit_kwargs branches) | priority, body, parent fields |
| happy (_apply_list_diff) | tags add path (195-200), tags remove path (201) |
| happy (_apply_block_kwargs + tag ops) | block_reason=non-None adds block:user (174-175, 217-219, 224-226, 231), block_reason=null removes block:user (211-215, 231-235) |
| happy (read routes) | get_board, get_task 404, list_tasks cache-hit, cache-hit+filter, list_sessions filter=all, list_activity with limit |

### Remaining uncovered lines (2)
- `mutation.py` lines 71, 75: `_task_to_single` else-branch for non-Pydantic task objects — not reachable via real view returns; not worth a fragile low-value mock test.
[[2026-04-27]]
## Builder Notes
- Implementation: no additional source edits in this pass; existing route implementation in `serve/cockpit/src/owlbear_cockpit/routes/read.py` and `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` already satisfies refined AC behavior validated by task-owned tests.
- Verification (fresh quality-runner scoped run): `tests/test_cockpit_kanban_routes_1082.py` = 48 passed, 0 failed, 0 skipped.
- Lint (fresh quality-runner scoped run): ruff clean for `serve/cockpit/src/owlbear_cockpit/routes/read.py`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, and `tests/test_cockpit_kanban_routes_1082.py`.
- Coverage evidence: latest `## Test-Writer Notes (coverage retry)` in this task body reports `owlbear_cockpit.routes.mutation` 98% and `owlbear_cockpit.routes.read` 95% for task-scoped run; quality-runner currently cannot emit these module percentages due coverage source package configuration, but functional/lint verification is green.
- Evidence summary: builder gate conditions for this task are satisfied with passing task-owned suite, clean lint, and documented >=90% route-module coverage.

### Reflection
- Main friction was coverage-reporting mismatch between task-scoped direct run output and quality-runner module extraction.
- No new code changes were needed after test-writer’s coverage retry; this pass was verification-focused.
- Keeping verification strictly scoped to task-owned tests avoided reintroducing unrelated durable-suite drift.
- Residual risk is tooling-level visibility (coverage reporting config), not route behavior correctness.
[[2026-04-27]]
## Review Evidence
### Test Results
- Quality-runner scoped run on task-owned plus overlapping durable cockpit suites: 141 passed, 0 failed, 0 skipped.
- tests/test_cockpit_kanban_routes_1082.py: 48 passed.
- tests/test_cockpit_routes_1144.py: 9 passed.
- tests/test_cockpit_read_api.py: 53 passed.
- tests/test_cockpit_mutation_api.py: 31 passed.

### Lint
- Ruff clean on serve/cockpit/src/owlbear_cockpit/routes/read.py, serve/cockpit/src/owlbear_cockpit/routes/mutation.py, tests/test_cockpit_kanban_routes_1082.py, tests/test_cockpit_routes_1144.py, tests/test_cockpit_read_api.py, and tests/test_cockpit_mutation_api.py.

### Coverage
- owlbear_cockpit.routes.read: 100%
- owlbear_cockpit.routes.mutation: 98%
- Combined scoped coverage: 98.5%
- Remaining uncovered mutation lines: 71, 75, 233

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If Violated? | Verdict |
|---------|-------------|-------------------------|---------|
| Edit rejects status in body before CockpitView | tests/test_cockpit_kanban_routes_1082.py:502 | Yes. Asserts HTTP 422, FastAPI validation shape, and no CockpitView edit call. | COVERED |
| edit, move, and release forward exact expected_updated | tests/test_cockpit_kanban_routes_1082.py:531, 554, 578 | Yes. Asserts exact kwarg equality for all three delegated routes. | COVERED |
| edit, move, and release stale conflicts map to 409 | tests/test_cockpit_kanban_routes_1082.py:410, 606, 628 | Yes. | COVERED |
| edit, move, and release not found cases map to 404 | tests/test_cockpit_kanban_routes_1082.py:432, 654, 676 | Yes. | COVERED |
| edit and move validation failures map to 422 | tests/test_cockpit_kanban_routes_1082.py:454, 702 | Yes. | COVERED |
| edit config failure maps to 500 | tests/test_cockpit_kanban_routes_1082.py:476 | Yes. | COVERED |
| GET /api/tasks returns cockpit list envelope with tasks and guidance, with mtime preserved | tests/test_cockpit_kanban_routes_1082.py:182, 195 and tests/test_cockpit_routes_1144.py:139, 163 | Yes for the refined AC. Guidance and mtime regressions would fail. | COVERED |
| GET /api/tasks/{id} returns ShowTaskResponse envelope | tests/test_cockpit_kanban_routes_1082.py:209, 222 and tests/test_cockpit_read_api.py:601, 610 | Yes. Guidance, missing_sections, and claimed-field contract are exercised. | COVERED |
| GET /api/activity returns filtered activity events | tests/test_cockpit_kanban_routes_1082.py:239, 250, 263 | Yes. | COVERED |
| GET /api/sessions returns a flat SessionRecord list | tests/test_cockpit_kanban_routes_1082.py:282, 296 and tests/test_cockpit_read_api.py:387 | Yes. | COVERED |
| POST /api/tasks/{id}/release returns SingleTaskResponse | tests/test_cockpit_kanban_routes_1082.py:346 | Yes for route envelope shape; exact OCC forwarding and error mapping are separately asserted above. | COVERED |
| POST /api/tasks/sweep returns a list of released task ids | tests/test_cockpit_kanban_routes_1082.py:317, 328 | Partially. The route contract is proved as a list[int] pass-through, but not with exact-id equality. | LAX |
| RED phase evidence exists | Task body Test-Writer Notes sections | Historical only, but adequately documented in the task body. | COVERED |
| No durable cockpit regressions remain after dependency reconciliation | Quality-runner: 141 passed, 0 failed across task-owned and overlapping durable suites | Yes. Durable overlap is currently green. | COVERED |

#### Security Review
- No issues found. Request bodies use extra=forbid, and the changed handlers only delegate to in-process engine or view methods.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-owned TestFromAC suite in tests/test_cockpit_kanban_routes_1082.py | Added stronger proofs for before-engine rejection, exact OCC forwarding, delegated error mapping, guard branches, and route coverage | STRENGTHENED |
| Durable cockpit overlap suites | Mtime injection and block:user lifecycle assertions remain present and passing | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Refined AC proofs are exact for no-call validation and OCC forwarding. Sweep remains wire-shape oriented. |
| Negative and error-path coverage | STRONG | edit, move, and release stale and not-found branches, move validation, guard branches, sessions filter, and activity limit paths are exercised. |
| Manual mutation reasoning | ADEQUATE | Removing expected_updated forwarding or delegated error mapping would fail. Replacing sweep with the wrong integer ids would not. |
| Test independence | STRONG | Fixture isolation and dependency override cleanup keep state local per test. |
| Descriptive names | STRONG | Test names remain explicit and behavior-oriented. |

#### Data Safety
- No issues found. OCC forwarding and stale-write rejection are implemented and exercised across edit, move, and release.

#### Implementation-Aware Gaps
- No blocking untested changed-code path remains.
- Non-blocking residuals:
  - list_tasks cache-hit normalization for guidance=[] and missing_ids=None is not asserted directly.
  - sweep route proof is limited to list[int] wire shape; exact released-id semantics rely on lower-layer engine and view suites.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- The latest Architecture Review refinement is the binding gate for this loop. The earlier failed review is stale; the current implementation satisfies the refined scope.
- Overlapping durable cockpit suites now agree with the route behavior. The prior cross-suite contract drift is no longer present in live execution.
- Two test names are stale but non-blocking: tests/test_cockpit_kanban_routes_1082.py:195 now asserts mtime presence despite the name, and tests/test_cockpit_read_api.py:610 asserts claimed_by absence despite the name.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-NEW-24 before-engine rejection | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:35-52 rejects extra fields before edit_task runs; tests/test_cockpit_kanban_routes_1082.py:502 asserts 422 and no CockpitView call | test_edit_status_field_rejected_before_cockpit_view | PASS |
| Exact expected_updated forwarding | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:123, 255, 292 forward req.updated; tests/test_cockpit_kanban_routes_1082.py:531, 554, 578 assert exact kwarg equality | exact expected_updated trio | PASS |
| Stale maps to 409 across delegated routes | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:134, 264, 297; tests/test_cockpit_kanban_routes_1082.py:410, 606, 628 | stale mapping trio | PASS |
| Not found maps to 404 across delegated routes | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:128, 260, 293; tests/test_cockpit_kanban_routes_1082.py:432, 654, 676 | not found mapping trio | PASS |
| ValidationError maps to 422 where applicable | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:132, 269; tests/test_cockpit_kanban_routes_1082.py:454, 702 | validation mapping tests | PASS |
| ConfigError maps to 500 on edit | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:271; tests/test_cockpit_kanban_routes_1082.py:476 | edit config error test | PASS |
| GET /api/tasks list envelope | serve/cockpit/src/owlbear_cockpit/routes/read.py:69-107; tests/test_cockpit_kanban_routes_1082.py:182, 195; tests/test_cockpit_routes_1144.py:139, 163 | list envelope tests | PASS |
| GET /api/tasks/{id} show envelope | serve/cockpit/src/owlbear_cockpit/routes/read.py:113-120; tests/test_cockpit_kanban_routes_1082.py:209, 222 | show envelope tests | PASS |
| GET /api/activity filtered list | serve/cockpit/src/owlbear_cockpit/routes/read.py:124-141; tests/test_cockpit_kanban_routes_1082.py:239, 250, 263 | activity tests | PASS |
| GET /api/sessions flat SessionRecord list | serve/cockpit/src/owlbear_cockpit/routes/read.py:145-147; tests/test_cockpit_kanban_routes_1082.py:282, 296; tests/test_cockpit_read_api.py:387 | sessions tests | PASS |
| POST /api/tasks/{id}/release SingleTaskResponse | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:277-299; tests/test_cockpit_kanban_routes_1082.py:346 | release envelope test | PASS |
| POST /api/tasks/sweep list of released ids | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:307-309; tests/test_cockpit_kanban_routes_1082.py:317, 328 | sweep endpoint tests | PASS |
| RED evidence exists in task history | Task body Test-Writer Notes | historical evidence | PASS |
| No durable cockpit regressions | Quality-runner 141 passed, 0 failed across overlapping cockpit suites | scoped durable rerun | PASS |

### Deductions
- 0.03: sweep proof at the route layer is wire-shape heavy rather than exact-id equality.
- 0.02: list_tasks cache-hit normalization fields are not directly asserted.

### Verdict
- PASS. Confidence: .95.
- Routing: docs.

### Action
- Advance to docs.
- Optional future cleanup: rename the two stale test names and add one direct assertion for cache-hit normalization or exact sweep ids if a tighter proof bar is desired.

### Reflection
- Fresh quality-runner evidence superseded the stale failed review and showed the adjacent durable cockpit suites are now green.
- The strongest proof upgrades are the no-call validation test, exact OCC forwarding assertions, and the delegated error-mapping matrix.
- Remaining gaps are proof-tightness nits, not failing behavior or live regressions.
[[2026-04-27]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md`: removed `sweep()` from Excluded methods, added `POST /tasks/sweep` to mutation routes table, added `list_activity(**kwargs)` to read routes table. |
| 2 | Module docstrings | Yes | Updated | `mutation.py` module docstring updated to include `sweep` in the route list. `read.py` function docstrings were already accurate. |
| 3 | External attribution | No | N/A | Task used no external patterns. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc was produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` `describes: serve/cockpit/src/**` matched changed route files. Footer updated from `6f1509ce` to `984259bf` (same date 2026-04-27). |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/src/owlbear_cockpit/routes/read.py` | IN (docstrings) | Verified accurate — no changes needed |
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | IN (docstrings) | Module docstring updated to include sweep |
| `tests/test_cockpit_kanban_routes_1082.py` | OUT | N/A |
| `serve/cockpit/README.md` | IN | Updated (activity endpoint, sweep route, excluded-methods row removed) |
| `share/diagrams/cockpit.excalidraw` | IN | Footer updated |

### Files Updated
- `serve/cockpit/README.md`
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` (docstring only)
- `share/diagrams/cockpit.excalidraw` (footer only)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1082-*` files found)
[[2026-04-27]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-NEW-24: status rejected before engine | test_edit_status_field_rejected_before_cockpit_view:L502 asserts 422 + view_mock.edit_task.assert_not_called() | PASS |
| OCC exact expected_updated forwarding | test_edit/move/release_passes_exact_expected_updated:L531,554,578 assert kwarg equality | PASS |
| ERR_STALE to 409 (edit, move, release) | tests at L410, L606, L628 assert 409 for all 3 delegated routes | PASS |
| ERR_NOT_FOUND to 404 (edit, move, release) | tests at L432, L654, L676 assert 404 for all 3 delegated routes | PASS |
| ValidationError to 422 (edit, move) | tests at L454, L702 | PASS |
| ConfigError to 500 (edit) | test at L476 | PASS |
| GET /api/tasks ListTasksResponse | tests at L182, L195 plus durable tests/test_cockpit_routes_1144.py:L139,L163 | PASS |
| GET /api/tasks/{id} ShowTaskResponse | tests at L209, L222 | PASS |
| GET /api/activity filtered events | tests at L239, L250, L263 | PASS |
| GET /api/sessions flat SessionRecord list | tests at L282, L296 plus durable tests/test_cockpit_read_api.py:L387 | PASS |
| POST /release SingleTaskResponse | test at L346 | PASS |
| POST /sweep list of released IDs | tests at L317, L328 | PASS |
| RED phase evidence | Task body Test-Writer Notes: 18 tests failing before builder | PASS |
| No durable cockpit regressions | Reviewer ran 141 passed, 0 failed across overlapping suites | PASS |

### Test Results
- Full suite (quality-runner mode=full): 2714 passed, 117 failed, 4 skipped
- 0 failures in cockpit route scope; 3 cockpit failures in unrelated test_cockpit_react_compiler_1015.py (pre-existing)
- 114 remaining failures in kanban engine, MCP, knowledge packages (pre-existing, unrelated)
- Task-owned suite: 48 passed, 0 failed
- ruff: clean on all task-scoped files; 8 violations in unrelated packages

### Architect Quality: 4/5
Original AC was adequate but needed one refinement cycle after the first review exposed proof gaps (before-engine semantics, OCC call_args, multi-route error coverage). The refined AC was specific, complete, and drove successful completion. Dependency on 1144 for durable suite reconciliation was correctly identified. Minor gap: original AC underspecified proof requirements, costing one full review/retry loop.

### Deduction Breakdown
- AC lines without evidence: 0 (all 14 PASS)
- Lint violations in scope: 0
- AC quality: 4/5 (above threshold)
- Reviewer evidence section: present, detailed, PASS at .95
- Full-suite task-scope failures: 0
- Sweep proof is wire-shape only (list[int] not exact IDs): -.01

### Confidence: .99
### Action: archive

### Upstream Commits Verified
| Commit | Type | Scope |
|--------|------|-------|
| 7064d054 | docs | README, diagram, docstring |
| 7b1ce085 | test | coverage expansion to >=90% |
| 6f1509ce | test | proof test strengthening |
| e67468fa | feat | route alignment with CockpitView |

All 4 commits reference #1082. No uncommitted task deliverables.