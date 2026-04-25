---
id: 1078
title: 'B-15: RED — CockpitView tests'
status: todo
priority: needed
created: '2026-04-21 10:50:12.218304+00:00'
updated: '2026-04-25 18:26:32.359853+00:00'
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:red
parent: 1044
depends_on:
- 1071
- 1075
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §5, §3.8
Module: `serve/kanban/tests/test_engine_cockpit_view.py`

Test CockpitView facade — OCC-guarded mutations, admin operations, activity/session reads. CockpitView wraps engine methods with OCC (edit_task, move_task) and adds admin-only operations (release_task, sweep, scan_corruption, repair_storage, compact_activity, list_activity, list_sessions).

## Acceptance Criteria

- [ ] CockpitView.edit_task requires `expected_updated` param; mismatch → ConcurrencyError(ERR_STALE) per D22+D46
- [ ] CockpitView.move_task requires `expected_updated` param; mismatch → ConcurrencyError(ERR_STALE)
- [ ] AC-NEW-21: release_task on unclaimed → idempotent no-op (updated NOT advanced)
- [ ] AC-NEW-22: sweep returns exactly the set of released task IDs (no extras, no missing); idempotent (second call → [])
- [ ] release_task on missing id → NotFoundError(ERR_NOT_FOUND)
- [ ] list_activity supports filter by task_id, action, source, time window
- [ ] list_sessions returns SessionRecord list with correct state derivation per D31
- [ ] scan_corruption is read-only (no file creation, deletion, or content mutation), returns list[CorruptionError]
- [ ] repair_storage: phase-1 scan_and_fix + phase-2 AR creation; never implicit at startup
- [ ] compact_activity calls storage.compact_activity_log
- [ ] CockpitView does NOT expose: create_task, start_work, end_work, pick_tasks
- [ ] ActivityEvent.source populated automatically: "agent" / "cockpit" / "engine" per §3.8
- [ ] All tests fail (RED phase)
[[2026-04-25]]
## Test-Writer Notes
- Test file: tests/test_engine_cockpit_view_1078.py
- Classes:
  - `TestFromAC_CockpitViewOCC` — OCC signatures and ERR_STALE behaviour for edit_task / move_task
  - `TestFromAC_CockpitViewReleaseTask` — idempotent no-op on unclaimed (AC-NEW-21), NotFoundError on missing
  - `TestFromAC_CockpitViewSweep` — expired-claim release, idempotency, return type (AC-NEW-22)
  - `TestFromAC_CockpitViewListActivity` — no-filter, task_id, action, source, since, until, empty-log
  - `TestFromAC_CockpitViewListSessions` — SessionRecord list, state derivation per D31 (running/all/released/empty)
  - `TestFromAC_CockpitViewScanCorruption` — clean board, corrupt file, read-only, archive dir
  - `TestFromAC_CockpitViewRepairStorage` — RepairOutcome list, phase-1 quarantine, phase-2 AR, no startup
  - `TestFromAC_CockpitViewCompactActivity` — returns ActivityCompactionResult, spy on storage delegate, empty log
  - `TestFromAC_CockpitViewRoleSeparation` — admin methods present, agent ops absent (guarded with admin-method hasattr)
  - `TestFromAC_ActivityEventSource` — source='agent' (AgentView), source='cockpit' (CockpitView), source='engine' (sweep)
- Tests per category: happy 12, edge 8, error 4, boundary 21
- Total: 45 tests, all FAIL
- ruff: clean
- Commit: d11c95c3

AC coverage:
| AC line | Tests |
|---|---|
| edit_task expected_updated; ERR_STALE | signature check + stale test + happy test |
| move_task expected_updated; ERR_STALE | signature check + stale test + happy test |
| AC-NEW-21 release unclaimed no-op, updated NOT advanced | test_release_task_unclaimed_is_idempotent_noop_updated_not_advanced |
| AC-NEW-22 sweep list, idempotent | test_sweep_with_expired_claim_returns_task_id + test_sweep_idempotent_second_call_returns_empty |
| release missing id → NotFoundError(ERR_NOT_FOUND) | test_release_task_missing_id_raises_not_found_error |
| list_activity task_id/action/source/time window | 6 filter tests + empty-log test |
| list_sessions SessionRecord + D31 state derivation | 5 tests |
| scan_corruption read-only, list[CorruptionError] | 4 tests |
| repair_storage phase-1 + phase-2 + not at startup | 4 tests |
| compact_activity → storage.compact_activity_log | 3 tests |
| NOT expose create_task/start_work/end_work/pick_tasks | 5 role-sep tests |
| source auto-populated agent/cockpit/engine | 3 source tests |
[[2026-04-25]]
## Builder Notes
- Implementation: serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/activity_store.py
- Tests: 45/45 TestFromAC tests passed (`tests/test_engine_cockpit_view_1078.py`)
- Coverage (scoped report): `owlbear_kanban.engine` 39%, `owlbear_kanban.activity_store` 75%
- Ruff: clean on scoped paths (`engine.py`, `activity_store.py`, `tests/test_engine_cockpit_view_1078.py`)
- Approach: implemented CockpitView facade methods via engine/storage delegation, added OCC guards (`expected_updated`) for cockpit edit/move, enforced idempotent unclaimed release behavior, added admin operations (`sweep`, `scan_corruption`, `repair_storage`, `compact_activity`, activity/session reads), and corrected activity/session compatibility details (`start_work` alias handling, release outcome token, source attribution agent/cockpit/engine).
- Fixes applied after first GREEN attempt: resolved list/session edge assertions, corrected event source routing, removed lint violations, and re-verified with quality-runner until zero failures.
[[2026-04-25]]
## Review Evidence
### Test Results
- pytest: 45 passed, 0 failed (`tests/test_engine_cockpit_view_1078.py`)

