---
id: 1054
title: 'C-09: RED — engine activity/session tests'
status: archived
priority: medium
created: 2026-04-21T10:42:50.316514+00:00
updated: 2026-04-23T01:49:36.152687+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief C (#1043) — paper-c.md §8.9
Module: `serve/kanban/tests/test_engine_activity.py`

## Acceptance Criteria

- [ ] AC-C42: Engine methods emit `ActivityEvent` entries via `append_activity_event` for claim/edit/move/end_work/sweep actions
- [ ] AC-C43: `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl` with `active`/`all`/`blocked-or-rejected`/`released` semantics matching §7.2
- [ ] Fresh canonical stream — no legacy migration of old activity history
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes

**Third attempt** — added 2 genuinely failing tests to resolve RED phase.

**File:** `serve/kanban/tests/test_engine_activity.py`

**Context:** The 22 tests from the previous retry were all PASSING because the builder had already implemented AC-C42 and AC-C43. Identified two behavioral gaps between the normative spec (paper-c.md §7.2) and the implementation:

1. **Sweep-released session visibility** — §7.2 specifies that `sweep-release` closes a session that must be visible in `list_sessions(filter="all")`. Current implementation silently drops sweep-closed sessions (no `WorkSession` appended in `_collect_task_sessions` for `sweep-release`).
2. **Unknown filter validation** — AC-C43 defines a closed set of filters (`active`/`all`/`failed-or-rejected`/`released`). Unknown filter names should raise `ValueError`; current implementation silently returns all sessions.

**New tests (both FAIL):**
- `test_ac_c43_sweep_released_session_visible_in_all_filter` — FAIL: no session produced for sweep-released task
- `test_ac_c43_unknown_filter_raises_value_error` — FAIL: no ValueError raised for unknown filter

**Results:** 24 tests total — 22 PASS, 2 FAIL (RED ✓). Ruff clean.

**AC coverage:**

| AC | Tests | Status |
|----|-------|--------|
| AC-C42: emit ActivityEvent for claim/edit/move/end_work/sweep | 8 tests | PASS (implementation done) |
| AC-C43: list_sessions WorkSession contract | 12 tests | PASS (implementation done) |
| AC-C43: sweep-released sessions visible | 1 test | **FAIL (RED)** |
| AC-C43: unknown filter raises ValueError | 1 test | **FAIL (RED)** |
| Fresh canonical stream | 1 test | PASS (implementation done) |
[[2026-04-22]]
## Builder Notes
- Implementation: no code changes required in this run; behaviors are already present in `serve/kanban/src/owlbear_kanban/engine.py`.
- Tests: 24 passed in scoped run of `serve/kanban/tests/test_engine_activity.py`; the two retry-context tests pass.
- Coverage: scoped quality-runner report returned package-level 34% (`owlbear_kanban`); no module edits were made in this run.
- Ruff: clean on scoped lint path.
- Evidence summary: `list_sessions(filter=...)` validates unknown filter names via `_validate_session_filter` and raises `ValueError`; `_collect_task_sessions` handles `sweep-release` in `_CLOSE_ACTIONS` and appends a closed `SessionRecord`, making sweep-released sessions visible in `filter="all"`.

- Reflection: incoming retry context was stale relative to current branch state.
- Reflection: validating RED before edits prevented unnecessary churn.
- Reflection: search-based verification quickly confirmed contract alignment between tests and engine logic.
[[2026-04-22]]
## Review Evidence
### Test Results
- Parallel fan-out note: code-reader returned no response, so I fell back to sequential review.
- Scoped quality-runner on serve/kanban/tests/test_engine_activity.py: 24 passed, 0 failed, 0 skipped.
- Broader related quality context on serve/kanban/tests/test_engine_activity.py, serve/kanban/tests/test_list_sessions.py, and serve/kanban/tests/test_activity_store.py: 80 passed, 18 failed. Those 18 failures are in pre-existing list_sessions contract tests and were used as context only, not as the sole gate for this task.

### Lint
- Scoped lint: clean.
- Broader related lint: clean.

### Coverage
- Scoped coverage: owlbear_kanban.engine 50%.
- Broader related coverage context: owlbear_kanban.engine 51%, owlbear_kanban.activity_store 98%.
- No builder source edit was evidenced in this run, so coverage is contextual rather than the primary rejection reason.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C42: Engine methods emit ActivityEvent entries for claim, edit, move, end_work, and sweep actions | serve/kanban/tests/test_engine_activity.py:101,113,126,138,150,167,182,207 | Yes. These tests would fail if the engine stopped emitting the expected action entries or omitted required ActivityEvent fields. | COVERED |
| AC-C43: list_sessions derives SessionRecord values from activity.jsonl with active, all, blocked-or-rejected, and released semantics | serve/kanban/tests/test_engine_activity.py:236,250,275,290,304,318,404,429,445,452,466,484 | Partly. The dedicated file covers derivation, state mapping, source-of-truth, empty-log, sweep visibility, and unknown-filter validation, but it does not create a true stuck session for the active-filter branch. | LAX |
| AC-C43: active filter semantics include both running and stuck sessions | serve/kanban/tests/test_engine_activity.py:332 | No. The test claims to cover running and stuck, but it only creates one running open session at lines 339 to 340 and one closed success session at line 341 before asserting states at line 344. The separate engine branch for age-based stuck classification lives in serve/kanban/src/owlbear_kanban/engine.py:130,135,165,210 and is not directly exercised here. | MISSING |
| Fresh canonical stream, no legacy migration of old activity history | serve/kanban/tests/test_engine_activity.py:207 | Yes. The test asserts a fresh board has no pre-seeded activity log and only sees engine-produced activity entries. | COVERED |
| All tests fail, RED phase, no implementation exists yet | .owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:31 and serve/kanban/tests/test_engine_activity.py:5 | No. Independent scoped execution produced 24 passed, 0 failed. The implementation already exists and the RED-phase acceptance line is stale. | MISSING |

#### Security Review
- No issues found in the reviewed engine and test paths. The inspected code is local filesystem activity logging and filter validation, with no secrets, shell injection, path traversal, eval, exec, or unvalidated network boundary introduced in serve/kanban/src/owlbear_kanban/engine.py:130 to 236 and 808 to 1179.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suite in serve/kanban/tests/test_engine_activity.py | Current workspace still contains the third-attempt tests at lines 466 and 484. No weakening or removal was visible in the current snapshot. Historical diff was not available through reviewer tools. | PRESERVED in current state |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Tests assert action names, state names, task ids, ValueError behavior, and required fields rather than using only truthiness checks. |
| Negative and error-path coverage | ADEQUATE | Unknown-filter validation is covered at serve/kanban/tests/test_engine_activity.py:484 and empty-log behavior at line 445. |
| Manual mutation reasoning | WEAK | If serve/kanban/src/owlbear_kanban/engine.py:135 were changed to always return running, the active-filter test at serve/kanban/tests/test_engine_activity.py:332 to 347 would still pass because it never creates a stale session. Existing related tests treat stuck classification as a distinct branch at serve/kanban/tests/test_list_sessions.py:251 and 265. |
| Test independence | STRONG | Each test uses tmp_path and a fresh board helper. |
| Descriptive names | STRONG | Test names are explicit and AC-aligned. |

#### Data Safety
- No task-local data-safety issue found in the reviewed engine paths.

#### Implementation-Aware Gaps
- Missing direct TestFromAC coverage for the stuck-session derivation branch that powers active-filter semantics. The engine computes running versus stuck in serve/kanban/src/owlbear_kanban/engine.py:130 to 135 and uses that logic when sessions remain open at lines 165 and 210. The dedicated task file does not force that branch.
- The task contract itself is stale. The task body still requires failing RED tests at .owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:31, and the module header repeats the same assumption at serve/kanban/tests/test_engine_activity.py:5, but the independently verified behavior is green already.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- The task body misstates the canonical filter as failed-or-rejected at .owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:42, while the Brief C contract names blocked-or-rejected at .owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:640 and AC-C43 at line 732. Engine currently keeps a compatibility alias in serve/kanban/src/owlbear_kanban/engine.py:220 to 225, so the dedicated tests still pass.
- Broader related suite context shows 18 pre-existing failures in serve/kanban/tests/test_list_sessions.py around legacy WorkSession field and state expectations. That is background session-contract drift, not a builder regression in this task, but it supports routing this stale RED task back to backlog for architectural rescoping.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C42 | Engine emits edit, move, claim, release, end_work, and sweep-release activity events in serve/kanban/src/owlbear_kanban/engine.py:808,849,890,915,1053,1096 via _emit_event at 1160 to 1173. Scoped quality-runner reported 24 passed, 0 failed. | test_ac_c42_claim_task_emits_activity_event; test_ac_c42_end_work_emits_activity_event; test_ac_c42_move_task_emits_activity_event; test_ac_c42_edit_task_emits_activity_event; test_ac_c42_sweep_emits_activity_event; test_ac_c42_activity_event_has_source_field; test_ac_c42_activity_event_schema_matches_activity_event_model; test_ac_c42_no_legacy_activity_log_format_after_fresh_start | PASS |
| AC-C43 | Brief C defines active, all, blocked-or-rejected, and released semantics plus expired close handling in .owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:608,621,632,636,640,647,732. Engine validates filters in serve/kanban/src/owlbear_kanban/engine.py:228 and derives sessions in lines 138 to 236 and 1179 to 1236. The dedicated task tests pass for many subcases, but the active-filter stuck branch is not directly exercised. | test_ac_c43_list_sessions_returns_session_records; test_ac_c43_session_record_has_required_fields; test_ac_c43_session_state_completed_on_success_end_work; test_ac_c43_session_state_blocked_on_block_end_work; test_ac_c43_session_state_rejected_on_reject_end_work; test_ac_c43_session_state_released_on_release; test_ac_c43_filter_active_returns_running_and_stuck; test_ac_c43_filter_all_returns_every_session; test_ac_c43_filter_blocked_or_rejected; test_ac_c43_filter_released; test_ac_c43_sessions_derived_from_activity_not_task_files; test_ac_c43_task_status_at_start_captured_from_activity_event; test_ac_c43_empty_activity_log_returns_empty_list; test_ac_c43_session_record_state_values_match_spec; test_ac_c43_sweep_released_session_visible_in_all_filter; test_ac_c43_unknown_filter_raises_value_error | FAIL |
| Fresh canonical stream | Fresh-start behavior is asserted in serve/kanban/tests/test_engine_activity.py:207 and compatible with the activity append path in serve/kanban/src/owlbear_kanban/engine.py:1160 to 1173. Scoped quality-runner passed. | test_ac_c42_no_legacy_activity_log_format_after_fresh_start | PASS |
| All tests fail, RED phase, no implementation exists yet | Task body at .owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:31 and module header at serve/kanban/tests/test_engine_activity.py:5 require a RED state. Independent scoped execution returned 24 passed, 0 failed, proving the phase contract is stale. | none | FAIL |

### Deductions
- 0.10: impossible RED acceptance line contradicted by independent test execution.
- 0.05: missing dedicated coverage for the active-filter stuck branch.
- 0.03: stale AC wording and surrounding session-contract drift reduce confidence that this task is correctly scoped for review.

### Confidence: 0.82
### Verdict: FAIL
### Action: Reject to backlog for architectural rescoping. The implementation is already green; the task should be rewritten or retired as a stale RED-phase artifact, with any remaining gap recast as a focused non-RED test task for active and stuck session semantics.
[[2026-04-22]]
## Architecture Review

### Root Cause Analysis

This task entered review with a structurally impossible AC: "All tests fail (RED phase — no implementation exists yet)." The builder's job is to make tests pass, but this AC says tests must stay failing — creating an unresolvable contradiction. This is the exact same pattern already resolved in sibling task #1095 (see its "Architecture Review (loop-breaker re-evaluation)" section on #1043).

The test-writing deliverable is complete: 24 tests committed covering AC-C42 (8 ActivityEvent emission tests) and AC-C43 (16 list_sessions tests realigned to SessionRecord by #1095). The implementation that satisfies them exists in `engine.py` from #1095's builder cycle.

### AC Refinement

**Retired AC:**
- ~~All tests fail (RED phase — no implementation exists yet)~~ — Structurally incompatible with pipeline. Same precedent as #1095 loop-breaker.

**Added AC:**
- No production source files modified — scope is `test_engine_activity.py` only

**Retained AC (AC-C42, AC-C43, fresh canonical stream):** All consistently PASS across review evidence. Test content is correct and committed.

### Tag Change Required

Replace `tdd:red` with `test` tag. The `test` tag is a pass-through for both test-writer and builder stages, preventing another loop. The test-writing work is already committed.

**MANUAL ACTION REQUIRED:** `edit_task` is not available in this session — tag change must be applied by orchestrator or user.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One test file, two AC groups (C42+C43) |
| Interface clarity | PASS | AC specifies ActivityEvent fields, SessionRecord type, filter names, state values |
| Dependency correctness | PASS | No upstream deps. #1063 depends on #1054 and will make remaining tests pass |
| Module layering | PASS | Test-only changes, no production code |
| TDD compliance | PASS | RED tests written and committed |
| KISS/YAGNI | PASS | Targeted test coverage for two AC groups |
| Premise challenge | PASS | Tests validate Brief C paper-c.md §7.2 and §8.9 contracts |
| Pattern consistency | PASS | Tests use SessionRecord per Brief C decisions.md |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban domain only |

### Test Quality Notes for Downstream

1. **Stuck-session coverage gap:** `test_ac_c43_filter_active_returns_running_and_stuck` (line 332) only creates a running session — it does not create an aged claim to trigger the stuck branch at `engine.py:130-138`. #1063's builder should ensure this branch is exercised, or create a follow-up if the gap persists.
2. **Stale wording:** Task body mentions "failed-or-rejected" at one point (historical from earlier retry); the tests correctly use "blocked-or-rejected" per §7.2.
3. **File header:** `test_engine_activity.py:5` still claims all tests fail because implementation doesn't exist — stale but cosmetic.

### Challenge Results
- Challenger: reconsider (confidence: 0.66)
- Findings: (1) stuck-session test gap overstated as "fully covered," (2) precedent supports routing fix but not completeness claim, (3) downstream wording (#1063 "RED tests") inconsistent, (4) stale wording remains, (5) public surface split
- Architect response: ACCEPTED on (1) and (2) — tightened coverage claims, documented stuck gap as downstream note. ACKNOWLEDGED on (3) and (4) — #1063's AC means "make these tests pass" not "tests must be failing now"; stale wording is cosmetic. REBUTTED on (5) — public surface split handled by #1063 and Brief B per #1043 impact matrix.

### Downstream Guidance

- **Test-writer:** Work complete. Verify test file exists and pass through.
- **Builder:** Test-only task. No source file modifications. Pass through.
- **Reviewer:** Scope quality-runner to `serve/kanban/tests/test_engine_activity.py` only. Legacy suite failures in `test_list_sessions.py` / `test_list_sessions_952.py` are from #1095's engine.py changes — those are #1063's concern, not #1054's.

### Verdict: APPROVE (with REFINE)
### Action: Advanced to todo. RED AC retired (loop cause). Tag change `tdd:red` → `test` required (manual).
[[2026-04-22]]
## Test-Writer Notes

**Pass-through** — per Architecture Review directive on this task: "Test-writer: Work complete. Verify test file exists and pass through."

**File:** `serve/kanban/tests/test_engine_activity.py` (489 lines, 24 tests)

**Verification:** File confirmed present at `serve/kanban/tests/test_engine_activity.py`.

**AC Coverage:**

| AC | Tests | Status |
|----|-------|--------|
| AC-C42: ActivityEvent emission for claim/edit/move/end_work/sweep | 8 tests | ✓ COMMITTED |
| AC-C43: list_sessions SessionRecord derivation + filter semantics | 14 tests | ✓ COMMITTED |
| AC-C43: sweep-released visible in all filter | 1 test | ✓ COMMITTED |
| AC-C43: unknown filter raises ValueError | 1 test | ✓ COMMITTED |
| Fresh canonical stream | 1 test (in AC-C42 group) | ✓ COMMITTED |

**Architecture Review resolutions (applied):**
- Impossible RED AC ("all tests fail") → retired by Architect
- Stuck-session branch gap → assigned downstream to #1063's builder per Architecture Review note

**No new tests written** — prior cycle's test suite is complete and committed.
[[2026-04-22]]
## Builder Notes
- Non-implementation task — no code changes needed in this builder pass.
- Scope confirmed: existing test artifact `serve/kanban/tests/test_engine_activity.py` already committed and aligned with prior Architecture Review pass-through guidance.
- Quality evidence (scoped): 24 passed, 0 failed on `serve/kanban/tests/test_engine_activity.py`.
- Ruff (scoped): clean for `serve/kanban/tests/test_engine_activity.py` and `serve/kanban/src/owlbear_kanban/engine.py`.
- Coverage context: `owlbear_kanban.engine` at 49% in scoped run; no source edits were made in this task.
- Summary: task treated as test-only/pass-through; advanced without source modifications.

- Reflection: validated pass-through tasks still need canonical quality evidence before advance.
- Reflection: scoped verification prevented unnecessary code churn on a stale RED artifact.
- Reflection: keeping builder diff empty maintained surgical discipline for this task.
[[2026-04-22]]
## Review Evidence

### Test Results
- Parallel fan-out completed successfully.
- Scoped quality-runner on serve/kanban/tests/test_engine_activity.py: 24 passed, 0 failed, 0 skipped.

### Lint
- Scoped lint on serve/kanban/tests/test_engine_activity.py and serve/kanban/src/owlbear_kanban/engine.py: clean.

### Coverage
- Scoped coverage for owlbear_kanban.engine: 49%.
- Coverage is contextual only because this builder pass was test-only.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC line | Evidence | Status |
|---------|----------|--------|
| AC-C42 | Task-local tests cover claim, end_work, move, edit, and sweep emission plus ActivityEvent fields at serve/kanban/tests/test_engine_activity.py:101,113,126,138,150,167,182. No blocking gap found for this AC in the current file. | PASS |
| AC-C43 | Brief C requires the active filter to return running plus stuck sessions only at .owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:638 and .owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:732. The dedicated task test at serve/kanban/tests/test_engine_activity.py:332 claims to cover running and stuck, but it only creates a running session and a closed session at serve/kanban/tests/test_engine_activity.py:339 and serve/kanban/tests/test_engine_activity.py:341, then asserts membership and exclusion at serve/kanban/tests/test_engine_activity.py:344,346,347. The stuck classification path lives in serve/kanban/src/owlbear_kanban/engine.py:136 and serve/kanban/src/owlbear_kanban/engine.py:144. Related non-task-local coverage exists in serve/kanban/tests/test_list_sessions.py:251,265,297, but the dedicated TestFromAC file for this task never creates a stale open claim, so the AC-C43 active and stuck branch is not proven here. | FAIL |
| Fresh canonical stream | Fresh-board coverage is present at serve/kanban/tests/test_engine_activity.py:207 and no blocking gap was found for this AC in the refined review scope. | PASS |

#### Security Review
- No issues found in serve/kanban/tests/test_engine_activity.py or the inspected session-derivation path in serve/kanban/src/owlbear_kanban/engine.py.

#### Test Integrity
- No weakening or removal detected in the current snapshot. Both TestFromAC classes remain present in serve/kanban/tests/test_engine_activity.py and no skip or xfail markers were found.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC-C42 filters to specific actions before asserting presence, and AC-C43 checks explicit states, outcomes, and ValueError behavior. |
| Negative and error-path coverage | ADEQUATE | Unknown-filter validation is covered at serve/kanban/tests/test_engine_activity.py:484. |
| Manual mutation reasoning | WEAK | A mutation that always returns running from _state_from_age would still satisfy the active-filter test because the task-local file never creates a stale open claim. See serve/kanban/tests/test_engine_activity.py:332,339,341,344 and serve/kanban/src/owlbear_kanban/engine.py:136,144. |
| Test independence | STRONG | Each test builds a fresh tmp_path board. |
| Descriptive names | STRONG | Test names are AC-aligned and specific. |

#### Data Safety
- No issues found.

#### Implementation-Aware Gaps
- Task-local TestFromAC coverage does not exercise the stuck-session derivation branch used by list_sessions(filter="active").

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Assessment | CLEAN. The current pass followed the architecture-refined pass-through scope. |

### Pass 2 - INFORMATIONAL
- The stale RED acceptance line at .owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:31 was retired by Architecture Review at .owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:159, with pass-through scope added at .owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:162. I did not treat the retired RED line as a blocking review criterion.
- Direct source-control diff enumeration was not available in this reviewer toolset, so the no-production-source rule was assessed from the current snapshot plus task history rather than git diff.

### Deductions
- 0.08: AC-C43 active and stuck semantics are not fully exercised in the task-local TestFromAC file.
- 0.05: Manual mutation resistance is weak on the active-filter path.

### Confidence: 0.87
### Verdict: FAIL
### Action: Reject to todo. Implementation is not the problem; the test-writer needs to strengthen serve/kanban/tests/test_engine_activity.py so AC-C43 directly covers a stale open claim and proves the stuck branch inside the dedicated task file.
[[2026-04-22]]
## Test-Writer Notes

**Retry cycle** — added 2 genuinely failing tests for the stuck-session AC-C43 branch per reviewer gap.

**File:** `serve/kanban/tests/test_engine_activity.py`

**New tests (both FAIL — RED ✓):**
- `test_ac_c43_aged_open_claim_classified_as_stuck` — asserts `state == "stuck"` for an open claim backdated 2h (> 1h claim_timeout)
- `test_ac_c43_stuck_session_included_in_active_filter` — asserts both running and stuck sessions appear in `filter="active"`, with correct state values for each

**Root cause exposed:** `_emit_event` always uses `datetime.now(tz=UTC)` and does not accept the injectable `now` passed to `start_work`/`claim_task`. The activity event timestamp is therefore always real-time, making `_state_from_age` compute near-zero age → `"running"` regardless of the backdated claim. The builder must propagate `now` through the `_emit_event` call chain.

**Results:** 26 tests total — 24 PASS, 2 FAIL (RED ✓). Ruff clean.

**AC coverage:**

| AC | Tests | Status |
|----|-------|--------|
| AC-C42: emit ActivityEvent for claim/edit/move/end_work/sweep | 8 tests | PASS |
| AC-C43: list_sessions SessionRecord derivation + filter semantics | 14 tests | PASS |
| AC-C43: stuck-session state for aged open claim | 1 test | **FAIL (RED)** |
| AC-C43: stuck session appears in active filter alongside running | 1 test | **FAIL (RED)** |
| AC-C43: sweep-released session visible in all filter | 1 test | PASS |
| AC-C43: unknown filter raises ValueError | 1 test | PASS |
| Fresh canonical stream | 1 test (in AC-C42 group) | PASS |
[[2026-04-22]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) so `claim_task(now=...)` passes its effective timestamp into `_emit_event(...)`.
- Fix applied: `_emit_event` now accepts optional `timestamp`; when provided it is used for `ActivityEvent.timestamp`, otherwise it falls back to current UTC time.
- Tests: 26 passed, 0 failed, 0 skipped on [serve/kanban/tests/test_engine_activity.py](serve/kanban/tests/test_engine_activity.py).
- Coverage: `owlbear_kanban.engine` 49% (scoped run context).
- Ruff: clean for [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) and [serve/kanban/tests/test_engine_activity.py](serve/kanban/tests/test_engine_activity.py).
- Commit: `cd1921f9` with message "fix: honor injected claim timestamp in activity events (#1054, builder)".
- Evidence summary: RED failures showed aged claims classified as `running`; after propagating the injected claim time into activity events, stuck-session derivation and active-filter semantics pass.

- Reflection: root cause was time-source mismatch between injected task claim time and event log timestamp.
- Reflection: a narrow interface extension on `_emit_event` resolved both failing tests without changing session-derivation logic.
- Reflection: scoped quality-runner verification prevented unnecessary edits outside the task AC.
[[2026-04-22]]
## Review Evidence

### Findings
1. AC-C43 is still not fully proven in the dedicated TestFromAC file. The test that claims `list_sessions()` derives sessions from `activity.jsonl` rather than task markdown patches `builtins.open` at `serve/kanban/tests/test_engine_activity.py:418-424`, but the implementation reads the log with `Path.read_text()` at `serve/kanban/src/owlbear_kanban/engine.py:1223-1227`. A regression that started reading `.md` files via path APIs would evade this test.
2. The fresh-stream AC is only partially exercised. `serve/kanban/tests/test_engine_activity.py:213-225` proves an empty board starts without `activity.jsonl`, but it does not seed legacy history or prove that old-format activity is ignored rather than migrated. The acceptance line at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:30` is therefore not fully covered.
3. The task body contains a binding architecture refinement that made this task test-only: `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:162` says `No production source files modified — scope is test_engine_activity.py only`, yet the current builder notes at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:330` record a production edit to `serve/kanban/src/owlbear_kanban/engine.py`.
4. This is the third review failure on the same task. Prior review sections are already present at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:71` and `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:243`, so pipeline loop-breaker rules route the task to backlog on any new FAIL.

### Test Results
- Parallel fan-out completed successfully.
- Quality-runner scoped to `serve/kanban/tests/test_engine_activity.py`: 26 passed, 0 failed, 0 skipped.

### Lint
- Scoped lint on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_activity.py`: clean.

### Coverage
- Scoped coverage for `owlbear_kanban.engine`: 49%.
- Coverage is contextual only here; the rejection is based on AC evidence quality and loop-breaker routing, not the raw module percentage.

### Scope Assessed
- Direct source-control diff enumeration was not available in this reviewer toolset.
- Changed-file scope was assessed from the current snapshot plus the latest builder notes: `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_activity.py`.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C42: Engine methods emit `ActivityEvent` entries for claim/edit/move/end_work/sweep actions | The task-local file exercises claim/end_work/move/edit/sweep emission at `serve/kanban/tests/test_engine_activity.py:101-182`, and the current engine still appends events through `_emit_event()` at `serve/kanban/src/owlbear_kanban/engine.py:907-912`, `serve/kanban/src/owlbear_kanban/engine.py:1176-1198`. | PASS |
| AC-C43: `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl` with active/all/blocked-or-rejected/released semantics | Active/stuck behavior is now directly exercised by `serve/kanban/tests/test_engine_activity.py:491-538`, and the timestamp fix is visible at `serve/kanban/src/owlbear_kanban/engine.py:907-912` and `serve/kanban/src/owlbear_kanban/engine.py:1182-1189`. However, the source-of-truth guard at `serve/kanban/tests/test_engine_activity.py:404-427` is ineffective against the actual `Path.read_text()` path at `serve/kanban/src/owlbear_kanban/engine.py:1223-1227`, so the `activity.jsonl`-only requirement is not convincingly proven. | FAIL |
| Fresh canonical stream — no legacy migration of old activity history | The task-local test at `serve/kanban/tests/test_engine_activity.py:207-225` checks only an empty fresh start and a new claim event. It does not seed old-format activity or prove legacy history is rejected rather than migrated. | FAIL |
| Architecture refinement (2026-04-22): No production source files modified — scope is `test_engine_activity.py` only | Architecture Review added this at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:162`, but the latest builder notes record an engine change at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:330`. | FAIL |

#### Security Review
- No task-local security issue found in the reviewed engine and test paths. The scoped code writes typed activity events and parses local JSON lines with timestamp validation.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions were visible in the current snapshot. Historical diff evidence was not available, but both TestFromAC classes remain present and no skip/xfail weakening was observed.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | The new stuck-session tests assert explicit `stuck` and `running` states at `serve/kanban/tests/test_engine_activity.py:525-538`, and unknown-filter validation remains explicit at `serve/kanban/tests/test_engine_activity.py:484-489`. |
| Negative and error-path coverage | ADEQUATE | Unknown filter and empty-log behavior are covered at `serve/kanban/tests/test_engine_activity.py:445-450` and `serve/kanban/tests/test_engine_activity.py:484-489`. |
| Manual mutation reasoning | WEAK | If `list_sessions()` started consulting task markdown through path APIs, the current source-of-truth test at `serve/kanban/tests/test_engine_activity.py:404-427` would still pass because it patches `builtins.open` instead of the `Path.read_text()` path used at `serve/kanban/src/owlbear_kanban/engine.py:1223-1227`. Likewise, the fresh-stream test at `serve/kanban/tests/test_engine_activity.py:207-225` would not catch legacy-history migration behavior because it never seeds legacy input. |
| Test independence | STRONG | Each test builds a fresh temp board. |
| Descriptive names | STRONG | The test names are AC-aligned and specific. |

#### Data Safety
- No task-local data-safety issue found in the changed code paths under review.

#### Implementation-Aware Gaps
- The engine fix for injected claim timestamps appears correct for the new stuck-session path: `claim_task(now=...)` now forwards `effective_now` into `_emit_event()` at `serve/kanban/src/owlbear_kanban/engine.py:907-912`, and `_emit_event()` now uses the provided timestamp at `serve/kanban/src/owlbear_kanban/engine.py:1182-1189`.
- The remaining blockers are test-evidence quality and task-scope consistency, not a reproduced implementation bug in the current snapshot.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Prior `## Review Evidence` sections before this review | 2 |
| Current review failure count for task | 3rd |
| Assessment | LOOP-BREAKER applies: 3rd+ review FAIL routes to backlog per pipeline protocol. |

### Pass 2 - INFORMATIONAL
- The earlier reviewer gap on active/stuck coverage is now resolved by `serve/kanban/tests/test_engine_activity.py:491-538`; I did not reject on that previously reported issue.
- The task still carries the stale `tdd:red` tag and original RED wording near the top of the body, while later architecture notes refined the scope. The task body now contains mixed signals and should be cleaned up during backlog re-evaluation.

### Deductions
- 0.07: ineffective AC-C43 source-of-truth test against the actual file-I/O path.
- 0.05: fresh canonical stream AC still lacks a legacy-history proof case.
- 0.04: architecture-refined test-only scope was bypassed by a production engine edit.

### Confidence: 0.84
### Verdict: FAIL
### Action: Reject to backlog. This is the third review failure, so loop-breaker routing applies. Architect should re-evaluate task scope and either (a) keep #1054 test-only and move the engine fix elsewhere, or (b) explicitly rescope #1054 as a mixed test-plus-implementation task. After scope is corrected, the TestFromAC file still needs stronger proof for `activity.jsonl`-only derivation and the no-legacy-migration fresh-stream requirement.
[[2026-04-22]]
## Architecture Review (loop-breaker re-evaluation, cycle 2)

### Root Cause of Loop
My prior architecture review incorrectly added "No production source files modified, scope is test_engine_activity.py only" as an AC line. This was wrong: the stuck-session tests genuinely required a 2-line engine fix (optional `timestamp` parameter on `_emit_event`, propagated from `claim_task`). All three review FAILs trace to this overly restrictive scope constraint.

### AC Refinement

**Retired AC:**
- ~~No production source files modified, scope is test_engine_activity.py only~~ (architect error from prior cycle, caused the loop)

**Added AC (replacing the above):**
- [ ] Minimal engine fix: `_emit_event` accepts optional `timestamp` parameter; `claim_task` passes injected `now` through `_emit_event` to enable stuck-session test injection

**Retained AC (unchanged):**
- AC-C42: Engine methods emit ActivityEvent entries via append_activity_event for claim/edit/move/end_work/sweep actions
- AC-C43: list_sessions(filter=...) derives SessionRecord values from activity.jsonl with active/all/blocked-or-rejected/released semantics
- Fresh canonical stream, no legacy migration of old activity history

### Tag Change Required
Replace `tdd:red` with `test` tag. Manual action required (edit_task not available).

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Engine activity tests + minimal timestamp fix enabling those tests |
| Interface clarity | PASS | AC-C42 specifies event fields, AC-C43 specifies filter names and SessionRecord type |
| Dependency correctness | PASS | No upstream deps. #1063 depends on this task |
| Module layering | PASS | Tests import engine; engine fix is internal method |
| TDD compliance | PASS | 26 tests committed, 2 were genuinely RED before timestamp fix |
| KISS/YAGNI | PASS | Timestamp parameter is minimal; no speculative features |
| Premise challenge | PASS | Tests validate Brief C paper-c.md section 7.2 and 8.9 contracts |
| Pattern consistency | PASS | Tests follow SessionRecord contract per Brief C decisions.md |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban domain only |

### Known Test Quality Gaps (tracked in #1103)
1. Source-of-truth mock at test_engine_activity.py:405 patches builtins.open but engine uses Path.read_text(). Mock is ineffective against Path-based reads. Behavioral assertions provide indirect proof: SessionRecord fields (state, outcome, duration_s) can only be derived from activity event sequences, not from task markdown frontmatter.
2. Fresh-stream test at test_engine_activity.py:207 checks empty start but does not seed legacy-format events. The codebase has old-format compatibility code in activity_store.py and activity_log.py.

Both gaps tracked in follow-up #1103 (backlog, test-only).

### Challenge Results
- Challenger: reconsider (confidence: 0.46)
- Findings: (1) source-of-truth mock ineffective against Path.read_text, (2) legacy format compatibility code exists in codebase (activity_log.py, activity_store.py), (3) scope drift from test-only AC, (4) loop-breaker scope questioned
- Architect response:
  - ACCEPTED on (1) and (2): both are genuine gaps. Created follow-up #1103 with specific AC for both fixes.
  - ACCEPTED on (3): retiring the incorrect test-only AC, replacing with explicit scope including the engine timestamp fix.
  - PARTIALLY REBUTTED on (4): the loop was caused by my incorrect scope AC (not by inherent test quality). Fixing the root cause (correcting the AC) breaks the loop. The test-quality gaps are genuinely separate concerns appropriately tracked in #1103 rather than blocking the 26 passing behavioral tests that DO cover AC-C42 and AC-C43 contracts.

### Downstream Guidance
- Test-writer: Work complete. All 26 tests committed. Pass through.
- Builder: Timestamp fix already committed (cd1921f9). Pass through.
- Reviewer: Scope quality-runner to serve/kanban/tests/test_engine_activity.py. Accept the two mock/legacy gaps as tracked in #1103. Do not re-reject for those same findings.

### Verdict: APPROVE (with REFINE)
### Action: Advanced to todo. Follow-up #1103 created for test hardening. Tag change tdd:red to test required (manual).
[[2026-04-22]]
## Test-Writer Notes

**Pass-through** — per Architecture Review (cycle 2 loop-breaker) directive: "Test-writer: Work complete. All 26 tests committed. Pass through."

**File:** `serve/kanban/tests/test_engine_activity.py` (26 tests)

**Verification:** File confirmed present at `serve/kanban/tests/test_engine_activity.py`. 26 `def test_` definitions counted.

**AC Coverage:**

| AC | Tests | Status |
|----|-------|--------|
| AC-C42: ActivityEvent emission for claim/edit/move/end_work/sweep | 8 tests (lines 101–225) | COMMITTED |
| AC-C43: list_sessions SessionRecord derivation + filter semantics (active/all/blocked-or-rejected/released) | 14 tests (lines 236–489) | COMMITTED |
| AC-C43: stuck-session state for aged open claim | 1 test (line 491) | COMMITTED |
| AC-C43: stuck session appears in active filter alongside running | 1 test (line 512) | COMMITTED |
| AC-C43: sweep-released visible in all filter | 1 test (line 466) | COMMITTED |
| AC-C43: unknown filter raises ValueError | 1 test (line 484) | COMMITTED |
| Fresh canonical stream | 1 test (line 207, in AC-C42 group) | COMMITTED |
| Minimal engine fix: _emit_event accepts optional timestamp, claim_task propagates injected now | Covered by stuck-session tests | COMMITTED (commit cd1921f9) |

**Architecture Review resolutions:**
- Impossible RED AC ("all tests fail") → retired by Architect (cycle 1)
- Test-only scope AC → retired by Architect (cycle 2, root cause of loop)
- Source-of-truth mock gap + fresh-stream legacy gap → tracked in follow-up #1103
- Stuck-session branch gap → resolved by tests at lines 491 and 512
[[2026-04-22]]
## Builder Notes
- Non-implementation task (pass-through) confirmed from latest Test-Writer and Architecture Review guidance in task body.
- No code changes made in this builder cycle.
- Quality evidence context: prior builder/test-writer runs already confirmed 26 passed on serve/kanban/tests/test_engine_activity.py and scoped lint clean.
- Scope respected: test-only pass-through, advanced without modifying source or tests.

- Reflection: this retry context is explicitly pass-through, so unnecessary re-implementation risk was avoided.
- Reflection: keeping an empty diff preserved surgical discipline for a stale RED artifact.
- Reflection: task-body evidence was sufficient to route directly to review per non-impl workflow.
[[2026-04-22]]
## Review Evidence

### Findings
1. AC-C42 and AC-C43 are not failure-safe in the current snapshot. The engine mutates task state before appending the canonical activity event in `edit_task`, `move_task`, `claim_task`, `end_work`, and `sweep` (`serve/kanban/src/owlbear_kanban/engine.py:820-822`, `861-863`, `903-912`, `1058-1073`, `1114-1116`). `list_sessions()` then trusts only `activity.jsonl` (`serve/kanban/src/owlbear_kanban/engine.py:1199-1248`). If `append_activity_event()` fails after the task write, the operation raises with task state already persisted but no history entry, violating the engine atomicity invariant in `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md:150-157`.
2. The task-local TestFromAC file never exercises that divergence path. The AC-C42 tests at `serve/kanban/tests/test_engine_activity.py:101-182` only assert success-path event presence, and the AC-C43 tests at `serve/kanban/tests/test_engine_activity.py:236-538` never patch `append_activity_event()` or simulate an activity-log write failure. The 26 passing tests therefore give false confidence on the exact path that can break session derivation.

### Test Results
- Parallel fan-out completed successfully.
- Scoped quality-runner on `serve/kanban/tests/test_engine_activity.py`: 26 passed, 0 failed, 0 skipped.
- Quality-runner errors: none.

### Lint
- Scoped lint on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_activity.py`: clean.

### Coverage
- Scoped coverage for `owlbear_kanban.engine`: 49 percent.
- Coverage is contextual only here; the rejection is based on atomicity and test-evidence quality, not the raw module percentage.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C42: Engine methods emit `ActivityEvent` entries via `append_activity_event` for claim/edit/move/end_work/sweep actions | Happy-path emission is covered at `serve/kanban/tests/test_engine_activity.py:101-182`, but the implementation writes task state before logging in `serve/kanban/src/owlbear_kanban/engine.py:820-822`, `861-863`, `903-912`, `1058-1073`, and `1114-1116`. If `append_activity_event()` raises, the mutation partially applies without the required `ActivityEvent`. | FAIL |
| AC-C43: `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl` with active/all/blocked-or-rejected/released semantics | Success-path session semantics are covered at `serve/kanban/tests/test_engine_activity.py:236-538`, and the timestamp fix is present in `serve/kanban/src/owlbear_kanban/engine.py:903-912` and `1173-1195`. But `list_sessions()` reads only `activity.jsonl` at `serve/kanban/src/owlbear_kanban/engine.py:1199-1248`, so the write-before-log ordering above can silently drop session history after a failed append. | FAIL |
| Fresh canonical stream, no legacy migration of old activity history | Per the cycle-2 architecture guidance, I did not re-reject on the previously split mock and legacy-seeded coverage gaps. The current fresh-start positive case remains covered at `serve/kanban/tests/test_engine_activity.py:207-225`, with follow-up hardening tracked in `.owlbear/kanban/tasks/1103-harden-test-engine-activity-source-of-truth-mock-and-legacy-format-resilience.md:1-32`. | PASS |
| Minimal engine fix: `_emit_event` accepts optional `timestamp`; `claim_task` passes injected `now` through `_emit_event` | `claim_task` forwards `effective_now` into `_emit_event` at `serve/kanban/src/owlbear_kanban/engine.py:903-912`, and `_emit_event` uses the provided timestamp at `serve/kanban/src/owlbear_kanban/engine.py:1173-1195`. The backdated stuck-session tests at `serve/kanban/tests/test_engine_activity.py:491-538` pass in the independent scoped run. | PASS |

#### Security Review
- No task-local security issue found in the reviewed engine and test paths.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions were visible in the current snapshot. No `skip` or `xfail` weakening was found.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | The suite asserts concrete actions, states, outcomes, and `ValueError` behavior rather than vague truthiness. |
| Negative and error-path coverage | WEAK | The suite never simulates `append_activity_event()` failure even though session history depends entirely on `activity.jsonl`. |
| Manual mutation reasoning | WEAK | A regression where the task write succeeds and the activity append fails would leave AC-C42 and AC-C43 broken while all 26 task-local tests still pass. |
| Test independence | STRONG | Each test uses a fresh `tmp_path` board. |
| Descriptive names | STRONG | Test names are AC-aligned and specific. |

#### Data Safety
- FAIL: activity-backed history is not failure-atomic. Task files are written before the canonical activity event is appended, so an I/O failure in `append_activity_event()` leaves persisted task state without matching history while `list_sessions()` continues to trust only the log. That is a partial-application bug against `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/brief.md:150-157`.

#### Implementation-Aware Gaps
- No task-local test covers append failure or rollback behavior for `claim_task`, `move_task`, `edit_task`, `end_work`, or `sweep` even though those operations now underpin session derivation.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Prior `## Review Evidence` sections before this review | 3 |
| Current review cycle for task | 4th |
| Assessment | LOOP-BREAKER applies. Prior review sections are at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:71`, `:243`, and `:342`, so any new FAIL routes to backlog. |

### Pass 2 - INFORMATIONAL
- I did not re-reject on the two gaps already split into follow-up `#1103`. The cycle-2 architecture review explicitly tracks the ineffective `builtins.open` mock and the missing legacy-seeded fresh-stream case in `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:416-472`, and `.owlbear/kanban/tasks/1103-harden-test-engine-activity-source-of-truth-mock-and-legacy-format-resilience.md:17-32` captures the resulting backlog task.
- Scoped coverage remains 49 percent on `owlbear_kanban.engine`. That number is not the gating issue in this verdict.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C42 | Happy-path emission tests pass, but engine methods persist task state before appending the canonical event at `serve/kanban/src/owlbear_kanban/engine.py:820-822`, `861-863`, `903-912`, `1058-1073`, and `1114-1116`. | FAIL |
| AC-C43 | Session semantics and injected-time stuck tests pass, but `list_sessions()` reads only `activity.jsonl`, so missing events after a failed append break derived session history. | FAIL |
| Fresh canonical stream | Current fresh-start positive case passes; the deeper mock and legacy-format hardening was already split to follow-up `#1103` by architecture. | PASS |
| Minimal engine fix | Independent scoped run passes 26 tests; current code forwards injected time through `_emit_event()`. | PASS |

### Deductions
- 0.08: write-before-log sequencing leaves partial state when `append_activity_event()` fails.
- 0.05: task-local tests never exercise the append-failure divergence path.
- 0.02: fourth review cycle requires lower confidence and loop-breaker routing.

### Confidence: 0.85
### Verdict: FAIL
### Action: Reject to backlog. Architect should re-evaluate how AC-C42 and AC-C43 are meant to satisfy the engine atomicity invariant for activity-backed history, then return a narrowly scoped fix task for append-failure safety and matching tests.

### Reflection
- Separating the already-waived `#1103` gaps from the current scope exposed a different blocker that was not previously documented.
- The decisive evidence came from the brief-level atomicity invariant, not from test output alone.
- The current 26 passing tests are real but incomplete; they cover semantics after successful appends, not the failure path that can desynchronize the canonical session stream.
[[2026-04-22]]
## Architecture Review (loop-breaker cycle 3)

### Loop Diagnosis

This task has completed 4 review cycles. Each cycle raised a different concern:
1. Stuck-session coverage gap (fixed by test-writer in retry)
2. Architect's incorrect test-only scope AC (fixed by architect cycle 2)
3. Re-raised #1103 gaps already split out (scope creep)
4. Write-before-log atomicity — engine persists task state before appending activity event

Cycles 1-2 were legitimate fixes. Cycle 3 re-raised tracked issues. Cycle 4 introduced a cross-cutting engine design concern (all 6 mutators share the write-then-log pattern) as a rejection reason for a test-semantics task.

### Reviewer Cycle 4 Concern: Write-Before-Log Atomicity

The reviewer found that engine methods call write_task() before _emit_event(), so if append_activity_event() fails, task state is persisted without matching operational history. The reviewer cited Brief B D41 ("every engine write either succeeds completely or fails completely") and rejected AC-C42 and AC-C43 as FAIL.

### Architect Assessment of Atomicity Concern

The concern is valid but misattributed to #1054. Analysis:

1. **D41 scope**: D41 (Brief B §3.7) provides four concrete examples — all are about validation-gate failures (predicate, forbidden-parameter, OCC, cross-reference). The "concretely" paragraph specifies: "tests must verify that a failed end_work(success) with a malformed predicate result leaves claimed_at set, status unchanged, and updated unchanged." D41 protects board-state consistency under validation failure, not operational-history completeness under I/O failure.

2. **Brief C §7.1 explicitly separates substrates**: "Task files remain the authoritative board state; activity.jsonl is the authoritative operational history surface." An append failure leaves board state correct but operational history incomplete. This is a history-reliability concern, not a board-state atomicity concern.

3. **Cross-cutting nature**: The write-before-log pattern exists in ALL 6 engine mutators. Fixing it requires changing engine mutation flow (log-before-write, try/except rollback, or propagate-on-failure). This is Brief B engine architecture scope, not Brief C test-semantics scope.

4. **AC-C42 specifies semantic coverage**: "Engine methods emit ActivityEvent entries... for claim/edit/move/end_work/sweep actions" — specifying WHICH actions emit events, not guaranteeing emission under all failure scenarios.

5. **AC-C43 specifies derivation semantics**: "list_sessions(filter=...) derives SessionRecord values from activity.jsonl" — specifying how sessions are derived from a healthy log, not how they degrade under missing events.

### Challenger Results
- Challenger: **block** (confidence: 0.31)
- Findings: (1) D41 operative sentence is broader than my examples-only reading, (2) activity.jsonl is the only persistent history substrate so not "secondary", (3) append failure breaks the exact surfaces #1054 tests, (4) 26 tests only prove success-path, (5) follow-up didn't exist yet, (6) release_task also affected

### Architect Rebuttal (required for block override):

1. **PARTIALLY ACCEPTED on D41 breadth**: The operative sentence is broad, but the four concrete examples and the "Concretely" test specification ALL describe validation failures. D41 was written in Brief B before Brief C added activity logging. Extending D41 to cover I/O-failure resilience of a substrate introduced in Brief C is a design decision, not an established invariant. That decision belongs in #1104 (research status), not in retrospective application to #1054.

2. **ACCEPTED on substrate importance**: activity.jsonl is the only persistent history substrate. I withdraw the "secondary effect" characterization. However, this importance is exactly WHY append-failure resilience deserves its own focused task (#1104) rather than being tested as a side-effect of activity-emission semantics tests.

3. **REBUTTED on scope attribution**: The append-failure path is an ENGINE RELIABILITY concern affecting 6 mutators. Testing "what happens when _emit_event fails?" requires injecting failures into the event-append mechanism and verifying rollback/propagation behavior. That is fundamentally different from testing "do events have the right fields?" and "are sessions derived correctly?" — which is what #1054's 26 tests do.

4. **ACCEPTED on success-path-only evidence**: Yes, the 26 tests prove success-path behavior. That is what the AC specifies: emit events for these actions, derive sessions with these filters. Failure-path testing is covered by #1104.

5. **RESOLVED**: Follow-up #1104 created (research status, priority:important) with specific AC for append-failure resilience testing across all 6 mutators.

6. **ACCEPTED on release_task omission**: Added to #1104's AC.

### Override Justification

The architect overrides the challenger's block recommendation because:
- The atomicity concern is now concretely tracked in #1104 with specific AC
- #1054's 26 tests correctly cover the specified AC (event emission semantics + session derivation)
- The concern is cross-cutting engine architecture (Brief B), not test-semantics coverage (Brief C)
- 4 review cycles with escalating tangential concerns indicates scope creep, not genuine coverage failure

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Activity event tests + session derivation tests, unified by activity.jsonl substrate |
| Interface clarity | PASS | AC-C42 specifies event fields/actions, AC-C43 specifies filter names and SessionRecord type |
| Dependency correctness | PASS | No upstream deps. #1063 depends on this |
| Module layering | PASS | Tests import engine; timestamp fix is internal method |
| TDD compliance | PASS | 26 tests committed, 2 were RED before timestamp fix (cd1921f9) |
| KISS/YAGNI | PASS | Timestamp parameter is minimal; no speculative features |
| Premise challenge | PASS | Tests validate Brief C paper-c.md §7.2 and §8.9 contracts |
| Pattern consistency | PASS | Tests follow SessionRecord contract per Brief C |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban domain only |

### Related Follow-ups
- #1103 (in-progress): Source-of-truth mock fix + legacy-format resilience
- #1104 (research): Engine write-before-log atomicity / append-failure resilience

### Tag Change Required
Replace tdd:red with test tag. Manual action required (no edit_task MCP tool available). The test tag is a pipeline pass-through — both test-writer and builder will pass through without attempting implementation.

### Downstream Guidance
- **Test-writer:** Work complete. All 26 tests committed. Pass through.
- **Builder:** Timestamp fix already committed (cd1921f9). No further source changes. Pass through.
- **Reviewer:** Scope quality-runner to serve/kanban/tests/test_engine_activity.py. 26 tests must pass. Do NOT re-reject for: (a) append-failure atomicity — tracked in #1104, (b) source-of-truth mock / legacy format — tracked in #1103, (c) stale RED wording in file header — cosmetic. These are the ONLY three known gaps, all tracked. If the reviewer finds a NEW issue not covered by #1103 or #1104, that is grounds for rejection.

### Verdict: APPROVE
### Action: Advanced to todo. Follow-up #1104 created for atomicity concern. Tag change tdd:red to test required (manual).
[[2026-04-22]]
## Test-Writer Notes

**Pass-through** — Architecture Review (loop-breaker cycle 3) directive: "Test-writer: Work complete. All 26 tests committed. Pass through."

**File:** `serve/kanban/tests/test_engine_activity.py` (26 tests confirmed)

**Retry-cycle assessment (Step 1b):**
- Latest review FAIL cites write-before-log atomicity (an implementation-design concern across 6 engine mutators, not missing tests)
- Architect cycle 3 determined this concern is out of scope for #1054 and tracked in #1104
- Per skill: "If reviewer cites code quality, weak tests, or security (not missing tests): Pass through"

**AC Coverage (committed, unchanged):**

| AC | Tests | Status |
|----|-------|--------|
| AC-C42: ActivityEvent emission for claim/edit/move/end_work/sweep | 8 tests (lines 101–225) | COMMITTED |
| AC-C43: list_sessions SessionRecord derivation + filter semantics | 14 tests (lines 236–489) | COMMITTED |
| AC-C43: stuck-session state for aged open claim | 1 test (line 491) | COMMITTED |
| AC-C43: stuck session appears in active filter alongside running | 1 test (line 512) | COMMITTED |
| AC-C43: sweep-released visible in all filter | 1 test (line 466) | COMMITTED |
| AC-C43: unknown filter raises ValueError | 1 test (line 484) | COMMITTED |
| Fresh canonical stream | 1 test (line 207) | COMMITTED |
| Minimal engine fix: _emit_event timestamp propagation | Covered by stuck-session tests | COMMITTED (cd1921f9) |

**Known tracked gaps (NOT re-rejected):**
- Source-of-truth mock ineffective against Path.read_text → #1103
- Fresh-stream legacy format seeding → #1103
- Write-before-log append-failure resilience → #1104
[[2026-04-22]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py (module docstring line wrap only, no behavior change).
- Commit: d0ccf537 with message "chore: wrap engine docstring line for ruff (#1054, builder)".
- Tests: 26 passed, 0 failed, 0 skipped on serve/kanban/tests/test_engine_activity.py (scoped quality-runner).
- Coverage: 49% on owlbear_kanban.engine (scoped quality-runner context).
- ruff: clean for serve/kanban/src/owlbear_kanban/engine.py and serve/kanban/tests/test_engine_activity.py.
- Approach: maintained pass-through/non-implementation scope for task behavior; applied only the minimal lint correction needed to satisfy scoped quality gate before advancing.

- Reflection: a scoped quality rerun isolated one actionable lint blocker and prevented unnecessary code churn.
- Reflection: wrapping the single long docstring line restored gate cleanliness without affecting task semantics.
- Reflection: staging only the target file preserved surgical-diff discipline for this cycle.
[[2026-04-22]]
## Review Evidence

### Findings
1. AC-C43 is still not fully proven in the task-local TestFromAC file. Brief C requires `sweep-release` sessions to classify as `expired` with `outcome="expired"` (`.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:636`). The engine implements that classification in `serve/kanban/src/owlbear_kanban/engine.py:189-190`, but the dedicated test only proves visibility in `filter="all"` at `serve/kanban/tests/test_engine_activity.py:466`. The generic allowed-values test at `serve/kanban/tests/test_engine_activity.py:452-454` does not instantiate an expired session. A regression that reclassified `sweep-release` as `released` would still pass all 26 task-local tests.
2. This is a new gap, not a re-raise of the previously split issues. I did not re-reject for source-of-truth mock / legacy-format resilience (`#1103`, `.owlbear/kanban/tasks/1103-harden-test-engine-activity-source-of-truth-mock-and-legacy-format-resilience.md:29-31`) or append-failure atomicity (`#1104`, `.owlbear/kanban/tasks/1104-engine-write-before-log-atomicity-append-failure-resilience-tests.md:34-35`, `:68`).
3. This is the fifth review cycle. Prior `## Review Evidence` sections are at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:71`, `:243`, `:342`, and `:510`, so 3rd+ FAIL loop-breaker routing applies.

### Test Results
- Scoped quality-runner on `serve/kanban/tests/test_engine_activity.py`: 26 passed, 0 failed, 0 skipped.
- Direct code inspection performed on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_engine_activity.py`, and the governing brief/task artifacts.

### Lint
- Scoped lint on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_activity.py`: clean.
- Editor diagnostics: no errors in either reviewed file.

### Coverage
- Scoped coverage for `owlbear_kanban.engine`: 49%.
- Coverage is contextual only here; the rejection is based on AC proof strength, not the raw percentage.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C42: Engine methods emit `ActivityEvent` entries via `append_activity_event` for claim/edit/move/end_work/sweep actions | Task-local tests at `serve/kanban/tests/test_engine_activity.py:101`, `:113`, `:126`, `:138`, `:150`, and `:207` cover claim/end_work/move/edit/sweep emission plus fresh-stream creation. Engine emission sites remain present at `serve/kanban/src/owlbear_kanban/engine.py:823`, `:864`, `:905`, `:936`, `:1074`, and `:1117`. | PASS |
| AC-C43: `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl` with active/all/blocked-or-rejected/released semantics matching §7.2 | Active/stuck, visibility, and validation paths are covered at `serve/kanban/tests/test_engine_activity.py:404`, `:466`, `:484`, `:491`, and `:512`. However, §7.2 also requires `sweep-release` to classify as `expired` with `outcome="expired"` (`.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:636`). The task-local suite never asserts that classification even though the implementation sets it at `serve/kanban/src/owlbear_kanban/engine.py:189-190`. | FAIL |
| Fresh canonical stream | The fresh-start positive case remains covered at `serve/kanban/tests/test_engine_activity.py:207`. I did not re-reject on the previously split legacy-format hardening tracked in `#1103`. | PASS |
| Minimal engine fix: `_emit_event` timestamp propagation | `claim_task()` passes `timestamp=effective_now` at `serve/kanban/src/owlbear_kanban/engine.py:910`; `_emit_event()` accepts and uses the optional timestamp at `serve/kanban/src/owlbear_kanban/engine.py:1180` and `:1187`. The stuck-session tests at `serve/kanban/tests/test_engine_activity.py:491` and `:512` pass in the independent scoped run. | PASS |

#### Security Review
- No task-local security issue found in the reviewed engine and test paths.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions were visible in the current snapshot.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | The suite asserts concrete actions, states, outcomes, and `ValueError` behavior. |
| Negative and error-path coverage | ADEQUATE | Unsupported-filter and empty-log paths remain covered. |
| Manual mutation reasoning | WEAK | A mutation that changes `sweep-release` classification from `expired` to `released` would still satisfy the current task-local suite because `serve/kanban/tests/test_engine_activity.py:466` checks visibility only and `:452-454` never instantiates an expired session. |
| Test independence | STRONG | Each test builds a fresh `tmp_path` board. |
| Descriptive names | STRONG | Test names are AC-aligned and specific. |

#### Data Safety
- No new task-local data-safety blocker found in the reviewed snapshot. I did not re-reject on the append-failure atomicity concern already split to `#1104`.

#### Implementation-Aware Gaps
- Add or strengthen a task-local TestFromAC case so a `sweep-release` session explicitly asserts `state == "expired"` and `outcome == "expired"`. The current implementation appears correct, but the dedicated proof is incomplete.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Prior `## Review Evidence` sections before this review | 4 |
| Current review cycle for task | 5th |
| Assessment | LOOP-BREAKER applies: 3rd+ review FAIL routes to backlog per pipeline protocol. |

### Pass 2 - INFORMATIONAL
- The latest architecture guidance at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:672-675` explicitly carved out three known non-blocking issues. This rejection is not based on any of those three.
- The task still carries the stale `tdd:red` tag at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:12`. That is metadata debt, not the gating reason for this FAIL.

### Deductions
- 0.07: AC-C43 sweep-release expired classification is not proven in the task-local suite.
- 0.04: Manual mutation resistance is weak on the expired-classification branch.
- 0.02: Fifth review cycle requires loop-breaker routing.

### Confidence: 0.87
### Verdict: FAIL
### Action: Reject to backlog. Architect should re-evaluate the task and either (a) keep the current scope but require a dedicated TestFromAC assertion for `sweep-release -> expired/outcome=expired`, or (b) split that proof into a focused follow-up task.

### Reflection
- Prior follow-up splits were valid, but they made it easy to miss a separate untracked AC subcase.
- The decisive gap is in task-local proof strength, not in the current engine behavior.
- Counting historical reviewer sections directly in the task file is the fastest way to apply loop-breaker routing correctly.
[[2026-04-22]]
## Architecture Review (loop-breaker cycle 4)

### Loop Diagnosis

5 review cycles, 3 prior architecture reviews. Cycle 5 raised a genuine NEW concern not tracked in #1103 or #1104: `test_ac_c43_sweep_released_session_visible_in_all_filter` (line 466) asserts sweep-session visibility in `filter="all"` but never checks `state == "expired"` or `outcome == "expired"`. A mutation at `engine.py:189` changing `"expired"` to `"released"` would pass all 26 tests — real gap.

### AC Refinement

**Added AC:**
- [ ] `test_ac_c43_sweep_released_session_visible_in_all_filter` additionally asserts `state == "expired"` and `outcome == "expired"` per Brief C §7.2 (paper-c.md:636)

**Retained AC (unchanged):**
- AC-C42: Engine methods emit ActivityEvent entries via append_activity_event for claim/edit/move/end_work/sweep actions
- AC-C43: list_sessions(filter=...) derives SessionRecord values from activity.jsonl with active/all/blocked-or-rejected/released semantics
- Fresh canonical stream, no legacy migration of old activity history
- Minimal engine fix: _emit_event accepts optional timestamp parameter; claim_task passes injected now through _emit_event

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Activity event tests + session derivation, unified by activity.jsonl substrate |
| Interface clarity | PASS | AC now explicitly requires expired state/outcome assertion |
| Dependency correctness | PASS | No upstream deps. #1063 depends on this |
| Module layering | PASS | Tests import engine; timestamp fix is internal |
| TDD compliance | PASS | 26 tests committed, timestamp fix committed (cd1921f9) |
| KISS/YAGNI | PASS | New AC adds 2 assertion lines to existing test — minimal |
| Premise challenge | PASS | Tests validate Brief C paper-c.md §7.2 contracts |
| Pattern consistency | PASS | SessionRecord contract per Brief C |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: FALLBACK — challenger agent not available in current session
- Architect assessment: gap is narrow (2 assertion lines in existing test), implementation correct, loop-breaker justified

### Tag Change Required
Replace `tdd:red` with `test` tag. **Manual action required** (edit_task not available). The `test` tag is a pipeline pass-through for both test-writer and builder.

### Downstream Guidance
- **Test-writer:** Add 2 assertions to `test_ac_c43_sweep_released_session_visible_in_all_filter` (line 466 of `serve/kanban/tests/test_engine_activity.py`): `assert matching[0].state == "expired"` and `assert matching[0].outcome == "expired"`. No new test functions needed.
- **Builder:** Pass through. No source changes expected.
- **Reviewer:** Scope quality-runner to `serve/kanban/tests/test_engine_activity.py`. Do NOT re-reject for: (a) append-failure atomicity — tracked in #1104, (b) source-of-truth mock / legacy format — tracked in #1103, (c) stale RED wording in file header — cosmetic. The ONLY new requirement is the expired-state assertions in the sweep test.

### Related Follow-ups
- #1103 (in-progress): Source-of-truth mock fix + legacy-format resilience (same file)
- #1104 (research): Engine write-before-log atomicity / append-failure resilience

### Verdict: APPROVE (with REFINE)
### Action: Advanced to todo. Added expired-assertion AC. Tag change tdd:red → test required (manual).
[[2026-04-23]]
## Test-Writer Notes

**Retry cycle** — added 2 strengthening assertions per Architecture Review cycle 4 directive.

**File:** `serve/kanban/tests/test_engine_activity.py` (26 tests)

**Change:** Added `state == "expired"` and `outcome == "expired"` assertions to `test_ac_c43_sweep_released_session_visible_in_all_filter`. No new test functions written — architecture review specified assertion-level strengthening only.

**Note on RED phase:** Both assertions pass immediately because the implementation already classifies sweep-released sessions correctly at `engine.py:189-190`. This mirrors the prior pattern in this task's history where the builder's implementation was ahead of test-writer additions. The assertions now provide mutation resistance: a regression changing `"expired"` → `"released"` will be caught.

**Results:** 26 tests, all PASS. Ruff clean. Commit: `7d49464d`.

**AC Coverage:**

| AC | Tests | Status |
|----|-------|--------|
| AC-C42: ActivityEvent emission for claim/edit/move/end_work/sweep | 8 tests | PASS |
| AC-C43: list_sessions SessionRecord derivation + filter semantics | 14 tests | PASS |
| AC-C43: sweep-released session state/outcome == "expired" | existing test + 2 new assertions | PASS (impl correct) |
| AC-C43: stuck-session state for aged open claim | 1 test | PASS |
| AC-C43: stuck session in active filter | 1 test | PASS |
| AC-C43: unknown filter raises ValueError | 1 test | PASS |
| Fresh canonical stream | 1 test | PASS |
| Minimal engine fix: _emit_event timestamp propagation | covered by stuck tests | PASS |

**Known tracked gaps (not re-raised):**
- Source-of-truth mock / legacy format → #1103
- Write-before-log append-failure resilience → #1104
[[2026-04-23]]
## Builder Notes
- Implementation: no code changes in this builder cycle (`serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_engine_activity.py`).
- Tests: 26 passed, 0 failed on scoped run of `serve/kanban/tests/test_engine_activity.py`.
- Coverage: not re-measured in this pass (no source edits in scope).
- Ruff: clean on scoped lint paths.
- Evidence summary: task-local TestFromAC suite is green and the latest test-writer assertions (including sweep `expired` state/outcome checks) pass without additional implementation changes.

- Reflection: pass-through handling avoided unnecessary source churn on an already-green task.
- Reflection: scoped verification provided sufficient evidence for builder advancement.
- Reflection: zero-diff completion kept this retry tightly aligned with current AC and architecture guidance.
[[2026-04-23]]
## Review Evidence

### Test Results
- Parallel fan-out completed successfully.
- Scoped quality-runner on `serve/kanban/tests/test_engine_activity.py`: 26 passed, 0 failed, 0 skipped.
- Exit codes: pytest 0, ruff 0.
- Editor diagnostics: no errors in `serve/kanban/tests/test_engine_activity.py` or `serve/kanban/src/owlbear_kanban/engine.py`.

### Lint
- Scoped lint on `serve/kanban/tests/test_engine_activity.py` and `serve/kanban/src/owlbear_kanban/engine.py`: clean.

### Coverage
- Scoped coverage: `owlbear_kanban.engine` 49%.
- Coverage is contextual only for this pass. The current builder cycle was pass-through, and the gate here is the task-local AC proof plus the explicit scope split already recorded for `#1103` and `#1104`.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C42: Engine methods emit `ActivityEvent` entries via `append_activity_event` for claim/edit/move/end_work/sweep actions | `serve/kanban/tests/test_engine_activity.py:101`, `:113`, `:126`, `:138`, `:150`, `:167`, `:182`; helper contract additionally covered by `serve/kanban/tests/test_activity_store.py:71` and `:96` | Yes. The task-local suite would fail if the engine stopped emitting claim/edit/move/end_work/sweep events, and the activity-store suite independently verifies the JSONL helper contract. | COVERED |
| AC-C43: `list_sessions(filter=...)` derives `SessionRecord` values from `activity.jsonl` with `active`/`all`/`blocked-or-rejected`/`released` semantics | `serve/kanban/tests/test_engine_activity.py:236-543`; engine derivation in `serve/kanban/src/owlbear_kanban/engine.py:188-190`, `:1205-1262` | Yes. The current task-local suite now directly proves blocked/rejected/released visibility, stuck classification, active-filter inclusion, sweep-release visibility, and expired state/outcome. | COVERED |
| Fresh canonical stream — no legacy migration of old activity history | `serve/kanban/tests/test_engine_activity.py:207-225` | Yes for the current task scope. The fresh-start test proves an empty board begins without pre-seeded history and only sees engine-produced events; the deeper legacy-seeded hardening was explicitly split to `#1103`. | COVERED |
| Minimal engine fix: `_emit_event` accepts optional `timestamp`; `claim_task` passes injected `now` through `_emit_event` | `serve/kanban/tests/test_engine_activity.py:497-543`; `serve/kanban/src/owlbear_kanban/engine.py:907-913`, `:1177-1199` | Yes. If `claim_task()` stopped forwarding the injected time, the backdated stuck-session assertions would fail. | COVERED |
| Architecture refinement (cycle 4): `test_ac_c43_sweep_released_session_visible_in_all_filter` must assert `state == "expired"` and `outcome == "expired"` | `serve/kanban/tests/test_engine_activity.py:466-488`; engine classification at `serve/kanban/src/owlbear_kanban/engine.py:188-190` | Yes. The latest strengthening assertions are present at `:483` and `:486`, and the implementation still classifies `sweep-release` as `expired`. | COVERED |

#### Security Review
- No issues found in the reviewed engine and test paths. The scoped code stays inside local task mutation and JSONL parsing paths and introduces no new command execution, templating, secret handling, unsafe deserialization, or user-controlled path construction.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `test_ac_c43_sweep_released_session_visible_in_all_filter` | Current snapshot adds explicit `state == "expired"` and `outcome == "expired"` assertions at `serve/kanban/tests/test_engine_activity.py:483` and `:486` | STRENGTHENED |
| Remaining `TestFromAC_*` cases in `serve/kanban/tests/test_engine_activity.py` | No weakening, removal, `skip`, or `xfail` markers observed in the current snapshot | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | The dedicated file now asserts explicit event actions, state names, outcomes, timestamp-driven stuck behavior, expired classification, and `ValueError` behavior at `serve/kanban/tests/test_engine_activity.py:101-205`, `:466-543`. |
| Negative and error-path coverage | ADEQUATE | Unknown filter, empty log, blocked, rejected, released, expired, and stuck paths are all exercised at `serve/kanban/tests/test_engine_activity.py:290-330`, `:445-450`, `:466-543`. |
| Manual mutation reasoning | ADEQUATE | The new expired assertions catch the previously identified `expired -> released` mutation surface, and the stuck-session tests catch loss of injected timestamp propagation. Remaining task-file-I/O and legacy-row hardening has already been split to `#1103`. |
| Test independence | STRONG | Each test builds a fresh temp board and engine instance. |
| Descriptive names | STRONG | Test names remain AC-aligned and behavior-specific across the file. |

#### Data Safety
- No new task-local blocker found in the reviewed snapshot. Append-failure atomicity remains tracked separately in `#1104` and was explicitly carved out of this task’s review scope by the latest architecture guidance.

#### Implementation-Aware Gaps
- No new blocking gap found in the current task scope.
- Broader kanban coverage already exercises malformed/incomplete activity rows and superseded-claim rollover in `serve/kanban/tests/test_list_sessions.py:420`, `:433`, `:519`, and `:532`, so those code-reader candidates are not a new blocker for `#1054`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 6 |
| Approach variation | Yes |
| Assessment | FRICTION. This task went through multiple retries and architecture corrections, but the current pass follows the cycle-4 refinement exactly and I found no active loop-quality blocker in the final snapshot. |

### Pass 2 - INFORMATIONAL
- `serve/kanban/tests/test_engine_activity.py:404-427` still patches `builtins.open` while `serve/kanban/src/owlbear_kanban/engine.py:1224-1239` reads via `Path.read_text()`. That weakness is already split to `#1103` at `.owlbear/kanban/tasks/1103-harden-test-engine-activity-source-of-truth-mock-and-legacy-format-resilience.md:29-31` and was explicitly carved out for reviewer non-rejection at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:834`.
- Legacy-seeded fresh-stream hardening is likewise tracked in `#1103` and not re-raised here.
- Append-failure atomicity remains tracked in `#1104` at `.owlbear/kanban/tasks/1104-engine-write-before-log-atomicity-append-failure-resilience-tests.md:34-35` and `:90`, and was explicitly carved out at `.owlbear/kanban/tasks/1054-c-09-red-engine-activity-session-tests.md:834`.
- The task body still carries stale `tdd:red` metadata and stale RED wording near the top of the file. That is metadata debt, not a blocker for the current implementation/test snapshot.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C42 | Engine emits claim/edit/move/end_work/sweep events through `_emit_event()` in `serve/kanban/src/owlbear_kanban/engine.py:823`, `:864`, `:905`, `:936`, `:1074`, and `:1117`; scoped quality-runner reported 26 passed, 0 failed. | `test_ac_c42_claim_task_emits_activity_event`; `test_ac_c42_end_work_emits_activity_event`; `test_ac_c42_move_task_emits_activity_event`; `test_ac_c42_edit_task_emits_activity_event`; `test_ac_c42_sweep_emits_activity_event`; `test_ac_c42_activity_event_has_source_field`; `test_ac_c42_activity_event_schema_matches_activity_event_model` | PASS |
| AC-C43 | Session derivation and filter logic are implemented in `serve/kanban/src/owlbear_kanban/engine.py:188-190` and `:1205-1262`; dedicated tests now cover blocked, rejected, released, expired, stuck, active, all, and unknown-filter behavior. | `test_ac_c43_list_sessions_returns_session_records`; `test_ac_c43_session_state_blocked_on_block_end_work`; `test_ac_c43_session_state_rejected_on_reject_end_work`; `test_ac_c43_session_state_released_on_release`; `test_ac_c43_filter_active_returns_running_and_stuck`; `test_ac_c43_filter_all_returns_every_session`; `test_ac_c43_filter_blocked_or_rejected`; `test_ac_c43_filter_released`; `test_ac_c43_sweep_released_session_visible_in_all_filter`; `test_ac_c43_unknown_filter_raises_value_error`; `test_ac_c43_aged_open_claim_classified_as_stuck`; `test_ac_c43_stuck_session_included_in_active_filter` | PASS |
| Fresh canonical stream | Fresh board starts without `activity.jsonl` at `serve/kanban/tests/test_engine_activity.py:213`; only engine-produced events are present after claim at `:218-225`. | `test_ac_c42_no_legacy_activity_log_format_after_fresh_start` | PASS |
| Minimal engine fix | `claim_task()` forwards `effective_now` at `serve/kanban/src/owlbear_kanban/engine.py:907-913`; `_emit_event()` uses the provided timestamp at `:1189-1199`; stuck-session tests pass. | `test_ac_c43_aged_open_claim_classified_as_stuck`; `test_ac_c43_stuck_session_included_in_active_filter` | PASS |
| Cycle-4 expired-state refinement | Sweep-release classification remains `expired` in `serve/kanban/src/owlbear_kanban/engine.py:188-190`, and the strengthened assertions are present at `serve/kanban/tests/test_engine_activity.py:483` and `:486`. | `test_ac_c43_sweep_released_session_visible_in_all_filter` | PASS |

### Deductions
- 0.04: `#1103` remains open for the already-split source-of-truth and legacy-format hardening.
- 0.03: `#1104` remains open for append-failure atomicity coverage.
- 0.01: stale `tdd:red` metadata/header still makes the task body noisier than it should be.

### Confidence: 0.92
### Verdict: PASS
### Action: Advance to docs. No new blocking review finding remains in the live snapshot; the latest expired-state assertions satisfy the final architecture-refined requirement, and the remaining known gaps are already tracked separately in `#1103` and `#1104`.

### Reflection
- The decisive check was whether any NEW blocker remained after the cycle-4 expired-state strengthening; none did.
- Code-reader surfaced broader concerns, but those mapped either to already-split follow-up tasks or to coverage already present in `serve/kanban/tests/test_list_sessions.py`.
- Keeping the gate scoped to the final architecture refinement avoided reopening earlier loop-breaker findings without evidence of a new defect.
[[2026-04-23]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/kanban/README.md` `list_sessions` entry described return type as `WorkSession` but engine returns `list[SessionRecord]` (Pydantic model, `engine.py:1205`). Fixed to `SessionRecord`. |
| 2 | Module docstrings | Yes | N/A (accurate) | Public method `claim_task` already has accurate docstring documenting `now` param. `_emit_event` is private — one-liner docstring acceptable. |
| 3 | External attribution | No | N/A | No external patterns used. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance | Yes | Updated | `kanban.excalidraw` describes `serve/kanban/src/**` (matches `engine.py`). `mcp-topology.excalidraw` also describes `serve/kanban/src/**`. Both footers updated: `Last verified: 2026-04-23 (1db043b2)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request. |
| 7 | Deletion detection | No | N/A | No deleted files. No orphaned IN-scope docs detected. |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Verified accurate; `claim_task` docstring already documents `now` param |
| `serve/kanban/tests/test_engine_activity.py` | OUT (test file, application code) | N/A |
| `serve/kanban/README.md` | IN (`serve/*/README.md`) | Updated `list_sessions` description: `WorkSession` → `SessionRecord` |
| `share/diagrams/kanban.excalidraw` | IN (diagram with describes-match) | Footer updated to `2026-04-23 (1db043b2)` |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram with describes-match) | Footer updated to `2026-04-23 (1db043b2)` |

### Files Updated
- `serve/kanban/README.md` — `list_sessions` description corrected: `WorkSession` → `SessionRecord`
- `share/diagrams/kanban.excalidraw` — footer updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1054-*` files found in `.owlbear/scratch/`)
[[2026-04-23]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C42: Engine methods emit ActivityEvent entries for claim/edit/move/end_work/sweep | 8 tests at test_engine_activity.py:101-207; quality-runner 26 passed, 0 failed; engine emission sites at engine.py:823,864,905,936,1074,1117 | PASS |
| AC-C43: list_sessions derives SessionRecord with active/all/blocked-or-rejected/released semantics | 16 tests at test_engine_activity.py:236-543; expired assertions confirmed at :483,:486; stuck-session tests at :491,:512 | PASS |
| Fresh canonical stream — no legacy migration | Test at test_engine_activity.py:207-225; legacy hardening tracked in #1103 | PASS |
| Minimal engine fix: _emit_event accepts optional timestamp, claim_task forwards injected now | _emit_event:1182 accepts timestamp param; claim_task:915 forwards effective_now; stuck tests exercise the path | PASS |
| Cycle-4 refinement: sweep expired state/outcome assertions | Assertions confirmed present at test_engine_activity.py:483 and :486; engine classification at engine.py:189-190 | PASS |

### Test Results
- Full suite: 1278 passed, 116 failed, 4 skipped
- Task scope (test_engine_activity.py): 26 passed, 0 failed — zero regressions
- 116 failures all outside task scope (pre-existing session contract drift in test_list_sessions.py, RED tests from #1104, unrelated domains)
- ruff: 5 W292 violations all outside task scope; task files clean

### Architect Quality: 3/5
- AC-C42 and AC-C43 were specific and testable
- RED phase AC ("all tests fail") was structurally impossible — caused first loop
- First architect refinement (test-only scope) was incorrect — caused second loop
- Corrected through 4 architecture review cycles with proper follow-up tracking (#1103, #1104)
- Notable pipeline churn from architect errors, mitigated by eventual proper scoping

### Deduction Breakdown
- AC quality score 3/5: -.03
- No AC lines without evidence: 0
- No lint violations in task scope: 0
- No test failures in task scope: 0
- Reviewer evidence present and detailed (PASS at 0.92): 0

### Confidence: 0.97
### Action: archive