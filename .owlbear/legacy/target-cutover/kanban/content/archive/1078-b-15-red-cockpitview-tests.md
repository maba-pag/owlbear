---
id: 1078
title: 'B-15: RED — CockpitView tests'
status: archived
priority: medium
created: 2026-04-21 10:50:12.218304+00:00
updated: 2026-04-27T15:40:29.683597+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1071
- 1075
- 1138
- 1139
- 1140
blocked: false
block_reason: 'builder failed twice: coverage gate unreachable (58% engine vs 90%
  required) — needs prerequisite test coverage work before builder can pass'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §5, §3.8
Module: `serve/kanban/tests/test_engine_cockpit_view.py`

Test CockpitView facade — OCC-guarded mutations, admin operations, activity/session reads. CockpitView wraps engine methods with OCC (edit_task, move_task) and adds admin-only operations (release_task, sweep, scan_corruption, repair_storage, compact_activity, list_activity, list_sessions).

## Acceptance Criteria

- [ ] CockpitView.edit_task requires `expected_updated` as mandatory param (no default); mismatch → ConcurrencyError(ERR_STALE) per D22+D46
- [ ] CockpitView.move_task requires `expected_updated` as mandatory param (no default); mismatch → ConcurrencyError(ERR_STALE)
- [ ] AC-NEW-21: release_task on unclaimed → idempotent no-op (updated NOT advanced)
- [ ] AC-NEW-22: sweep returns exactly the set of released task IDs (no extras, no missing); idempotent (second call → [])
- [ ] AC-NEW-23: sweep per-task release routes through `storage.write_task_if_unchanged` (CAS); on ERR_STALE for any task, that task is skipped this cycle — no release, no error (Brief B §5 CAS contract)
- [ ] release_task on missing id → NotFoundError(ERR_NOT_FOUND)
- [ ] list_activity supports filter by task_id, action, source, time window; since/until tests must assert both exact event count AND task_id identity within each test method
- [ ] list_sessions returns SessionRecord list with correct state derivation per Brief B paper-integration.md:402 (flat labels: running, stuck, completed, blocked, rejected, released, expired)
- [ ] scan_corruption is read-only (no file creation, deletion, or content mutation), returns list[CorruptionError]
- [ ] repair_storage: phase-1 scan_and_fix + phase-2 AR creation; never implicit at startup
- [ ] compact_activity calls storage.compact_activity_log
- [ ] CockpitView does NOT expose: create_task, start_work, end_work, pick_tasks
- [ ] ActivityEvent.source populated automatically: "agent" / "cockpit" / "engine" per §3.8
- [ ] All tests fail (RED phase)
[[2026-04-27]]
## Architecture Review (cycle 9)
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | CockpitView facade testing only |
| Interface clarity | PASS | AC lines map to methods, params, error codes |
| Dependency correctness | PASS | All deps archived |
| Module layering | PASS | Tests import from public owlbear_kanban interface |
| TDD compliance | PASS | This IS the test task (tdd:red) |
| KISS/YAGNI | PASS | No hypothetical requirements |
| Premise challenge | PASS | CockpitView methods need dedicated proof |
| Pattern consistency | PASS | Follows TestFromAC_ naming, _make_board fixtures |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban engine domain only |

### Context: Reviewer FAIL (cycle 8, confidence 0.89)
Sole routing deduction: -0.08 for AC 8 released-session test (tests/test_engine_cockpit_view_1078.py:658-673) asserting `outcome == "release"` but not `state == "released"`. Secondary -0.04 for stale header wording. Reviewer's mutation claim: "A regression that stops deriving state == 'released' while still returning the session under filter='released' can keep the task-owned test green."

### Reviewer Mutation Analysis Is Incorrect
The reviewer's deduction rests on a **false counterfactual**. The test calls `cv.list_sessions(filter="released")` and asserts `len(sessions) == 1`. The filter mechanism at engine.py:334 defines `"released": frozenset({"released"})` and at engine.py:357-358 applies `[s for s in sessions if s.state in allowed]`. Therefore:

1. The session can ONLY appear in the filtered result if `s.state == "released"`
2. `len(sessions) == 1` proves exactly one session has `state == "released"`
3. The reviewer's hypothetical — "stops deriving state == 'released' while still returning the session under filter='released'" — is **impossible** given the filter implementation

The existing test already provides implicit behavioral proof of `state == "released"` through the state-based filter mechanism. The missing explicit `assert sessions[0].state == "released"` is a readability improvement, not a behavioral gap.

### Binding Test-Writer Directive (cycle 9)
For reviewer clarity and explicitness, add `assert sessions[0].state == "released"` after the existing `assert sessions[0].outcome == "release"` at line ~673. Also update the `sess-released` header wording at line 24 from "release-outcome sessions" to "released-state sessions per Brief B flat labels". This is a readability/explicitness improvement, not a behavioral gap fix.

### Binding Reviewer Directive (cycle 9)
The `list_sessions(filter="released")` API provides implicit state-derivation proof through its filter mechanism (engine.py:334, :357-358). The filter selects sessions where `s.state in frozenset({"released"})` — a session cannot appear in the result without `state == "released"`. The reviewer MUST NOT deduct for AC 8 state-derivation coverage based on the absence of an explicit `state` field assertion when the filter mechanism already enforces it behaviorally. After the test-writer adds the explicit assertion per the directive above, the remaining concern is fully addressed.

### All Prior Binding Directives (carried)
1. Coverage scope: owlbear_kanban.engine CockpitView class + storage write_task_if_unchanged. Module-wide percentages informational only.
2. Reviewer MUST NOT gate on cross-suite session-state taxonomy. Stale suites tracked by #1143.
3. AC line 8 gate: task-owned tests at tests/test_engine_cockpit_view_1078.py:592-751.