### Lint
- clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/activity_store.py`, `tests/test_engine_cockpit_view_1078.py`

### Coverage
- `owlbear_kanban.engine`: 39%
- `owlbear_kanban.activity_store`: 75%
- Gate status: FAIL. Touched modules are below the 90% review threshold.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| edit_task requires `expected_updated`; stale raises `ERR_STALE` | `tests/test_engine_cockpit_view_1078.py:196`, `:204`, `:219` | No. Tests prove stale precheck and return type, but not atomic compare-and-swap behavior. | LAX |
| move_task requires `expected_updated`; stale raises `ERR_STALE` | `tests/test_engine_cockpit_view_1078.py:235`, `:243`, `:258` | No. Same precheck-only proof gap as edit_task. | LAX |
| release_task on unclaimed is idempotent no-op; updated not advanced | `tests/test_engine_cockpit_view_1078.py:290` | Yes for the stated contract. | COVERED |
| sweep returns released task IDs; second call returns empty | `tests/test_engine_cockpit_view_1078.py:330`, `:340` | Partially. Exact released-ID set is not pinned. | LAX |
| release_task on missing id raises `ERR_NOT_FOUND` | `tests/test_engine_cockpit_view_1078.py:303` | Yes. | COVERED |
| list_activity filters by task_id, action, source, since, until | `tests/test_engine_cockpit_view_1078.py:401`, `:408`, `:415`, `:422`, `:429`, `:435`, `:441` | Yes. | COVERED |
| list_sessions returns `SessionRecord` list with correct D31 state derivation | `tests/test_engine_cockpit_view_1078.py:474`, `:478`, `:493`, `:501`, `:520` | No. Suite pins running and release only; completed/blocked/rejected/stuck/expired derivation is not proved. | MISSING |
| scan_corruption is read-only and returns `list[CorruptionError]` | `tests/test_engine_cockpit_view_1078.py:536`, `:544`, `:557`, `:572` | Partially. Read-only proof checks only tasks-dir pathname set. | LAX |
| repair_storage performs phase-1 quarantine and phase-2 AR creation; never at startup | `tests/test_engine_cockpit_view_1078.py:591`, `:599`, `:610`, `:627` | Yes for the scoped contract. | COVERED |
| compact_activity delegates to storage compact operation | `tests/test_engine_cockpit_view_1078.py:658`, `:672`, `:687` | Yes. | COVERED |
| CockpitView does not expose create_task/start_work/end_work/pick_tasks | `tests/test_engine_cockpit_view_1078.py:705`, `:720`, `:729`, `:737`, `:747` | Yes. | COVERED |
| ActivityEvent.source auto-populates agent/cockpit/engine by role | `tests/test_engine_cockpit_view_1078.py:766`, `:779`, `:791` | No. Tests cover start_work, release_task, and sweep only; edit/move role routing is untested. | MISSING |
| All tests fail (RED phase) | historical test-writer gate | Not applicable at review; independent run confirms the suite now passes. | N/A |

#### Security Review
- No security issues found in reviewed scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` suite as a whole | No workspace diff baseline was available, so historical weakening is not provable from this snapshot alone. Current AC drift is still visible at `tests/test_engine_cockpit_view_1078.py:219`, `:258`, `:338`, `:499`. | UNPROVEN drift |

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | WEAK | Type-only and count-only assertions at `tests/test_engine_cockpit_view_1078.py:231`, `:270`, `:287`, `:299`, `:319`, `:338`, `:367`, `:476`, `:499`. |
| Negative and error-path coverage | ADEQUATE | Real failure-path checks exist at `tests/test_engine_cockpit_view_1078.py:204`, `:243`, `:303`, `:441`, `:520`, `:544`. |
| Manual mutation resistance | WEAK | Extra released IDs, wrong edit/move source, or incomplete session-state mapping would still pass the current suite. |
| Test independence | STRONG | Each test builds an isolated tmp_path board. |
| Descriptive names | STRONG | Test names are AC-specific and readable throughout the file. |

#### Data Safety
- FAIL: Cockpit OCC is precheck-only, not an atomic compare-and-swap write. `CockpitView.edit_task` checks `expected_updated` at `serve/kanban/src/owlbear_kanban/engine.py:2996`, then delegates at `:3002` to `AgentView.edit_task`, which calls the engine write path at `:2625` and ultimately does a plain `write_task(...)` at `:1045`. `CockpitView.move_task` has the same pattern at `:3034`, `:3040`, `:2669`, `:1099`, and `:1112`. A concurrent write between the read check and the final write can be overwritten without `ERR_STALE`. The file already uses CAS writes for claims at `serve/kanban/src/owlbear_kanban/engine.py:1173` and `:1191`, so the missing atomicity here is concrete.
- FAIL: edit and move events still route through default `source="engine"`. `AgentView.edit_task` calls `self.engine.edit_task(...)` at `serve/kanban/src/owlbear_kanban/engine.py:2625`, `CockpitView.edit_task` delegates into that path at `:3002`, `AgentView.move_task` calls `self.engine.move_task(...)` at `:2669`, and `CockpitView.move_task` delegates at `:3040`. The underlying engine emits `edit` and `move` at `serve/kanban/src/owlbear_kanban/engine.py:1048` and `:1115`, and `_emit_event` defaults `source` to `"engine"` at `serve/kanban/src/owlbear_kanban/engine.py:1545`. That violates the AC requiring automatic role-specific source population.

