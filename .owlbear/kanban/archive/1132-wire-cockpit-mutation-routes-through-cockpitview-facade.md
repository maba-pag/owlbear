---
id: 1132
title: Wire cockpit mutation routes through CockpitView facade
status: archived
priority: medium
created: 2026-04-26T15:52:11.982906+00:00
updated: 2026-04-27T11:22:42.199867+00:00
tags:
- cockpit
parent: 1130
depends_on:
- 1130
- 1133
- 1134
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
Objective: Route move and release mutations through CockpitView facade for OCC parity and pattern consistency. Edit route stays on direct engine (fixed by #1134; full CockpitView delegation deferred to #1141).

**Errata (from reviewer cycle 1):** The original AC assumed POST /move had no OCC. Live code already has full OCC: `MoveRequest.updated` (L28-34), stale-snapshot precheck (L94), `expected_updated` pass-through (L108-109), and `ConcurrencyError` → 409 (L110-113). Move routing through CockpitView is a pattern-consistency change, not an OCC fix.

**Errata (from architect cycle 1):** Original AC said "all three routes" but researcher recommended Option B (move + release only). CockpitView.edit_task lacks `title` param (#1141 at research), blocking full edit delegation. AC refined to match Option B. Dependency on #1134 added (same-file edit route changes must land first). Challenger raised critical contract contradiction on unclaimed-release guard — resolved by keeping claimed check via CockpitView read.

Acceptance Criteria:
- [ ] AC1: `get_view` dependency added to deps.py returning `CockpitView(engine)`. Import: `from owlbear_kanban.engine import CockpitView`.
- [ ] AC2: POST /move delegates to `CockpitView.move_task(task_id, req.status, expected_updated=req.updated)`. Route retains `adapter.valid_transitions` precheck before the CockpitView call (preserves same-status → 422 rejection).
- [ ] AC3: POST /release accepts a new `ReleaseRequest(updated: str)` body model. Route delegates to `CockpitView.release_task(task_id, expected_updated=req.updated)`.
- [ ] AC4a: Move error mapping: `NotFoundError` → 404, `ValidationError` → 422, `ConcurrencyError` → 409. All from `owlbear_kanban.errors`.
- [ ] AC4b: Release error mapping: `NotFoundError` → 404, `ConcurrencyError` → 409. No release-side `ValidationError` source exists.
- [ ] AC5: Release route replaces broken `claimed_by` guard (always None due to `Field(exclude=True)`) with CockpitView-based claimed check using the `claimed` boolean. Unclaimed release → 409 behavior preserved.
- [ ] AC6: `_task_to_detail` helper adapted for `SingleTaskResponse` (CockpitView return type lacks `claimed_by`; has `claimed_at` and `claimed`). Both raw `Task` (edit route) and `SingleTaskResponse` (move/release) handled.
- [ ] AC7: New test: POST /release with stale `updated` token → 409.
- [ ] AC8: ALL release test calls across test_cockpit_mutation_api.py and test_cockpit_mutation_race_1131.py updated to send `ReleaseRequest` body with `updated` field. Release xfail markers referencing #1132 removed.
- [ ] AC9: Existing move tests pass unchanged (behavior-preserving refactor).
- [ ] AC10: Activity events from move and release include source=cockpit (CockpitView sets this automatically).
- [ ] AC11: Edit route unchanged — stays on direct engine path (no CockpitView delegation for edit).

Scope boundary: Route layer only (mutation.py, deps.py, models.py, cockpit tests). Edit route not touched. Engine changes are #1133 (done).

## Builder Guidance
- **Move route engine access:** Move still needs `engine.show_task` for `valid_transitions` check. Access engine via `view.engine` or inject both `get_engine` and `get_view` — builder's discretion.
- **Release claimed check:** `CockpitView.show_task` returns `ShowTaskResponse` (inherits TaskSummary) with correct `claimed` boolean derived from `claimed_at`. Use this instead of broken `claimed_by`. Note: `view.show_task` raises raw `FileNotFoundError` (not wrapped), while `view.release_task` wraps it into `NotFoundError`.
- **Response adaptation:** `SingleTaskResponse.model_dump()` includes `claimed_at` and `claimed` but not `claimed_by`. `TaskDetailOut._coerce_claimed` derives `claimed` from `claimed_at` in dict data. Simplest approach: `TaskDetailOut.model_validate(result.model_dump())` — extra fields silently ignored, `claimed` correctly derived. Alternatively, `getattr(task, 'claimed_by', None)` in `_task_to_detail`.
- **Imports:** After #1134 lands, mutation.py will already have `from owlbear_kanban.errors import ConcurrencyError`. Extend to include `NotFoundError, ValidationError`.
- `ValidationError` from `owlbear_kanban.errors` does NOT conflict with pydantic's `ValidationError` in this module.
- `ReleaseRequest` model: `ConfigDict(extra="forbid")`, single field `updated: str`.
- Release xfail markers exist in 3 tests (2 in TestFromAC_ReleaseTask, 1 in TestFromAC_AuditLogging). Plus ~6 non-xfail release calls need body updates.
- Characterization tests in test_cockpit_mutation_race_1131.py also have release calls that need body updates.

Likely files:
- serve/cockpit/src/owlbear_cockpit/routes/mutation.py
- serve/cockpit/src/owlbear_cockpit/deps.py
- serve/cockpit/src/owlbear_cockpit/models.py (ReleaseRequest if placed here; or inline in mutation.py)
- tests/test_cockpit_mutation_api.py
- tests/test_cockpit_mutation_race_1131.py

Research: .owlbear/research/cockpit-mutation-occ-parity.md

[[2026-04-27]]
## Research
- Research doc: .owlbear/research/1132-cockpit-mutation-cockpitview-wiring.md
- Sources: 10 studied, 7 high-relevance (all codebase)
- Recommendation: Option B (hybrid) — route move + release through CockpitView; leave edit on direct engine (fixed by #1134). Full CockpitView delegation blocked by CockpitView.edit_task missing title param. (confidence: 0.78)
- Follow-up tasks created: #1141 (extend CockpitView.edit_task with title param) at research
- Decision requests: none — T1 (incremental route-layer changes)

Key findings:
1. Release route is BROKEN — uses task.claimed_by which is Field(exclude=True), always None from disk. CockpitView fixes this.
2. CockpitView.edit_task lacks title param — blocks full edit delegation (scope boundary: route layer only).
3. Move same-status regression risk — engine.move_task allows same-status; route precheck rejects. Must retain valid_transitions precheck.
4. _task_to_detail helper has claimed_by AttributeError risk with SingleTaskResponse + pre-existing claimed:False bug.
5. Edit TOCTOU already being fixed by #1134 (in-progress) via direct engine CAS.
6. AC refined: reduced from "all three routes" to "move + release through CockpitView" per Option B.

## Challenge Results (researcher)
- Challenger: reconsider (confidence 0.58)
- Key challenges: (1) CockpitView edit prerequisite underestimated, (2) move same-status regression, (3) acceptance-surface undercount for release tests, (4) overlap with existing #1134 edit fix path
- Researcher response: accepted all 4 — revised from full delegation (Option A) to hybrid (Option B)

## Challenge Results (architect)
- Challenger: block (confidence 0.41)
- 4 challenges raised: (1) CRITICAL: AC5 contract contradiction — removing claimed_by guard without preserving unclaimed→409 contract, (2) ValidationError verifiability gap in release error mapping, (3) acceptance-surface undercount — 8+ release calls need body updates not just xfail tests, (4) response-shape drift — claimed derivation path not just claimed_by
- Architect response: accepted all 4 — revised AC5 (kept claimed check via CockpitView), split AC4→AC4a/AC4b, expanded AC8 to all release calls, clarified AC6 and builder guidance for model_dump approach
[[2026-04-27]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Move + release facade wiring only; edit explicitly excluded (AC11) |
| Interface clarity | PASS (after refinement) | 12 AC lines, each verifiable. Error mapping split per route (AC4a/AC4b). Claimed check preserved (AC5). Builder guidance section added. |
| Dependency correctness | PASS (after fix) | Added depends_on: [1134] — same-file edit route changes must land first. #1130, #1133 archived (done). |
| Module layering | PASS | CockpitView imported from owlbear_kanban.engine; errors from owlbear_kanban.errors. Same dependency direction as existing engine DI. |
| TDD compliance | PASS | Test-writer will process next; AC7/AC8 specify test deliverables |
| KISS/YAGNI | PASS | Option B (move + release only) is minimal scope. Full delegation deferred to #1141. |
| Premise challenge | PASS | Release route is genuinely broken (claimed_by always None). 3 xfail tests confirm. Move is pattern consistency + source tagging. |
| Pattern consistency | PASS | Follows CockpitView facade pattern already used by read API. Error taxonomy matches owlbear_kanban.errors. |
| Security surface | N/A | No new system boundaries; existing HTTP API |
| Single domain | PASS | Cockpit route layer only |

### AC Refinement Summary
- Scope narrowed from "all three routes" to move + release (Option B) per research recommendation
- AC4 split into AC4a (move) and AC4b (release) — ValidationError only grounded on move side
- AC5 revised: preserved unclaimed-release→409 contract using CockpitView `claimed` boolean instead of broken `claimed_by`
- AC6 clarified: model_dump approach for response adaptation, not just getattr patch
- AC8 expanded: all release test calls (8+) need body updates, not just 3 xfail tests
- AC11 added: explicit edit exclusion
- Builder Guidance section added: engine access, claimed check, response adaptation, imports, ReleaseRequest shape

### Challenge Results
- Challenger: block (confidence 0.41) — 4 concerns: contract contradiction, ValidationError gap, acceptance-surface undercount, response-shape drift
- Architect response: accepted all 4 — AC5 revised (kept claimed check), AC4 split, AC8 expanded, AC6+guidance clarified
- Post-revision confidence: .88 — all challenger concerns addressed in AC

### Verdict: APPROVE (after refinement)
### Action Taken: Rewrote AC (original 11 → refined 12 lines), added depends_on [1134], added Builder Guidance section, narrowed scope to Option B (move + release only), advanced to todo
[[2026-04-27]]
## Test-Writer Notes

**Test file:** `tests/test_cockpit_mutation_api_1132.py`

**Classes:**
- `TestFromAC_GetViewDependency` — AC1 (3 tests)
- `TestFromAC_MoveCockpitViewDelegation` — AC2 (3 tests)
- `TestFromAC_ReleaseRequestModel` — AC3 + AC8 (6 tests)
- `TestFromAC_MoveErrorMapping` — AC4a (3 tests)
- `TestFromAC_ReleaseErrorMapping` — AC4b (2 tests)
- `TestFromAC_ReleaseClaim` — AC5 (3 tests)
- `TestFromAC_ResponseAdaptation` — AC6 (2 tests)
- `TestFromAC_ReleaseStaleToken` — AC7 (2 tests)
- `TestFromAC_ReleaseActivityLogging` — AC10 (1 test)

**Total: 25 tests, all FAIL** (13 failed, 12 errors)
**Lint: ruff clean**

**AC coverage table:**

| AC | Tests | Failure reason |
|----|-------|---------------|
| AC1 | 3 | ImportError: `get_view` not in deps.py |
| AC2 | 3 | ERROR: `mock_view_client` ImportError; after fix → assertion (move_task not called) |
| AC3 | 6 | ImportError for model; AssertionError 422≠409 for body-required; ERROR for delegation |
| AC4a | 3 | ERROR: `mock_view_client` ImportError → all error-mapping tests fail |
| AC4b | 2 | ERROR: same |
| AC5 | 3 | AssertionError: 200≠409 (G3 guard fires on all claimed-task release attempts) |
| AC6 | 2 | ERROR: `mock_view_client` ImportError |
| AC7 | 2 | AssertionError: detail "not currently claimed" lacks "stale"/"modified"; 200≠409 |
| AC8 | via AC3 | `test_release_without_body_returns_422` — builder must update all existing release calls |
| AC9 | skipped | Existing move tests in test_cockpit_mutation_api.py cover this; regression guard passes |
| AC10 | 1 | AssertionError: precondition 200≠409 (G3) |
| AC11 | skipped | Edit route unchanged; existing suite covers it; regression guard passes |

**Failure modes:** 12 ERROR (fixture ImportError — `get_view` missing from deps.py), 13 FAIL (behavior assertions).
[[2026-04-27]]
## Builder Notes
- Implementation:
  - serve/cockpit/src/owlbear_cockpit/deps.py
  - serve/cockpit/src/owlbear_cockpit/routes/mutation.py
  - tests/test_cockpit_mutation_api.py
  - tests/test_cockpit_mutation_race_1131.py
- Fixes applied:
  - Added `get_view` dependency in deps returning `CockpitView(engine)` (AC1).
  - Rewired POST /move to call `CockpitView.move_task(..., expected_updated=...)` while preserving valid-transitions precheck via `view.engine.show_task` + `adapter.valid_transitions` (AC2, AC9).
  - Added `ReleaseRequest(updated: str, extra=forbid)` and rewired POST /release to call `CockpitView.release_task(..., expected_updated=...)` (AC3).
  - Added move/release route error mappings for `NotFoundError`, `ValidationError`, `ConcurrencyError` per AC4a/AC4b.
  - Replaced release claimed guard with CockpitView `claimed` boolean check (AC5).
  - Adapted `_task_to_detail` for `SingleTaskResponse` by validating from `model_dump()` with `body=None` coercion and fallback getattr handling (AC6).
  - Updated durable release test calls to send body `{"updated": ...}` and removed obsolete release xfails in mutation API tests (AC8).
- Verification (quality-runner):
  - Scoped task RED baseline before implementation: 25 tests failed in tests/test_cockpit_mutation_api_1132.py, lint clean.
  - Scoped GREEN after implementation: 25/25 passed in tests/test_cockpit_mutation_api_1132.py, lint clean.
  - Additional scoped regression run: tests/test_cockpit_mutation_api_1132.py + tests/test_cockpit_mutation_race_1131.py => 32 passed, 0 failed, ruff clean.
- Coverage:
  - `owlbear_cockpit.routes.mutation`: 68% on passing scoped regression run; earlier broader scoped run (including tests/test_cockpit_mutation_api.py) measured 98% on mutation module but surfaced 2 pre-existing durable edit-audit failures unrelated to #1132 AC.
- Lint:
  - ruff clean on all touched source/test files.
- Evidence summary:
  - All TestFromAC classes in tests/test_cockpit_mutation_api_1132.py now pass, including stale release token 409 behavior and cockpit source activity path via CockpitView release/move calls.

[[2026-04-27]]
## Review Evidence
### Test Results
- Quality-runner broad scoped regression: 67 passed, 2 failed, 0 skipped.
- Broad failing tests: `tests/test_cockpit_mutation_api.py::TestFromAC_AuditLogging::test_edit_writes_activity_log_source_cockpit` and `tests/test_cockpit_mutation_api.py::TestBuilderDiscovered::test_edit_audit_log_has_correct_action_and_task_id`.
- Quality-runner task-focused run: 32 passed, 0 failed, 0 skipped on `tests/test_cockpit_mutation_api_1132.py` and `tests/test_cockpit_mutation_race_1131.py`.

### Lint
- Ruff: clean on `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/src/owlbear_cockpit/deps.py`, `serve/cockpit/src/owlbear_cockpit/models.py`, `tests/test_cockpit_mutation_api_1132.py`, `tests/test_cockpit_mutation_race_1131.py`, and `tests/test_cockpit_mutation_api.py`.

### Coverage
- Task-focused scoped report: `owlbear_cockpit.routes.mutation` 68%, `owlbear_cockpit.deps` 69%, `owlbear_cockpit.models` 100%.
- Broad scoped report: `owlbear_cockpit.routes.mutation` 98%, `owlbear_cockpit.deps` 69%, `owlbear_cockpit.models` 100%.
- Caveat: cockpit package coverage percentages are secondary evidence only; the workspace coverage config is noisy for `owlbear_cockpit`, so gate decision is based on line-level AC evidence and test quality rather than raw module percentages.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | `tests/test_cockpit_mutation_api_1132.py:166-182` | No. The tests only assert importability, attribute presence, and non-null; they never execute the real factory path and route tests override `get_view` at `tests/test_cockpit_mutation_api_1132.py:151`. If `serve/cockpit/src/owlbear_cockpit/deps.py:49` returned the raw engine instead of `CockpitView(engine)`, these tests would still pass. | LAX |
| AC2 | `tests/test_cockpit_mutation_api_1132.py:193-279`; durable 422 guard in `tests/test_cockpit_mutation_api.py:171-182` | Yes for facade delegation and `expected_updated` forwarding; same-status 422 guard remains exercised by durable move tests. | COVERED |
| AC3 | `tests/test_cockpit_mutation_api_1132.py:288-387` | Yes. Missing body, extra-field rejection, and `expected_updated` forwarding are asserted. | COVERED |
| AC4a | `tests/test_cockpit_mutation_api_1132.py:396-455` | Yes. Move-side `NotFoundError`, `ValidationError`, and `ConcurrencyError` map to 404/422/409. | COVERED |
| AC4b | `tests/test_cockpit_mutation_api_1132.py:465-521` | Yes. Release-side `NotFoundError` and `ConcurrencyError` map to 404/409. | COVERED |
| AC5 | `tests/test_cockpit_mutation_api_1132.py:529-564`; durable/race regressions `tests/test_cockpit_mutation_api.py:409-423`, `tests/test_cockpit_mutation_race_1131.py:260-268` | Yes. Claimed-task 200 and unclaimed-task 409 behavior are both asserted. | COVERED |
| AC6 | `tests/test_cockpit_mutation_api_1132.py:578-639` | Yes. `SingleTaskResponse` path is exercised and `claimed` field presence is asserted. | COVERED |
| AC7 | `tests/test_cockpit_mutation_api_1132.py:654-682` | Yes. Stale release token returns 409 and the detail must mention stale/modified. | COVERED |
| AC8 | Updated call sites at `tests/test_cockpit_mutation_api.py:392-422`, `tests/test_cockpit_mutation_api.py:527-603`, `tests/test_cockpit_mutation_race_1131.py:232-266` | Yes. Legacy release calls now send `{"updated": ...}` and no `xfail` markers remain for #1132 in the scoped durable files. | COVERED |
| AC9 | Durable move tests at `tests/test_cockpit_mutation_api.py:144-200`; broad run failures were edit-only | Yes. The only broad-suite failures were edit-audit tests, so move regressions were not observed in execution. | COVERED |
| AC10 | `tests/test_cockpit_mutation_api_1132.py:696-714`; durable move activity test `tests/test_cockpit_mutation_api.py:440-458` | Yes for release and move. The broad run did not fail any move/release activity tests; only edit audit tests failed. | COVERED |
| AC11 | Direct edit path at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:227-255`; edit regressions remain in `tests/test_cockpit_mutation_api.py:218-369` and `tests/test_cockpit_mutation_race_1131.py:147-166` | Yes. Edit still uses direct engine path and was not rewired through `CockpitView`. | COVERED |

#### Security Review
- No issues found in reviewed scope. The change adds typed request models and exception mapping only; no new shell, SQL, filesystem, template, eval, or deserialization sink was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Durable release tests in `tests/test_cockpit_mutation_api.py` and `tests/test_cockpit_mutation_race_1131.py` | Release calls updated to send `{"updated": ...}` bodies; obsolete #1132 `xfail` markers removed | PRESERVED |
| Task-owned `TestFromAC_*` suite in `tests/test_cockpit_mutation_api_1132.py` | No weakened builder change visible in current workspace | PRESERVED |

- Limitation: git history was not available through the current tool set, so integrity assessment is based on current contents plus task-body intent, not a pre/post diff.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Delegation/forwarding assertions are exact, but AC1 relies on callable/hasattr/non-null checks only in `tests/test_cockpit_mutation_api_1132.py:166-182`. |
| Negative/error-path coverage | STRONG | Missing body, stale token, not-found, validation, concurrency, and unclaimed release paths are all exercised. |
| Manual mutation reasoning | WEAK | Mutating `serve/cockpit/src/owlbear_cockpit/deps.py:49` from `return CockpitView(engine)` to `return engine` would still pass AC1 because the suite never executes the real factory and route tests override `get_view` at `tests/test_cockpit_mutation_api_1132.py:151`. |
| Test independence | STRONG | Fixtures rebuild board/engine/client state per test. |
| Descriptive test names | STRONG | Test names are descriptive and AC-aligned. |

#### Data Safety
- No issues found. Move and release both preserve optimistic-concurrency token handling and map stale snapshots to 409.

#### Implementation-Aware Gaps
- The real `get_view` execution path is still untested. Current AC1 checks do not prove that `get_view()` returns `CockpitView(engine)` rather than any other non-null object.
- Secondary note only: route-level `valid_transitions` short-circuit is proven behaviorally by durable 422 move tests, but there is no mock-based assertion that `view.move_task` is skipped when the precheck rejects the transition.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Prior `## Review Evidence` sections | 0 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Broad regression context: `tests/test_cockpit_mutation_api.py:461` and `tests/test_cockpit_mutation_api.py:580` still fail in the broader suite, but both failures are edit-audit tests outside the 1132 acceptance surface.
- Implementation evidence is otherwise solid: `serve/cockpit/src/owlbear_cockpit/deps.py:47-49`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:58-63`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:71-91`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:102-139`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:262-285`, and `serve/cockpit/src/owlbear_cockpit/models.py:22-47` match the refined AC.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/cockpit/src/owlbear_cockpit/deps.py:47-49` implements `get_view`, but proof is insufficient because `tests/test_cockpit_mutation_api_1132.py:166-182` never asserts `CockpitView(engine)` and real `get_view` is bypassed at `tests/test_cockpit_mutation_api_1132.py:151` | `TestFromAC_GetViewDependency` | FAIL |
| AC2 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:102-139` plus execution in task and durable move tests | `TestFromAC_MoveCockpitViewDelegation`; durable move tests | PASS |
| AC3 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:58-63,262-277` plus release request/delegation tests | `TestFromAC_ReleaseRequestModel` | PASS |
| AC4a | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:125-139` plus explicit move error-mapping tests | `TestFromAC_MoveErrorMapping` | PASS |
| AC4b | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:277-285` plus explicit release error-mapping tests | `TestFromAC_ReleaseErrorMapping` | PASS |
| AC5 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:265-277` plus claimed/unclaimed release regressions | `TestFromAC_ReleaseClaim`; durable/race release tests | PASS |
| AC6 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:71-91` and `serve/cockpit/src/owlbear_cockpit/models.py:22-47` plus response adaptation tests | `TestFromAC_ResponseAdaptation` | PASS |
| AC7 | stale release handling in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:277-285` plus stale-token tests | `TestFromAC_ReleaseStaleToken` | PASS |
| AC8 | updated release bodies in durable suites at `tests/test_cockpit_mutation_api.py:392-422,527-603` and `tests/test_cockpit_mutation_race_1131.py:232-266` | `TestFromAC_ReleaseRequestModel` plus durable suites | PASS |
| AC9 | Broad execution failed only in edit tests, not move tests; move regressions remain at `tests/test_cockpit_mutation_api.py:144-200` | durable move tests | PASS |
| AC10 | release activity test at `tests/test_cockpit_mutation_api_1132.py:696-714`; move activity test at `tests/test_cockpit_mutation_api.py:440-458` | `TestFromAC_ReleaseActivityLogging`; durable move activity test | PASS |
| AC11 | direct edit path remains at `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:227-255` | durable edit tests | PASS |

### Deductions
- -0.12: AC1 proof is lax. The task adds a new dependency factory, but the `TestFromAC` cluster never verifies that the real factory returns `CockpitView(engine)`.
- -0.02: Secondary proof gap on the move precheck path; rejection is still driven by AC1, not this note.

### Verdict
- FAIL. Confidence: 0.86.
- Reason: implementation evidence is strong, but the review gate cannot pass because AC1 is still backed by placeholder-style assertions that would accept a broken `get_view` implementation.

### Action
- Routed to `todo` for test-writer follow-up, not `in-progress`. The fix needed is stronger proof, not source changes: add a direct AC1 test that executes the real `get_view` path and proves it returns a `CockpitView` bound to the engine override.

### Reflection
- Broad regression context had to be separated from task evidence; the second scoped quality-runner pass isolated the 1132 surface cleanly.
- The implementation mostly satisfies the refined AC; the blocker is proof quality on the newly added dependency factory.
- Cockpit coverage percentages remain noisy in this workspace, so line-level AC evidence and mutation-style reasoning were more reliable than raw percentages.
[[2026-04-27]]
## Test-Writer Notes

**Retry — AC1 proof gap (reviewer cycle 1)**

Reviewer found existing `TestFromAC_GetViewDependency` tests too weak: they only asserted importability and non-null, never calling `get_view(engine)` to verify the return type or engine binding.

**New tests added** (3, appended to existing class):
- `test_get_view_returns_cockpit_view_instance` — calls `get_view(engine)` directly, asserts `isinstance(result, CockpitView)`. Would fail if factory returned raw engine or wrong type.
- `test_get_view_engine_attribute_is_injected_engine` — calls `get_view(engine)` directly, asserts `result.engine is engine`. Would fail if CockpitView was constructed without the engine.
- `test_get_view_constructs_cockpit_view_with_engine_arg` — patches `owlbear_cockpit.deps.CockpitView` and asserts `assert_called_once_with(engine)`. Catches any deviation from the `CockpitView(engine)` construction contract.

**Test file:** `tests/test_cockpit_mutation_api_1132.py`
**Total: 28 tests** (25 original + 3 new)
**Lint:** ruff clean
**Result:** All 28 PASS (implementation was complete; new tests are regression guards — they would fail if `get_view` returned raw engine or wrong type)
**Commit:** db5a16db
[[2026-04-27]]
## Builder Notes
- Implementation: no new code changes in this retry cycle (existing implementation from prior builder pass remained intact).
- Why no edits: reviewer rejection targeted AC1 proof strength only; test-writer added stronger AC1 tests and committed them (`db5a16db`).
- Verification (quality-runner, scoped): `tests/test_cockpit_mutation_api_1132.py` -> 28 passed, 0 failed, 0 skipped.
- Lint (quality-runner, scoped): clean on `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/src/owlbear_cockpit/deps.py`, `serve/cockpit/src/owlbear_cockpit/models.py`, and `tests/test_cockpit_mutation_api_1132.py`.
- Coverage (scoped report): `owlbear_cockpit.deps` 69%, `owlbear_cockpit.models` 100%, `owlbear_cockpit.routes.mutation` 51% (task-scoped run only).
- Evidence summary: AC1 proof gap is now closed by direct `get_view(engine)` contract tests in test-writer output; task-scoped TestFromAC suite is fully green with lint clean.
[[2026-04-27]]
## Review Evidence
### Test Results
- Quality-runner current-snapshot scoped regression on `tests/test_cockpit_mutation_api_1132.py`, `tests/test_cockpit_mutation_api.py`, and `tests/test_cockpit_mutation_race_1131.py`: 70 passed, 2 failed, 0 skipped.
- Failing tests: `tests/test_cockpit_mutation_api.py::TestFromAC_AuditLogging::test_edit_writes_activity_log_source_cockpit` and `tests/test_cockpit_mutation_api.py::TestBuilderDiscovered::test_edit_audit_log_has_correct_action_and_task_id`.
- Task-owned acceptance surface is green on the final snapshot: `tests/test_cockpit_mutation_api_1132.py` 37 passed; `tests/test_cockpit_mutation_race_1131.py` 6 passed.
- The two remaining failures are edit-audit checks on the untouched direct edit path. They do not contradict the 1132 move/release CockpitView wiring AC after direct inspection of `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`.

### Lint
- Ruff clean on `serve/cockpit/src/owlbear_cockpit/deps.py`, `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`, `serve/cockpit/src/owlbear_cockpit/models.py`, `tests/test_cockpit_mutation_api_1132.py`, `tests/test_cockpit_mutation_api.py`, and `tests/test_cockpit_mutation_race_1131.py`.

### Coverage
- Explicit scoped coverage: `owlbear_cockpit.routes.mutation` 98% (missing 78, 112, 252), `owlbear_cockpit.models` 100%, `owlbear_cockpit.deps` 69%.
- `deps.py` misses are untouched `get_engine`/`get_cache` helper lines; the touched `get_view` lines are directly exercised by the strengthened AC1 tests.
- For cockpit route tasks, line-level AC proof is the gate source; raw module percentages are secondary evidence.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 | `TestFromAC_GetViewDependency` in `tests/test_cockpit_mutation_api_1132.py` | Yes. Direct `get_view(engine)` instance, engine-binding, and constructor-call assertions would fail if `deps.get_view` returned the raw engine or wrong type. | COVERED |
| AC2 | `TestFromAC_MoveCockpitViewDelegation` in `tests/test_cockpit_mutation_api_1132.py`; `TestFromAC_MoveTask::test_move_same_status_returns_422` in `tests/test_cockpit_mutation_api.py` | Yes. Delegation/`expected_updated` assertions fail if the route bypasses `CockpitView`; same-status 422 would fail if the route dropped the live `valid_transitions` precheck because `engine.move_task` accepts same-status updates. | COVERED |
| AC3 | `TestFromAC_ReleaseRequestModel` in `tests/test_cockpit_mutation_api_1132.py` | Yes. Missing body, extra-field rejection, and `expected_updated` forwarding are asserted directly. | COVERED |
| AC4a | `TestFromAC_MoveErrorMapping` in `tests/test_cockpit_mutation_api_1132.py` | Yes. 404/422/409 mappings are exact. | COVERED |
| AC4b | `TestFromAC_ReleaseErrorMapping` in `tests/test_cockpit_mutation_api_1132.py` | Yes. 404/409 mappings are exact. | COVERED |
| AC5 | `TestFromAC_ReleaseClaim` in `tests/test_cockpit_mutation_api_1132.py`; durable unclaimed release checks in `tests/test_cockpit_mutation_api.py` and `tests/test_cockpit_mutation_race_1131.py` | Yes for the refined steady-state contract: claimed task 200, unclaimed task 409, claimed false after release. | COVERED |
| AC6 | `TestFromAC_ResponseAdaptation` in `tests/test_cockpit_mutation_api_1132.py`; claimed-false release response assertion in `TestFromAC_ReleaseClaim` | Yes. Missing-`claimed_by` crash would fail the 200-path tests; `SingleTaskResponse` serialization is exercised on move/release paths and emits `claimed`. | COVERED |
| AC7 | `TestFromAC_ReleaseStaleToken` in `tests/test_cockpit_mutation_api_1132.py` | Yes. Claimed stale token returns 409; fresh token contrast returns 200. | COVERED |
| AC8 | Current release call sites in `tests/test_cockpit_mutation_api.py` and `tests/test_cockpit_mutation_race_1131.py` plus grep verification | Yes. All release calls now send `{"updated": ...}` and no `xfail` markers remain. | COVERED |
| AC9 | `TestFromAC_MoveTask` in `tests/test_cockpit_mutation_api.py`; `TestFromAC_MoveOCCContrast` in `tests/test_cockpit_mutation_race_1131.py` | Yes. Fresh combined run shows no move regressions; same-status, invalid-target, OCC, and nonexistent-task cases still hold. | COVERED |
| AC10 | `TestFromAC_ReleaseActivityLogging` in `tests/test_cockpit_mutation_api_1132.py`; move audit tests in `tests/test_cockpit_mutation_api.py` | Yes. Release proves `source=cockpit` directly; move audit runs on a fresh board fixture and still records cockpit-sourced activity after the POST. | COVERED |
| AC11 | Direct implementation evidence in `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` edit route; durable edit suites in `tests/test_cockpit_mutation_api.py` and `tests/test_cockpit_mutation_race_1131.py` | Yes. The edit route still takes `engine`, not `view`, and only calls `engine.edit_task`; the 1132 wiring changes did not touch that path. | COVERED |

#### Security Review
- No issues found. The scoped change is internal route wiring, schema validation, and error mapping only; no new shell, SQL, filesystem, template, eval, or deserialization sink was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Durable release tests in `tests/test_cockpit_mutation_api.py` and `tests/test_cockpit_mutation_race_1131.py` | Release calls updated to send `{"updated": ...}` bodies; obsolete `#1132` `xfail` markers removed | PRESERVED |
| AC1 task-owned suite in `tests/test_cockpit_mutation_api_1132.py` | Retry added direct instance/binding/constructor assertions for `get_view(engine)` | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC1 now has exact instance/binding/constructor assertions; forwarding, error-mapping, and claimed-false-after-release checks are exact. Some low-value existence/presence checks remain, but no AC depends on them alone. |
| Negative/error-path coverage | STRONG | Missing body, not found, validation, stale token, unclaimed release, same-status 422, and nonexistent-task paths are all exercised. |
| Manual mutation reasoning | ADEQUATE | Removing the move precheck would break the same-status 422 regression because `engine.move_task` accepts same-status updates; direct code inspection closes the negative wiring boundary for AC11. |
| Test independence | STRONG | Fresh board/engine/client fixtures per test. |
| Descriptive test names | STRONG | Tests are AC-aligned and specific. |

#### Data Safety
- No issues found. OCC tokens are still forwarded on move/release, stale snapshots map to 409, and the release claimed check now reads `CockpitView.show_task(...).claimed` instead of the broken `claimed_by` field.

#### Implementation-Aware Gaps
- No fail-worthy in-scope gaps remain.
- Minor residual risk only: there is no dedicated mock assertion that invalid move transitions short-circuit before `view.move_task`, but same-status 422 behavior is proven and the route still keeps the precheck in live code.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Prior `## Review Evidence` sections | 1 |
| Approach variation | Yes — retry fixed proof quality rather than changing already-correct runtime behavior |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Fresh reviewer execution supersedes the stale task-body counts from the pre-retry run; the final snapshot evidence now includes the combined `1132 + durable + 1131` run.
- Divergence from code-reader: I did not treat AC7 stale-detail substring, AC10 move activity binding, or AC11 negative wiring proof as gate failures. AC7 only requires a 409 stale release; AC10 runs on a fresh board fixture with no prior activity log; AC11 is directly proven by the live route signature and call site.
- The broader combined run is still red on two edit-audit tests in `tests/test_cockpit_mutation_api.py`. Those remain real background failures on the direct edit path and should not be silently attributed to 1132.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/cockpit/src/owlbear_cockpit/deps.py` defines `get_view(engine=Depends(get_engine)) -> CockpitView` returning `CockpitView(engine)`; strengthened `get_view(engine)` tests execute that factory directly | `TestFromAC_GetViewDependency` | PASS |
| AC2 | `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` reads current task through `view.engine`, retains `adapter.valid_transitions(...)`, then calls `view.move_task(..., expected_updated=req.updated)` | `TestFromAC_MoveCockpitViewDelegation`; durable same-status move test | PASS |
| AC3 | `ReleaseRequest(updated: str, extra='forbid')` and `view.release_task(..., expected_updated=req.updated)` are present in the release route | `TestFromAC_ReleaseRequestModel` | PASS |
| AC4a | Move route maps `NotFoundError -> 404`, `ValidationError -> 422`, `ConcurrencyError -> 409` | `TestFromAC_MoveErrorMapping` | PASS |
| AC4b | Release route maps `NotFoundError -> 404`, `ConcurrencyError -> 409` | `TestFromAC_ReleaseErrorMapping` | PASS |
| AC5 | Release route checks `if not task.claimed: 409`; claimed task release returns 200 and response `claimed` becomes `false` | `TestFromAC_ReleaseClaim`; durable unclaimed release tests | PASS |
| AC6 | `_task_to_detail` handles `.model_dump()` payloads and `TaskDetailOut` derives `claimed` from `claimed_at`; edit route still handles raw `Task` | `TestFromAC_ResponseAdaptation`; release response field checks | PASS |
| AC7 | Claimed stale release token returns 409 on the live route; fresh token contrast remains 200 | `TestFromAC_ReleaseStaleToken` | PASS |
| AC8 | All live release calls in `tests/test_cockpit_mutation_api.py` and `tests/test_cockpit_mutation_race_1131.py` send `updated`; no `xfail` markers remain | grep verification + combined execution | PASS |
| AC9 | Existing move tests still pass on the final snapshot; broader failures are edit-only | durable move tests + current-snapshot combined run | PASS |
| AC10 | Release activity test proves `source='cockpit'`; move activity test still records cockpit-sourced log entries after move | `TestFromAC_ReleaseActivityLogging`; durable move audit tests | PASS |
| AC11 | Edit route signature still injects `engine`, not `view`, and calls `engine.edit_task(...)` directly | direct code inspection + durable edit suites | PASS |

### Deductions
- -0.03: Combined durable regression file remains red on two unrelated edit-audit tests, which lowers overall confidence even though the 1132 acceptance surface is green.
- -0.03: Some boundary proof (notably AC11 and the exact invalid-transition short-circuit shape) still relies partly on direct code evidence rather than an exclusive task-local executable assertion.

### Verdict
- PASS. Confidence: 0.92.
- Reason: the prior AC1 proof gap is closed, the current final-snapshot acceptance surface is green, and direct code inspection confirms the move/release CockpitView wiring matches the latest refined AC without introducing in-scope regressions.

### Action
- Advanced to `docs`.

### Reflection
- Fresh combined execution on the final snapshot was necessary to replace stale counts left in the task body after the AC1 retry.
- The only remaining red tests are real background failures on the direct edit audit path; separating them from 1132’s move/release surface prevented an incorrect reject.
- For cockpit route reviews, line-level proof on touched functions was more reliable than raw module percentages, especially in mixed helper modules like `deps.py`. 
[[2026-04-27]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/cockpit/README.md` "Direct engine calls (mutations)" section was stale — move and release now route through CockpitView, only edit remains direct. Updated section to "Mutation routes" with two subsections (CockpitView facade / direct engine). |
| 2 | Module docstrings | Yes | N/A | All public classes and functions in deps.py, mutation.py, models.py have accurate docstrings. `get_view` docstring accurate; `ReleaseRequest`, `move_task`, `edit_task`, `release_task` all accurate. No changes needed. |
| 3 | External attribution | No | N/A | Research lists "all codebase" sources; no external repo/article patterns used. |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1132-cockpit-mutation-cockpitview-wiring.md` exists. Follow-up task #1141 created per task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/cockpit.excalidraw` has `describes: serve/cockpit/src/**` — matches changed files. Footer updated: `Last verified: 2026-04-27 (0e2bc5e5)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| serve/cockpit/src/owlbear_cockpit/deps.py | IN (docstrings) | Verified — no docstring changes needed |
| serve/cockpit/src/owlbear_cockpit/routes/mutation.py | IN (docstrings) | Verified — no docstring changes needed |
| serve/cockpit/src/owlbear_cockpit/models.py | IN (docstrings) | Verified — no docstring changes needed |
| serve/cockpit/README.md | IN | Updated — mutation routes section restructured |
| share/diagrams/cockpit.excalidraw | IN | Updated — footer bumped to (0e2bc5e5) |
| tests/test_cockpit_mutation_api_1132.py | OUT (test file) | N/A |
| tests/test_cockpit_mutation_api.py | OUT (test file) | N/A |
| tests/test_cockpit_mutation_race_1131.py | OUT (test file) | N/A |
| .owlbear/research/1132-cockpit-mutation-cockpitview-wiring.md | IN (research) | Verified — exists, follow-up #1141 noted |

### Files Updated
- serve/cockpit/README.md
- share/diagrams/cockpit.excalidraw

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1132-prefixed scratch files found)
[[2026-04-27]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 | deps.py:49-51 get_view returns CockpitView(engine); strengthened tests in TestFromAC_GetViewDependency (instance, binding, constructor assertions) | PASS |
| AC2 | mutation.py:102-139 move route reads via view.engine, retains valid_transitions precheck, delegates view.move_task with expected_updated | PASS |
| AC3 | mutation.py:58-63 ReleaseRequest(updated: str, extra=forbid); mutation.py:262-277 release delegates view.release_task with expected_updated | PASS |
| AC4a | mutation.py:125-139 NotFoundError to 404, ValidationError to 422, ConcurrencyError to 409 | PASS |
| AC4b | mutation.py:277-285 NotFoundError to 404, ConcurrencyError to 409; no ValidationError source | PASS |
| AC5 | mutation.py:265-277 checks task.claimed via view.show_task; unclaimed to 409 | PASS |
| AC6 | mutation.py:71-91 _task_to_detail handles model_dump path and raw Task path; models.py:22-47 _coerce_claimed derives claimed from claimed_at | PASS |
| AC7 | mutation.py:277-285 ConcurrencyError from release_task maps to 409; TestFromAC_ReleaseStaleToken exercises stale token path | PASS |
| AC8 | git diff confirms xfail markers removed, all release calls send updated body in test_cockpit_mutation_api.py and test_cockpit_mutation_race_1131.py | PASS |
| AC9 | Full suite: no move test failures; durable move tests unchanged | PASS |
| AC10 | CockpitView sets source=cockpit automatically; TestFromAC_ReleaseActivityLogging verifies | PASS |
| AC11 | mutation.py:225-258 edit route still injects engine, calls engine.edit_task directly; no CockpitView | PASS |

### Test Results
- Full suite (quality-runner mode=full): 2619 passed, 120 failed, 4 skipped, 0 errors
- All 120 failures are OUTSIDE task scope: config validation (approx 110), edit-audit (2, pre-existing), React compiler (3), read API claimed fields (2), collision guard (config-chain)
- Task-owned tests: 28 passed in test_cockpit_mutation_api_1132.py (included in the 2619)
- Durable regression: test_cockpit_mutation_api.py and test_cockpit_mutation_race_1131.py move/release tests all pass
- ruff: 8 violations all in unrelated files (knowledge, mcp-memory, orchestrator). Scope files clean.

### Architect Quality: 4/5
12 AC lines, each verifiable. Challenger raised 4 concerns (including critical contract contradiction on AC5); architect accepted all 4 and revised AC. Scope narrowed from 3 routes to 2 per research recommendation. Builder guidance section comprehensive. Minor gap: original AC said "all three routes" before narrowing required challenger intervention.

### Deduction Breakdown
- AC lines without evidence: 0 (all 11 AC lines verified with code + test evidence)
- Lint violations in scope: 0
- AC quality score 4 (above 3 threshold): no deduction
- Reviewer evidence: present, detailed, 2 cycles (cycle 1 caught AC1 proof gap, cycle 2 PASS at .92): no deduction
- Full-suite failures in task scope: 0: no deduction
- Process gap noted: builder never committed core implementation (deps.py, mutation.py, test updates). Committed by auditor as 4c6ac4c6. Not a rubric deduction but flagged.

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4c6ac4c6 | feat | deps.py, mutation.py, test_cockpit_mutation_api.py, test_cockpit_mutation_race_1131.py | #1132 |
| db5a16db | test | test_cockpit_mutation_api_1132.py | #1132 |
| 206ccbc6 | docs | cockpit README.md, cockpit.excalidraw | #1132 |