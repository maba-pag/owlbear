---
id: 1445
title: 'P4-08: Make pick_tasks read-only and keep start_work as claim writer'
status: archived
priority: critical
created: 2026-05-08T19:32:02.327561+00:00
updated: 2026-05-11T03:10:21.943902+00:00
tags:
- phase-4
- scope:kanban
- type:refactor
- dispatch
- claims
- deployment-readiness
parent: 1437
depends_on:
- 1444
- 1439
- 1443
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context
Brief: see parent #1437.

## Scope
In scope: AgentView.pick_tasks, legacy dispatch helper behavior as needed, and start_work claim reclamation boundaries.
Out of scope: explicit resolve_drs MCP tool, Cockpit maintenance cleanup, and docs.

## Acceptance Criteria
1. AgentView.pick_tasks returns dispatch waves without calling sweep, repair_storage, resolve_pending_drs, edit_task, move_task, write_task, or task archival helpers.
2. Given an unblocked backlog task with expired claimed_at and no unresolved dependencies, AgentView.pick_tasks returns the task in a wave and leaves claimed_at unchanged on disk.
3. Given a pending DR whose response is approved, AgentView.pick_tasks leaves the DR file in decisions/pending and leaves the linked task body and blocked fields unchanged.
4. AgentView.start_work remains the writer that clears an expired claim and applies the caller's claim in one compare-and-swap retry loop.
5. Builder verifies AC-1 through AC-4 using the probe artifacts from #1444 and does not use pytest or vitest as the functional proof.
[[2026-05-10]]


## Corrected Acceptance Criteria (supersedes original AC)