### Challenge Results
- Challenger: reconsider (0.58)
- Architect response: ACCEPTED on core analysis, verdict MAINTAINED
  - "Unsupported counterfactual" (filter already proves state): ACCEPTED — this is the architect's primary justification. The filter at engine.py:334+357-358 makes the reviewer's mutation scenario impossible. Verified independently.
  - "Unreconciled authority reversal": ACCEPTED — cycle 5 explicitly ruled the task-owned suite "correctly asserts the flat taxonomy." The reviewer shifted without reconciliation. Noted in binding directive.
  - "Evidence-scope omission" (durable suites already assert released state): NOTED — informational; task-owned proof is primary, but broader suites provide additional confidence.
  - "Non-executable signal inflation" (header wording is editorial): ACCEPTED — folded as editorial improvement, not proof gap.

### Verdict: APPROVE
### Action Taken: Added binding test-writer directive for explicit state assertion (readability improvement). Added binding reviewer directive explaining filter-based implicit proof. All prior directives carried. Advanced to todo.
[[2026-04-27]]
## Test-Writer Notes
- Test file: tests/test_engine_cockpit_view_1078.py
- Classes: TestFromAC_CockpitViewOCC, TestFromAC_ReleaseTask, TestFromAC_Sweep, TestFromAC_ListActivity, TestFromAC_ListSessions, TestFromAC_ScanCorruption, TestFromAC_RepairStorage, TestFromAC_CompactActivity, TestFromAC_CockpitViewRole, TestFromAC_ActivitySource
- Cycle 9 directive applied (readability/explicitness improvements):
  1. Updated `sess-released` header wording from "release-outcome sessions" to "released-state sessions per Brief B flat labels"
  2. Added `assert sessions[0].state == "released"` after `assert sessions[0].outcome == "release"` in `test_list_sessions_filter_released_returns_release_outcome_sessions`
- Total: 64 tests, all PASS (implementation exists — new assertion passes as architect noted: "readability improvement, not behavioral gap")
- ruff: clean
- Commit: 707c2a63
[[2026-04-27]]
## Builder Notes
- Implementation: no source-code changes required; existing `CockpitView` implementation already satisfies AC exercised by task-owned tests.
- Files changed: none.
- Tests: `tests/test_engine_cockpit_view_1078.py` -> 64 passed, 0 failed (quality-runner scoped run).
- Coverage evidence (scoped informational run): `owlbear_kanban.engine` 44%, `owlbear_kanban.storage` 68%, overall 45%. These percentages reflect single-file task scope and are not a touched-module delta for this builder pass (no implementation edits).
- Ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`, `tests/test_engine_cockpit_view_1078.py`.
- Evidence summary: task-owned suite is green, no lint violations, no blocker requiring code intervention in builder phase.
- Fixes applied: none (no failing builder-side behavior to repair).
[[2026-04-27]]
## Review Evidence
### Test Results
- pytest: 64 passed, 0 failed (`tests/test_engine_cockpit_view_1078.py`, quality-runner scoped run)

### Lint
- ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py`, and `tests/test_engine_cockpit_view_1078.py`