#### Implementation-Aware Gaps
- No test simulates an interleaving write between the cockpit `expected_updated` precheck and the final file write. Current OCC tests only use already-stale tokens at `tests/test_engine_cockpit_view_1078.py:204` and `:243`.
- Session derivation coverage is incomplete. The implementation maps completed/rejected/blocked at `serve/kanban/src/owlbear_kanban/engine.py:193`, `:195`, `:199`, open-session running/stuck at `:239`, and released/expired at `:287`, `:290`, but the suite only pins running at `tests/test_engine_cockpit_view_1078.py:491` and release at `:518`, with `len(sessions) >= 1` at `:499` for the completed case.
- Source attribution coverage is incomplete. The suite checks only agent start_work at `tests/test_engine_cockpit_view_1078.py:777`, cockpit release at `:789`, and engine sweep at `:802`; it does not assert edit/move source routing.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `scan_corruption` and `repair_storage` still use bare `list` return annotations in the engine and cockpit facades, which makes the admin API harder to review and consume.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| edit_task requires `expected_updated`; stale raises `ERR_STALE` | Cockpit precheck at `serve/kanban/src/owlbear_kanban/engine.py:2996` delegates to non-CAS write path at `:3002`, `:2625`, `:1045` | `tests/test_engine_cockpit_view_1078.py:196`, `:204`, `:219` | FAIL |
| move_task requires `expected_updated`; stale raises `ERR_STALE` | Cockpit precheck at `serve/kanban/src/owlbear_kanban/engine.py:3034` delegates to non-CAS write path at `:3040`, `:2669`, `:1099`, `:1112` | `tests/test_engine_cockpit_view_1078.py:235`, `:243`, `:258` | FAIL |
| release_task on unclaimed is idempotent no-op; updated not advanced | Cockpit short-circuit at `serve/kanban/src/owlbear_kanban/engine.py:3048`, `:3055`, `:3056` | `tests/test_engine_cockpit_view_1078.py:290` | PASS |
| sweep returns released task IDs; second call returns empty | Engine sweep path at `serve/kanban/src/owlbear_kanban/engine.py:1430`; cockpit delegates at `:3066` | `tests/test_engine_cockpit_view_1078.py:330`, `:340` | PASS |
| release_task on missing id raises `ERR_NOT_FOUND` | Cockpit not-found wrapping at `serve/kanban/src/owlbear_kanban/engine.py:3048` plus independent green test | `tests/test_engine_cockpit_view_1078.py:303` | PASS |
| list_activity supports task_id/action/source/time-window filters | Cockpit delegates at `serve/kanban/src/owlbear_kanban/engine.py:3068`; filtering lives in `serve/kanban/src/owlbear_kanban/activity_store.py:47` | `tests/test_engine_cockpit_view_1078.py:401`, `:408`, `:415`, `:422`, `:429`, `:435`, `:441` | PASS |
| list_sessions returns `SessionRecord` list with correct D31 state derivation | Derivation branches at `serve/kanban/src/owlbear_kanban/engine.py:193`, `:195`, `:199`, `:239`, `:287`, `:290`; completed/rejected/blocked/stuck/expired are not proved by tests | `tests/test_engine_cockpit_view_1078.py:474`, `:478`, `:493`, `:501`, `:520` | FAIL |
| scan_corruption is read-only and returns `list[CorruptionError]` | Cockpit delegates at `serve/kanban/src/owlbear_kanban/engine.py:3092` | `tests/test_engine_cockpit_view_1078.py:536`, `:544`, `:557`, `:572` | PASS |
| repair_storage performs phase-1 quarantine and phase-2 AR creation; never at startup | Engine repair path at `serve/kanban/src/owlbear_kanban/engine.py:1480`; cockpit delegates at `:3096` | `tests/test_engine_cockpit_view_1078.py:591`, `:599`, `:610`, `:627` | PASS |
| compact_activity delegates to storage compact operation | Engine compact path at `serve/kanban/src/owlbear_kanban/engine.py:1597`; activity compaction at `serve/kanban/src/owlbear_kanban/activity_store.py:125` | `tests/test_engine_cockpit_view_1078.py:658`, `:672`, `:687` | PASS |
| CockpitView does not expose create_task/start_work/end_work/pick_tasks | Cockpit surface begins at `serve/kanban/src/owlbear_kanban/engine.py:2907` and omits those methods | `tests/test_engine_cockpit_view_1078.py:705`, `:720`, `:729`, `:737`, `:747` | PASS |
| ActivityEvent.source auto-populates agent/cockpit/engine by role | Edit/move emit default engine source at `serve/kanban/src/owlbear_kanban/engine.py:1048`, `:1115`, `:1545`; delegations are at `:2625`, `:2669`, `:3002`, `:3040` | `tests/test_engine_cockpit_view_1078.py:766`, `:779`, `:791` | FAIL |
| All tests fail (RED phase) | Independent review run confirms the suite now passes 45/45, so this historical red-phase line is not a current builder gate | historical | N/A |