1. AgentView.pick_tasks returns dispatch waves without calling sweep, repair_storage, resolve_pending_drs, edit_task, move_task, write_task, or task archival helpers. (td:1)
2. Given an unblocked backlog task with expired claimed_at (per engine's claim_timeout configuration) and no unresolved dependencies, AgentView.pick_tasks returns the task in a wave and leaves claimed_at unchanged on disk. (td:2)
3. Given a pending DR whose response is approved, AgentView.pick_tasks leaves the DR file in decisions/pending and leaves the linked task body and blocked fields unchanged. (td:1)
4. engine.claim_task (delegated through engine.start_work → AgentView.start_work) remains the writer that clears an expired claim and applies the caller's claim in one compare-and-swap retry loop. (td:0)
5. Existing tests asserting pick_tasks calls resolve_pending_drs (test_pick_tasks_resolve.py, relevant cases in test_engine_ble001.py and test_engine_lazy_agent_map.py) are removed or updated to match the new read-only contract. Regression suites pass. (td:0)

### Refinement Notes
1. **AC-4 boundary corrected**: Original said "AgentView.start_work remains the writer" — the actual CAS writer is `engine.claim_task` (engine.py:1354). AgentView.start_work (agent_view.py:941) delegates to engine.start_work (engine.py:1537) which delegates to engine.claim_task. Corrected to name the real write boundary.
2. **AC-5 removed (no-pytest clause)**: Removed "does not use pytest or vitest as the functional proof" per sibling precedent — #1439 and #1443 both removed this identical clause as pipeline-incompatible. The probe artifacts from #1444 serve as implementation reference alongside the test-writer's test suite.
3. **AC-5 added (test cleanup)**: Builder must update/remove existing tests that assert the old resolve_pending_drs integration: `test_pick_tasks_resolve.py` (full file), 5 tests in `test_engine_ble001.py` (lines 297-648), 1 test in `test_engine_lazy_agent_map.py` (line 383).
4. **Test-depth annotations added**: AC-1 td:1, AC-2 td:2 (expired vs. live claim paths, timeout boundary, file immutability), AC-3 td:1, AC-4 td:0 (preserves existing tested behavior), AC-5 td:0 (mechanical test cleanup).

### Builder Guidance
- **AC-1 implementation**: Remove the `resolve_pending_drs` call block (agent_view.py:384-391) and update the pick_tasks docstring (lines 304-321) to remove the "Resolve" step.
- **AC-2 implementation**: Replace `list_tasks(unclaimed=True)` with unclaimed=False (or omit), then filter locally using `dispatch._claim_is_active(task, timeout)` — already exists in dispatch.py:71 and is used by the legacy dispatch helper at dispatch.py:181. Access timeout via `_parse_duration(config.pipeline.claim_timeout)` from `owlbear_kanban._duration`.
- **AC-3**: Follows from AC-1 — removing resolve_pending_drs means DRs and linked tasks are untouched.
- **AC-4**: No code change needed — preserves existing engine.claim_task CAS behavior.
- **Rollout note**: After this task and before #1447 (explicit resolve_drs MCP tool), approved DRs will not auto-resolve during dispatch. This is the intended brief design.

[[2026-05-10]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: make pick_tasks read-only. All AC lines serve this purpose. |
| Interface clarity | PASS (after refinement) | AC-4 boundary corrected to engine.claim_task; claim_timeout reference added to AC-2; test cleanup AC added. |
| Dependency correctness | PASS | #1444 (probe), #1439 (topology), #1443 (id allocation) all archived/done. |
| Module layering | PASS | Changes within agent_view.py (pick_tasks method) in kanban package. No upward imports. dispatch._claim_is_active reuse follows existing pattern. |
| TDD compliance | PASS (after refinement) | Original AC-5 prohibited pytest — REMOVED per sibling precedent (#1439, #1443). Task goes through normal test-writer → builder flow. |
| KISS/YAGNI | PASS | Code deletion (remove resolve_pending_drs) + filter modification (expired claims). Minimal scope. |
| Premise challenge | PASS | pick_tasks write side-effects must be removed for deployment readiness. No existing alternative. |
| Pattern consistency | PASS | Follows Phase 4 probe+implementation pattern; reuses dispatch._claim_is_active for claim eligibility. |
| Security surface | N/A | No new system boundaries. |
| Single domain | PASS | kanban domain only (scope:kanban). |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| pick_tasks expired-claim filter | _claim_is_active timeout parse fails | ValueError | Yes — config validated at load | No dispatch, guidance logged |
| pick_tasks DR left pending | Approved DR not auto-resolved | N/A (by design) | Yes — #1447 adds explicit tool | Interim: manual DR resolution until #1447 |

### Codebase Context
- pick_tasks: agent_view.py:299 — currently calls resolve_pending_drs (line 388) and list_tasks(unclaimed=True) (line 394)
- list_tasks unclaimed filter: engine.py:689 — filters claimed_at is None (excludes expired claims)
- resolve_pending_drs: decisions.py:143 — moves DR files, edits task bodies, clears blocked
- _claim_is_active: dispatch.py:71 — existing helper, used by legacy dispatch at line 181
- claim_task CAS: engine.py:1354 — two-step CAS with 4 stale retries (_MAX_CLAIM_STALE_RETRIES=4)
- _parse_duration: _duration.py:11 — already imported in engine.py, available for agent_view.py
- Existing tests to update: test_pick_tasks_resolve.py (full file), test_engine_ble001.py (5 tests: lines 297-648), test_engine_lazy_agent_map.py (1 test: line 383)

### Dependency Analysis
- Inbound: none active
- Outbound: #1447 depends on #1445 for resolve_drs MCP tool (confirmed via task search)
- Rollout gap: between #1445 and #1447, approved DRs don't auto-resolve — intentional per brief

### Challenge Results
- Challenger: INVOKED, returned high risk (confidence 0.42)
- Critical findings accepted: (1) AC-4 boundary corrected to engine.claim_task, (2) no-pytest clause removed per sibling precedent
- Moderate findings addressed: test cleanup surface enumerated in new AC-5; rollout gap documented as intentional
- Override: none — all critical findings incorporated

### Verdict: APPROVE (after refinement)
Corrected 3 AC issues: (1) AC-4 write boundary → engine.claim_task, (2) removed pipeline-incompatible no-pytest clause, (3) added test cleanup AC. Added td annotations and builder guidance with codebase references. Advanced to todo.
[[2026-05-10]]
## Test-Writer Notes

**Test file:** `tests/test_agent_view_pick_tasks_1445.py`
**Class:** `TestFromAC_PickTasksReadOnly`, `TestFromAC_PickTasksExpiredClaim`, `TestFromAC_PickTasksDRImmutability`

### Tests per category

| Class | Category | Count |
|---|---|---|
| `TestFromAC_PickTasksReadOnly` | smoke | 1 |
| `TestFromAC_PickTasksExpiredClaim` | happy / boundary / edge | 4 |
| `TestFromAC_PickTasksDRImmutability` | smoke / regression guard | 2 |

**Total: 7 tests — all FAIL**

### AC Coverage

| AC | td | Tests |
|---|---|---|
| AC-1: pick_tasks doesn't call resolve_pending_drs | td:1 | `test_resolve_pending_drs_not_called` |
| AC-2: expired-claim task dispatched, claimed_at unchanged | td:2 | 4 tests (happy, boundary, edge, immutability) |
| AC-3: approved DR stays in pending; linked task unchanged | td:1 | `test_approved_dr_stays_in_pending_directory`, `test_linked_task_not_modified_by_pick_tasks` |
| AC-4: engine.claim_task CAS behavior preserved | td:0 | skip |
| AC-5: test cleanup (remove old resolve tests) | td:0 | skip |

### Failure confirmation
All 7 tests fail against current implementation:
- AC-1 test: `assert_not_called()` fails — resolve_pending_drs called 1 time
- AC-2 tests (4): expired-claim tasks excluded by `list_tasks(unclaimed=True)`
- AC-3 tests (2): resolve_pending_drs moves DR + edits linked task

Ruff: clean. Commit: `23a1cbb9`.
[[2026-05-10]]
## Builder Notes
- Implementation:
  - Updated `serve/kanban/src/owlbear_kanban/agent_view.py` to make `pick_tasks()` read-only.
  - Removed `resolve_pending_drs` side-effect from `pick_tasks()`.
  - Switched `list_tasks(..., unclaimed=True)` to timeout-aware local filtering using `dispatch._claim_is_active(task, _parse_duration(config.pipeline.claim_timeout))`, so expired claims are dispatchable without mutating disk state.
  - Updated `pick_tasks()` docstring pipeline steps to match new read-only behavior.
- Legacy test cleanup (AC-5):
  - Deleted obsolete `tests/test_pick_tasks_resolve.py` (encoded old resolve-on-pick contract).
  - Removed obsolete resolve-pending-drs assertions from `tests/test_engine_ble001.py`.
  - Removed obsolete resolve ordering test from `tests/test_engine_lazy_agent_map.py`.
- Tests (quality-runner):
  - RED verification before implementation:
    - `tests/test_agent_view_pick_tasks_1445.py` -> 0 passed / 7 failed (expected).
  - GREEN verification after implementation:
    - scoped run: `tests/test_agent_view_pick_tasks_1445.py`, `tests/test_engine_ble001.py` -> 27 passed / 0 failed.
    - expanded scoped regression: `tests/test_agent_view_pick_tasks_1445.py`, `tests/test_agent_view_extraction.py`, `tests/test_engine_ble001.py` -> 42 passed / 0 failed.
- Lint (quality-runner):
  - clean: true on touched source/tests.
- Coverage (quality-runner scoped report):
  - overall_pct: 29
  - `owlbear_kanban.agent_view`: 23%
- Evidence summary:
  - AC-1/3 satisfied: `pick_tasks()` no longer imports/calls decisions resolver; DR files/task bodies remain untouched during dispatch.
  - AC-2 satisfied: expired claims are considered dispatchable using claim-timeout semantics while `claimed_at` remains unchanged on disk.
  - AC-4 preserved: no changes to claim CAS writer path (`engine.claim_task` via `start_work`).
  - AC-5 satisfied: outdated resolve-coupled tests removed/updated and scoped regressions pass.
- Commit:
  - `f28b51e0` (`refactor(kanban): make pick_tasks read-only dispatch (#1445, builder)`)
[[2026-05-10]]
## Review Evidence
### Test Results
- quality-runner broad scoped pass: 353 passed, 10 failed, 0 skipped. All 10 failures were unrelated `TestFromAC_PickTasksValidatesAgentMap` / MCP validation cases in `tests/test_engine_lazy_agent_map.py`; used as regression context only.
- quality-runner narrow scoped rerun: 349 passed, 0 failed, 0 skipped across `tests/test_agent_view_pick_tasks_1445.py`, `tests/test_engine_ble001.py`, `tests/test_agent_view_extraction.py`, `serve/kanban/tests/test_engine_coverage.py`, and `serve/kanban/tests/test_engine_move_claim.py`.

### Lint Results
- Ruff clean on touched source/tests.

### Coverage
- `owlbear_kanban.agent_view`: 72% module coverage. Diff-scoped gate not disproven; module percentage informational only.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. `AgentView.pick_tasks` returns dispatch waves without calling sweep, repair_storage, resolve_pending_drs, edit_task, move_task, write_task, or task archival helpers. | Implementation is read-only in `serve/kanban/src/owlbear_kanban/agent_view.py:298-516`, but task-local proof only asserts `resolve_pending_drs.assert_not_called()` in `tests/test_agent_view_pick_tasks_1445.py:120-140`; no discriminating sentinel covers the remaining named writer/helper calls. | FAIL |
| 2. Expired-claim backlog task is dispatchable per configured `claim_timeout` and leaves `claimed_at` unchanged on disk. | Implementation reads `config.pipeline.claim_timeout` at `serve/kanban/src/owlbear_kanban/agent_view.py:374` and filters without writing, and task-local tests prove expired-task inclusion plus on-disk immutability in `tests/test_agent_view_pick_tasks_1445.py:152-234`. But the suite never overrides `_BASE_CONFIG` (`tests/test_agent_view_pick_tasks_1445.py:31`) and its boundary proof hardcodes the default 1h assumption (`tests/test_agent_view_pick_tasks_1445.py:196`), so the `per engine configuration` clause is not fully discriminated. | FAIL |
| 3. Approved pending DR stays in `decisions/pending` and linked task body/blocked fields remain unchanged. | Directly asserted in `tests/test_agent_view_pick_tasks_1445.py:247-301`; current `pick_tasks` body contains no decision-processing branch before response assembly. | PASS |
| 4. `engine.claim_task` remains the CAS writer via `engine.start_work -> AgentView.start_work`. | `engine.claim_task` remains the writer at `serve/kanban/src/owlbear_kanban/engine.py:1354`; `engine.start_work` still delegates at `serve/kanban/src/owlbear_kanban/engine.py:1537-1554`; adjacent CAS/retry regressions remain green in `serve/kanban/tests/test_engine_coverage.py:1132` and `serve/kanban/tests/test_engine_move_claim.py:612`, `:712`, `:760`. | PASS |
| 5. Old resolve-on-pick tests are removed/updated and regressions pass. | `tests/test_pick_tasks_resolve.py` is absent; `tests/test_engine_lazy_agent_map.py` has no remaining `resolve_pending_drs` expectation; `tests/test_engine_ble001.py:278` retains only stale docstring wording. Narrow regression rerun is green. | PASS |

### Test Quality / Deductions
- `-0.08` AC-1 proof is lax. Current TestFromAC coverage would not fail if another named write helper were introduced while leaving `resolve_pending_drs` untouched.
- `-0.08` AC-2 proof is lax. Current TestFromAC coverage would still pass if timeout handling were hardcoded to 1h instead of honoring `config.pipeline.claim_timeout`.
- `-0.03` Dirty-tree contamination could not be ruled out definitively because terminal/git status access was unavailable; commit `f28b51e0` existence was verified indirectly.

### Verdict
- FAIL. First review cycle. Implementation appears correct, but AC-1 and AC-2 are not proven strongly enough by the current tests, so confidence is `0.81` (< `0.90`).

### Action
- Reject to `todo` for test-writer strengthening only. No builder source change identified.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen AC-1 proof with discriminating assertions or sentinels for the remaining named write helpers so `pick_tasks` would fail review if it called any of `sweep`, `repair_storage`, `edit_task`, `move_task`, `write_task`, or archival helpers. | `tests/test_agent_view_pick_tasks_1445.py` | Current proof only pins `resolve_pending_drs` non-call at `tests/test_agent_view_pick_tasks_1445.py:120-140`. |
| 2 | test-writer | Add a non-default `claim_timeout` configuration case proving expired-claim eligibility follows `config.pipeline.claim_timeout` rather than a hardcoded 1h timeout. | `tests/test_agent_view_pick_tasks_1445.py` | `_BASE_CONFIG` stays default at `tests/test_agent_view_pick_tasks_1445.py:31` while implementation reads the configured timeout at `serve/kanban/src/owlbear_kanban/agent_view.py:374`; current boundary proof at `tests/test_agent_view_pick_tasks_1445.py:196` assumes 1h. |
[[2026-05-10]]
## Test-Writer Notes
- Retry (Step 1b.1): reviewer gaps filled — all new tests PASS against current impl → builder skipped, advancing directly to review.
- Test file: `tests/test_agent_view_pick_tasks_1445.py`
- Classes: `TestFromAC_PickTasksReadOnly`, `TestFromAC_PickTasksExpiredClaim`, `TestFromAC_PickTasksDRImmutability`

### New tests added (2 total)

| Test | Class | Gap addressed |
|---|---|---|
| `test_no_engine_write_methods_called` | `TestFromAC_PickTasksReadOnly` | AC-1: patches `sweep`, `repair_storage`, `edit_task`, `move_task` on engine; asserts none are called — catches any write helper introduction beyond `resolve_pending_drs` |
| `test_expired_claim_respects_configured_timeout` | `TestFromAC_PickTasksExpiredClaim` | AC-2: patches `owlbear_kanban.agent_view._parse_duration` to return 5 min; asserts task claimed 6 min ago is dispatched — fails if implementation uses hardcoded 1h |

### Quality-runner result (9 tests total)
- passed: 9, failed: 0
- ruff: clean
- Commit: `cb70041a`
[[2026-05-11]]
## Builder Notes
- Scope check: task entered builder with implementation already present from prior cycle (`serve/kanban/src/owlbear_kanban/agent_view.py`) and test-writer retry already committed (`tests/test_agent_view_pick_tasks_1445.py`).
- Code changes this cycle: none (no source or test edits required).
- Verification (quality-runner, broad scoped): 10 failures in `tests/test_engine_lazy_agent_map.py` (`DID NOT RAISE` expectations), treated as unrelated background regression context.
- Verification (quality-runner, narrow task evidence): 351 passed, 0 failed, 0 skipped across:
  - `tests/test_agent_view_pick_tasks_1445.py`
  - `tests/test_engine_ble001.py`
  - `tests/test_agent_view_extraction.py`
  - `serve/kanban/tests/test_engine_coverage.py`
  - `serve/kanban/tests/test_engine_move_claim.py`
- Coverage (scoped): `owlbear_kanban.agent_view` 72% (informational; unchanged module this cycle).
- Ruff: clean on scoped paths.
- AC evidence summary:
  - AC-1/AC-3 behavior remains read-only in `pick_tasks`; no dispatch-side decision mutation observed in task suite.
  - AC-2 timeout-aware expired-claim dispatch behavior remains green in strengthened task tests.
  - AC-4 CAS writer path remains in engine (`engine.claim_task` via `engine.start_work -> AgentView.start_work`) with regression tests passing.
  - AC-5 cleanup remains in place with updated BLE001 expectations and obsolete resolve-on-pick suite removed.
- Outcome: GREEN verification complete with no additional builder intervention required.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 351 passed, 0 failed, 0 skipped across `tests/test_agent_view_pick_tasks_1445.py`, `tests/test_engine_ble001.py`, `tests/test_agent_view_extraction.py`, `serve/kanban/tests/test_engine_coverage.py`, and `serve/kanban/tests/test_engine_move_claim.py`.

### Lint Results
- Ruff clean on the scoped source/test paths.

### Coverage
- `owlbear_kanban.agent_view`: 72% module coverage.
- Coverage is informational here; the gate failure is proof quality on AC-1 / AC-2, not runtime regressions.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| 1. `pick_tasks` returns dispatch waves without calling `sweep`, `repair_storage`, `resolve_pending_drs`, `edit_task`, `move_task`, `write_task`, or task archival helpers. | `tests/test_agent_view_pick_tasks_1445.py::test_resolve_pending_drs_not_called`; `tests/test_agent_view_pick_tasks_1445.py::test_no_engine_write_methods_called`; DR immutability tests at lines 307+ and 336+ | No. The retry only patches engine methods `sweep`, `repair_storage`, `edit_task`, and `move_task` (`tests/test_agent_view_pick_tasks_1445.py:159-162`). It still does not pin `write_task` or archival helpers named in the AC. | LAX |
| 2. Expired-claim task is dispatchable per configured `claim_timeout` and leaves `claimed_at` unchanged on disk. | `tests/test_agent_view_pick_tasks_1445.py::test_expired_claim_task_included_in_waves`; `::test_expired_claim_claimed_at_unchanged_on_disk`; `::test_claim_just_expired_beyond_timeout_included`; `::test_multiple_expired_claim_tasks_all_dispatched`; `::test_expired_claim_respects_configured_timeout` | No. The implementation correctly reads `config.pipeline.claim_timeout` and passes it into `_claim_is_active` (`serve/kanban/src/owlbear_kanban/agent_view.py:374,383`), but the retry test only patches `_parse_duration` to return 5 minutes (`tests/test_agent_view_pick_tasks_1445.py:289`) while the board config remains default-only (`tests/test_agent_view_pick_tasks_1445.py:32`). That test would still pass if the implementation hardcoded `_parse_duration("1h")` instead of using the configured value. The on-disk immutability assertion is also substring-only (`tests/test_agent_view_pick_tasks_1445.py:221`). | LAX |
| 3. Approved pending DR stays in `decisions/pending` and linked task body / blocked fields stay unchanged. | `tests/test_agent_view_pick_tasks_1445.py::test_approved_dr_stays_in_pending_directory`; `::test_linked_task_not_modified_by_pick_tasks` | Yes. These tests directly assert the pending/resolved file state and unchanged blocked/body content. | COVERED |
| 4. `engine.claim_task` remains the writer via `engine.start_work -> AgentView.start_work`. | td:0 AC; verified by source and adjacent regressions | PASS. `AgentView.start_work` still delegates at `serve/kanban/src/owlbear_kanban/agent_view.py:951`; `engine.start_work` still delegates to `claim_task` at `serve/kanban/src/owlbear_kanban/engine.py:1554`; scoped regression suites stayed green. | PASS |
| 5. Legacy resolve-on-pick tests are removed/updated and regressions pass. | Static inspection + scoped regression run | PASS. `tests/test_pick_tasks_resolve.py` is absent; `tests/test_engine_ble001.py` retains only stale prose, not the old assertion contract; scoped regressions are green. | PASS |

#### Security Review
- No new security issues found in the scoped implementation. `pick_tasks` remains a read-only selection path over internal board state.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `tests/test_agent_view_pick_tasks_1445.py` | Retry added tests for engine mutator non-calls and timeout handling | STRENGTHENED |
| `tests/test_engine_ble001.py` | Old resolve-on-pick executable assertions removed; stale prose remains | PRESERVED |
| `tests/test_engine_lazy_agent_map.py` | No remaining `resolve_pending_drs` assertion found | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | AC-2 immutability still uses substring presence (`tests/test_agent_view_pick_tasks_1445.py:221`) rather than exact `claimed_at` field equality. |
| Negative/error-path coverage | ADEQUATE | DR immutability and stale-claim edge paths are exercised. |
| Manual mutation reasoning | WEAK | AC-1 still lacks a sentinel for direct `write_task` / archival-helper calls; AC-2 retry still passes if the implementation uses `_parse_duration("1h")` instead of `config.pipeline.claim_timeout`. |
| Test independence | STRONG | Task tests build a fresh board per case. |
| Descriptive test names | ADEQUATE | Names are generally clear, but one adjacent delegation test still overstates proof. |

#### Data Safety
- No new data safety issues found.

#### Implementation-Aware Gaps
- No implementation bug found in the live source for AC-1 through AC-5. The failing condition is insufficient proof quality on the remaining AC-1 / AC-2 assertions.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 - INFORMATIONAL
- `serve/kanban/src/owlbear_kanban/agent_view.py` docstring still says pick_tasks excludes claimed tasks, while the implementation now excludes only active claims.
- `tests/test_engine_ble001.py` retains stale prose describing `resolve_pending_drs` failure handling.
- Dirty-tree contamination could not be ruled out directly because git-status access was unavailable in this review environment; commit presence for `f28b51e0` and `cb70041a` was verified via `.git/logs/*`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1 | Source is read-only in `serve/kanban/src/owlbear_kanban/agent_view.py:374-516`, but the retry only patches `sweep` / `repair_storage` / `edit_task` / `move_task` in `tests/test_agent_view_pick_tasks_1445.py:159-162`; no discriminating proof covers `write_task` or archival helpers named in the AC. | `test_resolve_pending_drs_not_called`; `test_no_engine_write_methods_called`; DR immutability tests | FAIL |
| 2 | Source correctly reads `config.pipeline.claim_timeout` at `serve/kanban/src/owlbear_kanban/agent_view.py:374` and filters with it at `:383`, but the retry test proves only `_parse_duration` return usage (`tests/test_agent_view_pick_tasks_1445.py:289`) while config stays default (`:32`); immutability proof is substring-only (`:221`). | Expired-claim task suite in `tests/test_agent_view_pick_tasks_1445.py` | FAIL |
| 3 | Pending DR path is directly pinned by file-existence and task-content assertions in `tests/test_agent_view_pick_tasks_1445.py:307-361`. | DR immutability tests | PASS |
| 4 | Delegation chain remains `AgentView.start_work -> engine.start_work -> claim_task` at `serve/kanban/src/owlbear_kanban/agent_view.py:951` and `serve/kanban/src/owlbear_kanban/engine.py:1554`; adjacent regression suites stayed green. | td:0 / adjacent regressions | PASS |
| 5 | `tests/test_pick_tasks_resolve.py` is gone and the scoped regression run is green (351 passed, 0 failed). | Static inspection + quality-runner | PASS |

### Deductions
- `-0.07` AC-1 proof still does not discriminate against direct `write_task` or archival-helper regressions.
- `-0.08` AC-2 retry still does not prove the configured-timeout input path; it proves only patched parser output.
- `-0.03` AC-2 on-disk immutability assertion is substring-only.
- `-0.02` Dirty-tree contamination could not be checked directly in this environment.

### Confidence: 0.80
### Verdict: FAIL
### Action
- Reject to `backlog`. This is the second review-cycle failure on the same proof gap family (`## Review Evidence` already exists in the task body), so the loop-breaker rule applies. The implementation remains plausible, but the TestFromAC proof contract still does not satisfy the refined AC strongly enough for a PASS.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine the AC-1 proof contract so the next retry explicitly discriminates against lower-level `write_task` and archival-helper calls, not only engine mutators. | `.owlbear/kanban/tasks/1445-p4-08-make-pick-tasks-read-only-and-keep-start-work-as-claim-writer.md`, `tests/test_agent_view_pick_tasks_1445.py` | Current retry only patches `sweep`, `repair_storage`, `edit_task`, and `move_task` at `tests/test_agent_view_pick_tasks_1445.py:159-162`. |
| 2 | architect | Refine the AC-2 proof contract to require a non-default `config.pipeline.claim_timeout` case and an exact `claimed_at` field comparison on disk before re-dispatching to test-writer. | `.owlbear/kanban/tasks/1445-p4-08-make-pick-tasks-read-only-and-keep-start-work-as-claim-writer.md`, `tests/test_agent_view_pick_tasks_1445.py` | Retry test uses patched parser output at `tests/test_agent_view_pick_tasks_1445.py:289` while config stays default at `:32`; immutability check is substring-only at `:221`. |
[[2026-05-11]]

## Proof-Contract Refinement (Review Cycle 2 Return)

### AC-1: Add `write_task` sentinel

The test `test_no_engine_write_methods_called` patches `sweep`, `repair_storage`, `edit_task`, `move_task` on the engine instance. This covers engine-level mutators but misses `storage.write_task` — a module-level function in `owlbear_kanban.storage` (line 363) that is the low-level file writer used by all engine mutators.

**Required change:** Add a sentinel patch for `owlbear_kanban.storage.write_task` (not an engine method — patch the module-level function) and assert it is not called. This closes the remaining AC-1 gap; "task archival helpers" are already covered since archiving routes through `engine.move_task` (already patched).

### AC-2: Config-path proof and exact field comparison

**Gap 1 — config input path:** The retry test `test_expired_claim_respects_configured_timeout` patches `owlbear_kanban.agent_view._parse_duration` to return `timedelta(minutes=5)`. This overrides the function regardless of its input, so the test passes even if the implementation hardcodes `_parse_duration("1h")`.

**Required change:** Do NOT patch `_parse_duration`. Instead, mutate `engine._config.pipeline.claim_timeout = "5m"` after engine construction (PipelineConfig is a mutable Pydantic BaseModel, not frozen). Then call `pick_tasks`. The real `_parse_duration("5m")` runs and returns `timedelta(minutes=5)`. A task claimed 6 minutes ago is expired under 5m but active under 1h — if the implementation ignores the configured value, the test fails.

**Gap 2 — exact immutability assertion:** The on-disk immutability check at line 221 uses `expired_ts_raw in content` (substring match). This does not prove the `claimed_at` field value is unchanged — only that the string appears somewhere in the file.

**Required change:** Parse the task file's YAML frontmatter (split on `---`, parse the YAML block, extract `claimed_at`) and compare the field value exactly against the original timestamp. This proves the field itself was not modified, not merely that the string is present.

### Summary of test-writer actions
1. In `test_no_engine_write_methods_called`: add `patch("owlbear_kanban.storage.write_task") as mock_write_task` and `mock_write_task.assert_not_called()`.
2. In `test_expired_claim_respects_configured_timeout`: remove the `_parse_duration` patch; set `engine._config.pipeline.claim_timeout = "5m"` before `pick_tasks()`.
3. In `test_expired_claim_claimed_at_unchanged_on_disk`: replace substring check with YAML frontmatter parse and exact `claimed_at` field comparison.
[[2026-05-11]]
## Architecture Review (Cycle 2 Return)

### Context
Loop-breaker return from reviewer. Implementation is correct; the issue is test proof quality on AC-1 and AC-2. Two review cycles failed on the same gap family.

### Refinement Actions
1. **AC-1**: Added `write_task` sentinel requirement — `owlbear_kanban.storage.write_task` (module-level function, not engine method) must be patched and asserted not-called alongside existing engine mutator sentinels.
2. **AC-2 config-path**: Replaced `_parse_duration` patch approach with direct config mutation (`engine._config.pipeline.claim_timeout = "5m"`). Forces real parser to run with configured value — fails if implementation hardcodes `"1h"`.
3. **AC-2 immutability**: Replaced substring check with YAML frontmatter parse and exact `claimed_at` field comparison.

### Verdict: APPROVE (refinement applied)
AC wording unchanged. Proof-contract refinement appended with explicit test-writer instructions for 3 surgical test changes. No AC rewrite needed. Advancing to todo for test-writer retry.
[[2026-05-11]]
## Test-Writer Notes
- Retry (Step 1b.1): architect proof-contract refinement applied — all 3 new tests PASS against current impl → builder skipped, advancing directly to review.
- Test file: `tests/test_agent_view_pick_tasks_1445.py`
- Classes: `TestFromAC_PickTasksReadOnly`, `TestFromAC_PickTasksExpiredClaim`, `TestFromAC_PickTasksDRImmutability`

### Changes made (3 surgical edits)

| Test | Change | Gap addressed |
|---|---|---|
| `test_no_engine_write_methods_called` | Added `patch("owlbear_kanban.storage.write_task") as mock_write_task` + `assert_not_called()` | AC-1: closes `write_task` sentinel gap — detects any file-write bypass of engine mutators |
| `test_expired_claim_respects_configured_timeout` | Removed `_parse_duration` patch; added `engine._config.pipeline.claim_timeout = "5m"` config mutation before `pick_tasks()` | AC-2: real `_parse_duration` now runs with configured value — fails if hardcoded 1h |
| `test_expired_claim_claimed_at_unchanged_on_disk` | Replaced `expired_ts_raw in content` substring check with YAML frontmatter parse + exact `claimed_at` field equality | AC-2: exact field value comparison proves `claimed_at` is unchanged, not just string-present |

### Quality-runner result (9 tests total)
- passed: 9, failed: 0
- ruff: clean
- Commit: `d2f13036`
[[2026-05-11]]
## Builder Notes
- Scope check: implementation and proof-contract test updates were already present from prior cycles; no additional builder code edits were required in this pass.
- Files changed this cycle: none.
- Verification (quality-runner, scoped): 351 passed, 0 failed, 0 errors across:
  - tests/test_agent_view_pick_tasks_1445.py
  - tests/test_engine_ble001.py
  - tests/test_agent_view_extraction.py
  - serve/kanban/tests/test_engine_coverage.py
  - serve/kanban/tests/test_engine_move_claim.py
- Lint (ruff): clean on all scoped source/test paths.
- Coverage: owlbear_kanban.agent_view 72% (informational in this cycle; no source edits).
- AC evidence summary:
  - AC-1: read-only dispatch contract remains validated by strengthened sentinels in task-scoped tests.
  - AC-2: configured claim-timeout path + exact claimed_at immutability assertions remain green.
  - AC-3: approved DR remains in pending and linked task remains unchanged during pick_tasks.
  - AC-4: claim CAS writer path unchanged (`engine.claim_task` via `engine.start_work -> AgentView.start_work`).
  - AC-5: resolve-on-pick legacy tests remain removed/updated; scoped regressions pass.
- Commit activity this cycle: none (no file modifications).
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner scoped pass: 351 passed, 0 failed, 0 skipped across `tests/test_agent_view_pick_tasks_1445.py`, `tests/test_engine_ble001.py`, `tests/test_agent_view_extraction.py`, `serve/kanban/tests/test_engine_coverage.py`, and `serve/kanban/tests/test_engine_move_claim.py`.
- quality-runner follow-up regression on `serve/kanban/tests/test_engine_pick_tasks.py`: 26 passed, 1 failed. Failing test: `TestFromAC_PickTasksAC22Proof::test_claimed_task_excluded_from_pick_tasks`.

### Lint Results
- Ruff clean on scoped source/tests and on `serve/kanban/tests/test_engine_pick_tasks.py`.

### Coverage
- `owlbear_kanban.agent_view`: 72% on the main scoped run.
- `owlbear_kanban.agent_view`: 28% on the single-file follow-up regression run.
- Coverage is informational here. The gate failure is AC-2 proof quality / adjacent regression health, not line coverage.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| 1. `AgentView.pick_tasks` returns dispatch waves without calling `sweep`, `repair_storage`, `resolve_pending_drs`, `edit_task`, `move_task`, `write_task`, or task archival helpers. | Live source is read-only in `serve/kanban/src/owlbear_kanban/agent_view.py:374-516`. Task tests pin no `resolve_pending_drs` call plus no `sweep` / `repair_storage` / `edit_task` / `move_task` / `write_task` calls at `tests/test_agent_view_pick_tasks_1445.py:121-172`. | `test_resolve_pending_drs_not_called`; `test_no_engine_write_methods_called` | PASS |
| 2. Expired-claim backlog task is dispatchable per configured `claim_timeout` and leaves `claimed_at` unchanged on disk. | Source reads config at `serve/kanban/src/owlbear_kanban/agent_view.py:374` and filters at `:383`. Task-local tests prove expired-claim inclusion, exact on-disk `claimed_at` equality, and non-default config input at `tests/test_agent_view_pick_tasks_1445.py:200-225` and `:271-297`. But the architecture refinement explicitly bound td:2 proof to expired-vs-live claim paths, and the surviving durable live-claim regression is red on the current snapshot: `serve/kanban/tests/test_engine_pick_tasks.py:622-639` writes `claimed_at='"2026-04-25T10:00:00+00:00"'` at `:633` and fails `assert 1 not in ids` at `:638`. The task retry never replaced that missing live-claim branch with a current proof. | Expired-claim task suite in `tests/test_agent_view_pick_tasks_1445.py`; failing adjacent regression `serve/kanban/tests/test_engine_pick_tasks.py::TestFromAC_PickTasksAC22Proof::test_claimed_task_excluded_from_pick_tasks` | FAIL |
| 3. Approved pending DR stays in `decisions/pending` and linked task body / blocked fields stay unchanged. | Directly asserted at `tests/test_agent_view_pick_tasks_1445.py:309-361`. | `test_approved_dr_stays_in_pending_directory`; `test_linked_task_not_modified_by_pick_tasks` | PASS |
| 4. `engine.claim_task` remains the CAS writer via `engine.start_work -> AgentView.start_work`. | `AgentView.start_work` still delegates at `serve/kanban/src/owlbear_kanban/agent_view.py:951`; `engine.start_work` still returns `claim_task` at `serve/kanban/src/owlbear_kanban/engine.py:1554`; claim CAS writes remain in `serve/kanban/src/owlbear_kanban/engine.py:1401-1421`. Adjacent start-work regressions stayed green at `serve/kanban/tests/test_engine_move_claim.py:563`, `:612`, `:634`, `:712`, `:760` and `serve/kanban/tests/test_engine_coverage.py:1111`, `:1132`. | Adjacent regression suites | PASS |
| 5. Old resolve-on-pick tests are removed/updated and regressions pass. | `tests/test_pick_tasks_resolve.py` is absent. `tests/test_engine_lazy_agent_map.py` has no remaining `resolve_pending_drs` assertion. `tests/test_engine_ble001.py:272-278` retains stale prose but not the old executable contract. | Static inspection + scoped regression run | PASS |

### Pass 1 - CRITICAL
#### Security Review
- No new security issues found in the scoped implementation. `pick_tasks` remains a read-only selection path over internal board state.

#### Test Integrity
- No weakened `TestFromAC_*` assertions found in the current snapshot.
- Commit presence for task-related changes was verified in `.git/logs/*` for `f28b51e0`, `cb70041a`, and `d2f13036`. Diff-based immutability could not be proven directly in this environment.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | The latest retry closes the earlier `write_task` and exact-`claimed_at` gaps in `tests/test_agent_view_pick_tasks_1445.py:164`, `:225`, and `:290`. |
| Negative/error-path coverage | WEAK | AC-2 td:2 was refined to cover expired-vs-live claim paths, but the live-claim exclusion branch is not proven in the task-local retry and the older durable proof is red at `serve/kanban/tests/test_engine_pick_tasks.py:622-639`. |
| Manual mutation reasoning | WEAK | Removing or bypassing the active-claim branch at `serve/kanban/src/owlbear_kanban/agent_view.py:383` would not fail any task-local AC-2 test on this review surface. |
| Test independence | STRONG | Task tests build isolated temporary boards. |
| Descriptive test names | ADEQUATE | Names are clear overall; one adjacent durable test is stale, not ambiguous. |

#### Data Safety
- No new data-safety issues found.

#### Implementation-Aware Gaps
- No implementation bug was identified in the live source for AC-1 / AC-3 / AC-4 / AC-5.
- The blocking issue is AC-2 proof quality: the current task-local suite proves expired-claim inclusion, but the live-claim branch remains unowned after the durable regression in `serve/kanban/tests/test_engine_pick_tasks.py` went stale.

### Pass 2 - INFORMATIONAL
- `tests/test_engine_ble001.py:272-278` still documents the old `resolve_pending_drs` path in prose.
- Dirty-tree contamination could not be checked directly because `git status` access was unavailable in this review environment.

### Deductions
- `-0.10` AC-2 still lacks a passing live-claim exclusion proof on the current snapshot.
- `-0.03` Adjacent durable regression for claimed-task filtering is red.
- `-0.02` Dirty-tree contamination could not be checked directly.

### Confidence: 0.83
### Verdict: FAIL
### Action
- Reject to `backlog`. This is a 2nd+ review failure on task `#1445`, so the loop-breaker rule applies. The implementation is plausible, but the AC-2 proof contract is still incomplete on the live snapshot.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Refine AC-2 so the next retry explicitly owns the active-claim exclusion branch alongside the expired-claim inclusion branch, and decide whether that proof must live in the task-local suite or an adjacent durable suite. | `.owlbear/kanban/tasks/1445-p4-08-make-pick-tasks-read-only-and-keep-start-work-as-claim-writer.md`, `tests/test_agent_view_pick_tasks_1445.py`, `serve/kanban/tests/test_engine_pick_tasks.py` | Task-local AC-2 proof covers only expired claims (`tests/test_agent_view_pick_tasks_1445.py:200-297`); adjacent live-claim proof is red at `serve/kanban/tests/test_engine_pick_tasks.py:622-639`. |
| 2 | architect | Update or split the stale durable claimed-task regression so it uses a truly active claim timestamp and can serve as discriminating proof on future retries. | `serve/kanban/tests/test_engine_pick_tasks.py` | The current fixture writes `claimed_at='"2026-04-25T10:00:00+00:00"'` at `serve/kanban/tests/test_engine_pick_tasks.py:633` and then fails `assert 1 not in ids` at `:638` on the live snapshot. |
[[2026-05-11]]

## Proof-Contract Refinement (Review Cycle 3 Return)

### AC-2: Add active-claim exclusion branch (td:2 both paths)

**Gap:** td:2 requires multiple paths/edges. The current proof covers only the expired-claim inclusion path. The complementary path — that a task with an *active* claim (within `claim_timeout`) is excluded from waves — has no passing test. The durable test that previously covered this (`serve/kanban/tests/test_engine_pick_tasks.py::test_claimed_task_excluded_from_pick_tasks`) is stale because it uses a fixed timestamp in the past.

**Required change (task-local suite):** Add `test_active_claim_excluded_from_waves` to `TestFromAC_PickTasksExpiredClaim` in `tests/test_agent_view_pick_tasks_1445.py`:
- Create a task with `claimed_at` set to `datetime.now(UTC) - timedelta(minutes=5)` (5 minutes ago, well within the default 1h timeout).
- Call `pick_tasks()`.
- Assert the task is NOT in the returned wave IDs.
- This is the discriminating complement: removing the `claim_is_active` filter at `agent_view.py:388` would pass all existing expired-claim tests but fail this one.

### AC-5: Add stale durable test to cleanup scope

**Gap:** `serve/kanban/tests/test_engine_pick_tasks.py::TestFromAC_PickTasksAC22Proof::test_claimed_task_excluded_from_pick_tasks` (lines 622-639) was written for the old `list_tasks(unclaimed=True)` contract. It uses a hardcoded timestamp `"2026-04-25T10:00:00+00:00"` which is now expired relative to the 1h default timeout, so the implementation correctly *includes* it — causing the assertion to fail.

**Required change:** Update the test to use a truly active claim timestamp (`datetime.now(UTC) - timedelta(minutes=5)`). Update the docstring to reference the new timeout-aware filtering contract instead of `unclaimed=True`. The assertion logic (`assert 1 not in ids`) remains the same.

### Summary of test-writer actions
1. In `tests/test_agent_view_pick_tasks_1445.py`, class `TestFromAC_PickTasksExpiredClaim`: add `test_active_claim_excluded_from_waves` — task with `claimed_at` 5 min ago must NOT appear in waves.
2. In `serve/kanban/tests/test_engine_pick_tasks.py`, class `TestFromAC_PickTasksAC22Proof`: update `test_claimed_task_excluded_from_pick_tasks` — replace fixed past timestamp with `datetime.now(UTC) - timedelta(minutes=5)` and update docstring.

[[2026-05-11]]
## Architecture Review (Cycle 3 Return)

### Context
Loop-breaker return from reviewer (2nd review failure). Implementation is correct. The blocking issue is AC-2 proof incompleteness: task-local suite proves expired claims are dispatched but has no test proving active claims are excluded. The durable test that previously covered this is stale.

### Refinement Actions
1. **AC-2 active-claim branch**: Required `test_active_claim_excluded_from_waves` in task-local suite — task with `claimed_at` 5 min ago (within 1h timeout) must NOT appear in waves. This is the td:2 complementary path; removing the `claim_is_active` filter at `agent_view.py:388` would fail this test while passing all existing expired-claim tests.
2. **AC-5 durable test fix**: Added `test_engine_pick_tasks.py::test_claimed_task_excluded_from_pick_tasks` to cleanup scope — replace hardcoded past timestamp with `datetime.now(UTC) - timedelta(minutes=5)` and update docstring from `unclaimed=True` to timeout-aware filtering.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same single concern: make pick_tasks read-only |
| Interface clarity | PASS | AC-2 now requires both branches; AC-5 now covers stale durable test |
| Dependency correctness | PASS | Dependencies all archived/done |
| Module layering | PASS | No new imports or cross-package dependencies |
| TDD compliance | PASS | Refinement is test-only; no source changes needed |
| KISS/YAGNI | PASS | Two surgical test additions/fixes |
| Pattern consistency | PASS | Follows existing test patterns in both suites |

### Verdict: APPROVE (refinement applied)
AC wording unchanged. Proof-contract refinement appended with explicit test-writer instructions for 2 changes: (1) add active-claim exclusion test to task-local suite, (2) fix stale durable test. Advancing to todo.
[[2026-05-11]]
## Test-Writer Notes
- Retry (Step 1b.1): architect proof-contract refinement (Cycle 3) applied — all new tests PASS against current impl → builder skipped, advancing directly to review.
- Test file: `tests/test_agent_view_pick_tasks_1445.py`
- Durable file: `serve/kanban/tests/test_engine_pick_tasks.py`
- Classes: `TestFromAC_PickTasksReadOnly`, `TestFromAC_PickTasksExpiredClaim`, `TestFromAC_PickTasksDRImmutability`

### Changes made (2 surgical edits)

| File | Change | Gap addressed |
|---|---|---|
| `tests/test_agent_view_pick_tasks_1445.py` | Added `test_active_claim_excluded_from_waves` to `TestFromAC_PickTasksExpiredClaim` — task with `claimed_at` 5 min ago (within 1h default) must NOT appear in waves | AC-2: td:2 complementary path — removing `_claim_is_active` filter at `agent_view.py:388` would fail this test while passing all expired-claim tests |
| `serve/kanban/tests/test_engine_pick_tasks.py` | Added `from datetime import UTC, datetime, timedelta`; updated `test_claimed_task_excluded_from_pick_tasks` — replaced hardcoded past timestamp `"2026-04-25T10:00:00+00:00"` with `datetime.now(UTC) - timedelta(minutes=5)` and updated docstring from `unclaimed=True` to timeout-aware filtering | AC-2/AC-5: stale durable test now uses a truly active claim — previously expired relative to 1h default, causing incorrect inclusion |

### Quality-runner result (37 tests total)
- passed: 37, failed: 0
- ruff: clean
- Commit: `8ec4171c`
[[2026-05-11]]
## Builder Notes
- Files changed: none in this builder pass (implementation and test-proof updates were already present from prior cycles).
- Verification run (quality-runner, scoped): 379 passed, 0 failed, 0 skipped.
- Test scope:
  - tests/test_agent_view_pick_tasks_1445.py
  - tests/test_engine_ble001.py
  - tests/test_agent_view_extraction.py
  - serve/kanban/tests/test_engine_coverage.py
  - serve/kanban/tests/test_engine_move_claim.py
  - serve/kanban/tests/test_engine_pick_tasks.py
- Lint: ruff clean (`clean: true`, no violations).
- Coverage: `owlbear_kanban.agent_view` 74% (overall scoped run 51%).
- Evidence summary:
  - AC-1: read-only pick_tasks contract remains validated.
  - AC-2: expired-claim inclusion and active-claim exclusion paths are both green in current suite.
  - AC-3: approved DR remains pending; linked task remains unchanged.
  - AC-4: claim CAS writer path remains engine.claim_task via start_work delegation.
  - AC-5: legacy resolve-on-pick expectations remain removed/updated with passing regression coverage.
- Outcome: GREEN verification complete; advancing to review.
[[2026-05-11]]
## Review Evidence
### Test Results
- quality-runner task-local pass: `tests/test_agent_view_pick_tasks_1445.py` -> 10 passed, 0 failed.
- quality-runner expanded scoped regression: 383 passed, 10 failed across `tests/test_agent_view_pick_tasks_1445.py`, `serve/kanban/tests/test_engine_pick_tasks.py`, `tests/test_engine_ble001.py`, `tests/test_engine_lazy_agent_map.py`, `tests/test_agent_view_extraction.py`, `serve/kanban/tests/test_engine_coverage.py`, and `serve/kanban/tests/test_engine_move_claim.py`.
- All 10 failures are isolated to pre-existing RED-phase `agent_map` validation tests in `tests/test_engine_lazy_agent_map.py` (task #1221 scope). They do not exercise the read-only dispatch contract reviewed here.
- Relevant adjacent durable suites for #1445 are green: `serve/kanban/tests/test_engine_pick_tasks.py`, `tests/test_engine_ble001.py`, `tests/test_agent_view_extraction.py`, `serve/kanban/tests/test_engine_coverage.py`, and `serve/kanban/tests/test_engine_move_claim.py`.

### Lint Results
- Ruff clean on `serve/kanban/src/owlbear_kanban/agent_view.py`, `tests/test_agent_view_pick_tasks_1445.py`, `serve/kanban/tests/test_engine_pick_tasks.py`, `tests/test_engine_ble001.py`, and `tests/test_engine_lazy_agent_map.py`.

### Coverage
- `owlbear_kanban.agent_view`: 74% module coverage.
- Coverage is informational here; the changed-path proof is carried by the task-local assertions plus adjacent green regressions.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| 1. `AgentView.pick_tasks` returns dispatch waves without calling sweep, repair_storage, resolve_pending_drs, edit_task, move_task, write_task, or task archival helpers. | Live `pick_tasks` reads config, filters active claims, rehydrates with `show_task`, and builds response entries in `serve/kanban/src/owlbear_kanban/agent_view.py:374-516`; `resolve_pending_drs` is absent from the file. Task tests pin no calls to `resolve_pending_drs`, `sweep`, `repair_storage`, `edit_task`, `move_task`, and `storage.write_task` in `tests/test_agent_view_pick_tasks_1445.py:121-164`. No current archival-helper or other writer call surface is present in the reviewed method body. | PASS |
| 2. Expired-claim backlog task is dispatchable per configured `claim_timeout` and leaves `claimed_at` unchanged on disk. | Exact on-disk `claimed_at` equality is asserted via YAML frontmatter parse in `tests/test_agent_view_pick_tasks_1445.py:200-225`. Non-default config proof sets `engine._config.pipeline.claim_timeout = "5m"` in `tests/test_agent_view_pick_tasks_1445.py:271-297`. Active-claim exclusion is pinned in `tests/test_agent_view_pick_tasks_1445.py:300-323`, and the adjacent durable live-claim regression is green in `serve/kanban/tests/test_engine_pick_tasks.py:623-643`. | PASS |
| 3. Approved pending DR stays in `decisions/pending` and linked task body / blocked fields stay unchanged. | Pending DR immutability is asserted by file-presence / no-resolved-file checks in `tests/test_agent_view_pick_tasks_1445.py:344-362`. Linked task immutability is asserted by unchanged `blocked: true` and no appended decision-summary marker in `tests/test_agent_view_pick_tasks_1445.py:365-390`. Combined with AC-1's no-writer evidence, no task mutation path remains in `pick_tasks`. | PASS |
| 4. `engine.claim_task` remains the CAS writer via `engine.start_work -> AgentView.start_work`. | `AgentView.start_work` still delegates at `serve/kanban/src/owlbear_kanban/agent_view.py:941-951`. `engine.start_work` still delegates to `claim_task` at `serve/kanban/src/owlbear_kanban/engine.py:1537-1554`. `claim_task` still performs the expired-claim clear and new claim via CAS writes inside one retry loop at `serve/kanban/src/owlbear_kanban/engine.py:1372-1419`. Adjacent CAS/retry suites in `serve/kanban/tests/test_engine_move_claim.py` and `serve/kanban/tests/test_engine_coverage.py` remained green in the scoped run. | PASS |
| 5. Old resolve-on-pick tests are removed/updated and regressions pass. | `tests/test_pick_tasks_resolve.py` is absent. No `resolve_pending_drs` executable expectation remains in `tests/test_engine_lazy_agent_map.py`. `tests/test_engine_ble001.py:277-289` retains stale prose only, not an executable resolve-on-pick assertion. Relevant regression suites are green; unrelated RED-phase `agent_map` failures in `tests/test_engine_lazy_agent_map.py` are outside #1445 scope. | PASS |

### Reviewer Synthesis
- Code-reader raised an archival-helper proof concern on AC-1. Direct source inspection found no archival-helper or other writer call surface in the current `pick_tasks` implementation beyond the already-pinned engine/storage methods, so this was classified as non-blocking.
- Code-reader also flagged AC-4 wording against the adjacent CAS suite. Direct inspection of `engine.claim_task` shows the expired-claim path performs two CAS writes inside a single retry loop, which matches the AC's write-boundary requirement rather than contradicting it.

### Deductions
- `-0.03` Dirty-tree contamination could not be checked directly in this environment because `git status` access was unavailable.
- `-0.02` Task commit ownership was verified indirectly via `.git/logs/*` entries for `f28b51e0`, `cb70041a`, `d2f13036`, and `8ec4171c`, not via direct diff inspection.
- `-0.01` `tests/test_engine_ble001.py` still contains stale prose about the removed resolve-on-pick contract, but the executable proof surface is correct.

### Confidence: 0.94
### Verdict: PASS
### Action
- Advance to docs.
[[2026-05-11]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/kanban/README.md` line 62 said "exclude claimed" — inaccurate after timeout-aware filtering was introduced; updated to "exclude tasks with an active claim per configured `claim_timeout`" |
| 2 | Module docstrings | Yes | Updated | `agent_view.py` pick_tasks docstring Filter step said "exclude claimed" — same inaccuracy; updated to "exclude tasks with an active claim (per configured ``claim_timeout``)" |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `kanban.excalidraw` and `mcp-topology.excalidraw` both have `describes: serve/kanban/src/**` — footers bumped from `2026-05-10 (f5dcd426)` → `2026-05-11 (8ec4171c)` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | `tests/test_pick_tasks_resolve.py` deleted — test file is OUT-scope; no IN-scope docs reference it |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/agent_view.py` | IN (docstrings) | Updated docstring |
| `serve/kanban/README.md` | IN | Updated prose |
| `share/diagrams/kanban.excalidraw` | IN | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN | Footer updated |
| `tests/test_agent_view_pick_tasks_1445.py` | OUT (test) | N/A |
| `tests/test_pick_tasks_resolve.py` (deleted) | OUT (test) | N/A |
| `tests/test_engine_ble001.py` | OUT (test) | N/A |
| `tests/test_engine_lazy_agent_map.py` | OUT (test) | N/A |
| `serve/kanban/tests/test_engine_pick_tasks.py` | OUT (test) | N/A |

### Files Updated
- `serve/kanban/README.md`
- `serve/kanban/src/owlbear_kanban/agent_view.py` (docstring only)
- `share/diagrams/kanban.excalidraw`
- `share/diagrams/mcp-topology.excalidraw`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `1445-*` scratch files existed)
[[2026-05-11]]
## Audit
### Regression Detection
- quality-runner mode full: 2784 passed, 192 failed (Python); 179/974 (Vitest env issue). Task-scoped regression (6 files, 379 tests): 0 failed.
- Broader failures investigated: `test_engine_lazy_agent_map.py` (10, RED-phase #1221), `test_engine_dispatch_validation.py` (10, RED-phase #1474), `test_mcp_kanban.py` (1, missing fixture #1170), remainder in cockpit/ideation/shell domains — all pre-existing, none attributable to #1445.
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS — all changed files in kanban domain: `agent_view.py`, task tests, legacy test cleanup, `README.md`, diagrams
- purpose match: PASS — pick_tasks made read-only by removing resolve_pending_drs and switching to timeout-aware claim filtering; matches stated purpose exactly
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 3/5
Original AC needed 3 architect refinement cycles (initial correction + 2 loop-breaker returns) to reach sufficient proof-contract specificity. Behavioral AC was correct after initial arch review; the cycling was caused by insufficient test-proof guidance — write_task sentinel (cycle 2), config-path proof and exact field comparison (cycle 2), active-claim exclusion branch (cycle 3). Each refinement was surgical and correct, but a 4/5 AC would have specified discriminating proof contracts upfront, avoiding 2 full review rejections.

### Commit Integrity
- upstream commit presence: PASS — builder `f28b51e0`, test-writer `cb70041a`/`d2f13036`/`8ec4171c`, doc-writer `28d3c7e3` all verified via git log
- kanban commit packaging: PASS (pending this archive commit)
- deleted file verified: `tests/test_pick_tasks_resolve.py` absent
- dirty tree: only kanban task files modified (expected for archival)

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| AC quality score 3 | -.03 |

### Confidence: 0.97
### Action: archive