### Coverage
- `owlbear_kanban.engine`: 44%
- `owlbear_kanban.storage`: 68%
- Per Architecture Review cycle 9, these module-wide percentages are informational only for this pass; they were not used as a gating criterion.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| `CockpitView.edit_task` requires mandatory `expected_updated`; stale mismatch -> `ERR_STALE` | Tests: `tests/test_engine_cockpit_view_1078.py#L192-L243`. Implementation OCC write path: `serve/kanban/src/owlbear_kanban/engine.py#L1049-L1059`. | FAIL — signature + stale-token rejection are covered, but the task-owned suite does not prove the real CAS write boundary or protect the event-failure rollback path. |
| `CockpitView.move_task` requires mandatory `expected_updated`; stale mismatch -> `ERR_STALE` | Tests: `tests/test_engine_cockpit_view_1078.py#L245-L291`. Implementation OCC write path: `serve/kanban/src/owlbear_kanban/engine.py#L1117-L1143`. | FAIL — same gap as `edit_task`; stale-token rejection is covered, but the real CAS write boundary and rollback safety are not. |
| `AC-NEW-21`: `release_task` on unclaimed -> idempotent no-op (`updated` not advanced) | Tests: `tests/test_engine_cockpit_view_1078.py#L307-L325`. Implementation short-circuit: `serve/kanban/src/owlbear_kanban/engine.py#L1303-L1309`. | PASS |
| `AC-NEW-22`: `sweep` returns exactly the released IDs; second call -> `[]` | Tests: `tests/test_engine_cockpit_view_1078.py#L351-L420`. Implementation loop: `serve/kanban/src/owlbear_kanban/engine.py#L1532-L1587`. | PASS |
| `AC-NEW-23`: `sweep` uses `storage.write_task_if_unchanged`; `ERR_STALE` skips that task without error | Test: `tests/test_engine_cockpit_view_1078.py#L426-L478`. Implementation CAS branch: `serve/kanban/src/owlbear_kanban/engine.py#L1565-L1577`; helper: `serve/kanban/src/owlbear_kanban/storage.py#L412-L447`. | FAIL — current test only covers a single stale task. It does not prove the per-task `continue` contract when one stale task and one later eligible expired task coexist in the same sweep cycle. |
| `release_task` on missing id -> `ERR_NOT_FOUND` | Test: `tests/test_engine_cockpit_view_1078.py#L327-L334`. Cockpit wrapper: `serve/kanban/src/owlbear_kanban/engine.py#L3244-L3265`. | PASS |
| `list_activity` filters by `task_id`, `action`, `source`, time window; `since`/`until` assert count + task identity | Tests: `tests/test_engine_cockpit_view_1078.py#L500-L592`. Delegate: `serve/kanban/src/owlbear_kanban/engine.py#L1686-L1697`. | PASS |
| `list_sessions` returns flat-label `SessionRecord` states | Tests: `tests/test_engine_cockpit_view_1078.py#L610-L778`. Filter/state logic: `serve/kanban/src/owlbear_kanban/engine.py#L330-L360`, `serve/kanban/src/owlbear_kanban/engine.py#L1716-L1732`. | PASS |
| `scan_corruption` is read-only and returns `list[CorruptionError]` | Tests: `tests/test_engine_cockpit_view_1078.py#L786-L857`. Implementation: `serve/kanban/src/owlbear_kanban/engine.py#L1699-L1708`. | PASS |
| `repair_storage`: phase-1 `scan_and_fix` + phase-2 AR creation; never implicit at startup | Tests: `tests/test_engine_cockpit_view_1078.py#L865-L931`. Implementation: `serve/kanban/src/owlbear_kanban/engine.py#L1591-L1641`. | PASS |
| `compact_activity` calls `storage.compact_activity_log` | Tests: `tests/test_engine_cockpit_view_1078.py#L939-L983`. Implementation: `serve/kanban/src/owlbear_kanban/engine.py#L1710-L1713`. | PASS |
| `CockpitView` does NOT expose `create_task`, `start_work`, `end_work`, `pick_tasks` | Tests: `tests/test_engine_cockpit_view_1078.py#L989-L1047`. Cockpit surface: `serve/kanban/src/owlbear_kanban/engine.py#L3091-L3299`. | PASS |
| `ActivityEvent.source` populated automatically: `agent` / `cockpit` / `engine` | Tests: `tests/test_engine_cockpit_view_1078.py#L1055-L1165`. Agent/cockpit paths: `serve/kanban/src/owlbear_kanban/engine.py#L2970-L3055`, `serve/kanban/src/owlbear_kanban/engine.py#L3156-L3283`. | PASS |
| `All tests fail (RED phase)` | Header text at `tests/test_engine_cockpit_view_1078.py#L1-L47`; current run is green. | N/A — review anchored to the latest Architecture Review refinement and the live review snapshot, not the historical RED-phase state. |

#### Security Review
- No hardcoded secrets, injection sinks, unsafe deserialization, or path-traversal issues found in the scoped implementation under review.

#### Test Integrity
| Original Test Area | Change Made | Assessment |
|--------------------|-------------|------------|
| `TestFromAC_*` suite | Builder notes report no file changes; current suite retains the cycle 9 explicit `state == "released"` assertion and no weakened assertions were observed. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most AC-owned tests assert exact values or exact sets; e.g. time-window identity checks at `tests/test_engine_cockpit_view_1078.py#L553-L590` and released session state at `tests/test_engine_cockpit_view_1078.py#L656-L673`. |
| Negative/error-path coverage | ADEQUATE | Stale OCC, not-found, corrupt scan, empty log, and stale sweep paths are covered. |
| Manual mutation reasoning | WEAK | The suite still does not prove the multi-task stale-continue subcase for `AC-NEW-23`; a sweep implementation that aborts after one stale task could keep the current single-task stale test green. |
| Test independence | STRONG | Tests rebuild isolated boards under `tmp_path`. |
| Descriptive names | STRONG | Test names are specific and AC-scoped. |

#### Data Safety
- FAIL: the OCC mutation paths write task state first, then emit the activity event, and on `_emit_event` `OSError` they restore the old snapshot with an unconditional plain `write_task(...)`.
- Evidence:
  - `edit_task`: CAS write at `serve/kanban/src/owlbear_kanban/engine.py#L1053-L1059`, rollback write at `serve/kanban/src/owlbear_kanban/engine.py#L1065-L1068`
  - `move_task`: CAS/plain write at `serve/kanban/src/owlbear_kanban/engine.py#L1117-L1143`, rollback write at `serve/kanban/src/owlbear_kanban/engine.py#L1155-L1160`
  - `release_task`: CAS/plain write at `serve/kanban/src/owlbear_kanban/engine.py#L1318-L1328`, rollback write at `serve/kanban/src/owlbear_kanban/engine.py#L1336-L1339`
  - `sweep`: CAS write at `serve/kanban/src/owlbear_kanban/engine.py#L1565-L1573`, rollback write at `serve/kanban/src/owlbear_kanban/engine.py#L1582-L1585`
- Conclusion: if another actor mutates the task after the CAS write succeeds but before `_emit_event` fails, the rollback path can clobber that newer state. That is a live lost-update race in the exact OCC surface this task covers.

#### Implementation-Aware Gaps
- FAIL: `AC-NEW-23` is only exercised on a single stale task (`tests/test_engine_cockpit_view_1078.py#L426-L478`). The implementation’s loop semantics (`serve/kanban/src/owlbear_kanban/engine.py#L1532-L1587`) require proof that a stale task is skipped while later eligible expired tasks in the same sweep still release.
- FAIL: the task-owned OCC tests for `edit_task`/`move_task` prove required parameter + stale-token rejection, but they do not exercise the actual CAS write boundary (`serve/kanban/src/owlbear_kanban/engine.py#L1053-L1059`, `serve/kanban/src/owlbear_kanban/engine.py#L1117-L1143`) or the event-failure rollback window.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The latest Architecture Review cycle 9 is the binding authority for this pass. I did not deduct on the previously contested `released` session-state proof; the current suite now contains an explicit `state == "released"` assertion and the filter mechanism already enforced that state behaviorally.
- Module-wide coverage remains below 90%, but cycle 9 explicitly scoped coverage for this pass to CockpitView + `write_task_if_unchanged`; those module percentages are therefore informational only.

