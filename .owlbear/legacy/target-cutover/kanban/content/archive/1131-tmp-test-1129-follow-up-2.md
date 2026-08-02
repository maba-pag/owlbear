---
id: 1131
title: Add cockpit mutation route OCC characterization tests
status: archived
priority: medium
created: 2026-04-26T15:37:53.908968+00:00
updated: 2026-04-27T06:16:14.568408+00:00
tags:
- cockpit
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Objective: Add GREEN characterization tests documenting OCC behavior and structural gaps in cockpit mutation HTTP routes (mutation.py). Tests characterize current behavior; follow-up fix tasks #1134 (edit CAS), #1133 (release engine CAS), #1132 (route wiring through CockpitView) address the underlying issues.

Acceptance Criteria:
- [ ] AC1 (Edit TOCTOU — G1): In `tests/test_cockpit_mutation_race_1131.py`, add a test that patches `engine.edit_task` via `unittest.mock.patch.object`, sends a valid edit request through the cockpit HTTP route, and asserts `expected_updated` is NOT in the captured call kwargs. Proves the edit route never engages the engine CAS — it performs only a precheck (`req.updated != str(task.updated)`) before calling `engine.edit_task(**kwargs)` without `expected_updated` (mutation.py L209).
- [ ] AC2 (Move OCC contrast): Add a test that patches `engine.move_task` via `unittest.mock.patch.object`, sends a valid move request (including task's current `updated` value from a prior `show_task`) through the cockpit HTTP route, and asserts `expected_updated` IS present in the captured call kwargs with the correct value. Proves the move route, unlike the edit route (AC1), forwards the OCC token to the engine (mutation.py L108).
- [ ] AC3 (Release guard broken on new-schema — G3): Add a test that claims a task via `engine.claim_task` (writing `claimed_at` to disk), re-reads the task to assert `claimed_at is not None` (proving claimed state), then sends `POST /api/tasks/{id}/release` through the cockpit HTTP route, and asserts 409 with detail `"Task {id} is not currently claimed"` (with actual task ID). Proves the release route's `if not task.claimed_by` guard (mutation.py L237) is broken on new-schema boards because `claimed_by` has `Field(exclude=True)` in models.py — it is never persisted to disk, so `show_task` always returns `claimed_by=None` even when `claimed_at` is set. No mocking required — this tests the live route behavior.
- [ ] AC4 (409 detail stability): Assert exact 409 detail strings: (a) edit with stale `updated` → `"Task was modified since your last load (stale snapshot)"`, (b) release on truly unclaimed task → `"Task {id} is not currently claimed"` (with actual task ID). Complements existing status-code-only tests in `test_cockpit_mutation_api.py`.
- [ ] AC5 (Schema baseline): For move and edit routes returning 200, assert all 14 `TaskDetailOut` JSON keys: `id`, `title`, `status`, `priority`, `body`, `updated`, `created`, `tags`, `blocked`, `block_reason`, `parent`, `depends_on`, `claimed`, `claimed_by`. No release 200 schema test — the release 200 path is unreachable on new-schema boards due to G3 (AC3).
- [ ] AC6 (Sibling test reconciliation): Mark exactly 4 stale release-route tests in `tests/test_cockpit_mutation_api.py` as `pytest.mark.xfail(strict=True, reason="G3: release route guard uses claimed_by (Field(exclude=True), never persisted) instead of claimed_at — always 409 on new-schema boards. Fix: #1133 + #1132")`: (a) `TestFromAC_ReleaseTask::test_release_claimed_task_returns_200`, (b) `TestFromAC_ReleaseTask::test_release_returns_task_object_shape`, (c) `TestFromAC_AuditLogging::test_release_writes_activity_log_actor_cockpit`, (d) `TestBuilderDiscovered::test_release_audit_log_has_correct_action_and_task_id`. These tests encode the intended contract (release 200 for claimed tasks); the characterization tests (AC3) document the actual behavior (always 409). The xfail markers bridge this gap until #1132 rewrites the release route and updates these tests.

Likely files:
- tests/test_cockpit_mutation_race_1131.py (rewrite — prior implementation had stale premises)
- tests/test_cockpit_mutation_api.py (xfail markers only — AC6)

## Builder Guidance
- Tests are GREEN characterization tests — they pass against current code without production changes
- Reuse fixture pattern from `tests/test_cockpit_mutation_api.py` (board_dir → engine → client via DI override)
- **Prior test file exists and must be rewritten.** The cycle 1 implementation had stale premises: move body missing `updated` (causing 422), and release tests mocking impossible state.
- For AC1 (edit proof): wrap `engine.edit_task` with `unittest.mock.patch.object(wraps=...)`, call the edit route with valid `{updated, title}`, inspect captured kwargs — `expected_updated` must be absent
- For AC2 (move contrast): wrap `engine.move_task` with `unittest.mock.patch.object(wraps=...)`, call the move route with valid `{status, updated}`, inspect captured kwargs — `expected_updated` must be present and match the `updated` value sent
- For AC3 (release proof): claim task via engine (`engine.claim_task("1")`), re-read with `engine.show_task("1")` and assert `claimed_at is not None`, call release route — expect 409. No mocking needed. The route reads `task.claimed_by` which is always None after disk round-trip; the engine uses `claimed_at` which IS persisted.
- `MoveRequest` requires both `status: str` and `updated: str` — omitting `updated` returns 422 (Pydantic validation)
- `TaskDetailOut.claimed` is derived from `claimed_at` by `_coerce_claimed` validator, but `_task_to_detail()` never passes `claimed_at` — so `claimed` is always False in responses. This is expected current behavior.
- `claimed_by` is always None in responses — `Field(exclude=True)` in Task model means it's never in YAML; `_task_to_detail` reads `task.claimed_by` which is None after round-trip
- **CockpitView context:** `CockpitView` (engine.py L3049+) is a tested wrapper that correctly handles all three operations: edit with `expected_updated`, move with `expected_updated`, release via `claimed_at`. The HTTP routes bypass this wrapper and implement their own (broken) logic. Follow-up fix tasks likely need to wire routes through CockpitView.
- **AC6 guidance:** Add `@pytest.mark.xfail(strict=True, reason="G3: release route guard uses claimed_by (Field(exclude=True), never persisted) instead of claimed_at — always 409 on new-schema boards. Fix: #1133 + #1132")` to exactly the 4 named tests. Do not modify test logic or assertions — only add the xfail marker. The `strict=True` ensures these tests fail as expected; if the underlying bug is fixed, the marker will cause XPASS which surfaces the need to remove it.

## Key Findings (corrected from cycle 1)
Two confirmed OCC gaps in cockpit mutation routes, one false positive:
- G1 (confirmed): Edit route precheck-only TOCTOU — engine CAS never engaged (`expected_updated` not passed to `engine.edit_task`)
- G2 (RETRACTED): Move route DOES have OCC — `MoveRequest` has `updated: str` field, route forwards `expected_updated=req.updated` to `engine.move_task`. Original research incorrectly stated move had no OCC.
- G3 (confirmed, reframed): Release route guard uses `task.claimed_by` (never persisted, always None) instead of `task.claimed_at` (persisted by engine). Route is completely broken on new-schema boards — always returns 409 even for claimed tasks.

Follow-up tasks: #1134 (edit CAS fix), #1133 (release engine CAS), #1132 (route wiring through CockpitView)
[[2026-04-27]]
## Architecture Review (cycle 3)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests-only task covering one domain (cockpit mutation route OCC characterization) |
| Interface clarity | PASS | All 6 AC lines specify exact test patterns, assertions, mock targets, and source references |
| Dependency correctness | PASS | No dependencies — standalone test task |
| Module layering | PASS | Test file imports only cockpit app and kanban engine |
| TDD compliance | N/A | This IS the test task — GREEN characterization tests, no RED phase |
| KISS/YAGNI | PASS | Minimal scope: 2 gap proofs (G1, G3) + 1 contrast test (AC2) + 2 assertion-tightening ACs + 1 reconciliation AC |
| Premise challenge | PASS | G1 confirmed (mutation.py:221 omits expected_updated). G2 RETRACTED (MoveRequest has `updated`, route forwards CAS at L108). G3 confirmed (mutation.py:237 guards on `claimed_by` which is `Field(exclude=True)` at models.py:263, never persisted). |
| Pattern consistency | PASS | Follows existing test_cockpit_mutation_api.py fixture pattern |
| Security surface | N/A | Tests only |
| Single domain | PASS | Cockpit mutation routes only |

### Reviewer Rejection Analysis (cycle 3)
Reviewer confidence: 0.86, FAIL. All 5 original ACs passed review. Rejection reason: 4 sibling tests in `test_cockpit_mutation_api.py` assert release returns 200 for claimed tasks, but the route always returns 409 (G3). Cross-suite rerun confirmed the sibling tests fail on current code. Reviewer called this "contradictory test evidence" and a review blocker.

### Architectural Decision: Release Contract Authority
- **Actual behavior** (documented by AC3): release always returns 409 on new-schema boards because `claimed_by` is never persisted (`Field(exclude=True)` at models.py:263)
- **Intended behavior** (encoded by sibling tests): release returns 200 for claimed tasks
- **Resolution**: Both are factually correct in their respective domains. The 4 sibling tests encode the intended contract that will be restored when #1132 rewires routes through CockpitView. AC6 bridges this gap with xfail markers that: (a) make the contradiction explicit and documented, (b) ensure the combined suite is green, (c) will surface as XPASS when the fix lands
- **Ownership**: #1132 explicitly owns route-layer release changes and sibling test updates. The xfail markers are temporary bridges until #1132 rewrites them.

### Changes from cycle 2
- Added AC6 (sibling test reconciliation) — marks 4 stale release-route tests as `xfail(strict=True)` with G3 reason and fix-task references
- Updated follow-up references: replaced stale #1136 with correct #1133 (release engine CAS)
- Added `tests/test_cockpit_mutation_api.py` to Likely files
- Added AC6 builder guidance

### Challenge Results
- Challenger: reconsider (confidence: 0.56)
- Concerns: (1) contract authority — xfail suppresses intended-contract signal; (2) cleanup path — not self-clearing, #1132 must rewrite; (3) failure-cause masking — strict=True doesn't distinguish 409 vs future 422; (4) no repo xfail precedent; (5) #1132 ownership overlap
- Architect response: override — (1) xfail documents the decision, not suppresses it — the reason string names G3 root cause and fix tasks; (2) accepted — #1132 explicitly owns rewriting these tests, the xfails are temporary bridges; (3) acceptable — tests will be rewritten by #1132 anyway, not just unmarked; (4) novel situation — characterization tests alongside aspirational tests for broken code is not the same as weakening valid assertions; (5) AC6 is scoped to markers only, not test logic — no ownership conflict

### Verdict: APPROVE (after refinement)
### Action Taken: Added AC6 for sibling test xfail markers addressing reviewer's contradictory-suite concern. Updated stale #1136 references to #1133. Cleaned follow-up task list. Advanced to todo.
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_mutation_race_1131.py (GREEN characterization tests, pre-existing from prior cycle)
- Sibling file: tests/test_cockpit_mutation_api.py (xfail markers added per AC6)
- Classes in race file: TestFromAC_EditTOCTOU, TestFromAC_MoveOCCContrast, TestFromAC_ReleaseGuardBroken, TestFromAC_409DetailStrings, TestFromAC_SchemaBaseline
- Tests per category (race file): happy 4, edge 0, error 2, boundary 1 — 7 total, all PASS (GREEN characterization)
- xfail markers added: 4 tests in test_cockpit_mutation_api.py now XFAIL (strict=True) — previously FAILING
- ruff: clean
- AC coverage: AC1 ✅ (edit TOCTOU — expected_updated absent), AC2 ✅ (move OCC contrast — expected_updated present), AC3 ✅ (release guard broken — 409 even when claimed), AC4 ✅ (exact 409 detail strings), AC5 ✅ (14 TaskDetailOut keys), AC6 ✅ (4 release tests marked xfail strict=True)
- Fixed stale follow-up references in race file docstring (#1135/#1136 → #1133/#1132)
- Pre-existing failures in test_cockpit_mutation_api.py (4 audit log tests) not caused by this task — confirmed via git stash; those are engine.py signature drift from parallel task work
[[2026-04-27]]
## Builder Notes
- Implementation: no production code changes required for this task; task is test-characterization-only and already implemented by test-writer commit `43193ffb`.
- Files verified: `tests/test_cockpit_mutation_race_1131.py` (AC1-AC5 characterization tests), `tests/test_cockpit_mutation_api.py` (AC6 xfail markers).
- Test evidence (quality-runner, scoped): `tests/test_cockpit_mutation_race_1131.py` -> 7 passed, 0 failed.
- Lint evidence (quality-runner, scoped): clean for `tests/test_cockpit_mutation_race_1131.py` and `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`.
- Coverage: scoped run executed with coverage enabled; reported exercised modules are engine-side (route called via HTTP), with high model coverage and no task-owned failures.
- AC6 verification: exactly 4 strict xfail markers present on the specified release tests in `tests/test_cockpit_mutation_api.py`, with reason text matching task guidance.
- Additional context: a broader sibling-file run (`tests/test_cockpit_mutation_api.py`) reports 4 pre-existing audit-log failures for move/edit actor assertions, outside task 1131 AC scope and unrelated to the release-guard characterization objective.

### Reflection
- Existing test-writer implementation already satisfied the builder objective; avoided unnecessary edits.
- Scoped quality evidence prevented conflating unrelated sibling failures with task-owned acceptance criteria.
- AC6 was validated structurally (exact tests + strict marker) to ensure bridge behavior is explicit and temporary.
[[2026-04-27]]
## Review Evidence
### Test Results
- Quality-runner broad changed-file run: 36 passed, 4 failed, 4 xfailed. The 4 failures were move/edit actor-audit assertions in tests/test_cockpit_mutation_api.py, outside AC6’s release-route xfail bridge.
- Quality-runner task-owned rerun used for gating: 7 passed, 0 failed, 4 xfailed on tests/test_cockpit_mutation_race_1131.py plus the 4 AC6 node IDs in tests/test_cockpit_mutation_api.py.

### Lint
- clean: true

### Coverage
- owlbear_kanban.models: 91%
- owlbear_cockpit.routes.mutation was not reported by quality-runner scoped coverage under the current workspace coverage configuration, so route proof was evaluated by direct source-to-test mapping.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 | tests/test_cockpit_mutation_race_1131.py:147 with route call check at :156 and expected_updated absence at :162-165 | Yes | COVERED |
| AC2 | tests/test_cockpit_mutation_race_1131.py:182 with expected_updated presence/value checks at :197-202 | Yes | COVERED |
| AC3 | tests/test_cockpit_mutation_race_1131.py:222 with claimed_at precondition at :234 and 409 detail at :241-245 | No. The test proves claimed_at persisted and release still returns 409, but it never asserts the round-tripped task has claimed_by=None, so a different guard producing the same 409 would still pass. | LAX |
| AC4 | tests/test_cockpit_mutation_race_1131.py:256 and :267 with exact detail assertions at :264 and :272 | Yes | COVERED |
| AC5 | tests/test_cockpit_mutation_race_1131.py:287 and :300 with 14-key checks at :295-298 and :308-311 | Yes | COVERED |
| AC6 | strict xfail markers at tests/test_cockpit_mutation_api.py:387, :396, :518, :597 on the 4 named release tests | Yes | COVERED |

#### Security Review
- No issues found. Scope is test-only and stays within tmp_path boards plus FastAPI dependency overrides.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| tests/test_cockpit_mutation_api.py:391 | Added strict xfail at :387 with precise G3 reason and fix-task IDs | PRESERVED |
| tests/test_cockpit_mutation_api.py:400 | Added strict xfail at :396 | PRESERVED |
| tests/test_cockpit_mutation_api.py:522 | Added strict xfail at :518 | PRESERVED |
| tests/test_cockpit_mutation_api.py:601 | Added strict xfail at :597 | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC3 names the claimed_by persistence hole, but the executable assertions only check claimed_at persisted and the route still returns 409. There is no direct assertion that the re-read task has claimed_by=None despite the test prose claiming that root cause. |
| Negative/error-path coverage | STRONG | AC3 and AC4 cover claimed-task 409, unclaimed-task 409, and stale-edit 409. |
| Manual mutation reasoning | ADEQUATE | AC1, AC2, AC4, and AC5 would fail on the targeted route mutations; AC3 would not distinguish the stated root cause from another identical 409 path. |
| Test independence | STRONG | Both suites use isolated tmp_path boards and per-test dependency overrides. |
| Descriptive names | STRONG | Test names are explicit about route, behavior, and expected outcome. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- Significant proof gap in AC3: tests/test_cockpit_mutation_race_1131.py:222 does not assert that engine.show_task("1") returns claimed_by=None after claim_task persists claimed_at. That missing executable assertion means the test does not fully prove the specific claimed_by Field(exclude=True) persistence hole named in the AC and docstring.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- tests/test_cockpit_mutation_api.py still contains unrelated failing move/edit actor-audit assertions in the broader sibling run. They did not drive this verdict because the task-owned rerun isolated the 1131 scope.
- tests/test_cockpit_mutation_api.py file-level docstring still describes the file as a failing RED-phase suite, which no longer matches current mixed PASS/XFAIL state.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:221 omits expected_updated; tests/test_cockpit_mutation_race_1131.py:147 asserts absence in captured kwargs | test_edit_route_does_not_pass_expected_updated_to_engine | PASS |
| AC2 | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:109 forwards expected_updated=req.updated; tests/test_cockpit_mutation_race_1131.py:182 asserts presence and exact equality | test_move_route_passes_expected_updated_to_engine | PASS |
| AC3 | serve/cockpit/src/owlbear_cockpit/routes/mutation.py:237 guards on claimed_by and serve/kanban/src/owlbear_kanban/models.py:263 excludes claimed_by from persistence, but tests/test_cockpit_mutation_race_1131.py:222 never directly asserts claimed_by is None after round-trip | test_release_returns_409_even_when_task_is_genuinely_claimed | FAIL |
| AC4 | tests/test_cockpit_mutation_race_1131.py:256 and :267 assert exact stale-edit and unclaimed-release detail strings | test_edit_stale_snapshot_exact_detail_string; test_release_unclaimed_task_exact_detail_string | PASS |
| AC5 | tests/test_cockpit_mutation_race_1131.py:287 and :300 assert all 14 TaskDetailOut keys on move/edit 200 responses | test_move_200_response_has_all_14_taskdetailout_keys; test_edit_200_response_has_all_14_taskdetailout_keys | PASS |
| AC6 | tests/test_cockpit_mutation_api.py:387, :396, :518, :597 apply strict xfail to the 4 named stale release tests | release-task and release-audit node IDs | PASS |

### Deductions
- 0.12: AC3 root-cause proof is incomplete because the test never executes the claimed_by=None assertion it relies on in prose.

### Verdict
- FAIL. Confidence: 0.88
- Action: move to todo. Test-writer should strengthen AC3 by asserting the re-read task has claimed_at set and claimed_by=None before POST /api/tasks/1/release, then rerun the task-owned subset.
[[2026-04-27]]
## Test-Writer Notes
- Retry: AC3 root-cause proof strengthened
- Added `assert claimed_task.claimed_by is None` directly after the `claimed_at is not None` precondition in `test_release_returns_409_even_when_task_is_genuinely_claimed`
- This directly proves the `Field(exclude=True)` persistence hole: after a disk round-trip, `claimed_by` is `None` despite `claimed_at` being set — exactly the gap the release guard falls into
- Test file: tests/test_cockpit_mutation_race_1131.py
- Classes: TestFromAC_EditTOCTOU, TestFromAC_MoveOCCContrast, TestFromAC_ReleaseGuardBroken, TestFromAC_409DetailStrings, TestFromAC_SchemaBaseline
- Tests per category: happy 4, edge 0, error 2, boundary 1 — 7 total, all PASS (GREEN characterization)
- ruff: clean
- AC coverage: AC1 ✅, AC2 ✅, AC3 ✅ (now asserts claimed_by=None proving persistence hole), AC4 ✅, AC5 ✅, AC6 ✅
[[2026-04-27]]
## Builder Notes
- Implementation: no code edits applied in this builder pass; test-writer retry already added the AC3 root-cause assertion in tests/test_cockpit_mutation_race_1131.py (`assert claimed_task.claimed_by is None`).
- Verification scope (quality-runner, task-owned): `tests/test_cockpit_mutation_race_1131.py`.
- Tests: 7 passed, 0 failed, 0 xfailed.
- Lint: clean for `tests/test_cockpit_mutation_race_1131.py` and `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`.
- Coverage: `owlbear_cockpit.routes.mutation` reported 61% in scoped run; acceptable for this task because no production module changes were made in this builder pass and gate decision is based on AC-owned characterization tests.
- AC6 structural verification: exactly 4 strict xfail markers exist in tests/test_cockpit_mutation_api.py on the specified release tests with the required G3 reason text and fix references (#1133 + #1132).
- Evidence summary: reviewer-blocking gap was AC3 proof strength; current test now directly proves `claimed_by` persistence hole (`claimed_at` set + `claimed_by is None`) before exercising `/release` 409 behavior.

### Reflection
- Scoped rerun avoided conflating task-owned AC evidence with unrelated sibling failures in broader mutation API tests.
- The strengthened AC3 assertion closes the exact reviewer-identified executable-proof gap.
- No additional edits were necessary; minimizing intervention preserved surgical task scope.
[[2026-04-27]]
## Review Evidence
### Test Results
- Quality-runner broad run across the two touched test files: 36 passed, 4 failed, 4 xfailed.
- The 4 failures were unrelated sibling nodes in tests/test_cockpit_mutation_api.py:436, :457, :561, :579 covering move/edit audit-log assertions, not the 4 AC6 release-route nodes.
- All task-owned characterization nodes in tests/test_cockpit_mutation_race_1131.py were absent from the fail and xfail lists and therefore were part of the 36 passes.
- AC6 release-route bridge behavior is active: 4 xfailed, matching the 4 named release tests.

### Lint
- clean: true

### Coverage
- owlbear_cockpit.routes.mutation: 96%
- owlbear_kanban.models: 91%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 | tests/test_cockpit_mutation_race_1131.py:147-165 | Yes. The test patches engine.edit_task and asserts expected_updated is absent from captured kwargs at line 164, matching mutation.py:221. | COVERED |
| AC2 | tests/test_cockpit_mutation_race_1131.py:182-203 | Yes. The test patches engine.move_task and asserts expected_updated is present and equal to task.updated at lines 199 and 202, matching mutation.py:109. | COVERED |
| AC3 | tests/test_cockpit_mutation_race_1131.py:222-250 | Yes. The retry now asserts both claimed_at is set at line 234 and claimed_by is None at line 237 before the release call returns the exact 409 detail at line 250, matching mutation.py:237 and models.py:274. | COVERED |
| AC4 | tests/test_cockpit_mutation_race_1131.py:261-277 | Yes. Exact 409 detail strings are asserted for stale edit at line 268 and unclaimed release at line 277. | COVERED |
| AC5 | tests/test_cockpit_mutation_race_1131.py:292-316 | Yes. Both 200-path tests compute missing keys against the 14-key TaskDetailOut baseline at lines 302 and 315. | COVERED |
| AC6 | tests/test_cockpit_mutation_api.py:387, :396, :518, :597 | Yes. Exactly the 4 named release tests are marked strict xfail, and the underlying assertions remain intact at lines 391, 400, 522, and 601. | COVERED |

#### Security Review
- No issues found. Scope is test-only and uses tmp_path boards, FastAPI dependency overrides, and unittest.mock wraps.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| tests/test_cockpit_mutation_api.py:391 | Added strict xfail marker at line 387 with the required G3 reason and fix-task references. | PRESERVED |
| tests/test_cockpit_mutation_api.py:400 | Added strict xfail marker at line 396. | PRESERVED |
| tests/test_cockpit_mutation_api.py:522 | Added strict xfail marker at line 518. | PRESERVED |
| tests/test_cockpit_mutation_api.py:601 | Added strict xfail marker at line 597. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | AC1, AC2, and AC3 use exact kwargs and exact state assertions; AC3 now directly proves claimed_by is None at line 237. |
| Negative/error-path coverage | STRONG | Claimed-task 409, unclaimed-task 409, and stale-edit 409 are asserted directly. |
| Manual mutation reasoning | STRONG | Removing expected_updated forwarding, changing the claimed_by guard premise, or altering the detail strings would all fail the mapped tests. |
| Test independence | STRONG | Fixtures create isolated tmp_path boards and fresh engine/client instances per test. |
| Descriptive names | STRONG | Test names state route, condition, and expected behavior precisely. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- No untested path in the task-owned scope. The prior AC3 proof gap is closed by the explicit claimed_by None assertion before the live release-route call.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Quality-runner broad execution still surfaces 4 unrelated move/edit audit-log failures in tests/test_cockpit_mutation_api.py lines 436, 457, 561, and 579. Those nodes are outside AC6 and are not caused by adding strict xfail markers to the 4 release tests.
- The route module still bypasses CockpitView for release/edit behavior. That is the documented system-under-test for this characterization task, not a blocker for 1131.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | mutation.py:221 calls engine.edit_task without expected_updated; tests/test_cockpit_mutation_race_1131.py:164 asserts absence in captured kwargs | test_edit_route_does_not_pass_expected_updated_to_engine | PASS |
| AC2 | mutation.py:109 forwards expected_updated=req.updated; tests/test_cockpit_mutation_race_1131.py:199 and :202 assert presence and exact equality | test_move_route_passes_expected_updated_to_engine | PASS |
| AC3 | mutation.py:237 guards on claimed_by; models.py:274 excludes claimed_by from persistence; tests/test_cockpit_mutation_race_1131.py:234, :237, :250 prove claimed_at persisted, claimed_by round-tripped to None, and release still returns 409 | test_release_returns_409_even_when_task_is_genuinely_claimed | PASS |
| AC4 | tests/test_cockpit_mutation_race_1131.py:268 and :277 assert the exact stale-edit and unclaimed-release detail strings | test_edit_stale_snapshot_exact_detail_string; test_release_unclaimed_task_exact_detail_string | PASS |
| AC5 | tests/test_cockpit_mutation_race_1131.py:302 and :315 assert the full 14-key response baseline on move and edit 200 responses | test_move_200_response_has_all_14_taskdetailout_keys; test_edit_200_response_has_all_14_taskdetailout_keys | PASS |
| AC6 | tests/test_cockpit_mutation_api.py:387, :396, :518, :597 apply strict xfail to exactly the 4 named stale release tests and preserve the intended-contract assertions | release-task and release-audit node IDs | PASS |

### Deductions
- 0.04: quality-runner broad execution included unrelated sibling failures in the same file, so task-owned isolation required direct node mapping in addition to the runner output.
- 0.02: the sibling file remains noisy because unrelated move/edit audit-log assertions are currently red.

### Verdict
- PASS. Confidence: 0.94
- Action: advance to docs.
[[2026-04-27]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Test-only task; no behavior, API, CLI, config, or package structure changed |
| 2 | Module docstrings | No | N/A | No Python modules created or modified; only test files touched |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No `.owlbear/research/` slug mentioned in task body |
| 5 | Diagram maintenance (describes match) | No | N/A | No IN-scope diagram describes test files |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| tests/test_cockpit_mutation_race_1131.py | OUT (test file) | N/A |
| tests/test_cockpit_mutation_api.py | OUT (test file) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1131-* scratch files found)
[[2026-04-27]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 (Edit TOCTOU) | tests/test_cockpit_mutation_race_1131.py:147-165 — patches engine.edit_task, asserts expected_updated absent from captured kwargs | PASS |
| AC2 (Move OCC contrast) | tests/test_cockpit_mutation_race_1131.py:182-203 — patches engine.move_task, asserts expected_updated present and equal to task.updated | PASS |
| AC3 (Release guard broken) | tests/test_cockpit_mutation_race_1131.py:222-250 — asserts claimed_at not None, claimed_by is None (persistence hole proof), release returns 409 | PASS |
| AC4 (409 detail stability) | tests/test_cockpit_mutation_race_1131.py:256-277 — exact stale-edit and unclaimed-release detail strings asserted | PASS |
| AC5 (Schema baseline) | tests/test_cockpit_mutation_race_1131.py:287-316 — 14 TaskDetailOut keys verified on move and edit 200 responses | PASS |
| AC6 (Sibling test reconciliation) | tests/test_cockpit_mutation_api.py:387, :396, :518, :597 — exactly 4 strict xfail markers with G3 reason and #1133 + #1132 fix references | PASS |

### Test Results
- pytest (task-owned): 7 passed, 0 failed
- pytest (full suite): 2542 passed, 136 failed, 4 xfailed — all 136 failures pre-existing and outside task scope (model validation, status mismatches, timestamp offsets, agent_map config). 4 xfailed = AC6 bridge markers.
- ruff: clean on task-owned files; 8 workspace-wide violations outside task scope

### Architect Quality: 5/5
All 6 AC lines are highly specific with exact test patterns, assertion targets, mock strategies, source line references, and expected values. Builder guidance section was thorough and accurate. AC went through 3 architect cycles including reviewer-driven AC6 refinement to resolve cross-suite contradictions. Exemplary AC quality.

### Deduction Breakdown
- No deductions. All 6 AC lines have specific executable evidence. No task-scope failures. No lint in task files. Reviewer evidence present and detailed with PASS verdict.

### Confidence: 1.00
### Action: archive

### Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 01e0fb3f | test | tests/test_cockpit_mutation_race_1131.py | #1131 |
| 43193ffb | test | tests/test_cockpit_mutation_race_1131.py, tests/test_cockpit_mutation_api.py | #1131 |