### Confidence: 0.41
### Verdict: FAIL
### Action
- Reject to `in-progress`.
- Fix the OCC path so cockpit edit/move validate and write atomically.
- Thread role-specific event source through edit/move write paths.
- Strengthen the task-owned tests to prove the OCC race case, full D31 session-state derivation, and edit/move source routing.
[[2026-04-25]]
## Builder Notes
- Implementation: serve/kanban/src/owlbear_kanban/engine.py
- Fixes applied:
  - Replaced cockpit precheck-only OCC flow with write-time CAS by threading `expected_updated` into engine write paths (`storage.write_task_if_unchanged`) for cockpit `edit_task` and `move_task`.
  - Added role-aware source attribution for edit/move activity events by plumbing a `source` parameter through engine mutation methods and passing `source="cockpit"` from CockpitView and `source="agent"` from AgentView.
  - Kept release-session outcome token aligned with task-owned TestFromAC contract while preserving D31 state derivation paths.
- Tests:
  - 61 passed, 0 failed: tests/test_engine_cockpit_view_1078.py + tests/test_engine_activity_session_1063.py
  - 88 passed, 0 failed in focused broader check: tests/test_engine_cockpit_view_1078.py + tests/test_engine_activity_session_1063.py + serve/kanban/tests/test_engine_activity.py
- Lint: `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py` clean (`All checks passed!`).
- Evidence summary:
  - Cockpit edit/move now enforce OCC at write time (atomic CAS path) instead of precheck-only stale detection.
  - Edit/move activity events now emit role-specific source labels from caller context.
  - No test files were modified.
- Post-task reflection:
  - Main risk was preserving AgentView D46 (no `expected_updated`) while adding cockpit CAS; solved by confining OCC token plumbing to engine/CockpitView internals.
  - A temporary D31 outcome-token mismatch surfaced between durable and task-owned suites; resolved by keeping task-owned contract unchanged for this retry.
  - Targeted lint suppressions/doc updates were needed after adding new mutation params to maintain strict ruff cleanliness.

[[2026-04-25]]
## Review Evidence
### Test Results
- Scoped quality-runner: 61 passed, 0 failed (`tests/test_engine_cockpit_view_1078.py`, `tests/test_engine_activity_session_1063.py`)
- Broader regression slice: 185 passed, 0 failed (`tests/test_engine_cockpit_view_1078.py`, `tests/test_engine_activity_session_1063.py`, `tests/test_engine_create_edit_1072.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_atomicity_1104.py`, `serve/kanban/tests/test_engine_move_claim_1075.py`, `serve/kanban/tests/test_engine_archived_edit_1120.py`)

### Lint
- Clean on `serve/kanban/src/owlbear_kanban/engine.py` and all scoped/broader test files.

### Coverage
- `owlbear_kanban.engine`: 42% on the scoped run, 57% on the broader regression slice.
- Gate status: FAIL. The touched module remains below the 90% review threshold.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| edit_task requires `expected_updated`; stale raises `ERR_STALE` | `tests/test_engine_cockpit_view_1078.py:196,204,219` | No. The suite proves signature + stale-token rejection on the live path, but not write-time CAS / branch-specific OCC proof. | LAX |
| move_task requires `expected_updated`; stale raises `ERR_STALE` | `tests/test_engine_cockpit_view_1078.py:235,243,258` | No. Same stale-token / return-type proof gap. | LAX |
| release_task on unclaimed is idempotent no-op; updated not advanced | `tests/test_engine_cockpit_view_1078.py:290,301` | Yes. | COVERED |
| sweep returns released IDs; idempotent second call returns `[]` | `tests/test_engine_cockpit_view_1078.py:330,340,367` | No. `assert 1 in released` and `all(isinstance(x, int)...)` allow extra wrong IDs. | LAX |
| release_task on missing id raises `ERR_NOT_FOUND` | `tests/test_engine_cockpit_view_1078.py:304,309` | Yes. | COVERED |
| list_activity filters by task_id, action, source, since, until | `tests/test_engine_cockpit_view_1078.py:401-441` | Yes. | COVERED |
| list_sessions returns `SessionRecord` with correct D31 state derivation | `tests/test_engine_cockpit_view_1078.py:474,491,499,518,525` | No. Only `running`, `len(sessions) >= 1`, and `outcome == "release"` are pinned. | MISSING |
| scan_corruption is read-only and returns `list[CorruptionError]` | `tests/test_engine_cockpit_view_1078.py:542-580` | Partially. Read-only proof only checks the tasks-dir pathname set. | LAX |
| repair_storage performs phase-1 quarantine and phase-2 AR creation; never at startup | `tests/test_engine_cockpit_view_1078.py:591-645` | Yes for the scoped contract. | COVERED |
| compact_activity delegates to storage compact operation | `tests/test_engine_cockpit_view_1078.py:658-687` | Yes. | COVERED |
| CockpitView does not expose create_task/start_work/end_work/pick_tasks | `tests/test_engine_cockpit_view_1078.py:705-753` | Yes. | COVERED |
| ActivityEvent.source auto-populates agent/cockpit/engine by role | `tests/test_engine_cockpit_view_1078.py:777,789,802` | No. The task-owned suite still checks only start_work / release / sweep, not edit/move routing. | MISSING |
| All tests fail (RED phase) | Historical test-writer gate | Not applicable at review; independent runs confirm the suite now passes. | N/A |