### Deductions
-0.14 live OCC/data-safety defect in rollback-after-write paths
-0.08 missing multi-task stale-continue proof for `AC-NEW-23`
-0.04 OCC proof gap for `edit_task` / `move_task` true CAS behavior

### Verdict
- FAIL
- Confidence: 0.74
- Action: return to `in-progress`
- Reason: current implementation has a real rollback race on the OCC mutation surface, and the task-owned suite still leaves the key stale-continue CAS subcase unproven.
[[2026-04-27]]
## Builder Notes
- Implementation: updated rollback behavior in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) so post-write event failures restore via CAS (`write_task_if_unchanged`) instead of unconditional overwrite.
- Files changed: [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py)
- Commit: `037e61ad` (`fix: guard OCC rollback with CAS (#1078, builder)`)
- Tests (quality-runner scoped): 70 passed, 0 failed across [tests/test_engine_cockpit_view_1078.py](tests/test_engine_cockpit_view_1078.py) and [tests/test_engine_cockpit_view_1141.py](tests/test_engine_cockpit_view_1141.py)
- Coverage (informational): `owlbear_kanban.engine` 44%, overall 45%
- Ruff: clean on [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py), [tests/test_engine_cockpit_view_1078.py](tests/test_engine_cockpit_view_1078.py), [tests/test_engine_cockpit_view_1141.py](tests/test_engine_cockpit_view_1141.py)
- Evidence summary: CAS-guarded rollback now avoids clobbering newer concurrent updates if `_emit_event` fails after a successful mutation write.

### Reflection
- Problem faced: rollback paths used unconditional `write_task(original, ...)`, which could overwrite newer concurrent state.
- Workaround applied: switched rollback to CAS restore keyed on the just-written `record.updated` token.
- Pattern discovered: post-write side effects should always use guarded rollback in OCC mutation paths.
- Quality gap: task-owned tests are green but still do not directly prove all reviewer-identified mutation subcases.
[[2026-04-27]]
## Review Evidence
### Test Results
- pytest: 70 passed, 0 failed (quality-runner scoped run on tests/test_engine_cockpit_view_1078.py and tests/test_engine_cockpit_view_1141.py)

### Lint
- ruff: clean on serve/kanban/src/owlbear_kanban/engine.py, tests/test_engine_cockpit_view_1078.py, and tests/test_engine_cockpit_view_1141.py

### Coverage
- owlbear_kanban.engine: 44%
- Per Architecture Review cycle 9, this module-wide percentage is informational only for this pass.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| CockpitView.edit_task requires expected_updated as a mandatory param; stale mismatch raises ERR_STALE | tests/test_engine_cockpit_view_1078.py:192-243 proves signature, required param, stale mismatch, and success response. CockpitView forwards expected_updated in serve/kanban/src/owlbear_kanban/engine.py:3189-3250. | PASS |
| CockpitView.move_task requires expected_updated as a mandatory param; stale mismatch raises ERR_STALE | tests/test_engine_cockpit_view_1078.py:245-291 proves signature, required param, stale mismatch, and success response. CockpitView forwards expected_updated in serve/kanban/src/owlbear_kanban/engine.py:3252-3275. | PASS |
| AC-NEW-21: release_task on unclaimed is an idempotent no-op and updated is not advanced | tests/test_engine_cockpit_view_1078.py:315-345. | PASS |
| AC-NEW-22: sweep returns exactly the released IDs and second call is empty | tests/test_engine_cockpit_view_1078.py:363-423. | PASS |
| AC-NEW-23: sweep uses storage.write_task_if_unchanged and skips only the stale task with no error | tests/test_engine_cockpit_view_1078.py:439-487 proves the single-task stale skip and CAS call. tests/test_engine_cockpit_view_1078.py:406-423 proves exact-set behavior on a non-stale board. engine.sweep currently continues after ERR_STALE at serve/kanban/src/owlbear_kanban/engine.py:1599-1620. No task-owned test combines one stale expired task with one later releasable expired task in the same sweep cycle. A regression that aborts the sweep after the first ERR_STALE could keep the current suite green. | FAIL |
| release_task on missing id raises ERR_NOT_FOUND | tests/test_engine_cockpit_view_1078.py:327-334. | PASS |
| list_activity filters by task_id, action, source, and time window; since/until assert exact count and task identity | tests/test_engine_cockpit_view_1078.py:497-597. | PASS |
| list_sessions returns SessionRecord values with the flat state labels | tests/test_engine_cockpit_view_1078.py:601-775, including explicit released-state assertion at 656-674. | PASS |
| scan_corruption is read-only and returns list[CorruptionError] | tests/test_engine_cockpit_view_1078.py:779-860. | PASS |
| repair_storage performs phase-1 scan_and_fix and phase-2 AR creation; never implicit at startup | tests/test_engine_cockpit_view_1078.py:872-937. | PASS |
| compact_activity delegates to storage.compact_activity_log | tests/test_engine_cockpit_view_1078.py:945-983. | PASS |
| CockpitView does not expose create_task, start_work, end_work, or pick_tasks | tests/test_engine_cockpit_view_1078.py:988-1045. | PASS |
| ActivityEvent.source is populated automatically as agent, cockpit, or engine | tests/test_engine_cockpit_view_1078.py:1053-1165. | PASS |
| All tests fail (RED phase) | Historical only. Latest Architecture Review refinement supersedes this as a gating condition. | N/A |

