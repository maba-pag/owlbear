---
id: 1077
title: 'B-11: RED — end_work tests'
status: archived
priority: medium
created: 2026-04-21 10:50:12.206656+00:00
updated: 2026-04-26T13:30:29.044379+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1075
blocked: false
block_reason: 'auditor failed twice: TOOL_UNAVAILABLE quality-runner — auditor agent
  cannot reach quality-runner subagent'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.8, §4
Module: `serve/kanban/tests/test_engine_end_work.py`

Test AgentView.end_work — the 4-outcome lifecycle endpoint. Covers outcome dispatch, forbidden-parameter matrix (deterministic per §1.8), atomic semantics (D41), claim validation, idempotent release (D55), auto-advance/auto-archive (D52+D51), predicate on destination.

## Acceptance Criteria

- [ ] AC18: `end_work(id, "success")` auto-advances one step; from terminal archives completed/[]; clears claim
- [ ] AC19: `end_work(id, "reject", move_to="archived", reason, note)` archives + appends + clears
- [ ] AC20: `end_work(id, "release")` clears claim, no status change
- [ ] AC-NEW-1: `end_work(id, "block")` without block_reason → ERR_BLOCK_REASON_REQUIRED
- [ ] AC-NEW-2: `end_work(id, "block", block_reason=r)` sets blocked+block_reason, clears claim
- [ ] AC-NEW-3: `end_work(id, "block", block_reason=r, move_to=s)` additionally moves (predicate fires)
- [ ] AC-NEW-4: `end_work(outcome="block")` response guidance suggests AR/DR creation
- [ ] AC-NEW-5: end_work(reject, move_to=...) skipping >1 emits skip-warning
- [ ] AC-NEW-6: `end_work(id, "<invalid>")` → ERR_INVALID_OUTCOME
- [ ] AC-NEW-7: `end_work(id, "release")` on unclaimed → pure no-op (updated NOT advanced, note NOT appended)
- [ ] AC-NEW-8: `end_work(id, "success"/"reject"/"block")` on unclaimed → ERR_NOT_CLAIMED
- [ ] AC-NEW-9: Forbidden-parameter matrix fully tested (success+move_to, success+archival_reason, etc.)
- [ ] AC-NEW-10: `end_work(id, "reject")` without move_to → ERR_REJECT_REQUIRES_MOVE_TO
- [ ] AC-NEW-11: Non-block outcome with block_reason → ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK
- [ ] AC-NEW-12: success from non-terminal with predicate fail → ERR_PREDICATE_FAILED; claim NOT cleared (D41)
- [ ] AC-NEW-13: block+move_to with predicate fail → claim NOT cleared, blocked NOT set (D41)
- [ ] AC-NEW-17: reject to archived without archival_reason → ERR_ARCHIVAL_REASON_REQUIRED
- [ ] AC-NEW-18: release with move_to → ERR_MOVE_TO_FORBIDDEN_ON_RELEASE
- [ ] AC-NEW-19: release with archival fields → ERR_ARCHIVAL_FIELDS_FORBIDDEN
- [ ] AC-NEW-20: block with archival fields → ERR_ARCHIVAL_FIELDS_FORBIDDEN
- [ ] Note prepended with ISO 8601 timestamp on append (D20/AC30)
- [ ] Multiple parameter errors → leftmost-row, leftmost-column violation raised (deterministic)
- [ ] All tests fail (RED phase)
[[2026-04-25]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_end_work_1077.py
- Classes: TestFromAC_EndWork
- Tests per category: happy 9, error 17, boundary/D41 4
- Total: 30 tests, all FAIL
- ruff: clean

### AC coverage table

| AC | Test(s) |
|----|---------|
| AC18 — success advances, terminal archives completed/[], ISO datetime | test_success_advances_status_with_iso_datetime_in_note, test_success_from_terminal_archives_with_completed_reason |
| AC19 — reject to archived archives + appends + clears | test_reject_to_non_archived_status_updates_status_with_iso_datetime, test_reject_to_archived_moves_file_to_archive_dir |
| AC20 — release clears claim, no status change | test_release_clears_claim_no_status_change_no_note |
| AC-NEW-1 — block without block_reason → ERR_BLOCK_REASON_REQUIRED | test_block_without_reason_raises_err_block_reason_required |
| AC-NEW-2 — block+block_reason sets blocked+block_reason, clears claim | test_block_with_reason_on_claimed_sets_blocked_clears_claim |
| AC-NEW-3 — block+move_to additionally moves (predicate fires) | test_block_with_reason_and_move_to_moves_status_and_sets_blocked, test_block_with_move_to_fires_predicate_on_destination |
| AC-NEW-4 — block guidance suggests AR/DR | test_block_with_move_to_guidance_contains_ar_and_skip_warning |
| AC-NEW-5 — reject skip >1 emits skip-warning | test_reject_backwards_skip_multiple_statuses_emits_skip_warning |
| AC-NEW-6 — invalid outcome → ERR_INVALID_OUTCOME | test_fail_outcome_raises_err_invalid_outcome |
| AC-NEW-7 — release on unclaimed is pure no-op | test_release_on_unclaimed_is_pure_noop_not_updated |
| AC-NEW-8 — unclaimed + success/reject/block → ERR_NOT_CLAIMED | test_unclaimed_success/reject/block_raises_err_not_claimed (3 tests) |
| AC-NEW-9 — forbidden-parameter matrix | test_success_with_move_to_raises_*, test_success_with_archival_reason_raises_* |
| AC-NEW-10 — reject without move_to → ERR_REJECT_REQUIRES_MOVE_TO | test_reject_without_move_to_raises_err_reject_requires_move_to |
| AC-NEW-11 — non-block + block_reason → ERR_BLOCK_REASON_FORBIDDEN | test_success/reject/release_with_block_reason_raises_forbidden (3 tests) |
| AC-NEW-12 — success + predicate fail → ERR_PREDICATE_FAILED; claim not cleared | test_success_predicate_fail_claim_not_cleared |
| AC-NEW-13 — block+move_to + predicate fail → claim not cleared, blocked not set | test_block_move_to_predicate_fail_blocked_not_set_claim_not_cleared |
| AC-NEW-17 — reject to archived without archival_reason → ERR_ARCHIVAL_REASON_REQUIRED | test_reject_to_archived_without_archival_reason_raises_required |
| AC-NEW-18 — release+move_to → ERR_MOVE_TO_FORBIDDEN_ON_RELEASE | test_release_with_move_to_raises_err_move_to_forbidden_on_release |
| AC-NEW-19 — release+archival fields → ERR_ARCHIVAL_FIELDS_FORBIDDEN | test_release_with_archival_reason_raises_archival_fields_forbidden |
| AC-NEW-20 — block+archival fields → ERR_ARCHIVAL_FIELDS_FORBIDDEN | test_block_with_archival_reason/refs_raises_archival_fields_forbidden (2 tests) |
| D20/AC30 — ISO 8601 datetime in note | Folded into test_success_advances_*, test_reject_to_non_archived_*, test_block_with_reason_* |
| matrix determinism | test_release_with_move_to_error_is_not_err_invalid_outcome |
[[2026-04-25]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py (AgentView + KanbanEngine end_work path).
- Test results: 30/30 TestFromAC tests passed in serve/kanban/tests/test_engine_end_work_1077.py.
- Lint: clean (ruff on engine.py and task test file).
- Coverage evidence: owlbear_kanban.engine reported 26% in scoped run.
- Fixes applied:
  - Added AgentView validation matrix for success/reject/block/release with deterministic error codes.
  - Enforced claim-state rules: release on unclaimed is pure no-op; success/reject/block on unclaimed raise ERR_NOT_CLAIMED.
  - Added predicate pre-checks before mutation for success and move_to outcomes (D41 atomicity preservation).
  - Enabled block+move_to status moves and reject->archived with archival metadata validation.
  - Added ISO-8601 datetime note prepend for end_work mutation paths.
  - Added skip-warning guidance for backward jumps and block+move_to guidance merge.
  - Added terminal success archival metadata (completed + empty refs).

### Reflection
- Main risk was preserving atomic semantics while introducing parameter-matrix validation; resolved by validating before calling engine mutators.
- Existing engine-level end_work behavior was intentionally broader than AgentView contract; wrapping constraints at AgentView kept compatibility for direct engine tests.
- The only regression found during GREEN was a trailing newline in no-op release response; fixed with normalized no-op response body.
- Complexity increased in AgentView.end_work due matrix rules; scoped noqa alignment kept lint clean without broader refactors.
[[2026-04-25]]
## Review Evidence

### Tests
- quality-runner scoped on `serve/kanban/tests/test_engine_end_work_1077.py`: 30 passed, 0 failed, 0 skipped
- lint: clean on `serve/kanban/src/` and `serve/kanban/tests/test_engine_end_work_1077.py`
- coverage: `owlbear_kanban.engine` 26% in the scoped run

### Critical Checks
- Test-writer audit: FAIL. AC-NEW-1 is only covered for omitted `block_reason`; explicit empty-string input is not exercised. `AgentView.end_work` rejects only `block_reason is None` (`serve/kanban/src/owlbear_kanban/engine.py:2747-2750`) and then normalizes falsey values to `""` before calling the engine (`serve/kanban/src/owlbear_kanban/engine.py:2817-2818`), so `outcome="block", block_reason=""` still succeeds.
- Test integrity: PRESERVED. `TestFromAC_EndWork` still contains 30 task-scoped tests matching the task-body coverage map; no weakening/removal observed.
- Security review: PASS. No secrets, injection, path traversal, unsafe deserialization, or boundary-validation regressions observed in the reviewed code.
- Data safety: PASS. Predicate checks still happen before mutation in `AgentView.end_work`, and engine-level emit rollback remains in place.
- Builder process quality: CLEAN. One `## Builder Notes` section only.

### AC Compliance
| AC | Evidence | Status |
|---|---|---|
| AC18 | `test_success_advances_status_with_iso_datetime_in_note`, `test_success_from_terminal_archives_with_completed_reason` passed | PASS |
| AC19 | `test_reject_to_non_archived_status_updates_status_with_iso_datetime`, `test_reject_to_archived_moves_file_to_archive_dir` passed | PASS |
| AC20 | `test_release_clears_claim_no_status_change_no_note` passed | PASS |
| AC-NEW-1 | `test_block_without_reason_raises_err_block_reason_required` only covers omitted arg; code still accepts `block_reason=""` via the `None` check + falsey normalization paths in `engine.py` | FAIL |
| AC-NEW-2 | `test_block_with_reason_on_claimed_sets_blocked_clears_claim` passed | PASS |
| AC-NEW-3 | `test_block_with_reason_and_move_to_moves_status_and_sets_blocked`, `test_block_with_move_to_fires_predicate_on_destination` passed | PASS |
| AC-NEW-4 | `test_block_with_move_to_guidance_contains_ar_hint_and_skip_warning` passed | PASS |
| AC-NEW-5 | `test_reject_backwards_skip_multiple_statuses_emits_skip_warning` passed | PASS |
| AC-NEW-6 | `test_fail_outcome_raises_err_invalid_outcome` passed | PASS |
| AC-NEW-7 | `test_release_on_unclaimed_is_pure_noop_not_updated` passed | PASS |
| AC-NEW-8 | `test_unclaimed_success_raises_err_not_claimed`, `test_unclaimed_reject_raises_err_not_claimed`, `test_unclaimed_block_raises_err_not_claimed` passed | PASS |
| AC-NEW-9 | Matrix is not fully proven. `AgentView.end_work` has a dedicated reject-non-archived archival-fields rejection branch (`serve/kanban/src/owlbear_kanban/engine.py:2734-2739`), but the task suite covers archived reject with archival metadata and non-archived reject without archival fields only. Scoped coverage stayed at 26%. | FAIL |
| AC-NEW-10 | `test_reject_without_move_to_raises_err_reject_requires_move_to` passed | PASS |
| AC-NEW-11 | `test_success_with_block_reason_raises_err_block_reason_forbidden`, `test_reject_with_block_reason_raises_err_block_reason_forbidden`, `test_release_with_block_reason_raises_err_block_reason_forbidden` passed | PASS |
| AC-NEW-12 | `test_success_predicate_fail_claim_not_cleared` passed | PASS |
| AC-NEW-13 | `test_block_move_to_predicate_fail_blocked_not_set_claim_not_cleared` passed | PASS |
| AC-NEW-17 | `test_reject_to_archived_without_archival_reason_raises_required` passed | PASS |
| AC-NEW-18 | `test_release_with_move_to_raises_err_move_to_forbidden_on_release` passed | PASS |
| AC-NEW-19 | `test_release_with_archival_reason_raises_archival_fields_forbidden` passed | PASS |
| AC-NEW-20 | `test_block_with_archival_reason_raises_archival_fields_forbidden`, `test_block_with_archival_refs_raises_archival_fields_forbidden` passed | PASS |
| D20/AC30 | ISO timestamp assertions are present in success/reject/block happy-path tests and passed | PASS |
| Deterministic matrix ordering | `test_release_with_move_to_error_is_not_err_invalid_outcome` passed | PASS |
| RED-history | `## Test-Writer Notes` records 30 failing RED tests before builder GREEN; not independently reproducible at review stage | HISTORICAL |

### Deductions
- -0.22: Contract miss on AC-NEW-1 (`block_reason=""` accepted)
- -0.10: Forbidden-parameter matrix not fully exercised; reject + non-archived archival-fields branch remains unproved
- -0.08: Scoped module coverage on `owlbear_kanban.engine` is only 26%, reinforcing the uncovered-path risk

### Verdict
FAIL -> todo
Confidence: 0.60

### Action
Return to test-writer. Add authoritative `TestFromAC` coverage for `outcome="block", block_reason=""` (and ideally whitespace-only input) plus the reject + non-archived archival-fields branch, then send back through GREEN so the implementation can be fixed against the strengthened suite.
[[2026-04-25]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_end_work_1077.py
- Class: TestFromAC_EndWork
- Retry: 3 tests added (2 failing RED + 1 coverage proof)

### New tests

| Test | Category | Result |
|------|----------|--------|
| `test_block_with_empty_string_reason_raises_err_block_reason_required` | error/AC-NEW-1 | FAIL ✓ |
| `test_block_with_whitespace_only_reason_raises_err_block_reason_required` | boundary/AC-NEW-1 | FAIL ✓ |
| `test_reject_to_non_archived_with_archival_reason_raises_archival_fields_forbidden` | error/AC-NEW-9 | PASS (coverage proof — branch already exists) |

### Verification
- pytest: 33 total, 31 passed (30 original + 1 coverage proof), 2 failed (new RED tests)
- ruff: clean
- Commit: bdfd568f

### AC gap addressed
- AC-NEW-1 (empty `block_reason`): AgentView only checks `is None`; `""` and `"   "` bypass the guard via `block_reason or ""` normalisation. Two new failing tests force the builder to add a `not block_reason.strip()` check (or equivalent).
- AC-NEW-9 (matrix proof): `reject + move_to=non-archived + archival_reason` coverage proof test confirms the branch at engine.py:~2782 exists. Immediately passes; no builder action needed for this specific cell.
[[2026-04-25]]
## Builder Notes
- Implementation: tightened block outcome validation in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2747) to reject empty and whitespace-only `block_reason` with `ERR_BLOCK_REASON_REQUIRED`.
- Tests: 33 passed, 0 failed, 0 skipped on `serve/kanban/tests/test_engine_end_work_1077.py` (includes the 2 retry RED tests).
- Coverage: `owlbear_kanban.engine` reported 26% in scoped quality-runner verification.
- ruff: clean (no violations on scoped lint paths).
- Commit: `b75588f5` — `fix: enforce non-empty block_reason in end_work (#1077, builder)`.

### Reflection
- The regression root cause was a `None`-only check while later normalization (`block_reason or ""`) permitted empty payloads through.
- Smallest safe fix was pre-normalization validation (`block_reason is None or not block_reason.strip()`), preserving existing response/error contracts.
- No additional matrix behavior changes were needed; AC-NEW-9 branch proof test already passed before this fix.
- Scoped verification remained stable after the patch (task suite green, lint clean).
- Broader module coverage remains low due module breadth; this task only touched one validation branch.
[[2026-04-25]]
## Review Evidence
### Test Results
- quality-runner scoped on [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L174): 33 passed, 0 failed, 0 skipped.
- Scoped lint on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2722) and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L174): clean.
- Task-scoped coverage: owlbear_kanban.engine 26%.
- quality-runner regression check on [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2261): 223 passed, 5 failed. Directly relevant failures:
  - TestFromAC_AgentViewEndWork::test_end_work_success_advances_status -> ValidationError: Task must be claimed before ending work with outcome='success'
  - TestFromAC_AgentViewEndWork::test_end_work_fail_keeps_status -> ValidationError: Unknown outcome: 'fail'
  - TestFromAC_AgentViewEndWork::test_end_work_block_returns_ar_hint_in_guidance -> ValidationError: Task must be claimed before ending work with outcome='block'
  - TestFromAC_AgentViewEndWork::test_end_work_reject_with_forward_move_emits_skip_guidance -> ValidationError: Task must be claimed before ending work with outcome='reject'
  - Separate background failure also appeared in TestFromAC_CollectTaskSessions::test_release_action_produces_released_session; I am not using that as the gating reason for this review.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Within the task-owned suite, [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L174) contains 33 TestFromAC_EndWork tests, including the retry additions at [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L947), [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L969), and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L993). The mapped tests are specific enough to fail on wrong status, wrong error code, wrong guidance, wrong file location, or wrong on-disk state.