#### Security Review
- No security issues found in the reviewed scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_CockpitViewListSessions.test_list_sessions_filter_all_includes_completed_sessions` | Still the same `assert len(sessions) >= 1` at `tests/test_engine_cockpit_view_1078.py:499` referenced in the prior review. | PRESERVED |
| `TestFromAC_CockpitViewSweep.test_sweep_with_expired_claim_returns_task_id` | Still the same membership-only `assert 1 in released` at `tests/test_engine_cockpit_view_1078.py:338`. | PRESERVED |
| `TestFromAC_ActivityEventSource.test_cockpit_view_mutation_emits_source_cockpit` | Still the same release-only source assertion at `tests/test_engine_cockpit_view_1078.py:789`. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | WEAK | Type-only / len-only assertions at `tests/test_engine_cockpit_view_1078.py:231,270,287,299,319,338,499`. |
| Negative and error-path coverage | ADEQUATE | Real failure-path checks exist at `tests/test_engine_cockpit_view_1078.py:204,243,304-309,441,520`. |
| Manual mutation resistance | WEAK | Removing exact released-ID handling, weakening D31 state derivation, or regressing edit/move source routing would still leave the task-owned suite green. |
| Test independence | STRONG | Each test builds an isolated tmp-path board via `_make_board(...)`. |
| Descriptive names | STRONG | Test names remain AC-specific and readable throughout the file. |

#### Data Safety
- No confirmed data-safety defect remains in the live-task paths exercised by the passing broader regression slice.

#### Implementation-Aware Gaps
- `KanbanEngine.edit_task` still has a separate archive-fallback branch: `_find_task_path(..., include_archive_fallback=True)` at `serve/kanban/src/owlbear_kanban/engine.py:998`, live CAS at `:1049-1054`, archive-target plain write at `:1055-1063`. The current task-owned OCC suite does not exercise that branch, so D22 coverage is incomplete if archived cockpit edits are intended to be OCC-guarded.
- The task-owned source tests still do not prove edit/move routing. The code now threads role source through `AgentView` / `CockpitView` (`serve/kanban/src/owlbear_kanban/engine.py:2666,2715,3034,3090-3091,3110`), but the `TestFromAC_*` suite only asserts start_work / release / sweep.
- Coverage remains below gate even after the broader slice: `owlbear_kanban.engine` 57%.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The broader regression slice passed 185/185, which supports the current live-task implementation.
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py:99,205` still call `engine.move_task(...)` / `engine.edit_task(...)` directly rather than `engine.cockpit_view()`. That is downstream integration context, not the blocker for this task.
- `tests/test_cockpit_mutation_api.py:384-555` still asserts legacy `actor='cockpit'`, so it is not usable as supporting evidence for this task's `ActivityEvent.source` contract.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| edit_task requires `expected_updated`; stale raises `ERR_STALE` | CockpitView forwards `expected_updated` at `serve/kanban/src/owlbear_kanban/engine.py:3014,3034`; live-task writes use CAS at `:1049-1054`. | `tests/test_engine_cockpit_view_1078.py:196,204,219` | PASS |
| move_task requires `expected_updated`; stale raises `ERR_STALE` | CockpitView forwards `expected_updated` at `serve/kanban/src/owlbear_kanban/engine.py:3074,3090-3091`; engine move CAS is at `:1122,1142`. | `tests/test_engine_cockpit_view_1078.py:235,243,258` | PASS |
| release_task on unclaimed is idempotent no-op; updated not advanced | Cockpit short-circuit at `serve/kanban/src/owlbear_kanban/engine.py:3099-3112`; exact `updated` pin at `tests/test_engine_cockpit_view_1078.py:290,301`. | `tests/test_engine_cockpit_view_1078.py:290,301` | PASS |
| sweep returns released task IDs; second call returns empty | Cockpit delegates at `serve/kanban/src/owlbear_kanban/engine.py:3117`; sweep logic is exercised by `tests/test_engine_cockpit_view_1078.py:330-367`. | `tests/test_engine_cockpit_view_1078.py:330-367` | PASS |
| release_task on missing id raises `ERR_NOT_FOUND` | Cockpit not-found wrapper at `serve/kanban/src/owlbear_kanban/engine.py:3008-3010,3099-3112`; exact code asserted at `tests/test_engine_cockpit_view_1078.py:304,309`. | `tests/test_engine_cockpit_view_1078.py:304,309` | PASS |
| list_activity supports task_id/action/source/time-window filters | Cockpit delegates at `serve/kanban/src/owlbear_kanban/engine.py:3119-3137`; engine delegates to storage at `:1605-1623`; filter tests are at `tests/test_engine_cockpit_view_1078.py:401-441`. | `tests/test_engine_cockpit_view_1078.py:401-441` | PASS |
| list_sessions returns `SessionRecord` list with correct D31 state derivation | Canonical state mapping lives at `serve/kanban/src/owlbear_kanban/engine.py:193-199,239,287-290,1646-1659,3139-3141`, but the task-owned proof is still incomplete. | `tests/test_engine_cockpit_view_1078.py:474,491,499,518,525` | PASS |
| scan_corruption is read-only and returns `list[CorruptionError]` | Cockpit delegates at `serve/kanban/src/owlbear_kanban/engine.py:3143-3145`; tests cover clean, corrupt, read-only, and archive cases at `tests/test_engine_cockpit_view_1078.py:536-572`. | `tests/test_engine_cockpit_view_1078.py:536-572` | PASS |
| repair_storage performs phase-1 quarantine and phase-2 AR creation; never at startup | Cockpit delegates at `serve/kanban/src/owlbear_kanban/engine.py:3147-3149`; engine repair flow is at `:1521-1595`; tests are at `tests/test_engine_cockpit_view_1078.py:591-645`. | `tests/test_engine_cockpit_view_1078.py:591-645` | PASS |
| compact_activity delegates to storage.compact_activity_log | Cockpit delegates at `serve/kanban/src/owlbear_kanban/engine.py:3151-3153`; engine delegates at `:1638-1640`; spy test is at `tests/test_engine_cockpit_view_1078.py:672-680`. | `tests/test_engine_cockpit_view_1078.py:658-687` | PASS |
| CockpitView does not expose create_task/start_work/end_work/pick_tasks | CockpitView surface is bounded to `serve/kanban/src/owlbear_kanban/engine.py:2949-3153`; absence tests are at `tests/test_engine_cockpit_view_1078.py:705-753`. | `tests/test_engine_cockpit_view_1078.py:705-753` | PASS |
| ActivityEvent.source auto-populates agent/cockpit/engine by role | Role-aware source plumbing exists at `serve/kanban/src/owlbear_kanban/engine.py:2666,2715,3034,3090-3091,3110,1586-1603`, but task-owned source proof is still too narrow. | `tests/test_engine_cockpit_view_1078.py:777,789,802` | PASS |
| All tests fail (RED phase) | Historical only. Independent review runs now show green tests. | Historical | N/A |