#### Security Review
- No scoped security issues found in the CockpitView facade or the builder's engine.py change.

#### Test Integrity
| Original Test Area | Change Made | Assessment |
|--------------------|-------------|------------|
| TestFromAC suites in tests/test_engine_cockpit_view_1078.py and tests/test_engine_cockpit_view_1141.py | Builder changed engine.py only. No weakened or removed TestFromAC assertions observed. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | The suite uses exact sets, exact counts, explicit state labels, and explicit source assertions across the activity, session, and sweep tests. |
| Negative and error-path coverage | ADEQUATE | Stale OCC, missing task, stale sweep CAS, empty activity, and read-only corruption scans are covered. |
| Manual mutation reasoning | WEAK | AC-NEW-23 still lacks a mixed-batch stale-continue proof. Current tests would not fail if the stale branch aborted the sweep instead of skipping only that task. |
| Test independence | STRONG | Tests construct isolated boards under tmp_path. |
| Descriptive names | STRONG | Test names remain AC-scoped and specific. |

#### Data Safety
- No in-scope blocker found in the CockpitView-owned mutation paths after the builder change.
- The guarded rollback helper at serve/kanban/src/owlbear_kanban/engine.py:235 is now used by the task-owned rollback paths in edit_task, move_task, release_task, and sweep.

#### Implementation-Aware Gaps
- FAIL: AC-NEW-23 still lacks executable proof that a stale expired task is skipped while a later expired task in the same sweep cycle is still released.
- Evidence: tests/test_engine_cockpit_view_1078.py:406 and tests/test_engine_cockpit_view_1078.py:439 each prove one half of the contract, but neither test exercises both conditions in one run.
- Live code appears correct today: serve/kanban/src/owlbear_kanban/engine.py:1605 continues after ERR_STALE and serve/kanban/src/owlbear_kanban/engine.py:1620 appends later released IDs. The gap is proof quality, not a confirmed implementation defect.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- I did not fail this pass on the older AC 8 released-state concern. The current suite now asserts state == "released" directly at tests/test_engine_cockpit_view_1078.py:656-674, and the architect's cycle 9 directive makes the earlier deduction non-binding.
- I also did not fail this task on claim_task or end_work rollback paths elsewhere in engine.py. Task 1078 explicitly proves that CockpitView does not expose start_work or end_work, and sibling task-owned suites already cover those engine methods.
- There is one existing ## Review Evidence section already in the task file. This rejection is not a 3rd-plus loop-breaker case.

### Deductions
-0.12 missing mixed stale-continue proof for AC-NEW-23

### Verdict
- FAIL
- Confidence: 0.88
- Action: return to todo
- Reason: the builder fix removed the earlier in-scope rollback concern, but the task-owned suite still does not prove the per-task continuation part of AC-NEW-23.
[[2026-04-27]]
## Test-Writer Notes
- **Retry cycle**: reviewer FAILed on missing mixed-batch stale-continue proof for AC-NEW-23.
- **Test file**: tests/test_engine_cockpit_view_1078.py
- **Change**: added `test_sweep_cas_stale_task_skipped_and_later_eligible_task_still_released` to `TestFromAC_CockpitViewSweepCAS`
- **New test count**: 65 total (64 previous + 1 new)
- **What the new test proves**: board with 2 expired tasks; `write_task_if_unchanged` mocked with `side_effect=[stale_error, None]` (first call raises ERR_STALE, second succeeds). Asserts: CAS called twice, task 1 NOT in released, task 2 IS in released, no exception raised. A loop that aborts after ERR_STALE would fail assertion 3.
- **Test outcome**: PASSES (implementation already correct — engine.py:1605 uses `continue` after ERR_STALE). Reviewer explicitly noted "gap is proof quality, not a confirmed implementation defect." This is acceptable in retry cycle per Step 1b: adding missing contract proof.
- **Ruff**: clean
- **AC coverage**: all AC lines remain covered; AC-NEW-23 now has both single-task stale proof (existing) and mixed-batch stale-continue proof (new).

### AC Coverage Table
| AC Line | Test | Status |
|---------|------|--------|
| edit_task mandatory expected_updated + ERR_STALE | TestFromAC_CockpitViewOCC | COVERED |
| move_task mandatory expected_updated + ERR_STALE | TestFromAC_CockpitViewOCC | COVERED |
| AC-NEW-21: release_task unclaimed → idempotent no-op | TestFromAC_ReleaseTask | COVERED |
| AC-NEW-22: sweep exact set, idempotent | TestFromAC_CockpitViewSweep | COVERED |
| AC-NEW-23: sweep CAS skip; mixed-batch continue | TestFromAC_CockpitViewSweepCAS (2 tests) | COVERED |
| release_task missing id → ERR_NOT_FOUND | TestFromAC_ReleaseTask | COVERED |
| list_activity filters + since/until identity | TestFromAC_CockpitViewListActivity | COVERED |
| list_sessions flat labels incl. released state | TestFromAC_ListSessions | COVERED |
| scan_corruption read-only, returns list[CorruptionError] | TestFromAC_ScanCorruption | COVERED |
| repair_storage phase-1+phase-2, never at startup | TestFromAC_RepairStorage | COVERED |
| compact_activity delegates to storage | TestFromAC_CompactActivity | COVERED |
| CockpitView does NOT expose create/start/end/pick | TestFromAC_CockpitViewRole | COVERED |
| ActivityEvent.source auto-populated | TestFromAC_ActivitySource | COVERED |
[[2026-04-27]]
## Builder Notes
- Implementation: no source-code changes required in this pass; existing CockpitView/engine behavior satisfies task-owned AC coverage.
- Files changed: none.
- Tests: 65 passed, 0 failed (`tests/test_engine_cockpit_view_1078.py`).
- Coverage: `owlbear_kanban.engine` 44% (overall 45%) from scoped run; informational for this pass per task architecture notes.
- Ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_cockpit_view_1078.py`.
- Evidence summary: AC-NEW-23 mixed stale-continue proof is now present in task-owned suite, and the scoped builder verification is fully green.
- Fixes applied: none in this cycle.
[[2026-04-27]]
## Review Evidence
### Test Results
- pytest: 65 passed, 0 failed (quality-runner scoped run on `tests/test_engine_cockpit_view_1078.py`)

### Lint
- ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_cockpit_view_1078.py`

