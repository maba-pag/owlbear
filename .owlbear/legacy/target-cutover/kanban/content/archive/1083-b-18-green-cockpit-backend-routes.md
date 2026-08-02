---
id: 1083
title: 'B-18: GREEN — cockpit backend routes'
status: archived
priority: medium
created: 2026-04-21 10:50:53.767229+00:00
updated: 2026-04-28T01:04:22.539877+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- scope:cockpit
- tdd:green
parent: 1044
depends_on:
- 1082
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §5
Module: `serve/cockpit/src/owlbear_cockpit/routes/kanban.py`

Implement FastAPI cockpit backend routes wrapping CockpitView. Error mapping: KanbanError subclass → HTTP status (NotFoundError → 404, ValidationError → 422, ConcurrencyError → 409, ConfigError → 500). Request schemas enforce AC-NEW-24 (no `status` field on edit body).

Routes rewire existing cockpit backend from legacy engine to CockpitView facade. Existing routes (/api/board, /api/tasks, /api/tasks/{id}, /api/sessions) are updated; new routes added for admin operations.

## Acceptance Criteria

- [ ] All RED tests from B-17 (#1082) pass
- [ ] AC-NEW-24: Edit request Pydantic schema excludes `status` field → 422 on inclusion
- [ ] Error mapping: NotFoundError → 404, ValidationError → 422, ConcurrencyError → 409
- [ ] OCC: `expected_updated` passed from request body to CockpitView
- [ ] Read routes: GET /api/tasks, GET /api/tasks/{id} return envelope responses
- [ ] Activity routes: GET /api/activity (filtered), GET /api/sessions (SessionRecord)
- [ ] Admin routes: POST .../release, POST .../sweep, POST .../scan, POST .../repair, POST .../compact-activity
- [ ] DI pattern maintained: `get_engine` override in tests per existing cockpit convention
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_kanban_routes_1083.py
- Classes: TestFromAC_AdminRoutes
- Tests per category: happy 13, edge 3, boundary 5 (overlap; 3 boundary tests are also DI proofs)
- Total: 18 tests, all FAIL (AssertionError: assert 405 == 200 — POST not registered; path partially matches existing GET /tasks/{task_id})
- ruff: clean

AC coverage:
| AC line | Tests |
|---------|-------|
| POST /api/tasks/scan → CockpitView.scan_corruption() | test_scan_endpoint_returns_200, test_scan_response_is_list, test_scan_clean_board_returns_empty_list, test_scan_delegates_to_cockpit_view_scan_corruption, test_scan_returns_list_of_corruption_items_when_corruption_detected |
| POST /api/tasks/repair → CockpitView.repair_storage() | test_repair_endpoint_returns_200, test_repair_response_is_list, test_repair_clean_board_returns_empty_list, test_repair_delegates_to_cockpit_view_repair_storage, test_repair_response_items_have_repair_outcome_fields |
| POST /api/tasks/compact-activity → CockpitView.compact_activity() | test_compact_activity_endpoint_returns_200, test_compact_activity_response_has_required_fields, test_compact_activity_result_fields_are_non_negative_integers, test_compact_activity_delegates_to_cockpit_view_compact_activity, test_compact_activity_response_values_match_view_result |
| DI pattern maintained: get_engine override | test_di_engine_override_reaches_scan_route, test_di_engine_override_reaches_repair_route, test_di_engine_override_reaches_compact_activity_route |

Note: AC items 1–6 (1082 RED tests, error mapping, OCC, read routes, activity routes) are already covered by tests/test_cockpit_kanban_routes_1082.py (48 tests, all GREEN).
[[2026-04-27]]
## Builder Notes
- Implementation: added admin maintenance POST routes in serve/cockpit/src/owlbear_cockpit/routes/mutation.py for /api/tasks/scan, /api/tasks/repair, and /api/tasks/compact-activity.
- Tests (RED verification): 18/18 `TestFromAC_AdminRoutes` failed before changes (all 405 vs expected 200).
- Tests (GREEN verification): 18/18 `TestFromAC_AdminRoutes` passed after changes; additional cockpit mutation route suites passed (161 tests total in broader scoped run).
- Coverage: 34% on touched module (`owlbear_cockpit.routes.mutation`) in task-scoped run; broader run coverage selector reported only kanban modules (coverage selector mismatch noted by quality-runner).
- ruff: clean.
- Evidence summary: endpoints now resolve exact POST paths so they no longer fall through to `/api/tasks/{task_id}` and return 405; route delegation verified by DI/mocking tests for `scan_corruption`, `repair_storage`, and `compact_activity`.
- Commit: fa2ef536 (`feat: add cockpit admin maintenance routes (#1083, builder)`).
- Reflections:
  - Problem faced: task brief pointed to stale module path (`routes/kanban.py`) while actual cockpit routes are split across `routes/read.py` and `routes/mutation.py`.
  - Workaround: resolved canonical route location first, then applied minimal diff to mutation router only.
  - Pattern discovered: missing explicit method/path registration can manifest as 405 via dynamic `/{task_id}` route shadowing, not 404.
  - Time sink: one coverage run used a selector that did not include cockpit modules; validated behavior with an additional scoped run.
  - Quality gap: module coverage for touched file remains below target in this task-scoped suite despite all AC tests and route-contract tests passing.
[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner scoped run: 161 passed, 0 failed, 0 skipped
- Included task suites: tests/test_cockpit_kanban_routes_1082.py and tests/test_cockpit_kanban_routes_1083.py, plus broader cockpit mutation route suites for regression context

### Lint
- quality-runner ruff result: clean, 0 violations

### Coverage
- quality-runner could not report numeric coverage for owlbear_cockpit.routes.mutation or owlbear_cockpit.routes.read
- Cause: pyproject.toml line 154 begins source_pkgs without owlbear_cockpit, so cockpit modules are excluded from coverage collection
- This is an evidence limitation, not the primary reject reason

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Were Violated? | Verdict |
|---------|-------------|----------------------------------|---------|
| All RED tests from B-17 pass | quality-runner run including tests/test_cockpit_kanban_routes_1082.py | Yes, suite executed green | COVERED |
| AC-NEW-24 edit schema forbids status field | tests/test_cockpit_kanban_routes_1082.py line 502 plus serve/cockpit/src/owlbear_cockpit/routes/mutation.py line 42 | Yes, 422 plus view not called | COVERED |
| Error mapping for NotFoundError, ValidationError, ConcurrencyError | tests/test_cockpit_kanban_routes_1082.py error-mapping blocks plus serve/cockpit/src/owlbear_cockpit/routes/mutation.py lines 128, 132, 134, 260, 264, 269, 293, 297 | Yes | COVERED |
| OCC forwards expected_updated | tests/test_cockpit_kanban_routes_1082.py lines 531, 554, 578 plus serve/cockpit/src/owlbear_cockpit/routes/mutation.py lines 126, 257, 292 | Yes, exact kwarg equality asserted | COVERED |
| Read routes return envelope responses | tests/test_cockpit_kanban_routes_1082.py lines 182, 209, 222 | Yes | COVERED |
| Activity routes and sessions contract | tests/test_cockpit_kanban_routes_1082.py lines 239, 263, 282, 296 | No for filtered activity: a broken handler returning [] would still satisfy the task_id assertion because all() on empty list is true | LAX |
| Admin routes for release, sweep, scan, repair, compact-activity | tests/test_cockpit_kanban_routes_1082.py lines 317, 346 and tests/test_cockpit_kanban_routes_1083.py lines 157, 188, 257, 349, 368 plus serve/cockpit/src/owlbear_cockpit/routes/mutation.py lines 309, 315, 321, 327 | Partially. Happy-path delegation is proven, but repair response proof does not bind the full JSON contract | LAX |
| DI pattern maintained in tests | tests/test_cockpit_kanban_routes_1083.py lines 394, 418, 441 plus serve/cockpit/src/owlbear_cockpit/deps.py lines 20, 47 and serve/cockpit/src/owlbear_cockpit/main.py lines 25, 26 | No. These tests assert only 200 after overriding get_engine and do not verify any engine-specific side effect or response that would fail if the override path were broken | LAX |

#### Security Review
- No route-layer security issues found in serve/cockpit/src/owlbear_cockpit/routes/mutation.py
- Request bodies remain schema-validated with extra forbid on lines 29, 42, and 57

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_CockpitRoutes | No builder-side weakening evident in inspected task-owned suites | PRESERVED |
| TestFromAC_AdminRoutes | No builder-side weakening evident in inspected task-owned suites | PRESERVED |
- Note: direct SCM diff was not available in the current toolset, so this assessment is based on inspected live suites plus the builder-scoped file under review

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | tests/test_cockpit_kanban_routes_1083.py line 272 checks only part of the RepairOutcome wire contract and does not assert detail; tests/test_cockpit_kanban_routes_1082.py line 263 can pass vacuously on an empty filtered activity result |
| Negative and error-path coverage | WEAK | tests/test_cockpit_kanban_routes_1083.py adds no exception-injection coverage for scan, repair, or compact-activity even though the route surface is newly introduced |
| Manual mutation reasoning | WEAK | tests/test_cockpit_kanban_routes_1083.py lines 394, 418, 441 would still pass if the routes ignored the overridden engine and returned 200 from some other path |
| Test independence | ADEQUATE | tmp_path fixtures isolate boards and dependency_overrides are cleared in fixture teardown |
| Naming clarity | ADEQUATE | names are mostly descriptive; one older 1082 test name is misleading but non-blocking |

#### Data Safety
- No route-layer data safety defect found
- OCC guards remain intact in serve/cockpit/src/owlbear_cockpit/routes/mutation.py lines 109 through 126, 252 through 257, and 286 through 292

#### Implementation-Aware Gaps
- The new admin routes are thin delegates at serve/cockpit/src/owlbear_cockpit/routes/mutation.py lines 312 through 327. The task-owned suite proves happy-path delegation, but does not prove the DI override path or any admin-route failure behavior.
- The repair route advertises response_model=list[RepairOutcome] at serve/cockpit/src/owlbear_cockpit/routes/mutation.py line 318, but the task-owned response-shape proof at tests/test_cockpit_kanban_routes_1083.py line 272 does not assert the full item contract described in the test header.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-17 pass | quality-runner executed the 1082 suite inside a 161-test scoped run with 0 failures | PASS |
| AC-NEW-24 status field rejected | mutation.py line 42 and tests/test_cockpit_kanban_routes_1082.py line 502 | PASS |
| Error mapping 404, 422, 409 | mutation.py exception handlers at lines 128, 132, 134, 260, 264, 269, 293, 297; mapped tests green in 1082 suite | PASS |
| OCC forwards expected_updated | mutation.py lines 126, 257, 292; exact-forwarding tests at lines 531, 554, 578 in 1082 suite | PASS |
| Read routes return envelopes | 1082 tests at lines 182, 209, 222 | PASS |
| Activity routes and sessions contract | sessions proof is direct at lines 282 and 296, but filtered activity proof at line 263 is lax | FAIL |
| Admin routes exist and delegate | mutation.py lines 312, 318, 324 with happy-path proofs in 1083 suite | PASS |
| DI pattern maintained | deps.py lines 20 and 47 plus main.py lines 25 and 26 establish the design, but 1083 DI tests at lines 394, 418, 441 do not prove it under failure | FAIL |

### Deductions
- 0.10 deducted: numeric cockpit coverage unavailable because workspace coverage config excludes owlbear_cockpit
- 0.15 deducted: admin DI proof is lax and does not fail on a broken override path
- 0.08 deducted: repair response-wire proof is incomplete
- 0.07 deducted: filtered activity proof is vacuous on an empty result set

### Verdict
- FAIL
- Confidence: 0.58
- Primary reason: task-owned test quality is below gate. The implementation appears plausible and the live scoped suite is green, but the acceptance proof is not strong enough to certify the DI contract or the full admin-route wire contract.

### Action
- Reject to backlog for upstream test-quality repair. The next cycle should strengthen the TestFromAC coverage before this implementation is re-reviewed.
- Minimum fixes needed:
  1. Replace the 1083 DI tests with assertions that can only pass when the overridden engine actually drives the route outcome.
  2. Add non-happy-path proofs for the new admin routes, or explicitly constrain the contract if only framework-default failures are intended.
  3. Tighten the repair response assertion to bind the full declared wire shape, including detail.
  4. Tighten the filtered activity proof so an empty list cannot satisfy the filter contract by vacuous truth.
[[2026-04-27]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Admin route registration only |
| Interface clarity | PASS | Routes delegate to CockpitView; request/response models explicit |
| Dependency correctness | PASS | Depends on 1082 (archived/done); engine and CockpitView APIs stable |
| Module layering | PASS | routes/mutation.py → deps.py → engine.py; no upward imports |
| TDD compliance | PASS | RED tests written in 1082+1083 before GREEN implementation |
| KISS/YAGNI | PASS | Thin delegate routes, no unnecessary abstractions |
| Premise challenge | PASS | Admin routes are specified in Brief B §5; not duplicating existing capability |
| Pattern consistency | PASS | Follows existing mutation router pattern with _View dependency |
| Security surface | PASS | No user input beyond route path; admin ops are board-internal |
| Single domain | PASS | Cockpit route layer only |

### Context
Task returning from reviewer reject (confidence 0.58). Implementation is complete and green (commit fa2ef536). The reject was for test-quality gaps, not implementation defects. The next cycle needs test-writer fixes, not re-implementation.

### Reviewer Fix Requirements (binding for next cycle)
1. **DI tests must assert engine-specific observables.** The 3 DI tests (lines 394, 418, 441) only assert status 200 after overriding get_engine. The existing cockpit convention uses payload/call assertions. Fix: each DI test must verify the response reflects data from the overridden engine's board (e.g., scan results from the alt board, or mock-verify the view was constructed from the overridden engine).
2. **Repair response must assert all 5 RepairOutcome fields.** test_repair_response_items_have_repair_outcome_fields (line 272) asserts task_id, file_path, code, action — missing `detail`. Add `assert "detail" in item`.
3. **Scan response must assert item field shape.** test_scan_returns_list_of_corruption_items_when_corruption_detected (line 214) only checks `len(data) == 1`. Add assertions for item keys (at minimum: code, detail, file_path).
4. **Filtered activity (1082 suite) is out of scope.** The vacuous empty-list proof at test_cockpit_kanban_routes_1082.py line 263 is a pre-existing 1082 test design issue. Do not modify the 1082 suite in this task.

### Challenge Results
- Challenger: reconsider (confidence 0.47)
- Key challenges: scope narrowing concern, adapter contract drift, scan wire-shape blind spot
- Architect response: rebutted. AC lines preserved unchanged; fix requirements added as guidance, not AC narrowing. Adapter error-body contract applies to CRUD ops (already mapped), not admin thin delegates. Scan wire-shape gap accepted and added to fix requirements.

### Verdict: REFINE → APPROVE
### Action: AC preserved. Reviewer fix requirements appended as binding guidance. Advancing to todo for test-writer cycle.
[[2026-04-27]]
Architecture review complete. AC preserved unchanged; 4 binding fix requirements from reviewer reject appended as builder guidance. Implementation is green (fa2ef536); test-quality gaps are the sole blocker. Next cycle: test-writer strengthens DI proofs, repair/scan wire-shape assertions.
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_kanban_routes_1083.py
- Classes: TestFromAC_AdminRoutes (5 new tests added to existing class)
- Tests per category: 3 edge/boundary (FAIL), 2 happy (PASS — regression guards)
- Total new: 5 tests | 18 original: all PASS | Grand total: 23 tests
- ruff: clean

### Retry summary
Retry cycle — reviewer FAILed for lax test quality on DI proofs, scan item shape, and repair detail field. Added 5 new tests:

| New test | Category | Status | Reason |
|----------|----------|--------|--------|
| test_scan_real_corrupt_board_returns_nonempty_list | edge | FAIL | ResponseValidationError: scan route's `response_model=list[dict[str, Any]]` cannot serialize CorruptionError objects returned by engine |
| test_scan_real_corrupt_board_item_has_code_detail_file_path | boundary | FAIL | Same — proves route must serialize CorruptionError to dict with code/detail/file_path |
| test_di_scan_observes_overridden_board_not_default | boundary | FAIL | Same — proves DI override routes to correct board AND serialization works |
| test_scan_mock_item_includes_all_required_fields | happy | PASS | Regression guard: mock returns full dict; asserts code/detail/file_path values (fix req #3) |
| test_repair_response_item_includes_detail_field | happy | PASS | Regression guard: asserts detail field value in repair response (fix req #2) |

### Root cause exposed
`engine.scan_corruption()` returns `CorruptionError` objects (Python exceptions, not Pydantic models). The route's `response_model=list[dict[str, Any]]` triggers FastAPI/Pydantic v2 ResponseValidationError: "Input should be a valid dictionary". Builder must convert CorruptionError instances to dicts before returning from the route.

### AC coverage (existing + new)
| AC line | Tests |
|---------|-------|
| scan delegates to CockpitView.scan_corruption() | (existing 5) + test_scan_mock_item_includes_all_required_fields |
| scan returns serializable items with code/detail/file_path | test_scan_real_corrupt_board_item_has_code_detail_file_path, test_scan_mock_item_includes_all_required_fields |
| DI get_engine override reaches scan route and drives data | test_di_scan_observes_overridden_board_not_default |
| repair response includes all RepairOutcome fields incl. detail | test_repair_response_item_includes_detail_field |

### Commit
7718f942 — test: strengthen admin route wire-shape and DI proofs (#1083, test-writer)
[[2026-04-27]]
## Builder Notes
- Implementation: normalized `/api/tasks/scan` response items in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` so `CorruptionError` objects are serialized as dictionaries with `code`, `detail`, and `file_path`.
- Tests (RED verification): `tests/test_cockpit_kanban_routes_1083.py` showed 3 failing `TestFromAC_AdminRoutes` tests before fix (scan serialization failures).
- Tests (GREEN verification): 23/23 passed in `tests/test_cockpit_kanban_routes_1083.py`; 71/71 passed across `tests/test_cockpit_kanban_routes_1082.py` + `tests/test_cockpit_kanban_routes_1083.py`.
- Coverage: 36% for `owlbear_cockpit.routes.mutation` in scoped run (target module report).
- ruff: clean in scoped runs.
- Evidence summary: scan route now handles both dict and object results from `CockpitView.scan_corruption()`, preventing FastAPI response-model validation errors and preserving the expected wire shape.
- Commit: c06b12e2 (`fix: serialize scan corruption response items (#1083, builder)`).
- Reflections:
  - Problem faced: route response model expected dictionaries while engine returned `CorruptionError` objects for real corruption cases.
  - Workaround applied: added a minimal route-level serializer helper instead of changing engine contracts.
  - Pattern discovered: object-vs-dict response shape mismatches can hide until non-mocked integration tests exercise real engine outputs.
  - Time sink: none beyond scoped re-verification.
  - Quality gap: module coverage for route layer remains below 90% in this isolated task scope.

[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner scoped run: 71 passed, 0 failed, 0 skipped across `tests/test_cockpit_kanban_routes_1082.py` and `tests/test_cockpit_kanban_routes_1083.py`

### Lint
- quality-runner ruff result: clean, 0 violations

### Coverage
- `owlbear_cockpit.routes.mutation`: 97% coverage
- Missing lines reported by quality-runner: 71, 75, 105-106, 256
- Previous coverage-config limitation is resolved for this review pass

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Were Violated? | Verdict |
|---------|-------------|----------------------------------|---------|
| All RED tests from B-17 (#1082) pass | quality-runner execution of the 1082 and 1083 suites | Yes | COVERED |
| AC-NEW-24 edit schema excludes `status` field | `tests/test_cockpit_kanban_routes_1082.py:502` and `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:35` | Yes | COVERED |
| Error mapping for NotFoundError, ValidationError, and ConcurrencyError | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:123`, `:261`, `:300` with the 1082 error-mapping tests | Yes for the implemented delegated paths exercised by the suite | COVERED |
| OCC forwards `expected_updated` | `tests/test_cockpit_kanban_routes_1082.py:531`, `:554`, `:578` | Yes, exact kwarg forwarding is asserted | COVERED |
| Read routes return envelope responses | `tests/test_cockpit_kanban_routes_1082.py:182`, `:209` | Yes | COVERED |
| Activity routes and sessions contract | `tests/test_cockpit_kanban_routes_1082.py:263`, `:296`; latest architecture refinement kept the older filtered-activity objection out of scope for this retry | Yes for the refined scope | COVERED |
| Admin routes exist for release, sweep, scan, repair, and compact-activity | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:330`, `:336`, `:342`, `:348`; tests at `tests/test_cockpit_kanban_routes_1082.py:317`, `:346`, and `tests/test_cockpit_kanban_routes_1083.py:153`, `:503`, `:559`, `:585` | Yes | COVERED |
| DI pattern maintained in tests | `serve/cockpit/src/owlbear_cockpit/deps.py:20`, `:47`; tests at `tests/test_cockpit_kanban_routes_1083.py:429`, `:452`, `:531` | No. The repair and compact DI tests only assert 200 after overriding `get_engine`, so a broken engine selection can still pass | LAX |

#### Security Review
- No route-layer security issues found in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
- Request bodies remain schema-constrained and the admin endpoints stay in-process view calls only

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_CockpitRoutes` | No weakening detected in the live 1082 suite | PRESERVED |
| `TestFromAC_AdminRoutes` | Retry added stronger scan and repair assertions at `tests/test_cockpit_kanban_routes_1083.py:503`, `:559`, and `:585` | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | `tests/test_cockpit_kanban_routes_1083.py:429` and `:452` only assert status 200 after overriding `get_engine`; they do not bind any engine-specific observable |
| Negative and error-path coverage | ADEQUATE | The admin routes now have clean-board, real-corrupt-board, delegation, and wire-shape proofs; no additional admin-route error mapping contract was added in this task |
| Manual mutation reasoning | WEAK | If `repair_storage()` or `compact_activity()` resolved the wrong engine but still returned 200, the DI tests at `tests/test_cockpit_kanban_routes_1083.py:429` and `:452` would remain green |
| Test independence | ADEQUATE | `tmp_path` boards and dependency override cleanup isolate state between tests |
| Naming clarity | ADEQUATE | The task-owned test names are descriptive and map cleanly to the AC |

#### Data Safety
- No route-layer data safety issue found in the changed implementation
- The scan serializer at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:94` safely normalizes engine scan items before returning them on the wire

#### Implementation-Aware Gaps
- The shared DI seam is `get_view(engine=Depends(get_engine))` at `serve/cockpit/src/owlbear_cockpit/deps.py:47`, and all admin routes consume that dependency at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:336`, `:342`, and `:348`
- Only scan now proves overridden-engine behavior. Repair and compact still lack a test that would fail if the route ignored the overridden engine, so AC line 8 remains under-proven
- This misses the latest architecture guidance, which required each DI test to assert an engine-specific observable on the overridden board

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- The prior review's coverage blocker is gone in this pass. `quality-runner` measured the touched route module directly and reported 97% coverage.
- I anchored this review to the latest architecture refinement in the task body and did not carry forward the older filtered-activity concern from the first review cycle.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-17 pass | quality-runner ran both task suites and reported 71 passed, 0 failed | PASS |
| AC-NEW-24 status field rejected | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:35` and `tests/test_cockpit_kanban_routes_1082.py:502` | PASS |
| Error mapping 404, 422, 409 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:123`, `:261`, `:300` plus the green 1082 error-mapping tests | PASS |
| OCC forwards `expected_updated` | `tests/test_cockpit_kanban_routes_1082.py:531`, `:554`, `:578` | PASS |
| Read routes return envelopes | `tests/test_cockpit_kanban_routes_1082.py:182`, `:209` | PASS |
| Activity routes and sessions contract | `tests/test_cockpit_kanban_routes_1082.py:263`, `:296` under the latest architecture refinement | PASS |
| Admin routes exist and return the expected shapes | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:330`, `:336`, `:342`, `:348` and the 1082/1083 admin-route suites | PASS |
| DI pattern maintained | `serve/cockpit/src/owlbear_cockpit/deps.py:20`, `:47` together with `tests/test_cockpit_kanban_routes_1083.py:429`, `:452`, `:531` | FAIL |

### Deductions
- 0.10 deducted: remaining DI proof gap on repair and compact routes. The retry fixed scan serialization and strengthened scan and repair wire-shape assertions, but it did not close the architect's binding requirement that each admin DI test fail on a broken override path.

### Verdict
- FAIL
- Confidence: 0.86
- Primary reason: implementation evidence is strong, but task-owned TestFromAC coverage for AC line 8 is still not strong enough to certify the DI contract on repair and compact-activity.

### Action
- Reject to `todo` because this is a test-gap failure, not an implementation defect.
- Required next-cycle fixes:
  1. Strengthen `test_di_engine_override_reaches_repair_route` so it asserts an outcome that can only come from the overridden engine or overridden board.
  2. Strengthen `test_di_engine_override_reaches_compact_activity_route` the same way, using exact compaction values or another engine-specific observable.
  3. Keep the current scan serializer and wire-shape assertions; those parts are now sufficient.
  4. Do not reopen the earlier filtered-activity complaint from the first review cycle unless the architecture guidance changes again.
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_kanban_routes_1083.py
- Classes: TestFromAC_AdminRoutes (2 new tests added to existing class)
- Tests per category: 2 boundary (regression guards, PASS)
- Total new: 2 tests | 23 previous: all PASS | Grand total: 25 tests
- ruff: clean

### Retry summary (cycle 3)
Reviewer FAILed cycle 2 for lax DI proofs on repair and compact-activity routes. Added 2 new boundary tests:

| New test | Category | Status | Reason |
|----------|----------|--------|--------|
| test_di_repair_observes_overridden_board_not_default | boundary | PASS | Regression guard: corrupt alt board → repair returns ≥1 outcome; proves route operated on overridden board. Would 500 or return [] if DI broken. |
| test_di_compact_observes_overridden_board_not_default | boundary | PASS | Regression guard: spy wrapper on `owlbear_cockpit.deps.CockpitView` captures engine arg; asserts `captured_engines[-1] is alt_engine`. Would fail assertion if DI delivers wrong engine. |

### Design rationale
Both tests PASS because the implementation is correct and the DI chain is intact. This is a regression-guard cycle — the implementation was already green; the test quality was the sole blocker. Comparable precedent: cycle 2 also added PASS regression guards (`test_scan_mock_item_includes_all_required_fields`, `test_repair_response_item_includes_detail_field`).

The compact DI test uses `mock.patch("owlbear_cockpit.deps.CockpitView", side_effect=spy_view)` to capture the engine passed through the DI chain without breaking the real route behavior. This is the "mock-verify the view was constructed from the overridden engine" approach recommended in the architect's binding guidance.

### AC coverage
| AC line | Tests |
|---------|-------|
| DI get_engine override drives repair route with observable outcome | test_di_repair_observes_overridden_board_not_default |
| DI get_engine override drives compact-activity route with observable outcome | test_di_compact_observes_overridden_board_not_default |

### Commit
974f6096 — test: strengthen repair/compact DI proofs with engine-observable assertions (#1083, test-writer)
[[2026-04-28]]
## Builder Notes
- Implementation: no source changes in this cycle; existing route implementation in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` already satisfies newly strengthened DI assertions.
- Tests (RED check on current snapshot): `tests/test_cockpit_kanban_routes_1083.py` ran 25/25 PASS, 0 FAIL (indicates implementation already covers the latest TestFromAC updates).
- Tests (GREEN verification): scoped route suites PASS (`tests/test_cockpit_kanban_routes_1082.py` + `tests/test_cockpit_kanban_routes_1083.py` evidence in prior cycle; current rerun confirms 25/25 on 1083 with no failures).
- ruff: clean on touched route + task suites.
- Coverage: current quality-runner scoped rerun for 1083-only reports 36% on `owlbear_cockpit.routes.mutation`; prior quality-runner review evidence on this same task body reports 97% for `owlbear_cockpit.routes.mutation` when evaluated with the paired 1082+1083 scope. Using the existing high-confidence review evidence for gate compliance.
- Evidence summary: test-writer’s strengthened DI tests (repair + compact engine-observable assertions) pass against current code; no additional builder intervention required.
- Commits: none in this cycle.
- Reflections:
  - Problem faced: quality-runner coverage in narrow 1083-only scope under-represents touched route paths.
  - Workaround applied: relied on existing task-local quality-runner evidence (97% module coverage) from the immediately preceding review cycle.
  - Pattern discovered: DI/wire-contract hardening can convert a builder retry into a verification-only pass when implementation already satisfies new assertions.
  - Time sink: repeated scoped coverage attempts with low-yield output.
  - Quality gap: none newly introduced by this builder cycle.
[[2026-04-28]]
## Review Evidence
### Test Results
- quality-runner scoped pytest on `tests/test_cockpit_kanban_routes_1082.py` and `tests/test_cockpit_kanban_routes_1083.py`: 73 passed, 0 failed, 0 skipped

### Lint
- quality-runner scoped ruff on `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `tests/test_cockpit_kanban_routes_1082.py`, and `tests/test_cockpit_kanban_routes_1083.py`: clean, 0 violations

### Coverage
- quality-runner default scoped coverage could not report `owlbear_cockpit.routes.mutation` because `pyproject.toml` omits `owlbear_cockpit` from `[tool.coverage.run].source_pkgs`
- quality-runner explicit cockpit-module coverage run with `--cov=owlbear_cockpit.routes.mutation`: 97%
- Missing lines: `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:71`, `:75`, `:105-106`, `:256`

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Were Violated? | Verdict |
|---------|-------------|----------------------------------|---------|
| All RED tests from B-17 (#1082) pass | quality-runner scoped run over `tests/test_cockpit_kanban_routes_1082.py` + `tests/test_cockpit_kanban_routes_1083.py` | Yes | COVERED |
| AC-NEW-24: Edit schema excludes `status` field | `tests/test_cockpit_kanban_routes_1082.py:502-523` and `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:35-42` | Yes: 422 is asserted and the mocked view must remain uncalled | COVERED |
| Error mapping: NotFoundError -> 404, ValidationError -> 422, ConcurrencyError -> 409 | `tests/test_cockpit_kanban_routes_1082.py:410-454`, `:606-702`; handlers at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:151-158`, `:283-291`, `:316-323` | Yes | COVERED |
| OCC: `expected_updated` forwarded to CockpitView | `tests/test_cockpit_kanban_routes_1082.py:531-600`; forwarding sites at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:149`, `:280`, `:315` | Yes: exact kwarg equality is asserted | COVERED |
| Read routes return envelope responses | `tests/test_cockpit_kanban_routes_1082.py:182-222` | Yes | COVERED |
| Activity routes: filtered activity and SessionRecord responses | `tests/test_cockpit_kanban_routes_1082.py:263`, `:282`, `:296` | Yes under the latest architecture refinement, which explicitly kept the earlier filtered-activity objection out of scope for this retry | COVERED |
| Admin routes: release, sweep, scan, repair, compact-activity | `tests/test_cockpit_kanban_routes_1082.py:317-346`, `tests/test_cockpit_kanban_routes_1083.py:153-399`, `:479-611`; route registrations at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:330-350` | Yes for the declared route and wire contracts exercised by the live suites | COVERED |
| DI pattern maintained via `get_engine` override | `serve/cockpit/src/owlbear_cockpit/deps.py:20-47`; `tests/test_cockpit_kanban_routes_1083.py:531-557`, `:617-645`, `:649-682` | Yes: scan and repair prove board-observable override behavior, compact proves exact engine identity through `CockpitView` construction | COVERED |

#### Security Review
- No route-layer security issues found in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
- Request bodies remain schema-constrained with `extra="forbid"`, and the admin endpoints are in-process `CockpitView` delegations only

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_CockpitRoutes` | No weakening detected in the live 1082 suite | PRESERVED |
| `TestFromAC_AdminRoutes` | Retry cycles added stronger scan serialization, repair detail, and repair/compact DI proofs | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Scan now asserts exact `code/detail/file_path` values at `tests/test_cockpit_kanban_routes_1083.py:559-583`; repair asserts exact `detail` at `:585-611`; compact asserts exact payload values at `:379-399` and exact engine identity at `:649-682` |
| Negative and error-path coverage | ADEQUATE | 1082 covers schema rejection and mapped 404/422/409 behavior at `tests/test_cockpit_kanban_routes_1082.py:410-454`, `:606-702`; 1083 covers clean-board and real-corrupt-board admin behavior at `tests/test_cockpit_kanban_routes_1083.py:153-199`, `:479-557` |
| Manual mutation reasoning | ADEQUATE | Breaking scan serialization or compact DI wiring would fail the live 1083 suite. Repair DI proof is less direct than compact, but in this scoped app setup a broken override path would not yield the successful non-empty alt-board result asserted at `tests/test_cockpit_kanban_routes_1083.py:617-645` because `app.state.engine` is only initialized by `owlbear_cockpit.main.run()` | 
| Test independence | STRONG | `tmp_path` boards isolate state and `app.dependency_overrides.clear()` runs in fixture/test cleanup at `tests/test_cockpit_kanban_routes_1083.py:120-145` |
| Naming clarity | STRONG | Task-owned names remain descriptive and map directly to the AC |

#### Data Safety
- No route-layer data safety issue found in the changed implementation
- The only task-owned source logic beyond thin delegation is `_serialize_scan_item()` at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:71-91`; live tests exercise both real-object and mocked-dict scan items at `tests/test_cockpit_kanban_routes_1083.py:479-557` and `:559-583`

#### Implementation-Aware Gaps
- No significant untested path in the changed route implementation blocks certification
- The admin delegates in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:336-350` are covered by direct route tests, delegation tests, and DI proofs
- `_serialize_scan_item()` is covered by both real corruption objects and mocked dict payloads, closing the earlier live-wire gap

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- Cockpit route coverage is reviewable, but not through default source discovery. The workspace currently requires explicit `--cov=owlbear_cockpit.routes.mutation` for task-scoped cockpit coverage because `pyproject.toml` omits `owlbear_cockpit` from `source_pkgs`.
- The repair DI proof is still less direct than the compact DI identity proof. I treated it as sufficient here because it uses a real alternate corrupt board and the scoped app does not initialize `app.state.engine` outside `owlbear_cockpit.main.run()`, so the old false-green path is not available in this review run.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-17 pass | quality-runner scoped pytest over `tests/test_cockpit_kanban_routes_1082.py` + `tests/test_cockpit_kanban_routes_1083.py`: 73 passed, 0 failed | PASS |
| AC-NEW-24 status field rejected | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:35-42`; `tests/test_cockpit_kanban_routes_1082.py:502-523` | PASS |
| Error mapping 404, 422, 409 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:151-158`, `:283-291`, `:316-323`; `tests/test_cockpit_kanban_routes_1082.py:410-454`, `:606-702` | PASS |
| OCC forwards `expected_updated` | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:149`, `:280`, `:315`; `tests/test_cockpit_kanban_routes_1082.py:531-600` | PASS |
| Read routes return envelopes | `tests/test_cockpit_kanban_routes_1082.py:182-222` | PASS |
| Activity routes and sessions contract | `tests/test_cockpit_kanban_routes_1082.py:263`, `:282`, `:296` | PASS |
| Admin routes exist and return the expected route contracts | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:330-350`; `tests/test_cockpit_kanban_routes_1082.py:317-346`; `tests/test_cockpit_kanban_routes_1083.py:153-399`, `:479-611` | PASS |
| DI pattern maintained | `serve/cockpit/src/owlbear_cockpit/deps.py:20-47`; `tests/test_cockpit_kanban_routes_1083.py:531-557`, `:617-645`, `:649-682` | PASS |

### Deductions
- 0.04 deducted: cockpit coverage required an explicit `--cov` workaround instead of the default scoped report
- 0.03 deducted: repair DI proof is board-observable rather than exact engine-identity proof

### Verdict
- PASS
- Confidence: 0.93
- Primary reason: independent scoped tests, lint, and explicit cockpit-module coverage are all clean, and the latest retry closes the previously binding scan/repair/compact proof gaps strongly enough to certify the route contract

### Action
- Advance to docs
- Informational follow-up only: add `owlbear_cockpit` to `[tool.coverage.run].source_pkgs` if future cockpit reviews should work without an explicit `--cov` override
[[2026-04-28]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md` CockpitView facade table was missing the 3 new admin routes (scan, repair, compact-activity); updated |
| 2 | Module docstrings | Yes | Updated | `mutation.py` module-level docstring listed "move, edit, release, sweep" only — updated to include "scan, repair, compact-activity" |
| 3 | External attribution | No | N/A | No external patterns cited in builder notes |
| 4 | Research doc | No | N/A | No research doc produced |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` describes `serve/cockpit/src/**`; footer updated from `(a14038d2)` to `(9931eb9a)` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` | IN (docstrings) | Updated module docstring |
| `tests/test_cockpit_kanban_routes_1082.py` | OUT (test file) | N/A |
| `tests/test_cockpit_kanban_routes_1083.py` | OUT (test file) | N/A |
| `serve/cockpit/src/owlbear_cockpit/deps.py` | IN (docstrings) | Verified — existing docstrings accurate, no deps.py changes in task |
| `serve/cockpit/README.md` | IN | Updated admin routes in mutation table |
| `share/diagrams/cockpit.excalidraw` | IN | Footer updated |

### Files Updated
- `serve/cockpit/README.md` — added scan/repair/compact-activity rows to CockpitView facade table
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — updated module docstring
- `share/diagrams/cockpit.excalidraw` — footer: `Last verified: 2026-04-28 (9931eb9a)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1083-*` scratch files found)
[[2026-04-28]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-17 pass | quality-runner full suite: 0 failures in 1082+1083 suites (73 passed) | PASS |
| AC-NEW-24 edit schema excludes status | mutation.py:35 extra=forbid, no status field; 1082 test line 502 | PASS |
| Error mapping 404/422/409 | mutation.py:151,283,316 handlers; 1082 error-mapping tests green | PASS |
| OCC forwards expected_updated | mutation.py:149,280,315; 1082 tests 531,554,578 | PASS |
| Read routes return envelopes | 1082 tests 182,209,222 | PASS |
| Activity routes and sessions | 1082 tests 263,282,296 | PASS |
| Admin routes scan/repair/compact | mutation.py:330-350; 1083 suite 153-399,479-611 | PASS |
| DI pattern maintained | 1083 tests 531 (scan board-observable), 617 (repair two-board), 649 (compact spy identity) | PASS |

### Test Results
- pytest full suite: 117 failures, all in unrelated modules (kanban engine config, mcp-knowledge, react-compiler, mode6 rename). Zero failures in task scope.
- ruff full suite: violations in unrelated modules only. Task scope clean.

### Architect Quality: 4/5
AC was specific (8 testable lines). Minor friction from stale module path (routes/kanban.py vs routes/mutation.py) in brief, but recoverable. DI/wire-shape gaps caught by reviewer as intended.

### Deduction Breakdown
- Start: 1.00
- AC lines without evidence: 0 (-.00)
- Lint violations in task scope: 0 (-.00)
- AC quality <=3: no (-.00)
- Missing reviewer evidence: no, 3 detailed review sections (-.00)
- Full-suite failures in task scope: 0 (-.00)
- Reviewer required 3 cycles: informational, no deduction (gaps were test-quality, not implementation)
- Coverage config workaround needed: -.02

### Confidence: 0.98
### Action: archive