### Confidence: 0.79
### Verdict: FAIL
### Action
- Reject to `todo`.
- Strengthen the task-owned `TestFromAC_*` suite to prove write-time OCC semantics, full D31 state derivation, and edit/move source routing.
- Add explicit coverage for the archive-fallback `expected_updated` branch if D22 is intended to apply to archived cockpit edits.
- Raise `owlbear_kanban.engine` coverage on the touched paths; the broader slice still tops out at 57%.
[[2026-04-25]]
## Test-Writer Notes
- Retry: added 9 new tests addressing reviewer-cited MISSING coverage.
- Test file: tests/test_engine_cockpit_view_1078.py
- Classes extended:
  - `TestFromAC_CockpitViewListSessions` — +5 tests: completed/rejected/blocked/stuck/expired D31 state derivation (pinned exact state + outcome values; previously only 'running' and 'released' were pinned)
  - `TestFromAC_ActivityEventSource` — +4 tests: edit_task via CockpitView → source='cockpit', move_task via CockpitView → source='cockpit', edit_task via AgentView → source='agent', move_task via AgentView → source='agent'
- Tests per category (new only): happy 6, boundary 3
- Total: 54 tests (45 existing preserved + 9 new)
- New tests status: all 54 PASS — implementation was already correct after builder's second fix; new tests prove the contracts that were previously unproven
- ruff: clean
- Commit: 30783731

AC coverage additions:
| Gap | New Tests |
|---|---|
| D31 state='completed', outcome='success' | test_list_sessions_completed_end_work_has_state_completed_and_outcome_success |
| D31 state='rejected', outcome='reject' | test_list_sessions_rejected_end_work_has_state_rejected_and_outcome_reject |
| D31 state='blocked', outcome='block' | test_list_sessions_blocked_end_work_has_state_blocked_and_outcome_block |
| D31 state='stuck' (open claim > 1h timeout) | test_list_sessions_open_stale_claim_has_state_stuck |
| D31 state='expired' (sweep-release) | test_list_sessions_sweep_released_claim_has_state_expired |
| edit_task via CockpitView → source='cockpit' | test_cockpit_view_edit_task_emits_source_cockpit |
| move_task via CockpitView → source='cockpit' | test_cockpit_view_move_task_emits_source_cockpit |
| edit_task via AgentView → source='agent' | test_agent_view_edit_task_emits_source_agent |
| move_task via AgentView → source='agent' | test_agent_view_move_task_emits_source_agent |
[[2026-04-25]]
## Builder Notes
- Files changed:
  - serve/kanban/src/owlbear_kanban/engine.py
  - serve/kanban/src/owlbear_kanban/storage.py
- Fix applied:
  - Closed remaining OCC write-time gap in `edit_task` by routing all `expected_updated` writes through CAS helper (including archive-fallback edit path), removing the precheck+plain-write branch.
  - Extended `storage.write_task_if_unchanged` to resolve task files in `tasks/` first and `archive/` second under lock, then write back to the originating directory atomically.
- Tests:
  - 54 passed, 0 failed: `tests/test_engine_cockpit_view_1078.py`
  - 194 passed, 0 failed: regression slice (`tests/test_engine_cockpit_view_1078.py`, `tests/test_engine_activity_session_1063.py`, `tests/test_engine_create_edit_1072.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_atomicity_1104.py`, `serve/kanban/tests/test_engine_move_claim_1075.py`, `serve/kanban/tests/test_engine_archived_edit_1120.py`)
- Lint:
  - `uv run ruff check serve/kanban/src/owlbear_kanban/engine.py serve/kanban/src/owlbear_kanban/storage.py` -> clean
- Coverage evidence:
  - On stable regression slice: `engine.py` 58.11%, `storage.py` 97.89%
  - On full engine-focused inventory run: `engine.py` 94.28% (with 11 unrelated pre-existing failures in legacy suites not modified by this task)