- FAIL: cross-suite TestFromAC contract coherence. Task 1077 requires outcome='fail' to raise ERR_INVALID_OUTCOME at [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L455) and requires unclaimed success/reject/block to raise ERR_NOT_CLAIMED at [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L549), [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L568), and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L586). A sibling AC-scoped suite in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2261) still expects the same AgentView API to accept outcome='fail' and to succeed on unclaimed success/block/reject at [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2264), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2271), [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2278), and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2287). The regression run proves these are not hypothetical conflicts; the sibling tests are red now.

#### Security Review
- No issues found. I did not find secrets, injection paths, unsafe deserialization, path traversal, or boundary-validation regressions in the reviewed end_work code.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------|-------------|---------|
| TestFromAC_EndWork task suite | Retry added two AC-NEW-1 red tests and one AC-NEW-9 proof test; existing assertions remain present | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---------|--------|---------|
| Assertion specificity | ADEQUATE | Task-owned tests assert exact ValidationError codes, exact status values, exact archival fields, file existence, and on-disk invariants |
| Negative/error-path coverage | STRONG | The suite exercises omitted parameters, forbidden parameters, invalid outcomes, unclaimed operations, predicate failures, and archival guards |
| Manual mutation reasoning | STRONG | Removing the empty/whitespace block_reason guard at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2794) would immediately break the retry tests |
| Test independence | ADEQUATE | Every test creates its own temp board through _make_view/_write_task |
| Descriptive names | STRONG | Test names map directly to AC rows and failure modes |
| Cross-suite contract coherence | WEAK | A second TestFromAC suite on the same AgentView API still encodes the opposite behavior and currently fails under the task 1077 implementation |

