---
id: 1131
title: Add cockpit mutation route OCC characterization tests
status: in-progress
priority: important
created: 2026-04-26T15:37:53.908968+00:00
updated: 2026-04-27T03:33:21.039708+00:00
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
Objective: Add GREEN characterization tests documenting OCC behavior and structural gaps in cockpit mutation HTTP routes (mutation.py). Tests characterize current behavior; follow-up fix tasks #1134, #1136 address the underlying issues. Note: #1135 (move OCC token) needs re-evaluation — the move route already has OCC (see Key Findings).

Acceptance Criteria:
- [ ] AC1 (Edit TOCTOU — G1): In `tests/test_cockpit_mutation_race_1131.py`, add a test that patches `engine.edit_task` via `unittest.mock.patch.object`, sends a valid edit request through the cockpit HTTP route, and asserts `expected_updated` is NOT in the captured call kwargs. Proves the edit route never engages the engine CAS — it performs only a precheck (`req.updated != str(task.updated)`) before calling `engine.edit_task(**kwargs)` without `expected_updated` (mutation.py L209).
- [ ] AC2 (Move OCC contrast): Add a test that patches `engine.move_task` via `unittest.mock.patch.object`, sends a valid move request (including task's current `updated` value from a prior `show_task`) through the cockpit HTTP route, and asserts `expected_updated` IS present in the captured call kwargs with the correct value. Proves the move route, unlike the edit route (AC1), forwards the OCC token to the engine (mutation.py L108).
- [ ] AC3 (Release guard broken on new-schema — G3): Add a test that claims a task via `engine.claim_task` (writing `claimed_at` to disk), then sends `POST /api/tasks/{id}/release` through the cockpit HTTP route, and asserts 409 with detail `"Task {id} is not currently claimed"` (with actual task ID). Proves the release route's `if not task.claimed_by` guard (mutation.py L237) is broken on new-schema boards because `claimed_by` has `Field(exclude=True)` in models.py — it is never persisted to disk, so `show_task` always returns `claimed_by=None` even when `claimed_at` is set. No mocking required — this tests the live route behavior.
- [ ] AC4 (409 detail stability): Assert exact 409 detail strings: (a) edit with stale `updated` → `"Task was modified since your last load (stale snapshot)"`, (b) release on truly unclaimed task → `"Task {id} is not currently claimed"` (with actual task ID). Complements existing status-code-only tests in `test_cockpit_mutation_api.py`.
- [ ] AC5 (Schema baseline): For move and edit routes returning 200, assert all 14 `TaskDetailOut` JSON keys: `id`, `title`, `status`, `priority`, `body`, `updated`, `created`, `tags`, `blocked`, `block_reason`, `parent`, `depends_on`, `claimed`, `claimed_by`. No release 200 schema test — the release 200 path is unreachable on new-schema boards due to G3 (AC3).

Likely files:
- tests/test_cockpit_mutation_race_1131.py (rewrite — prior implementation had stale premises)

## Builder Guidance
- Tests are GREEN characterization tests — they pass against current code without production changes
- Reuse fixture pattern from `tests/test_cockpit_mutation_api.py` (board_dir → engine → client via DI override)
- **Prior test file exists and must be rewritten.** The cycle 1 implementation had stale premises: move body missing `updated` (causing 422), and release tests mocking impossible state.
- For AC1 (edit proof): wrap `engine.edit_task` with `unittest.mock.patch.object(wraps=...)`, call the edit route with valid `{updated, title}`, inspect captured kwargs — `expected_updated` must be absent
- For AC2 (move contrast): wrap `engine.move_task` with `unittest.mock.patch.object(wraps=...)`, call the move route with valid `{status, updated}`, inspect captured kwargs — `expected_updated` must be present and match the `updated` value sent
- For AC3 (release proof): claim task via engine (`engine.claim_task("1")`), call release route — expect 409. No mocking needed. The route reads `task.claimed_by` which is always None after disk round-trip; the engine uses `claimed_at` which IS persisted.
- `MoveRequest` requires both `status: str` and `updated: str` — omitting `updated` returns 422 (Pydantic validation)
- `TaskDetailOut.claimed` is derived from `claimed_at` by `_coerce_claimed` validator, but `_task_to_detail()` never passes `claimed_at` — so `claimed` is always False in responses. This is expected current behavior.
- `claimed_by` is always None in responses — `Field(exclude=True)` in Task model means it's never in YAML; `_task_to_detail` reads `task.claimed_by` which is None after round-trip
- **CockpitView context:** `CockpitView` (engine.py L3049+) is a tested wrapper that correctly handles all three operations: edit with `expected_updated`, move with `expected_updated`, release via `claimed_at`. The HTTP routes bypass this wrapper and implement their own (broken) logic. Follow-up fix tasks likely need to wire routes through CockpitView.

## Key Findings (corrected from cycle 1)
Two confirmed OCC gaps in cockpit mutation routes, one false positive:
- G1 (confirmed): Edit route precheck-only TOCTOU — engine CAS never engaged (`expected_updated` not passed to `engine.edit_task`)
- G2 (RETRACTED): Move route DOES have OCC — `MoveRequest` has `updated: str` field, route forwards `expected_updated=req.updated` to `engine.move_task`. Original research incorrectly stated move had no OCC.
- G3 (confirmed, reframed): Release route guard uses `task.claimed_by` (never persisted, always None) instead of `task.claimed_at` (persisted by engine). Route is completely broken on new-schema boards — always returns 409 even for claimed tasks.

Follow-up tasks: #1134 (edit CAS fix, valid), #1135 (move OCC token — needs re-evaluation since move already has OCC), #1136 (release ownership check, valid)

## Cycle 1 Summary
Cycle 1 (research → backlog → todo → in-progress → review → FAIL) identified:
- AC2 premise was stale — built on false G2 claim that move had no OCC
- AC3/AC5c tests mocked impossible persisted state instead of testing real behavior
- 2/8 tests failed (move tests sent invalid request bodies missing `updated`)
- Reviewer confidence: 0.34 → rejected to backlog
- Full cycle notes preserved in git history
[[2026-04-26]]
## Architecture Review (cycle 2)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests-only task covering one domain (cockpit mutation route OCC characterization) |
| Interface clarity | PASS | All 5 AC lines specify exact test patterns, assertions, mock targets, and source line references |
| Dependency correctness | PASS | No dependencies — standalone test task |
| Module layering | PASS | Test file imports only cockpit app and kanban engine |
| TDD compliance | N/A | This IS the test task — GREEN characterization tests, no RED phase |
| KISS/YAGNI | PASS | Minimal scope: 2 gap proofs (G1, G3) + 1 contrast test (AC2) + 2 assertion-tightening ACs |
| Premise challenge | PASS | G1 confirmed (edit route L209 omits expected_updated). G2 RETRACTED (MoveRequest has `updated`, route forwards CAS at L108). G3 confirmed and reframed (route guards on `claimed_by` which is `exclude=True`, always None). CockpitView (L3049+) correctly handles all three operations — routes bypass it. |
| Pattern consistency | PASS | Follows existing test_cockpit_mutation_api.py fixture pattern |
| Security surface | N/A | Tests only |
| Single domain | PASS | Cockpit mutation routes only |

### Changes from cycle 1
- Retracted G2 (move "no OCC") — live MoveRequest has `updated: str`, route forwards `expected_updated`
- Reframed G3 from "actor-agnostic" to "claimed_by guard broken on new-schema boards"
- Rewrote AC2: now proves move DOES forward CAS (contrast with AC1's edit gap)
- Rewrote AC3: proves live route behavior without mocking — claim via engine, release via cockpit → 409
- Dropped AC5c (release 200 schema) — unreachable on new-schema boards due to G3
- Added CockpitView context to builder guidance — routes bypass the tested wrapper
- Flagged #1135 for re-evaluation (move already has OCC)

### Challenge Results
- Challenger: block (confidence: 0.46)
- Concerns: (1) stale body artifact — procedural, fixed by body rewrite; (2) move OCC overclaim — acknowledged, AC2 is deliberately narrow structural contrast; (3) release root-cause chain — addressed in builder guidance with CockpitView reference; (4) schema baseline false-green — AC5 explicitly key-presence only, semantic issues documented; (5) CockpitView blind spot — accepted, added to builder guidance; (6) research artifact contradiction — historical, corrected in Key Findings
- Architect response: override — critical concern was procedural (stale body), all substantive concerns addressed in refined AC and builder guidance

### Verdict: APPROVE (after refinement)
### Action Taken: Rewrote objective, AC (corrected G2 retraction, reframed G3), added CockpitView context to builder guidance, updated title, advanced to todo
[[2026-04-26]]
## Test-Writer Notes
- Test file: tests/test_cockpit_mutation_race_1131.py (full rewrite — cycle 1 stale premises corrected)
- Classes: TestFromAC_EditTOCTOU, TestFromAC_MoveOCCContrast, TestFromAC_ReleaseGuardBroken, TestFromAC_409DetailStrings, TestFromAC_SchemaBaseline
- Tests per category: happy 0, edge 0, error 4, boundary 3
- Total: 7 tests, all PASS (GREEN characterization tests by design — document existing behavior)
- ruff: clean

AC coverage:
| AC | Test | Status |
|----|------|--------|
| AC1: edit route omits expected_updated | TestFromAC_EditTOCTOU::test_edit_route_does_not_pass_expected_updated_to_engine | COVERED |
| AC2: move route includes expected_updated (contrast) | TestFromAC_MoveOCCContrast::test_move_route_passes_expected_updated_to_engine | COVERED |
| AC3: release returns 409 even when genuinely claimed | TestFromAC_ReleaseGuardBroken::test_release_returns_409_even_when_task_is_genuinely_claimed | COVERED |
| AC4a: stale edit → exact 409 detail | TestFromAC_409DetailStrings::test_edit_stale_snapshot_returns_exact_409_detail | COVERED |
| AC4b: unclaimed release → exact 409 detail | TestFromAC_409DetailStrings::test_release_unclaimed_task_returns_exact_409_detail | COVERED |
| AC5a: move 200 has all 14 keys | TestFromAC_SchemaBaseline::test_move_200_response_has_all_14_taskdetailout_keys | COVERED |
| AC5b: edit 200 has all 14 keys | TestFromAC_SchemaBaseline::test_edit_200_response_has_all_14_taskdetailout_keys | COVERED |

Key corrections from cycle 1:
- G2 retracted: AC2 now proves move DOES forward expected_updated (OCC contrast, not gap)
- G3 reframed: AC3 uses no mocking — live route returns 409 even for claimed tasks
- AC5: dropped release 200 test (unreachable on new-schema boards, per AC)
- Config: reverted to old format with agent_map (version-10 format missing agent_map causes ConfigError)
- board_dir: simplified to 1 task (AC3 claims task 1 internally; no pre-claimed tasks needed)
[[2026-04-26]]
## Builder Notes
- Implementation: no source changes required (characterization-test task).
- Files changed: none.
- Tests: 7/7 passed in `tests/test_cockpit_mutation_race_1131.py`.
- Ruff: clean (no violations).
- Coverage: no implementation files touched in this builder cycle; scoped report recorded baseline for `owlbear_cockpit.routes.mutation`.
- Evidence summary: task ACs are test characterization of existing cockpit mutation behavior (including known structural gaps), and all scoped checks passed without production edits.

[[2026-04-27]]
## Review Evidence
### Test Results
- pytest: 7 passed, 0 failed in tests/test_cockpit_mutation_race_1131.py

### Lint
- ruff: clean for tests/test_cockpit_mutation_race_1131.py and serve/cockpit/src/owlbear_cockpit/routes/mutation.py

### Coverage
- Requested module coverage for owlbear_cockpit.routes.mutation could not be measured.
- Evidence: pyproject.toml:153 defines [tool.coverage.run].source_pkgs, and the list does not include owlbear_cockpit.
- This was not the primary gate failure; the task already fails on AC3 proof quality.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1: edit route does not forward expected_updated | TestFromAC_EditTOCTOU::test_edit_route_does_not_pass_expected_updated_to_engine | Yes. tests/test_cockpit_mutation_race_1131.py:147 and :164 would fail if mutation.py:221 started forwarding expected_updated. | COVERED |
| AC2: move route forwards expected_updated with correct value | TestFromAC_MoveOCCContrast::test_move_route_passes_expected_updated_to_engine | Yes. tests/test_cockpit_mutation_race_1131.py:182, :199, and :202 would fail if mutation.py:109 omitted or changed expected_updated. | COVERED |
| AC3: claimed task release still returns 409 on new-schema boards | TestFromAC_ReleaseGuardBroken::test_release_returns_409_even_when_task_is_genuinely_claimed | No for the claimed precondition. The test calls engine.claim_task("1") at tests/test_cockpit_mutation_race_1131.py:231, then posts release at :234 and checks the same detail asserted by the truly unclaimed case at :262 and :267. It never proves an observable claimed state before the POST. | LAX |
| AC4a: stale edit returns exact 409 detail | TestFromAC_409DetailStrings::test_edit_stale_snapshot_exact_detail_string | Yes. tests/test_cockpit_mutation_race_1131.py:251 and :258 match mutation.py:214 exactly. | COVERED |
| AC4b: unclaimed release returns exact 409 detail | TestFromAC_409DetailStrings::test_release_unclaimed_task_exact_detail_string | Yes. tests/test_cockpit_mutation_race_1131.py:262 and :267 match mutation.py:239 exactly. | COVERED |
| AC5: move and edit 200 responses include all 14 TaskDetailOut keys | TestFromAC_SchemaBaseline::test_move_200_response_has_all_14_taskdetailout_keys; TestFromAC_SchemaBaseline::test_edit_200_response_has_all_14_taskdetailout_keys | Yes for missing-key regressions. tests/test_cockpit_mutation_race_1131.py:282, :292, :295, and :305 enforce the named 14-key baseline declared in TaskDetailOut at serve/cockpit/src/owlbear_cockpit/models.py:21-37. | COVERED |

#### Security Review
- No security issues found in the changed test file. The task adds only test scaffolding and route characterization.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_* classes in tests/test_cockpit_mutation_race_1131.py | No weakened or removed assertions observed in the current snapshot. Exact kwarg and detail-string assertions remain in place. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | AC1, AC2, and AC4 use exact kwarg presence/value and exact detail-string assertions. |
| Negative and error-path coverage | ADEQUATE | The suite covers stale edit 409, unclaimed release 409, and claimed-then-release 409 characterization. |
| Manual mutation reasoning | WEAK | AC3 can pass even if engine.claim_task("1") becomes a no-op, because the test never checks any claimed observable before posting release. The same release detail is already asserted for the truly unclaimed case. |
| Test independence | STRONG | Each test uses a fresh tmp_path board and per-test engine fixture. |
| Descriptive names | STRONG | Test names state the exact contract under test. |

#### Data Safety
- No data-safety issues found in the test code.

#### Implementation-Aware Gaps
- AC3 remains under-proven. The route rejects on mutation.py:237 using task.claimed_by, while the engine task model stores claim state in claimed_at at serve/kanban/src/owlbear_kanban/models.py:261 and explicitly excludes claimed_by from persistence at :263; storage also drops claimed_by on write at serve/kanban/src/owlbear_kanban/storage.py:386. Because the test never asserts claimed_at or another live claimed observable after engine.claim_task("1"), it does not prove that the release request started from a genuinely claimed task.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- The quality run could not produce module coverage for cockpit code because owlbear_cockpit is excluded from coverage source_pkgs in pyproject.toml.
- The AC5 schema checks are missing-key checks, which is consistent with the written AC but not an exact-only schema freeze.

### AC Compliance Table
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | tests/test_cockpit_mutation_race_1131.py:147 and :164; serve/cockpit/src/owlbear_cockpit/routes/mutation.py:221 | TestFromAC_EditTOCTOU::test_edit_route_does_not_pass_expected_updated_to_engine | PASS |
| AC2 | tests/test_cockpit_mutation_race_1131.py:182, :199, and :202; serve/cockpit/src/owlbear_cockpit/routes/mutation.py:109 | TestFromAC_MoveOCCContrast::test_move_route_passes_expected_updated_to_engine | PASS |
| AC3 | tests/test_cockpit_mutation_race_1131.py:222, :231, :234, :240, :262, and :267; serve/cockpit/src/owlbear_cockpit/routes/mutation.py:237 and :239; serve/kanban/src/owlbear_kanban/models.py:261 and :263; serve/kanban/src/owlbear_kanban/storage.py:386 | TestFromAC_ReleaseGuardBroken::test_release_returns_409_even_when_task_is_genuinely_claimed | FAIL |
| AC4 | tests/test_cockpit_mutation_race_1131.py:251, :258, :262, and :267; serve/cockpit/src/owlbear_cockpit/routes/mutation.py:214 and :239 | TestFromAC_409DetailStrings::* | PASS |
| AC5 | tests/test_cockpit_mutation_race_1131.py:282, :292, :295, and :305; serve/cockpit/src/owlbear_cockpit/models.py:21-37 | TestFromAC_SchemaBaseline::* | PASS |

### Deductions
- 0.11: AC3 proof is lax. The claimed-path test never establishes an observable claimed state, so it can pass on the same unclaimed 409 branch already covered elsewhere in the file.
- 0.03: Requested module coverage for cockpit code is unmeasurable under the current repository coverage configuration.

### Verdict
- FAIL
- Confidence: 0.86
- Action: return to todo for a test-writer fix.
- Required fix: strengthen AC3 by asserting a live claimed-state observable after engine.claim_task("1") and before POST /api/tasks/1/release. The cleanest proof is to re-read the task and assert claimed_at is not None; that closes the false-green path where claim_task has no effect.

### Post-task Reflection
- Problem faced: module coverage for cockpit code could not be measured because owlbear_cockpit is absent from coverage source_pkgs.
- Workaround applied: used scoped pytest and lint evidence plus direct reads of the route, cockpit response model, kanban task model, and storage writer.
- Pattern discovered: when a claimed-path test and an unclaimed-path test assert the same response, the claimed-path test must prove its precondition explicitly or it false-greens.
- Quality gap: AC3 currently proves the response string but not the claimed-state setup that makes the characterization meaningful.
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_cockpit_mutation_race_1131.py
- Classes: TestFromAC_EditTOCTOU, TestFromAC_MoveOCCContrast, TestFromAC_ReleaseGuardBroken, TestFromAC_409DetailStrings, TestFromAC_SchemaBaseline
- Tests per category: happy 0, edge 0, error 4, boundary 3
- Total: 7 tests, all PASS (GREEN characterization tests by design)
- ruff: clean

Retry fix (cycle 3): Strengthened AC3 claimed-state precondition.
- After `engine.claim_task("1")`, added `engine.show_task("1")` re-read with `assert claimed_task.claimed_at is not None`
- Closes the false-green path where claim_task could be a no-op — test now proves genuinely claimed state before POST /api/tasks/1/release
- All 7 tests pass, ruff clean, commit `02c1168e`

AC coverage:
| AC | Test | Status |
|----|------|--------|
| AC1: edit route omits expected_updated | TestFromAC_EditTOCTOU::test_edit_route_does_not_pass_expected_updated_to_engine | COVERED |
| AC2: move route includes expected_updated (contrast) | TestFromAC_MoveOCCContrast::test_move_route_passes_expected_updated_to_engine | COVERED |
| AC3: release returns 409 even when genuinely claimed | TestFromAC_ReleaseGuardBroken::test_release_returns_409_even_when_task_is_genuinely_claimed | COVERED (precondition strengthened) |
| AC4a: stale edit → exact 409 detail | TestFromAC_409DetailStrings::test_edit_stale_snapshot_exact_detail_string | COVERED |
| AC4b: unclaimed release → exact 409 detail | TestFromAC_409DetailStrings::test_release_unclaimed_task_exact_detail_string | COVERED |
| AC5a: move 200 has all 14 keys | TestFromAC_SchemaBaseline::test_move_200_response_has_all_14_taskdetailout_keys | COVERED |
| AC5b: edit 200 has all 14 keys | TestFromAC_SchemaBaseline::test_edit_200_response_has_all_14_taskdetailout_keys | COVERED |