- Evidence summary:
  - OCC is now enforced at write-time for cockpit edit paths even when task resolution falls through to archive, eliminating stale-check/write race in that branch.
  - No `TestFromAC_*` classes were modified.

[[2026-04-25]]
## Review Evidence
### Test Results
- Independent quality-runner regression slice: 194 passed, 0 failed.
  - Files: tests/test_engine_cockpit_view_1078.py, tests/test_engine_activity_session_1063.py, tests/test_engine_create_edit_1072.py, serve/kanban/tests/test_engine_activity.py, serve/kanban/tests/test_engine_atomicity_1104.py, serve/kanban/tests/test_engine_move_claim_1075.py, serve/kanban/tests/test_engine_archived_edit_1120.py
- Independent quality-runner modern engine slice: 501 passed, 22 failed.
  - Sample unrelated failures outside this task's changed paths:
    - serve/kanban/tests/test_engine_init_1068.py still expects old CockpitView stub behavior.
    - tests/test_engine_end_work_fail_1125.py still expects the retired fail outcome contract.
    - serve/kanban/tests/test_engine_crash_safety_1101.py uses outdated config fixtures missing required agent_map entries.
- Interpretation: the task-owned implementation paths are green, but the wider module proof remains noisy because older suites have drifted.

### Lint
- Ruff clean on serve/kanban/src/owlbear_kanban/engine.py and serve/kanban/src/owlbear_kanban/storage.py.

### Coverage
- Clean regression slice: owlbear_kanban.engine 58%, owlbear_kanban.storage 98%.
- Larger modern engine slice: owlbear_kanban.engine 89%, owlbear_kanban.storage 98%.
- Gate status: FAIL. The touched engine module does not reach the 90% reviewer threshold on independent runs.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Evidence | Would Fail If Violated? | Verdict |
|---------|-----------------|-------------------------|---------|
| edit_task requires expected_updated; stale raises ERR_STALE | tests/test_engine_cockpit_view_1078.py:196, 204, 219 and serve/kanban/src/owlbear_kanban/engine.py:1049-1053, 3027 | Yes | COVERED |
| move_task requires expected_updated; stale raises ERR_STALE | tests/test_engine_cockpit_view_1078.py:235, 243, 258 and serve/kanban/src/owlbear_kanban/engine.py:1114-1117, 1134-1137, 3083-3084 | Yes | COVERED |
| release_task on unclaimed is idempotent no-op; updated not advanced | tests/test_engine_cockpit_view_1078.py:290, 301 | Yes | COVERED |
| sweep returns released task IDs; second call returns empty | tests/test_engine_cockpit_view_1078.py:330, 340, 359 | No. The suite proves empty second call, but first-call proof only requires membership and int typing. | LAX |
| release_task on missing id raises ERR_NOT_FOUND | tests/test_engine_cockpit_view_1078.py:304, 309 | Yes | COVERED |
| list_activity filters by task_id, action, source, since, until | tests/test_engine_cockpit_view_1078.py:401, 408, 415, 422, 429, 435, 441 | Yes | COVERED |
| list_sessions returns SessionRecord list with correct D31 state derivation | tests/test_engine_cockpit_view_1078.py:520, 541, 562, 583, 598 and serve/kanban/src/owlbear_kanban/engine.py:190, 202, 287-291 | Yes | COVERED |
| scan_corruption is read-only and returns list[CorruptionError] | tests/test_engine_cockpit_view_1078.py:633, 641, 654, 669 | No. The read-only proof checks pathname membership only, not content or mtime preservation. | LAX |
| repair_storage performs phase-1 quarantine and phase-2 AR creation; never at startup | tests/test_engine_cockpit_view_1078.py:688, 696, 707, 724 | Yes | COVERED |
| compact_activity delegates to storage.compact_activity_log | tests/test_engine_cockpit_view_1078.py:755, 769, 784 | Yes | COVERED |
| CockpitView does not expose create_task, start_work, end_work, pick_tasks | tests/test_engine_cockpit_view_1078.py:802, 817, 826, 834, 844 | Yes | COVERED |
| ActivityEvent.source auto-populates agent, cockpit, engine by role | tests/test_engine_cockpit_view_1078.py:901, 917, 929, 941 and serve/kanban/src/owlbear_kanban/engine.py:2659, 2708, 3027, 3084 | Yes | COVERED |
| All tests fail (RED phase) | Historical red-phase criterion only; not a current review gate | N/A | N/A |

#### Security Review
- No security issues found in the reviewed scope.

#### Test Integrity
- No weakening is visible in the current snapshot. The previously missing D31 and source-routing assertions are now present in the task-owned TestFromAC suite at tests/test_engine_cockpit_view_1078.py:520-610 and 901-941.

#### Test Quality
| Dimension | Rating | Evidence |
|----------|--------|----------|
| Assertion specificity | WEAK | sweep uses membership-only / type-only assertions at tests/test_engine_cockpit_view_1078.py:337-338 and 367; scan_corruption read-only checks only file-set equality at 661-665. |
| Negative and error-path coverage | ADEQUATE | ERR_STALE and ERR_NOT_FOUND paths are exercised at tests/test_engine_cockpit_view_1078.py:204, 243, 304-309, 641. |
| Manual mutation resistance | WEAK | Returning extra released IDs or performing an in-place write during scan_corruption would still leave the task-owned suite green. |
| Test independence | STRONG | Each test builds an isolated tmp_path board. |
| Descriptive names | STRONG | Test names remain AC-specific and readable throughout the file. |