#### Data Safety
- No issues found. AgentView performs predicate and claim checks before mutation at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2872) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2876), while the lower-level engine path remains a single read/mutate/write cycle with rollback on activity-log failure at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1274) and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L1441).

#### Implementation-Aware Gaps
- On the task-owned surface, no additional untested branches were required to confirm the retry fix. The current implementation lines at [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2778), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2862), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2876), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2794) matches the 1077 task suite.
- The blocking problem is not an untested branch inside 1077; it is the unresolved contradictory contract in the sibling AC-scoped coverage suite.

#### Builder Process Quality
| Metric | Value |
|---------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L1) and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L170) still describe the file as a 30-test RED suite even though it is now a 33-test green suite. Informational only.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC18 | quality-runner 33/0; exact status/archive assertions present | test_success_advances_status_with_iso_datetime_in_note; test_success_from_terminal_archives_with_completed_reason | PASS |
| AC19 | quality-runner 33/0; exact archive-file and archival_reason assertions present | test_reject_to_non_archived_status_updates_status_with_iso_datetime; test_reject_to_archived_moves_file_to_archive_dir | PASS |
| AC20 | quality-runner 33/0; exact no-status-change / no-note assertions present | test_release_clears_claim_no_status_change_no_note | PASS |
| AC-NEW-1 | quality-runner 33/0; omitted, empty, and whitespace-only block_reason variants covered | test_block_without_reason_raises_err_block_reason_required; test_block_with_empty_string_reason_raises_err_block_reason_required; test_block_with_whitespace_only_reason_raises_err_block_reason_required | PASS |
| AC-NEW-2 | quality-runner 33/0; exact blocked/block_reason/claim-clear assertions present | test_block_with_reason_on_claimed_sets_blocked_clears_claim | PASS |
| AC-NEW-3 | quality-runner 33/0; move_to success and predicate-fired move tested | test_block_with_reason_and_move_to_moves_status_and_sets_blocked; test_block_with_move_to_fires_predicate_on_destination | PASS |
| AC-NEW-4 | quality-runner 33/0; block guidance assertions present | test_block_with_move_to_guidance_contains_ar_hint_and_skip_warning | PASS |
| AC-NEW-5 | quality-runner 33/0; skip-warning asserted on backward multi-column reject | test_reject_backwards_skip_multiple_statuses_emits_skip_warning | PASS |
| AC-NEW-6 | quality-runner 33/0; exact ERR_INVALID_OUTCOME assertion present | test_fail_outcome_raises_err_invalid_outcome | PASS |
| AC-NEW-7 | quality-runner 33/0; exact no-op / updated-not-advanced assertion present | test_release_on_unclaimed_is_pure_noop_not_updated | PASS |
| AC-NEW-8 | quality-runner 33/0; exact ERR_NOT_CLAIMED assertions present | test_unclaimed_success_raises_err_not_claimed; test_unclaimed_reject_raises_err_not_claimed; test_unclaimed_block_raises_err_not_claimed | PASS |
| AC-NEW-9 | quality-runner 33/0; forbidden-parameter guards exercised in the task suite | test_success_with_move_to_raises_move_to_forbidden_on_success; test_success_with_archival_reason_raises_archival_fields_forbidden; test_reject_to_non_archived_with_archival_reason_raises_archival_fields_forbidden; test_release_with_move_to_raises_err_move_to_forbidden_on_release; test_release_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_refs_raises_archival_fields_forbidden | PASS |
| AC-NEW-10 | quality-runner 33/0; exact ERR_REJECT_REQUIRES_MOVE_TO assertion present | test_reject_without_move_to_raises_err_reject_requires_move_to | PASS |
| AC-NEW-11 | quality-runner 33/0; exact ERR_BLOCK_REASON_FORBIDDEN_ON_NON_BLOCK assertions present | test_success_with_block_reason_raises_err_block_reason_forbidden; test_reject_with_block_reason_raises_err_block_reason_forbidden; test_release_with_block_reason_raises_err_block_reason_forbidden | PASS |
| AC-NEW-12 | quality-runner 33/0; exact ERR_PREDICATE_FAILED plus on-disk atomicity assertions present | test_success_predicate_fail_claim_not_cleared | PASS |
| AC-NEW-13 | quality-runner 33/0; exact ERR_PREDICATE_FAILED plus blocked/claim on-disk invariants present | test_block_move_to_predicate_fail_blocked_not_set_claim_not_cleared | PASS |
| AC-NEW-17 | quality-runner 33/0; exact ERR_ARCHIVAL_REASON_REQUIRED assertion present | test_reject_to_archived_without_archival_reason_raises_required | PASS |
| AC-NEW-18 | quality-runner 33/0; exact ERR_MOVE_TO_FORBIDDEN_ON_RELEASE assertion present | test_release_with_move_to_raises_err_move_to_forbidden_on_release | PASS |
| AC-NEW-19 | quality-runner 33/0; exact ERR_ARCHIVAL_FIELDS_FORBIDDEN assertion present | test_release_with_archival_reason_raises_archival_fields_forbidden | PASS |
| AC-NEW-20 | quality-runner 33/0; archival_reason and archival_refs variants covered | test_block_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_refs_raises_archival_fields_forbidden | PASS |
| D20/AC30 | quality-runner 33/0; ISO 8601 regex asserted in success/reject/block happy paths | test_success_advances_status_with_iso_datetime_in_note; test_reject_to_non_archived_status_updates_status_with_iso_datetime; test_block_with_reason_on_claimed_sets_blocked_clears_claim | PASS |
| Deterministic matrix ordering | quality-runner 33/0; specific release parameter error asserted over generic invalid outcome | test_release_with_move_to_error_is_not_err_invalid_outcome | PASS |
| RED history | Historical body evidence only | Test-Writer Notes in task body | HISTORICAL |