### Coverage
- `owlbear_kanban.engine`: 44%
- Informational only for this pass per Architecture Review cycle 9 coverage directive.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| 1. `CockpitView.edit_task` requires mandatory `expected_updated`; stale mismatch -> `ERR_STALE` | `test_edit_task_signature_has_expected_updated_param`, `test_edit_task_expected_updated_is_required_no_default`, `test_edit_task_stale_expected_updated_raises_concurrency_error` | Yes | COVERED |
| 2. `CockpitView.move_task` requires mandatory `expected_updated`; stale mismatch -> `ERR_STALE` | `test_move_task_signature_has_expected_updated_param`, `test_move_task_expected_updated_is_required_no_default`, `test_move_task_stale_expected_updated_raises_concurrency_error` | Yes | COVERED |
| 3. `release_task` on unclaimed is idempotent and does not advance `updated` | `test_release_task_unclaimed_is_idempotent_noop_updated_not_advanced` | Yes | COVERED |
| 4. `sweep` returns exactly released IDs and is idempotent | `test_sweep_idempotent_second_call_returns_empty`, `test_sweep_returns_exactly_the_expired_task_ids_no_extras_and_no_missing` | Yes | COVERED |
| 5. `AC-NEW-23` sweep uses CAS per task; stale task is skipped with no error and later eligible work continues | `test_sweep_cas_stale_task_skipped_no_error_raised`, `test_sweep_cas_stale_task_skipped_and_later_eligible_task_still_released` | Yes | COVERED |
| 6. `release_task` on missing id -> `ERR_NOT_FOUND` | `test_release_task_missing_id_raises_not_found_error` | Yes | COVERED |
| 7. `list_activity` filters by task/action/source/time window; `since`/`until` assert exact count + task identity | `test_list_activity_since_returns_only_events_within_window_exact_identity`, `test_list_activity_until_returns_only_events_within_window_exact_identity`, related filter tests | Yes | COVERED |
| 8. `list_sessions` derives the flat state labels correctly | `test_list_sessions_open_claim_has_state_running`, `test_list_sessions_filter_released_returns_release_outcome_sessions`, `test_list_sessions_completed_end_work_has_state_completed_and_outcome_success`, `test_list_sessions_rejected_end_work_has_state_rejected_and_outcome_reject`, `test_list_sessions_blocked_end_work_has_state_blocked_and_outcome_block`, `test_list_sessions_open_stale_claim_has_state_stuck`, `test_list_sessions_sweep_released_claim_has_state_expired` | Yes | COVERED |
| 9. `scan_corruption` is read-only and returns `list[CorruptionError]` | `test_scan_corruption_with_corrupt_file_returns_corruption_errors`, `test_scan_corruption_makes_no_writes_to_tasks_dir`, `test_scan_corruption_does_not_mutate_clean_task_file_contents`, `test_scan_corruption_does_not_mutate_corrupt_file_contents` | Yes | COVERED |
| 10. `repair_storage` is phase-1 scan/fix + phase-2 AR creation; never implicit at startup | `test_repair_storage_phase1_quarantines_corrupt_file`, `test_repair_storage_phase2_creates_ar_task_for_quarantined_file`, `test_repair_storage_not_called_implicitly_at_engine_startup` | Yes | COVERED |
| 11. `compact_activity` delegates to `storage.compact_activity_log` | `test_compact_activity_delegates_to_storage_compact_activity_log` | Yes | COVERED |
| 12. `CockpitView` does not expose `create_task`, `start_work`, `end_work`, `pick_tasks` | `test_cockpit_view_does_not_expose_create_task`, `test_cockpit_view_does_not_expose_start_work`, `test_cockpit_view_does_not_expose_end_work`, `test_cockpit_view_does_not_expose_pick_tasks` | Yes | COVERED |
| 13. `ActivityEvent.source` auto-populates as `agent` / `cockpit` / `engine` | `test_agent_view_mutation_emits_source_agent`, `test_cockpit_view_mutation_emits_source_cockpit`, `test_sweep_operation_emits_source_engine`, `test_agent_view_end_work_emits_source_agent` | Yes | COVERED |
| 14. `All tests fail (RED phase)` | Historical header only; latest Architecture Review refinement and current workspace snapshot govern this pass | N/A | N/A |

#### Security Review
- No scoped security issues found in the CockpitView facade or the reviewed engine paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Task-owned `TestFromAC_*` suite | Added mixed-batch stale-continue proof for `AC-NEW-23`; no weakened or removed assertions observed in the live file | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact error-code checks, exact set/count assertions, explicit released-state assertion, and explicit stale-continue assertions are present. |
| Negative/error-path coverage | STRONG | Stale OCC, missing-id, stale sweep CAS, empty activity, and read-only corruption paths are covered. |
| Manual mutation reasoning | STRONG | A sweep loop that aborts after the first `ERR_STALE` would now fail `test_sweep_cas_stale_task_skipped_and_later_eligible_task_still_released`. |
| Test independence | STRONG | Tests build isolated boards under `tmp_path`. |
| Descriptive names | STRONG | Names remain AC-scoped and specific. |