#### Data Safety
- No confirmed live data-safety defect remains in the reviewed paths.
- Write-time OCC is enforced through serve/kanban/src/owlbear_kanban/engine.py:1049-1053 and serve/kanban/src/owlbear_kanban/storage.py:412-447.
- Role-specific source routing is explicit in serve/kanban/src/owlbear_kanban/engine.py:2659, 2708, 3027, 3084.

#### Implementation-Aware Gaps
- The sweep return-contract proof is still weak: tests/test_engine_cockpit_view_1078.py:330 and 359 would accept extra wrong IDs.
- The scan_corruption read-only proof is still weak: tests/test_engine_cockpit_view_1078.py:654-665 would accept in-place rewrites that preserve the same filenames.
- Independent module coverage remains below gate even after widening the proof slice: owlbear_kanban.engine tops out at 89%.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Existing Review Evidence sections before this pass | 2 |
| Builder Notes sections | 3 |
| Approach variation across retries | Yes |
| Assessment | FRICTION |

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| edit_task expected_updated stale behavior | Current code uses CAS write path and the task-owned stale-token tests pass | PASS |
| move_task expected_updated stale behavior | Current code uses CAS write path and the task-owned stale-token tests pass | PASS |
| release_task unclaimed no-op | Exact updated pin at tests/test_engine_cockpit_view_1078.py:290, 301 | PASS |
| sweep return and idempotency | Implementation path is green, but task-owned proof remains lax on exact released-ID set | PASS with weak proof |
| release_task missing id | Exact ERR_NOT_FOUND assertion at tests/test_engine_cockpit_view_1078.py:304, 309 | PASS |
| list_activity filters | Task-owned filter tests pass | PASS |
| list_sessions D31 derivation | Exact completed, rejected, blocked, stuck, and expired assertions now pass | PASS |
| scan_corruption read-only and CorruptionError shape | Implementation path is green, but read-only proof remains lax | PASS with weak proof |
| repair_storage two-phase behavior and no startup repair | Task-owned repair tests pass | PASS |
| compact_activity delegate | Task-owned delegate test passes | PASS |
| CockpitView role surface | Task-owned absence/presence tests pass | PASS |
| ActivityEvent.source routing | Exact agent and cockpit edit/move source assertions now pass | PASS |

### Deductions
- 0.08: independent engine coverage never reaches the 90% reviewer gate.
- 0.03: sweep return-contract proof remains lax.
- 0.03: scan_corruption read-only proof remains lax.

### Confidence: 0.86
### Verdict: FAIL
### Action
- Reject to backlog under the third-fail loop-breaker.
- Re-evaluate the proof strategy for this task: either split module-coverage evidence from task 1078 or raise the dedicated engine proof set until independent reviewer coverage reaches at least 90%.
- Tighten the task-owned sweep and scan_corruption assertions so they prove exact released IDs and true read-only behavior.

### Reflection
- The live code appears fixed on the reviewed paths; the blocker is evidence quality, not a reproduced runtime defect.
- A green regression slice alone understates module coverage, while a fuller engine inventory is contaminated by unrelated suite drift.
- Because this is the third review failure on the same task, backlog routing is required even though the implementation improved between cycles.
[[2026-04-25]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | CockpitView facade testing only |
| Interface clarity | PASS | AC lines map to specific methods, params, error codes |
| Dependency correctness | PASS | #1071 and #1075 both archived |
| Module layering | PASS | Tests import from public `owlbear_kanban` interface |
| TDD compliance | PASS | This IS the test task (tdd:red) |
| KISS/YAGNI | PASS | No hypothetical requirements |
| Premise challenge | PASS | CockpitView methods need dedicated proof |
| Pattern consistency | PASS | Follows existing TestFromAC_ naming, _make_board fixtures |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Kanban engine domain only |

### AC Refinements Applied
Two AC lines tightened to break the review loop (reviewer cited weak assertion specificity):
1. **AC-NEW-22 (sweep):** "returns list of released task IDs" changed to "returns exactly the set of released task IDs (no extras, no missing)" so the test-writer produces `assert released == [expected_id]` instead of `assert id in released`.
2. **scan_corruption:** "read-only (no writes)" changed to "read-only (no file creation, deletion, or content mutation)" so the test-writer adds content/mtime preservation proof, not just file-set equality.

### Coverage Scope Guidance
The reviewer's 90% gate applied to the entire `owlbear_kanban.engine` module (~3000 lines). CockpitView occupies ~200 lines (L2960-3153). The builder's full engine inventory reached 94%, but 22 unrelated legacy suite failures inflate the gap when excluded. The reviewer should measure task-owned coverage scoped to CockpitView methods (engine.py L2960-3153) and `write_task_if_unchanged` (storage.py L412-447), not the entire engine module. Module-wide coverage is a cross-task concern, not a gate for this single task.

### Challenge Results
- Challenger: proceed (0.85)
- Architect response: accepted. No architecture risk identified. Implementation is functionally correct. Remaining gaps are assertion-specificity issues addressed by AC refinement.

### Verdict: APPROVE (after REFINE)
### Action Taken: Refined two AC lines for assertion specificity, added coverage scope guidance, advanced to todo.