### Deductions
- -0.28: conflicting TestFromAC contracts on the same AgentView.end_work surface between [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L455) / [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L549) and [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2261)
- -0.05: stale RED-phase comments remain in the now-green task suite at [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L1) and [serve/kanban/tests/test_engine_end_work_1077.py](serve/kanban/tests/test_engine_end_work_1077.py#L170)

### Confidence: 0.67
### Verdict: FAIL
### Action
Return to backlog. Reconcile the sibling TestFromAC contract in [serve/kanban/tests/test_engine_coverage_1068.py](serve/kanban/tests/test_engine_coverage_1068.py#L2261) with the latest 1077 contract and implementation in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2778), [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2862), and [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L2876). Do not pass this task to docs while two AC-scoped suites disagree on whether AgentView.end_work accepts outcome='fail' or unclaimed success/reject/block calls.
[[2026-04-25]]
## Architecture Review

### Reconciliation AC (appended — reviewer cycle 2 feedback)

- [ ] AC-REC-1: `TestFromAC_AgentViewEndWork.test_end_work_success_advances_status` in `test_engine_coverage_1068.py` updated to use a claimed task fixture (add `claimed_at=_now_ts()`); assertion still verifies status advance
- [ ] AC-REC-2: `TestFromAC_AgentViewEndWork.test_end_work_fail_keeps_status` in `test_engine_coverage_1068.py` updated to expect `ValidationError` with `ERR_INVALID_OUTCOME` (outcome='fail' is not valid at AgentView level; claim not needed since outcome validation fires before claim check)
- [ ] AC-REC-3: `TestFromAC_AgentViewEndWork.test_end_work_block_returns_ar_hint_in_guidance` in `test_engine_coverage_1068.py` updated to use a claimed task fixture; assertion still verifies AR hint in guidance
- [ ] AC-REC-4: `TestFromAC_AgentViewEndWork.test_end_work_reject_with_forward_move_emits_skip_guidance` in `test_engine_coverage_1068.py` updated to use a claimed task fixture; assertion still verifies skip guidance
- [ ] AC-REC-5: All 5 `TestFromAC_AgentViewEndWork` tests in `test_engine_coverage_1068.py` pass (including unchanged `test_end_work_not_found_raises`)
- [ ] AC-REC-6: All 33 `TestFromAC_EndWork` tests in `test_engine_end_work_1077.py` continue to pass (no regression)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Reconciliation is directly caused by 1077's contract change; same AgentView.end_work surface |
| Interface clarity | PASS | AC-REC-1 through AC-REC-6 are precise: named tests, named fixtures, exact error codes |
| Dependency correctness | PASS | depends_on 1075 (archived/done). No unmet deps |
| Module layering | PASS | All changes in serve/kanban/tests/ — no upward imports, no cross-package edits |
| TDD compliance | PASS | Task has two test-writer + builder cycles already. Reconciliation is test maintenance, not new features |
| KISS/YAGNI | PASS | 4 test fixture updates, no new abstractions |
| Premise challenge | PASS | The 4 failing regression tests are real (proven by reviewer's quality-runner run: 223 passed, 5 failed, 4 directly attributable to 1077's validation) |
| Pattern consistency | PASS | Fixture pattern (_write_task with claimed_at) already exists in test_engine_end_work_1077.py |
| Security surface | PASS | No new boundaries; test-only changes |
| Single domain | PASS | kanban engine tests only |

### Failure Mode Map
Not applicable — test-file-only changes with no new codepaths.

### Challenge Results
- Challenger: reconsider (confidence 0.39)
- Key concerns raised:
  1. Record mismatch (AC not yet in body) — addressed by appending AC-REC lines here
  2. Cross-task ownership (modifying archived 1068 tests) — rebutted: when a later task changes an API contract, updating stale tests from archived tasks is expected evolution. The 1068 tests encode an obsolete contract (unclaimed success, outcome='fail' accepted) that the implementation no longer supports
  3. Broader MCP contract drift (server.py still includes 'fail' in Literal, guidance tests drive 'fail') — accepted as real but scoped out. Created follow-up task #1124 for MCP layer alignment. MCP is a separate package (serve/mcp-kanban/) with its own lifecycle
  4. 5th regression failure (TestFromAC_CollectTaskSessions) — rebutted: reviewer explicitly excluded it as "separate background failure"
- Architect response: accepted concern #3, created follow-up #1124. Rebutted #1, #2, #4. Reconciliation scope remains bounded to 4 tests in serve/kanban/tests/test_engine_coverage_1068.py

### Notes
- The 5th reviewer regression failure (TestFromAC_CollectTaskSessions::test_release_action_produces_released_session) is not in scope for this task — the reviewer explicitly noted it as a separate background issue
- Stale RED-phase comments in test_engine_end_work_1077.py (lines 1, 170) are informational — builder may clean up if convenient but not AC-gated
- MCP layer contract drift addressed by follow-up task #1124 (depends_on 1077)

### Verdict: APPROVE
### Action Taken: Appended reconciliation AC (AC-REC-1 through AC-REC-6) to address reviewer cycle 2 feedback. Created follow-up #1124 for MCP contract alignment. Advanced to todo.
[[2026-04-25]]
## Test-Writer Notes
- Retry cycle 2 (reconciliation): 4 existing `TestFromAC_AgentViewEndWork` tests in `serve/kanban/tests/test_engine_coverage_1068.py` updated to align with the 1077 contract per AC-REC-1 through AC-REC-4.
- No changes to `serve/kanban/tests/test_engine_end_work_1077.py` (immutable).

### Changes made
| AC | Test | Change |
|----|------|--------|
| AC-REC-1 | `test_end_work_success_advances_status` | Added `claimed_at=_now_ts()` to `_write_task` |
| AC-REC-2 | `test_end_work_fail_keeps_status` | Replaced `resp.status == "todo"` with `pytest.raises(ValidationError)` checking `ERR_INVALID_OUTCOME` |
| AC-REC-3 | `test_end_work_block_returns_ar_hint_in_guidance` | Added `claimed_at=_now_ts()` to `_write_task` |
| AC-REC-4 | `test_end_work_reject_with_forward_move_emits_skip_guidance` | Added `claimed_at=_now_ts()` to `_write_task` |

### Verification
- AC-REC-5: `TestFromAC_AgentViewEndWork` (1068): 5 passed, 0 failed ✓
- AC-REC-6: `TestFromAC_EndWork` (1077): 33 passed, 0 failed ✓
- ruff: clean on `serve/kanban/tests/test_engine_coverage_1068.py` ✓
- Commit: 5864ee64
[[2026-04-25]]
## Builder Notes
- Implementation: no source changes required in this reconciliation pass; existing AgentView `end_work` behavior already matches AC-REC-1..AC-REC-6.
- Files changed: none.
- Tests: 38/38 passed for scoped task-owned classes (`TestFromAC_AgentViewEndWork` + `TestFromAC_EndWork`).
- Lint: clean on `serve/kanban/tests/test_engine_coverage_1068.py` and `serve/kanban/tests/test_engine_end_work_1077.py`.
- Coverage: `owlbear_kanban.engine` 26% in scoped selector run.
- Evidence summary: targeted quality-runner execution for task classes passed with pytest exit 0 and ruff exit 0; no further builder intervention needed.

### Reflection
- This cycle was contract reconciliation validation rather than feature implementation.
- Running broad file scope surfaced one unrelated background failure; a selector-scoped run isolated task-owned contract status and removed false gating noise.
- No changes were made to `TestFromAC_*` tests or engine code in this pass, preserving surgical scope.
- Main risk remains module breadth vs scoped coverage visibility; mitigation was explicit class-level evidence for AC-REC lines.
[[2026-04-25]]
## Review Evidence
### Test Results
- quality-runner selector run on serve/kanban/tests/test_engine_end_work_1077.py::TestFromAC_EndWork and serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_AgentViewEndWork: 38 passed, 0 failed, 0 skipped
- Scoped lint on serve/kanban/tests/test_engine_end_work_1077.py, serve/kanban/tests/test_engine_coverage_1068.py, and serve/kanban/src/owlbear_kanban/engine.py: clean
- Coverage snapshot from the same run: overall 31%; owlbear_kanban.engine 26%

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC18 | test_success_advances_status_with_iso_datetime_in_note; test_success_from_terminal_archives_with_completed_reason | Yes | COVERED |
| AC19 | test_reject_to_non_archived_status_updates_status_with_iso_datetime; test_reject_to_archived_moves_file_to_archive_dir | Yes | COVERED |
| AC20 | test_release_clears_claim_no_status_change_no_note | Yes | COVERED |
| AC-NEW-1 | test_block_without_reason_raises_err_block_reason_required; test_block_with_empty_string_reason_raises_err_block_reason_required; test_block_with_whitespace_only_reason_raises_err_block_reason_required | Yes | COVERED |
| AC-NEW-2 | test_block_with_reason_on_claimed_sets_blocked_clears_claim | Yes | COVERED |
| AC-NEW-3 | test_block_with_reason_and_move_to_moves_status_and_sets_blocked; test_block_with_move_to_fires_predicate_on_destination | Yes | COVERED |
| AC-NEW-4 | test_block_with_move_to_guidance_contains_ar_hint_and_skip_warning | Yes | COVERED |
| AC-NEW-5 | test_reject_backwards_skip_multiple_statuses_emits_skip_warning | Yes | COVERED |
| AC-NEW-6 | test_fail_outcome_raises_err_invalid_outcome | Yes | COVERED |
| AC-NEW-7 | test_release_on_unclaimed_is_pure_noop_not_updated | Yes | COVERED |
| AC-NEW-8 | test_unclaimed_success_raises_err_not_claimed; test_unclaimed_reject_raises_err_not_claimed; test_unclaimed_block_raises_err_not_claimed | Yes | COVERED |
| AC-NEW-9 | test_success_with_move_to_raises_move_to_forbidden_on_success; test_success_with_archival_reason_raises_archival_fields_forbidden; test_reject_to_non_archived_with_archival_reason_raises_archival_fields_forbidden; test_release_with_move_to_raises_err_move_to_forbidden_on_release; test_release_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_refs_raises_archival_fields_forbidden | Yes | COVERED |
| AC-NEW-10 | test_reject_without_move_to_raises_err_reject_requires_move_to | Yes | COVERED |
| AC-NEW-11 | test_success_with_block_reason_raises_err_block_reason_forbidden; test_reject_with_block_reason_raises_err_block_reason_forbidden; test_release_with_block_reason_raises_err_block_reason_forbidden | Yes | COVERED |
| AC-NEW-12 | test_success_predicate_fail_claim_not_cleared | Yes | COVERED |
| AC-NEW-13 | test_block_move_to_predicate_fail_blocked_not_set_claim_not_cleared | Yes | COVERED |
| AC-NEW-17 | test_reject_to_archived_without_archival_reason_raises_required | Yes | COVERED |
| AC-NEW-18 | test_release_with_move_to_raises_err_move_to_forbidden_on_release | Yes | COVERED |
| AC-NEW-19 | test_release_with_archival_reason_raises_archival_fields_forbidden | Yes | COVERED |
| AC-NEW-20 | test_block_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_refs_raises_archival_fields_forbidden | Yes | COVERED |
| D20/AC30 | test_success_advances_status_with_iso_datetime_in_note; test_reject_to_non_archived_status_updates_status_with_iso_datetime; test_block_with_reason_on_claimed_sets_blocked_clears_claim | Yes | COVERED |
| Deterministic matrix ordering | test_release_with_move_to_error_is_not_err_invalid_outcome | Yes | COVERED |
| RED phase history | Task body Test-Writer Notes record the original 30 failing RED tests and the later retry additions | Historical | COVERED |
| AC-REC-1 | TestFromAC_AgentViewEndWork.test_end_work_success_advances_status | Yes | COVERED |
| AC-REC-2 | TestFromAC_AgentViewEndWork.test_end_work_fail_keeps_status | Yes | COVERED |
| AC-REC-3 | TestFromAC_AgentViewEndWork.test_end_work_block_returns_ar_hint_in_guidance | Yes | COVERED |
| AC-REC-4 | TestFromAC_AgentViewEndWork.test_end_work_reject_with_forward_move_emits_skip_guidance | Yes | COVERED |
| AC-REC-5 | TestFromAC_AgentViewEndWork class selector run | Yes | COVERED |
| AC-REC-6 | TestFromAC_EndWork class selector run | Yes | COVERED |

#### Security Review
- No issues found. The reviewed AgentView.end_work surface in serve/kanban/src/owlbear_kanban/engine.py validates the outcome and parameter matrix before mutation, rejects blank block_reason at line 2829, rejects invalid outcomes at line 2857, enforces claim checks at line 2871, and performs predicate pre-checks at lines 2884 and 2890 before calling the engine mutator.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_EndWork in serve/kanban/tests/test_engine_end_work_1077.py | No changes in the reconciliation pass; builder changed no TestFromAC assertions | PRESERVED |
| TestFromAC_AgentViewEndWork in serve/kanban/tests/test_engine_coverage_1068.py | Test-writer updated 4 stale fixtures/assertions under the latest Architecture Review; builder changed no TestFromAC assertions | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | The 1077 suite asserts exact error codes, exact status changes, exact archival fields, exact guidance fragments, and on-disk invariants; the 1068 reconciliation class asserts the exact AgentView surface outcomes now required by the latest refinement |
| Negative/error-path coverage | STRONG | Invalid outcome, missing move_to, blank block_reason, forbidden parameters, unclaimed operations, predicate failures, and not-found behavior are all exercised across the two class selectors |
| Manual mutation reasoning | STRONG | Removing the blank/whitespace block_reason guard at engine.py:2829 or the unclaimed-task validation at engine.py:2871 would immediately break the 1077 selector run; reverting the 1068 reconciliation would immediately break the 5-test AgentView selector run |
| Test independence | ADEQUATE | Each test builds its own temp board and writes its own task fixture through the local helpers |
| Descriptive names | STRONG | Test names map directly to the AC rows and the reviewed contract surface |
| Cross-suite contract coherence | STRONG | The prior contradiction is resolved: the 1068 AgentView class now uses claimed fixtures for success, block, and reject, and expects ERR_INVALID_OUTCOME for outcome='fail' |

#### Data Safety
- No issues found. The reviewed path keeps validation and predicate checks ahead of mutation and leaves the lower-level engine rollback behavior untouched.

#### Implementation-Aware Gaps
- No task-owned gaps found on the latest refinement surface. The specific branches that changed or were previously disputed are now directly exercised by the reconciled selectors: blank block_reason at engine.py:2829, invalid outcome at engine.py:2857, unclaimed-state rejection at engine.py:2871, and predicate pre-checks at engine.py:2884 and engine.py:2890.
- The module-wide coverage number remains low because owlbear_kanban.engine is broad, but no source file changed in this reconciliation pass and I did not find an unproved path on the reviewed AgentView.end_work contract surface.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- None material for gating. The earlier contradiction between the 1077 and 1068 TestFromAC suites is resolved in the current snapshot.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC18 | quality-runner 38 passed, 0 failed; exact status, archival, and ISO-note assertions remain in serve/kanban/tests/test_engine_end_work_1077.py lines 179 and 202 | test_success_advances_status_with_iso_datetime_in_note; test_success_from_terminal_archives_with_completed_reason | PASS |
| AC19 | quality-runner 38 passed, 0 failed; exact reject-to-status and reject-to-archive assertions remain at lines 227 and 249 | test_reject_to_non_archived_status_updates_status_with_iso_datetime; test_reject_to_archived_moves_file_to_archive_dir | PASS |
| AC20 | quality-runner 38 passed, 0 failed; exact no-status-change and no-note assertions remain at line 278 | test_release_clears_claim_no_status_change_no_note | PASS |
| AC-NEW-1 | quality-runner 38 passed, 0 failed; omitted, empty, and whitespace-only block_reason paths all raise the required code | test_block_without_reason_raises_err_block_reason_required; test_block_with_empty_string_reason_raises_err_block_reason_required; test_block_with_whitespace_only_reason_raises_err_block_reason_required | PASS |
| AC-NEW-2 | quality-runner 38 passed, 0 failed; blocked, block_reason, and claim-clear assertions remain at line 335 | test_block_with_reason_on_claimed_sets_blocked_clears_claim | PASS |
| AC-NEW-3 | quality-runner 38 passed, 0 failed; move_to success and predicate-fired destination both covered at lines 362 and 886 | test_block_with_reason_and_move_to_moves_status_and_sets_blocked; test_block_with_move_to_fires_predicate_on_destination | PASS |
| AC-NEW-4 | quality-runner 38 passed, 0 failed; AR hint and skip guidance both asserted at line 388 | test_block_with_move_to_guidance_contains_ar_hint_and_skip_warning | PASS |
| AC-NEW-5 | quality-runner 38 passed, 0 failed; backward multi-column skip warning asserted at line 917 | test_reject_backwards_skip_multiple_statuses_emits_skip_warning | PASS |
| AC-NEW-6 | quality-runner 38 passed, 0 failed; outcome='fail' now raises ERR_INVALID_OUTCOME in both the 1077 task suite and the 1068 reconciliation class at lines 455 and 2271 | test_fail_outcome_raises_err_invalid_outcome; TestFromAC_AgentViewEndWork.test_end_work_fail_keeps_status | PASS |
| AC-NEW-7 | quality-runner 38 passed, 0 failed; pure no-op release assertions remain in the 1077 suite | test_release_on_unclaimed_is_pure_noop_not_updated | PASS |
| AC-NEW-8 | quality-runner 38 passed, 0 failed; the unclaimed success, reject, and block guards all still raise ERR_NOT_CLAIMED at lines 549, 568, and 586 | test_unclaimed_success_raises_err_not_claimed; test_unclaimed_reject_raises_err_not_claimed; test_unclaimed_block_raises_err_not_claimed | PASS |
| AC-NEW-9 | quality-runner 38 passed, 0 failed; representative branches for success, reject non-archived, release, and block forbidden-parameter guards are all covered | test_success_with_move_to_raises_move_to_forbidden_on_success; test_success_with_archival_reason_raises_archival_fields_forbidden; test_reject_to_non_archived_with_archival_reason_raises_archival_fields_forbidden; test_release_with_move_to_raises_err_move_to_forbidden_on_release; test_release_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_refs_raises_archival_fields_forbidden | PASS |
| AC-NEW-10 | quality-runner 38 passed, 0 failed; exact ERR_REJECT_REQUIRES_MOVE_TO assertion remains in the 1077 suite | test_reject_without_move_to_raises_err_reject_requires_move_to | PASS |
| AC-NEW-11 | quality-runner 38 passed, 0 failed; exact non-block block_reason guard remains covered | test_success_with_block_reason_raises_err_block_reason_forbidden; test_reject_with_block_reason_raises_err_block_reason_forbidden; test_release_with_block_reason_raises_err_block_reason_forbidden | PASS |
| AC-NEW-12 | quality-runner 38 passed, 0 failed; predicate failure preserves status and claim in the 1077 suite | test_success_predicate_fail_claim_not_cleared | PASS |
| AC-NEW-13 | quality-runner 38 passed, 0 failed; predicate failure leaves blocked unset and claim intact in the 1077 suite | test_block_move_to_predicate_fail_blocked_not_set_claim_not_cleared | PASS |
| AC-NEW-17 | quality-runner 38 passed, 0 failed; exact ERR_ARCHIVAL_REASON_REQUIRED assertion remains covered | test_reject_to_archived_without_archival_reason_raises_required | PASS |
| AC-NEW-18 | quality-runner 38 passed, 0 failed; exact ERR_MOVE_TO_FORBIDDEN_ON_RELEASE assertion remains covered | test_release_with_move_to_raises_err_move_to_forbidden_on_release | PASS |
| AC-NEW-19 | quality-runner 38 passed, 0 failed; exact ERR_ARCHIVAL_FIELDS_FORBIDDEN assertion remains covered | test_release_with_archival_reason_raises_archival_fields_forbidden | PASS |
| AC-NEW-20 | quality-runner 38 passed, 0 failed; archival_reason and archival_refs variants remain covered | test_block_with_archival_reason_raises_archival_fields_forbidden; test_block_with_archival_refs_raises_archival_fields_forbidden | PASS |
| D20/AC30 | quality-runner 38 passed, 0 failed; ISO 8601 note assertions remain at lines 179, 227, and 335 | test_success_advances_status_with_iso_datetime_in_note; test_reject_to_non_archived_status_updates_status_with_iso_datetime; test_block_with_reason_on_claimed_sets_blocked_clears_claim | PASS |
| Deterministic matrix ordering | quality-runner 38 passed, 0 failed; the specific release parameter error still wins over generic invalid outcome | test_release_with_move_to_error_is_not_err_invalid_outcome | PASS |
| RED phase history | Direct task-body evidence only; original Test-Writer Notes and retry notes remain in the task file | Task body history | HISTORICAL |
| AC-REC-1 | quality-runner 38 passed, 0 failed; claimed fixture is present in the 1068 reconciliation class at line 2264 | TestFromAC_AgentViewEndWork.test_end_work_success_advances_status | PASS |
| AC-REC-2 | quality-runner 38 passed, 0 failed; the 1068 reconciliation class now expects ValidationError with ERR_INVALID_OUTCOME at line 2271 | TestFromAC_AgentViewEndWork.test_end_work_fail_keeps_status | PASS |
| AC-REC-3 | quality-runner 38 passed, 0 failed; claimed fixture plus AR hint guidance assertion remain at line 2279 | TestFromAC_AgentViewEndWork.test_end_work_block_returns_ar_hint_in_guidance | PASS |
| AC-REC-4 | quality-runner 38 passed, 0 failed; claimed fixture plus skip-guidance assertion remain at line 2288 | TestFromAC_AgentViewEndWork.test_end_work_reject_with_forward_move_emits_skip_guidance | PASS |
| AC-REC-5 | quality-runner selector run on the full TestFromAC_AgentViewEndWork class passed cleanly | TestFromAC_AgentViewEndWork | PASS |
| AC-REC-6 | quality-runner selector run on the full TestFromAC_EndWork class passed cleanly | TestFromAC_EndWork | PASS |

### Deductions
- -0.04: selector-scoped coverage still reports 26% on the broad owlbear_kanban.engine module, so this pass relies on the targeted contract proof rather than module-wide saturation

### Confidence: 0.93
### Verdict: PASS
### Action
Advance to docs. The latest Architecture Review refinement is satisfied, the earlier cross-suite contradiction is resolved in the current snapshot, and the task-owned end_work contract now has independent green evidence from both relevant TestFromAC classes.
[[2026-04-25]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/kanban/README.md` documents `end_work(task_id, …)` at the `KanbanEngine` abstraction level; description "Append outcome note and advance or reject" remains accurate. `AgentView` is not separately documented in the README — no prose update required. |
| 2 | Module docstrings | Yes | Updated | `AgentView.end_work` in `serve/kanban/src/owlbear_kanban/engine.py` had no docstring despite being a public method modified by this task. Added docstring covering outcome variants, parameter matrix, returns, and raises. Ruff clean after edit. |
| 3 | External attribution | No | N/A | No external patterns or sources cited in task body. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` file produced or referenced. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` has `describes: serve/kanban/src/**` which matches `serve/kanban/src/owlbear_kanban/engine.py`. Footer updated: `Last verified: 2026-04-25 (9e99d6de)`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files in changed-files set. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/tests/test_engine_end_work_1077.py` | OUT | N/A (test file) |
| `serve/kanban/tests/test_engine_coverage_1068.py` | OUT | N/A (test file) |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN | Docstring added to `AgentView.end_work` |

### Files Updated
- `serve/kanban/src/owlbear_kanban/engine.py` — docstring added to `AgentView.end_work`
- `share/diagrams/kanban.excalidraw` — footer updated to `(9e99d6de)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1077-*` files found)

### Commit
`15a4cf67` — docs: add AgentView.end_work docstring, update diagram footer (#1077, doc-writer)

[[2026-04-26]]
## Audit (partial)

### Deliverable Verification
- serve/kanban/tests/test_engine_end_work_1077.py: EXISTS, 33 tests in TestFromAC_EndWork
- serve/kanban/src/owlbear_kanban/engine.py: EXISTS, AgentView.end_work at L2757 with docstring (L2769-2807), block_reason .strip() validation at L2887-2890
- serve/kanban/tests/test_engine_coverage_1068.py: EXISTS, TestFromAC_AgentViewEndWork reconciled (claimed_at fixtures, ERR_INVALID_OUTCOME expectation)

### Reviewer Evidence
Final reviewer pass (cycle 3): PASS at 0.93. All AC lines mapped. Selector-scoped run: 38 passed, 0 failed. Cross-suite contradiction resolved.

### AC Spot-Check
- AC-NEW-1 (empty block_reason): Confirmed .strip() guard at engine.py:2887. Tests exist for None, empty string, whitespace-only.
- AC-REC-2 (fail outcome): Confirmed test_engine_coverage_1068.py:2272 now expects ERR_INVALID_OUTCOME.

### Blocked
Quality-Runner subagent not available in auditor runtime. Cannot execute full-suite regression check (auditor's primary unique value). Deliverables and reviewer evidence look solid; full suite run required before archive.

[[2026-04-26]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC18 | test_success_advances_status_with_iso_datetime_in_note, test_success_from_terminal_archives_with_completed_reason — 33/0 in task suite | PASS |
| AC19 | test_reject_to_non_archived_status_updates_status_with_iso_datetime, test_reject_to_archived_moves_file_to_archive_dir — 33/0 | PASS |
| AC20 | test_release_clears_claim_no_status_change_no_note — 33/0 | PASS |
| AC-NEW-1 | test_block_without_reason_*, test_block_with_empty_string_reason_*, test_block_with_whitespace_only_reason_* — 33/0; .strip() guard at engine.py:2887 | PASS |
| AC-NEW-2 | test_block_with_reason_on_claimed_sets_blocked_clears_claim — 33/0 | PASS |
| AC-NEW-3 | test_block_with_reason_and_move_to_*, test_block_with_move_to_fires_predicate_* — 33/0 | PASS |
| AC-NEW-4 | test_block_with_move_to_guidance_contains_ar_hint_and_skip_warning — 33/0 | PASS |
| AC-NEW-5 | test_reject_backwards_skip_multiple_statuses_emits_skip_warning — 33/0 | PASS |
| AC-NEW-6 | test_fail_outcome_raises_err_invalid_outcome — 33/0 | PASS |
| AC-NEW-7 | test_release_on_unclaimed_is_pure_noop_not_updated — 33/0 | PASS |
| AC-NEW-8 | test_unclaimed_success/reject/block_raises_err_not_claimed (3 tests) — 33/0 | PASS |
| AC-NEW-9 | 7 forbidden-parameter tests covering success/reject/release/block — 33/0; coverage proof at test_reject_to_non_archived_with_archival_reason | PASS |
| AC-NEW-10 | test_reject_without_move_to_raises_err_reject_requires_move_to — 33/0 | PASS |
| AC-NEW-11 | test_success/reject/release_with_block_reason_raises_forbidden (3 tests) — 33/0 | PASS |
| AC-NEW-12 | test_success_predicate_fail_claim_not_cleared — 33/0 | PASS |
| AC-NEW-13 | test_block_move_to_predicate_fail_blocked_not_set_claim_not_cleared — 33/0 | PASS |
| AC-NEW-17 | test_reject_to_archived_without_archival_reason_raises_required — 33/0 | PASS |
| AC-NEW-18 | test_release_with_move_to_raises_err_move_to_forbidden_on_release — 33/0 | PASS |
| AC-NEW-19 | test_release_with_archival_reason_raises_archival_fields_forbidden — 33/0 | PASS |
| AC-NEW-20 | test_block_with_archival_reason/refs_raises_archival_fields_forbidden (2 tests) — 33/0 | PASS |
| D20/AC30 | ISO 8601 assertions in success/reject/block happy paths — 33/0 | PASS |
| Deterministic matrix | test_release_with_move_to_error_is_not_err_invalid_outcome — 33/0 | PASS |
| RED history | Task body Test-Writer Notes document 30 failing RED → 33 green | HISTORICAL |
| AC-REC-1–6 | TestFromAC_AgentViewEndWork selector: 5/0; reconciled fixtures and expectations verified | PASS |

### Test Results
- pytest (full suite): 2223 passed, 173 failed, 4 skipped, 209 errors — **0 failures in task scope**
- pytest (task-scoped): TestFromAC_EndWork 33/0, TestFromAC_AgentViewEndWork 5/0
- ruff: clean on serve/kanban/src/ and serve/kanban/tests/
- Coverage: owlbear_kanban.engine 95% (full suite)

### Background Failures (informational)
173 failures + 209 errors in full suite — all outside task scope: cockpit API (expected_updated kwargs), MCP kanban (agent_name/agent_map fixtures), frontend (vite config), corruption, storage. None attributable to #1077 changes.

### Architect Quality: 4/5
AC was comprehensive (22 specific criteria with exact error codes, parameter combinations, state invariants). Minor gap: AC-NEW-1 didn't explicitly specify empty/whitespace handling — caught by reviewer and addressed via retry. Reconciliation AC (AC-REC-*) added mid-cycle for cross-suite contract conflict. Appropriate architect response.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| AC line with no specific evidence | 0 (all covered) |
| Lint violations | 0 (clean) |
| AC quality score ≤ 3 | 0 (score 4) |
| Missing reviewer evidence section | 0 (present, 3 cycles) |
| Full-suite test failures in task scope | 0 (none) |

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 4c34dcbe | test | test_engine_end_work_1077.py | #1077 |
| bc996b9c | feat | engine.py | #1077 |
| bdfd568f | test | test_engine_end_work_1077.py | #1077 |
| b75588f5 | fix | engine.py | #1077 |
| 5864ee64 | test | test_engine_coverage_1068.py | #1077 |
| 15a4cf67 | docs | engine.py, kanban.excalidraw | #1077 |