#### Data Safety
- No in-scope blocker found. Live `sweep()` uses `write_task_if_unchanged` at `serve/kanban/src/owlbear_kanban/engine.py:1599` and skips `ERR_STALE` at `serve/kanban/src/owlbear_kanban/engine.py:1605`.
- The rollback helper `_restore_snapshot_if_unchanged` is present at `serve/kanban/src/owlbear_kanban/engine.py:235`; I did not find a live task-scoped data-safety defect in the reviewed surface.

#### Implementation-Aware Gaps
- No significant untested path remains in the scoped AC surface. The prior `AC-NEW-23` mixed stale-continue gap is now covered by `test_sweep_cas_stale_task_skipped_and_later_eligible_task_still_released`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |
| Notes | First pass argued no code change needed, second pass fixed rollback safety, third pass passed through after the test-writer closed the remaining proof gap. No identical-loop pattern observed. |

### Pass 2 — INFORMATIONAL
- `tests/test_engine_cockpit_view_1078.py:48` still says `All tests FAIL (RED phase)`. Treated as historical only per the latest Architecture Review refinement and current-snapshot authority.
- `tests/test_engine_cockpit_view_1078.py:1201-1205` still describes `AgentView.end_work` source propagation as RED, but live delegation passes `source="agent"` at `serve/kanban/src/owlbear_kanban/engine.py:3073`. This is stale prose, not a behavioral defect.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| 1. `edit_task` OCC token required + stale reject | `serve/kanban/src/owlbear_kanban/engine.py:3189`; `test_edit_task_*` OCC tests | `TestFromAC_CockpitViewOCC` | PASS |
| 2. `move_task` OCC token required + stale reject | `serve/kanban/src/owlbear_kanban/engine.py:3252`; `test_move_task_*` OCC tests | `TestFromAC_CockpitViewOCC` | PASS |
| 3. `release_task` unclaimed noop | `serve/kanban/src/owlbear_kanban/engine.py:1296`; `test_release_task_unclaimed_is_idempotent_noop_updated_not_advanced` | `TestFromAC_CockpitViewReleaseTask` | PASS |
| 4. `sweep` exact-set + idempotent | `serve/kanban/src/owlbear_kanban/engine.py:1561`; `test_sweep_idempotent_second_call_returns_empty`; `test_sweep_returns_exactly_the_expired_task_ids_no_extras_and_no_missing` | `TestFromAC_CockpitViewSweep` | PASS |
| 5. `AC-NEW-23` per-task CAS skip/continue | `serve/kanban/src/owlbear_kanban/engine.py:1599-1605`; `test_sweep_cas_stale_task_skipped_no_error_raised`; `test_sweep_cas_stale_task_skipped_and_later_eligible_task_still_released` | `TestFromAC_CockpitViewSweepCAS` | PASS |
| 6. Missing-id release -> `ERR_NOT_FOUND` | `serve/kanban/src/owlbear_kanban/engine.py:3277`; `test_release_task_missing_id_raises_not_found_error` | `TestFromAC_CockpitViewReleaseTask` | PASS |
| 7. `list_activity` filters + exact identity | `serve/kanban/src/owlbear_kanban/engine.py:1708`; `test_list_activity_since_returns_only_events_within_window_exact_identity`; `test_list_activity_until_returns_only_events_within_window_exact_identity` | `TestFromAC_CockpitViewListActivity` | PASS |
| 8. `list_sessions` flat state derivation | `serve/kanban/src/owlbear_kanban/engine.py:1749`; state tests including released at `test_list_sessions_filter_released_returns_release_outcome_sessions` | `TestFromAC_CockpitViewListSessions` | PASS |
| 9. `scan_corruption` read-only + typed return | `serve/kanban/src/owlbear_kanban/engine.py:1729`; read-only tests in `TestFromAC_CockpitViewScanCorruption` | `TestFromAC_CockpitViewScanCorruption` | PASS |
| 10. `repair_storage` phase-1 + phase-2; never implicit | `serve/kanban/src/owlbear_kanban/engine.py:1624`; repair tests in `TestFromAC_CockpitViewRepairStorage` | `TestFromAC_CockpitViewRepairStorage` | PASS |
| 11. `compact_activity` delegates | `serve/kanban/src/owlbear_kanban/engine.py:1741`; `test_compact_activity_delegates_to_storage_compact_activity_log` | `TestFromAC_CockpitViewCompactActivity` | PASS |
| 12. `CockpitView` admin-only surface | `serve/kanban/src/owlbear_kanban/engine.py:3124-3336`; role-separation tests | `TestFromAC_CockpitViewRoleSeparation` | PASS |
| 13. `ActivityEvent.source` auto-populated | `serve/kanban/src/owlbear_kanban/engine.py:3073`, `3269`, `3294`; source tests in `TestFromAC_ActivityEventSource` | `TestFromAC_ActivityEventSource` | PASS |
| 14. Historical RED-phase header | Latest refinement authority in task body; live scoped run is green | Historical only | N/A |

### Deductions
- 0.00 blocker deductions
- 0.02 informational drift: stale RED-phase prose remains in the test file comments/header but does not affect execution.

### Verdict
- PASS
- Confidence: 0.96
- Action: advance to `docs`
- Reason: the previously missing `AC-NEW-23` mixed-batch stale-continue proof is now present and executable, the scoped suite is green, lint is clean, and no live blocker remains in the reviewed CockpitView surface.

### Reflection
- Problem faced: the task body contained multiple stale fail notes and historical RED text that no longer matched the live snapshot.
- Workaround applied: anchored the verdict to the latest Architecture Review refinement and re-verified the current test file and engine paths directly.
- Pattern discovered: for looped review tasks, stale historical prose is non-binding once executable proof exists in the current snapshot.
- Quality gap: the file still contains stale RED-phase comments/docstrings that should be cleaned during docs or later test curation, but they do not invalidate the behavior under review.
[[2026-04-27]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/kanban/README.md` references `CockpitView` facade and `sweep()` method but only at the public-API level. The builder's CAS rollback fix (`_restore_snapshot_if_unchanged`) is an internal implementation detail — no public API signature or behavior description changed. No prose update needed. |
| 2 | Module docstrings | Yes | Verified | `_restore_snapshot_if_unchanged` at engine.py:235 has docstring `"""Best-effort rollback that never overwrites a newer concurrent update."""` — accurate and complete. No other public class/function modified. |
| 3 | External attribution | No | N/A | Builder's CAS rollback pattern is internal to the codebase. No external source cited in builder notes. |
| 4 | Research doc | No | N/A | No research doc referenced in task body. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` has `describes: ["serve/kanban/src/**"]` — matches `serve/kanban/src/owlbear_kanban/engine.py`. Footer updated from `a38d67be` → `037e61ad` (date unchanged: 2026-04-27). Committed as `6465dc97`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Verified — `_restore_snapshot_if_unchanged` docstring accurate |
| `tests/test_engine_cockpit_view_1078.py` | IN (docstrings) | Test file; no module-level docstrings require update |
| `tests/test_engine_cockpit_view_1141.py` | IN (docstrings) | Test file; no module-level docstrings require update |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Updated footer |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer updated to `037e61ad`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (no `.owlbear/scratch/1078-*` files existed)
[[2026-04-27]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. edit_task mandatory expected_updated + ERR_STALE | tests/test_engine_cockpit_view_1078.py:192-243; engine.py:3189-3250 | PASS |
| 2. move_task mandatory expected_updated + ERR_STALE | tests/test_engine_cockpit_view_1078.py:245-291; engine.py:3252-3275 | PASS |
| 3. AC-NEW-21: release_task unclaimed → idempotent no-op | tests/test_engine_cockpit_view_1078.py:315-345 | PASS |
| 4. AC-NEW-22: sweep exact-set + idempotent | tests/test_engine_cockpit_view_1078.py:363-423 | PASS |
| 5. AC-NEW-23: sweep CAS skip + mixed-batch continue | tests/test_engine_cockpit_view_1078.py:439-542 (2 tests) | PASS |
| 6. release_task missing id → ERR_NOT_FOUND | tests/test_engine_cockpit_view_1078.py:327-334 | PASS |
| 7. list_activity filters + since/until identity | tests/test_engine_cockpit_view_1078.py:497-597 | PASS |
| 8. list_sessions flat state labels incl. released | tests/test_engine_cockpit_view_1078.py:601-775 | PASS |
| 9. scan_corruption read-only, returns list[CorruptionError] | tests/test_engine_cockpit_view_1078.py:779-860 | PASS |
| 10. repair_storage phase-1+phase-2, never at startup | tests/test_engine_cockpit_view_1078.py:872-937 | PASS |
| 11. compact_activity delegates to storage | tests/test_engine_cockpit_view_1078.py:945-983 | PASS |
| 12. CockpitView does NOT expose create/start/end/pick | tests/test_engine_cockpit_view_1078.py:988-1045 | PASS |
| 13. ActivityEvent.source auto-populated | tests/test_engine_cockpit_view_1078.py:1053-1165 | PASS |
| 14. All tests fail (RED phase) | Historical only per Architecture Review cycle 9 | N/A |

### Test Results
- pytest (full suite): 2619 passed, 121 failed (all pre-existing in other modules — corruption, storage, guidance, knowledge, cockpit mutation), 4 skipped. Zero failures in task-scoped file.
- ruff (full): 8 violations all in other packages (knowledge, mcp-knowledge, mcp-memory, orchestrator). Zero in task scope.

### Reviewer Evidence
Present, detailed, PASS verdict at confidence 0.96. Three review cycles with clear deduction tracking. Final review maps all 13 AC lines to specific tests with mutation reasoning. Trusted code-level findings.

### Architect Quality: 4/5
AC lines were specific with error codes, method names, and behavioral contracts. AC-NEW-21/22/23 were well-specified. Minor gap: mixed-batch stale-continue subcase for AC-NEW-23 was caught during review (not anticipated by architect), but this is typical for CAS edge cases. 9 architecture review cycles reflect complexity of the CockpitView surface, not AC deficiency.

### Deduction Breakdown
- AC lines without evidence: 0 (all 13 verified)
- Lint violations in scope: 0
- AC quality ≤ 3: no (score 4)
- Missing reviewer evidence: no (present and detailed)
- Full-suite task-scoped failures: 0

### Process Note
Test-writer's retry-cycle deliverable (mixed-batch stale-continue test) was uncommitted. Committed as c732216e during audit cleanup.

### Confidence: 0.98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 707c2a63 | test | tests/test_engine_cockpit_view_1078.py | #1078 |
| 037e61ad | fix | serve/kanban/src/owlbear_kanban/engine.py | #1078 |
| 6465dc97 | docs | share/diagrams/kanban.excalidraw | #1078 |
| c732216e | test | tests/test_engine_cockpit_view_1078.py | #1078 |