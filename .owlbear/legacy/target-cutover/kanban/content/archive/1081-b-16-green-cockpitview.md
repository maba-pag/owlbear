---
id: 1081
title: 'B-16: GREEN — CockpitView'
status: archived
priority: medium
created: 2026-04-21 10:50:32.631056+00:00
updated: 2026-04-27T17:02:20.919798+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1078
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §5, §3.8
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement CockpitView facade — OCC-guarded mutations + admin operations. Two categories:

1. **OCC-guarded writes:** edit_task and move_task with mandatory `expected_updated` param, routed through `storage.write_task_if_unchanged` (Brief C CAS primitive). Mismatch → ConcurrencyError(ERR_STALE).

2. **Admin operations:** release_task (unconditional claim clear, idempotent), sweep (expire all stale claims via CAS), scan_corruption (read-only), repair_storage (two-phase: scan_and_fix + AR creation), compact_activity.

3. **Activity reads:** list_activity (filtered raw events), list_sessions (derived SessionRecord view per D31).

## Acceptance Criteria

- [ ] All RED tests from B-15 (#1078) pass
- [ ] edit_task/move_task route through storage CAS; ERR_STALE on mismatch
- [ ] release_task: idempotent on unclaimed (AC-NEW-21)
- [ ] sweep: returns released task IDs; idempotent (AC-NEW-22); per-task CAS, skip on ERR_STALE
- [ ] scan_corruption: read-only, returns list[CorruptionError]
- [ ] repair_storage: phase-1 (storage scan_and_fix) + phase-2 (AR creation via engine); never at startup
- [ ] compact_activity: delegates to storage.compact_activity_log
- [ ] list_activity: filter by task_id, action, source, time window
- [ ] list_sessions: derive SessionRecord from activity events; filter per D31
- [ ] ActivityEvent.source set automatically per §3.8 (agent/cockpit/engine)
- [ ] Method exposure: NO create_task, start_work, end_work, pick_tasks on CockpitView
[[2026-04-27]]
## Test-Writer Notes
- Non-impl pass-through: all 1081 ACs are fully covered by the RED phase test file from task #1078 (`tests/test_engine_cockpit_view_1078.py`, 65 tests, all currently passing).
- AC coverage map:
  - edit_task/move_task OCC → TestFromAC_CockpitViewOCC (8 tests)
  - release_task idempotent (AC-NEW-21) → TestFromAC_CockpitViewReleaseTask (5 tests)
  - sweep return/idempotent/CAS (AC-NEW-22/23) → TestFromAC_CockpitViewSweep + TestFromAC_CockpitViewSweepCAS (8 tests)
  - scan_corruption read-only → TestFromAC_CockpitViewScanCorruption (6 tests)
  - repair_storage phase-1+phase-2+startup guard → TestFromAC_CockpitViewRepairStorage (4 tests)
  - compact_activity delegate → TestFromAC_CockpitViewCompactActivity (3 tests)
  - list_activity filters → TestFromAC_CockpitViewListActivity (10 tests)
  - list_sessions derive/filter → TestFromAC_CockpitViewListSessions (11 tests)
  - ActivityEvent.source auto-set → TestFromAC_ActivityEventSource (8 tests)
  - Role separation (no agent-only methods) → TestFromAC_CockpitViewRoleSeparation (5 tests)
- No new test file created — #1078 RED tests serve as the GREEN phase contract.
- Builder target: make all 65 tests in test_engine_cockpit_view_1078.py pass (currently passing — implementation exists).
[[2026-04-27]]
## Builder Notes
- Non-implementation task detected from `## Test-Writer Notes` (explicit non-impl pass-through).
- No code changes were made.
- Passing task through to review per `w-tdd-green` Step 0a.
[[2026-04-27]]
## Review Evidence
### Test Results
- Task-owned suite via quality-runner: pytest 65 passed, 0 failed, 0 skipped on `tests/test_engine_cockpit_view_1078.py`.
- Broader engine-context rerun: 277 passed, 1 failed in `serve/kanban/tests/test_engine_atomicity_1104.py::TestFromAC_EngineAtomicity::test_move_task_archive_emit_failure_file_stays_in_tasks`; used only as background context because the task-scoped suite already isolated 1081-specific behavior.

### Lint
- Ruff clean on `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/activity_store.py`, `serve/kanban/src/owlbear_kanban/corruption.py`, `serve/kanban/src/owlbear_kanban/models.py`, and `tests/test_engine_cockpit_view_1078.py`.

### Coverage
- Scoped task suite: `owlbear_kanban.engine` 44%, `owlbear_kanban.activity_store` 76%, `owlbear_kanban.corruption` 47%, `owlbear_kanban.models` 90% (52% aggregate across specified modules).
- Broader engine-context run: `owlbear_kanban.engine` 62%.
- Coverage is supporting context here; the rejection is driven by weak AC proof in the task-owned `TestFromAC_*` suite.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All RED tests from B-15 (#1078) pass | quality-runner execution on `tests/test_engine_cockpit_view_1078.py` | Yes | COVERED |
| edit_task/move_task route through storage CAS; ERR_STALE on mismatch | `TestFromAC_CockpitViewOCC` | No — stale-token and response-type assertions do not prove `storage.write_task_if_unchanged` is used | LAX |
| release_task: idempotent on unclaimed (AC-NEW-21) | `TestFromAC_CockpitViewReleaseTask` | Yes | COVERED |
| sweep: returns released task IDs; idempotent; per-task CAS, skip on ERR_STALE | `TestFromAC_CockpitViewSweep` + `TestFromAC_CockpitViewSweepCAS` | Yes | COVERED |
| scan_corruption: read-only, returns list[CorruptionError] | `TestFromAC_CockpitViewScanCorruption` | Yes | COVERED |
| repair_storage: phase-1 (storage scan_and_fix) + phase-2 (AR creation via engine); never at startup | `TestFromAC_CockpitViewRepairStorage` | No — phase-2 only checks that some task file contains `type:user-action`, not that engine-mediated AR creation path was used | LAX |
| compact_activity: delegates to storage.compact_activity_log | `TestFromAC_CockpitViewCompactActivity` | Yes | COVERED |
| list_activity: filter by task_id, action, source, time window | `TestFromAC_CockpitViewListActivity` | Yes | COVERED |
| list_sessions: derive SessionRecord from activity events; filter per D31 | `TestFromAC_CockpitViewListSessions` | No — fixtures use compatibility alias `start_work` and `block:` instead of live engine-emitted `claim`, `blocked:`, and `outcome=fail` shapes | LAX |
| ActivityEvent.source set automatically per §3.8 (agent/cockpit/engine) | `TestFromAC_ActivityEventSource` | Yes | COVERED |
| Method exposure: NO create_task, start_work, end_work, pick_tasks on CockpitView | `TestFromAC_CockpitViewRoleSeparation` | Yes | COVERED |

#### Security Review
- No issues found in the reviewed paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `tests/test_engine_cockpit_view_1078.py` `TestFromAC_*` suite | Builder notes say no code changes; no weakening evidence surfaced in current snapshot | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | `test_edit_task_matching_expected_updated_returns_single_task_response` and `test_move_task_matching_expected_updated_returns_single_task_response` only assert wrapper type, not CAS helper route or persisted mutation |
| Negative/error-path coverage | WEAK | `list_sessions` tests never exercise the engine `outcome=fail` branch |
| Manual mutation reasoning | WEAK | Replacing the edit/move CAS helper with manual timestamp checks plus plain writes would still satisfy current assertions |
| Test independence | STRONG | Tests build isolated temp boards and activity logs per case |
| Descriptive names | STRONG | Test names map clearly to AC intent |

#### Data Safety
- No issues found. The implementation uses CAS writes and locked activity append/compact paths.

#### Implementation-Aware Gaps
- `edit_task` / `move_task` implementation calls `storage.write_task_if_unchanged`, but the task-owned suite never proves that helper route.
- `repair_storage` uses `type(self).create_task(...)` for phase-2 AR creation, but the suite only checks for any file containing `type:user-action`.
- `list_sessions` compatibility code accepts `claim` and `start_work`, but the suite only hand-writes `start_work` rows and uses `block:` instead of the engine’s `blocked:` / `outcome=fail` detail shapes.
- Because of those gaps, the suite is not mutation-resistant on multiple ACs.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `scan_corruption` / `repair_storage` are annotated as plain `list` rather than `list[CorruptionError]` / `list[RepairOutcome]`; not blocking.
- The broader engine-context run surfaced one unrelated atomicity failure around `.1001.lock` cleanup; not used to gate 1081 because the scoped suite and scoped lint already isolated the task contract.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All RED tests from B-15 (#1078) pass | quality-runner: 65 passed, 0 failed | `tests/test_engine_cockpit_view_1078.py` | PASS |
| edit_task/move_task route through storage CAS; ERR_STALE on mismatch | engine writes via CAS helper, but tests only prove stale error + wrapper type | `TestFromAC_CockpitViewOCC` | FAIL |
| release_task: idempotent on unclaimed (AC-NEW-21) | unclaimed path returns unchanged record and tests assert `updated` is not advanced | `TestFromAC_CockpitViewReleaseTask` | PASS |
| sweep: returns released task IDs; idempotent; per-task CAS, skip on ERR_STALE | spy-backed sweep CAS tests prove skip/continue semantics | `TestFromAC_CockpitViewSweep` + `TestFromAC_CockpitViewSweepCAS` | PASS |
| scan_corruption: read-only, returns list[CorruptionError] | tests assert no writes, archive scan, and typed error list | `TestFromAC_CockpitViewScanCorruption` | PASS |
| repair_storage: phase-1 + phase-2 via engine; never at startup | startup guard and phase-1 are proved, but phase-2 engine mediation is not | `TestFromAC_CockpitViewRepairStorage` | FAIL |
| compact_activity: delegates to storage.compact_activity_log | direct spy proves storage delegate | `TestFromAC_CockpitViewCompactActivity` | PASS |
| list_activity: filter by task_id, action, source, time window | tests assert exact task/action identity inside windows | `TestFromAC_CockpitViewListActivity` | PASS |
| list_sessions: derive SessionRecord from activity events; filter per D31 | tests do not cover real engine-emitted `claim`, `blocked:`, and `outcome=fail` shapes | `TestFromAC_CockpitViewListSessions` | FAIL |
| ActivityEvent.source set automatically per §3.8 (agent/cockpit/engine) | direct activity-log assertions for agent/cockpit/engine emissions | `TestFromAC_ActivityEventSource` | PASS |
| Method exposure: NO create_task, start_work, end_work, pick_tasks on CockpitView | direct `hasattr` checks on required/forbidden surface | `TestFromAC_CockpitViewRoleSeparation` | PASS |

### Deductions
- -0.08: `TestFromAC_CockpitViewOCC` does not prove the mandated CAS helper route.
- -0.05: `TestFromAC_CockpitViewRepairStorage` phase-2 proof is too indirect.
- -0.05: `TestFromAC_CockpitViewListSessions` uses compatibility fixtures instead of live engine event shapes and misses `outcome=fail`.
- -0.04: Overall task-owned `TestFromAC_*` assertion specificity is too weak for mutation-resistant review.
- Confidence: 0.78

### Verdict
- FAIL -> backlog
- Reason: implementation appears present, but the existing task-owned `TestFromAC_*` proof is structurally too weak for review. This is a test-quality rejection, not a builder-code rejection.

### Action
- Architect/test-writer should replace lax proofs with direct assertions or spies for edit/move CAS routing, engine-mediated AR creation in `repair_storage`, and real `list_sessions` wire-shape coverage (`claim`, `blocked:`, `outcome=fail`), then re-run GREEN.
[[2026-04-27]]
## Architecture Review (backlog re-entry)
### Context
Task returned from review (confidence 0.78, FAIL) due to 3 structurally weak test proofs in the task-owned `TestFromAC_*` suite. Reviewer explicitly states: "test-quality rejection, not a builder-code rejection." Implementation is correct; tests need strengthening.

### AC Refinements
Three AC lines refined for testable specificity. The test-writer must add tests per these refinements on the next cycle:

1. **edit_task/move_task CAS routing** — original: "route through storage CAS; ERR_STALE on mismatch"
   **Refined:** edit_task/move_task persist via `storage.write_task_if_unchanged` on success path (spy proving the CAS helper is called, not just that ERR_STALE behavior is exhibited on stale). Reference: engine.py L1069 (edit), L1162 (move).

2. **repair_storage phase-2 engine mediation** — original: "phase-2 (AR creation via engine)"
   **Refined:** repair_storage phase-2 creates AR tasks using the engine's `create_task` method (spy/call-args check). Current test only verifies `type:user-action` tag exists in any file, which would pass with a raw file write.

3. **list_sessions canonical event shapes** — original: "derive SessionRecord from activity events; filter per D31"
   **Refined:** list_sessions tests must cover canonical engine-emitted event shapes: `action="claim"` (not just compatibility alias `start_work`), `detail="blocked: {reason}"` (not `block:`), and `detail="outcome=fail"`. Implementation handles both at L274 (`{"claim", "start_work"}`), but the primary codepath must be proved.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | CockpitView facade, one domain |
| Interface clarity | PASS (after refinement) | 3 AC lines tightened for proof specificity |
| Dependency correctness | PASS | #1078 (RED tests) done |
| Module layering | PASS | CockpitView wraps KanbanEngine, no upward imports |
| TDD compliance | PASS | RED tests from #1078 exist; test-writer adds spy assertions per refined AC |
| KISS/YAGNI | PASS | Minimal facade, no speculative features |
| Premise challenge | PASS | CockpitView required for cockpit frontend OCC semantics |
| Pattern consistency | PASS | Follows existing AgentView/CockpitView role separation |
| Security surface | PASS | OCC via CAS prevents concurrent mutation; no new boundaries |
| Single domain | PASS | scope:kanban only |

### Challenge Results
- Challenger: SKIPPED (REFINE verdict — optional per w-arch-review Step 2.5)

### Verdict: REFINE → APPROVE
### Action Taken: Tightened 3 LAX AC lines per reviewer evidence. Test-writer must add spy/assertion tests for CAS routing proof, engine-mediated AR creation, and canonical event shape coverage before this task can pass review.
[[2026-04-27]]
## Architecture Review
Verdict: REFINE → APPROVE. Tightened 3 reviewer-identified LAX AC lines for testable specificity: (1) CAS routing — spy on `storage.write_task_if_unchanged` on success path, (2) repair_storage phase-2 — spy on engine's `create_task`, (3) list_sessions — canonical event shapes (`claim`, `blocked:`, `outcome=fail`). Implementation is sound; test proofs need strengthening. Advancing to todo for test-writer cycle.
[[2026-04-27]]
## Test-Writer Notes
- Retry cycle: reviewer rejected on weak AC proof (confidence 0.78, test-quality rejection). Architect refined 3 LAX AC lines and sent back to test-writer.
- Test file: `tests/test_engine_cockpit_view_1078.py`
- 6 new mutation-resistant tests added to existing `TestFromAC_*` classes (71 total, up from 65).

### New tests added

**TestFromAC_CockpitViewOCC** (2 new):
- `test_edit_task_success_path_routes_through_write_task_if_unchanged` — patches `storage.write_task_if_unchanged` with `side_effect=ERR_STALE`; proves CAS helper is called on the edit_task success path. Mutation guard: if plain `write_task` were used instead, mock never fires → `assert_called_once()` fails.
- `test_move_task_success_path_routes_through_write_task_if_unchanged` — same CAS proof pattern for move_task.

**TestFromAC_CockpitViewRepairStorage** (1 new):
- `test_repair_storage_phase2_ar_creation_uses_engine_create_task_method` — `patch.object(KanbanEngine, "create_task", wraps=original)` proves phase-2 AR creation goes through the engine method (type(self).create_task unbound call), not a raw file write.

**TestFromAC_CockpitViewListSessions** (3 new):
- `test_list_sessions_canonical_claim_action_opens_session` — action="claim" (primary engine codepath, not "start_work" alias) → state='running'.
- `test_list_sessions_canonical_blocked_colon_detail_creates_blocked_session` — detail="blocked: {reason}" (canonical engine shape from line 1539) → state='blocked'.
- `test_list_sessions_canonical_outcome_fail_detail_creates_blocked_session` — detail="outcome=fail" (canonical engine shape from line 1538) → state='blocked', outcome='fail'.

### AC coverage (3 previously LAX lines now closed)
| AC Line | Class | Status |
|---------|-------|--------|
| edit_task/move_task route through storage CAS | TestFromAC_CockpitViewOCC (10 tests) | CLOSED |
| repair_storage phase-2 via engine.create_task | TestFromAC_CockpitViewRepairStorage (5 tests) | CLOSED |
| list_sessions canonical shapes (claim, blocked:, outcome=fail) | TestFromAC_CockpitViewListSessions (14 tests) | CLOSED |

### Verification
- pytest: 71 passed, 0 failed (old 65 + new 6)
- ruff: clean
- Note: all 6 new tests pass immediately because the implementation is pre-existing and correct. Tests are mutation-resistant proofs, not RED-phase failures. The architect explicitly directed test strengthening knowing the implementation is sound.
[[2026-04-27]]
## Builder Notes
- Implementation: no code changes required; existing CockpitView implementation already satisfies AC behavior.
- Files changed: none.
- Tests: 71/71 passed in `tests/test_engine_cockpit_view_1078.py` (task-owned `TestFromAC_*` suite).
- Coverage: `owlbear_kanban.engine` 44% in scoped run (context only; no module edits in this pass).
- Ruff: clean on `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_cockpit_view_1078.py`.
- Evidence summary: strengthened mutation-resistant tests from the latest test-writer cycle pass unchanged, confirming GREEN with a surgical no-op builder pass.
[[2026-04-27]]
## Review Evidence
### Test Results
- quality-runner scoped run: pytest 71 passed, 0 failed, 0 skipped on `tests/test_engine_cockpit_view_1078.py`.
- Parallel fan-out note: `code-reader` returned no response during a GitHub service disruption, so this review fell back to sequential manual reading of `tests/test_engine_cockpit_view_1078.py`, `serve/kanban/src/owlbear_kanban/engine.py`, and the binding Brief B sections in `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md`.

### Lint
- Ruff clean on `serve/kanban/src/owlbear_kanban/engine.py` and `tests/test_engine_cockpit_view_1078.py`.

### Coverage
- Scoped task suite: `owlbear_kanban.engine` 44%.
- Recorded as residual context only: this retry changed no source files, so the gate decision is driven by AC proof quality in the task-owned suite rather than module expansion.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All RED tests from B-15 (#1078) pass | `tests/test_engine_cockpit_view_1078.py` via quality-runner | Yes | COVERED |
| edit_task/move_task route through storage CAS; ERR_STALE on mismatch | `TestFromAC_CockpitViewOCC` including `test_edit_task_stale_expected_updated_raises_concurrency_error`, `test_move_task_stale_expected_updated_raises_concurrency_error`, `test_edit_task_success_path_routes_through_write_task_if_unchanged`, `test_move_task_success_path_routes_through_write_task_if_unchanged` | Yes | COVERED |
| release_task: idempotent on unclaimed (AC-NEW-21) | `TestFromAC_CockpitViewReleaseTask` | Yes | COVERED |
| sweep: returns released task IDs; idempotent; per-task CAS, skip on ERR_STALE | `TestFromAC_CockpitViewSweep` + `TestFromAC_CockpitViewSweepCAS` | Yes | COVERED |
| scan_corruption: read-only, returns list[CorruptionError] | `TestFromAC_CockpitViewScanCorruption` | Yes | COVERED |
| repair_storage: phase-1 (storage scan_and_fix) + phase-2 (AR creation via engine); never at startup | `TestFromAC_CockpitViewRepairStorage` including `test_repair_storage_phase2_ar_creation_uses_engine_create_task_method` | Yes | COVERED |
| compact_activity: delegates to storage.compact_activity_log | `TestFromAC_CockpitViewCompactActivity` | Yes | COVERED |
| list_activity: filter by task_id, action, source, time window | `TestFromAC_CockpitViewListActivity` | Yes | COVERED |
| list_sessions: derive SessionRecord from activity events; filter per D31 | `TestFromAC_CockpitViewListSessions` including canonical `claim`, `blocked:`, and `outcome=fail` cases | Yes | COVERED |
| ActivityEvent.source set automatically per §3.8 (agent/cockpit/engine) | `TestFromAC_ActivityEventSource` | Yes | COVERED |
| Method exposure: NO create_task, start_work, end_work, pick_tasks on CockpitView | `TestFromAC_CockpitViewRoleSeparation` | Yes | COVERED |

#### Security Review
- No issues found in the reviewed paths. No hardcoded secrets, injection sinks, unsafe deserialization, path traversal, or unbounded-input additions surfaced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_CockpitViewOCC` | Test-writer added 2 CAS-helper spy tests; builder reported no test edits | STRENGTHENED |
| `TestFromAC_CockpitViewRepairStorage` | Test-writer added 1 engine-`create_task` spy test; builder reported no test edits | STRENGTHENED |
| `TestFromAC_CockpitViewListSessions` | Test-writer added 3 canonical event-shape tests; builder reported no test edits | STRENGTHENED |
| Remaining `TestFromAC_*` coverage | No weakening or removal detected in the current snapshot | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | The previously weak CAS, engine-mediated AR creation, and canonical session-shape proofs now use direct spies or exact state/outcome assertions. Older type-only checks remain, but every AC row now has at least one mutation-resistant proof. |
| Negative/error-path coverage | ADEQUATE | The suite covers stale OCC tokens, missing IDs, unclaimed release no-op, fresh-vs-expired sweep, corrupt-vs-clean scan, startup non-repair, and blocked/rejected/fail session closures. |
| Manual mutation reasoning | ADEQUATE | Replacing CAS helper calls with plain writes, bypassing engine `create_task`, or removing canonical `claim` / `blocked:` / `outcome=fail` handling would now fail dedicated tests. |
| Test independence | STRONG | Each case builds an isolated temp board/activity log. |
| Descriptive names | STRONG | Test names map directly to the task contract and the architect-refined proof obligations. |

#### Data Safety
- No issues found. The live implementation uses CAS writes for OCC paths, keeps `scan_corruption()` read-only, and preserves two-phase repair separation.

#### Implementation-Aware Gaps
- No blocking gaps found in the reviewed scope.
- Residual note: the CockpitView task-owned suite exercises `move_task` OCC through the active-status path. The broader archive validation matrix remains covered by the existing engine move suite, while the CockpitView wrapper itself is status-agnostic and passes `status`, `archival_reason`, `archival_refs`, and `expected_updated` straight through.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `CockpitView.scan_corruption()` and `CockpitView.repair_storage()` still advertise plain `list` return annotations in the wrapper. The behavior-level contract is correctly covered and this is not a blocker.
- `owlbear_kanban.engine` remains at 44% under the task-owned suite. Because this retry changed no source files, that coverage figure is recorded as residual breadth risk rather than a gate failure.
- One stale RED-era comment remains in `TestFromAC_ActivityEventSource.test_agent_view_end_work_emits_source_agent`; the passing assertion matches live behavior, so this is documentation drift only.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All RED tests from B-15 (#1078) pass | quality-runner scoped execution: 71 passed, 0 failed | `tests/test_engine_cockpit_view_1078.py` | PASS |
| edit_task/move_task route through storage CAS; ERR_STALE on mismatch | CockpitView forwards `expected_updated` and cockpit source; engine OCC branches call `storage.write_task_if_unchanged`; new CAS spy tests close the prior proof gap | `TestFromAC_CockpitViewOCC` | PASS |
| release_task: idempotent on unclaimed (AC-NEW-21) | exact `updated` no-advance assertion on unclaimed release and exact `ERR_STALE` / `ERR_NOT_FOUND` error checks | `TestFromAC_CockpitViewReleaseTask` | PASS |
| sweep: returns released task IDs; idempotent; per-task CAS, skip on ERR_STALE | exact released-ID set checks plus stale-skip and continue-after-stale CAS tests | `TestFromAC_CockpitViewSweep` + `TestFromAC_CockpitViewSweepCAS` | PASS |
| scan_corruption: read-only, returns list[CorruptionError] | exact no-write / byte-preservation checks and typed corruption list coverage | `TestFromAC_CockpitViewScanCorruption` | PASS |
| repair_storage: phase-1 + phase-2 via engine; never at startup | direct `scan_and_fix` spy, engine `create_task` spy, and startup non-repair assertion | `TestFromAC_CockpitViewRepairStorage` | PASS |
| compact_activity: delegates to storage.compact_activity_log | direct storage delegate spy and typed return assertion | `TestFromAC_CockpitViewCompactActivity` | PASS |
| list_activity: filter by task_id, action, source, time window | exact task/action identity assertions for `since` / `until` windows and targeted source/action filters | `TestFromAC_CockpitViewListActivity` | PASS |
| list_sessions: derive SessionRecord from activity events; filter per D31 | exact state/outcome assertions for completed, rejected, released, expired, canonical `claim`, canonical `blocked:`, and canonical `outcome=fail` | `TestFromAC_CockpitViewListSessions` | PASS |
| ActivityEvent.source set automatically per §3.8 (agent/cockpit/engine) | direct event-log assertions for agent, cockpit, and engine sources | `TestFromAC_ActivityEventSource` | PASS |
| Method exposure: NO create_task, start_work, end_work, pick_tasks on CockpitView | exact `hasattr` presence/absence checks on required and forbidden surface | `TestFromAC_CockpitViewRoleSeparation` | PASS |

### Deductions
- -0.02: `code-reader` execution failed during fan-out; manual sequential fallback was required.
- -0.02: task-scoped engine coverage remains shallow (44%), though non-gating in this no-source-change retry.
- -0.01: cockpit-specific OCC proof for the archive-status `move_task` variant remains indirect via status-agnostic wrapper reading plus broader engine move coverage.
- Confidence: 0.95

### Verdict
- PASS -> docs
- Reason: the scoped suite is green, lint is clean, the three prior LAX proofs are now closed with mutation-resistant assertions, and no new critical review findings remain.

### Action
- Advance to docs.

### Post-task Reflection
- The `code-reader` outage did not block review because the strengthened proofs were small enough to verify directly against the live engine paths.
- Cross-checking the binding brief prevented a checklist-only review and clarified that the remaining archive-path concern was already covered elsewhere in the engine suite.
- Low module coverage on a tests-only retry is still worth recording, but it should be separated from true contract failures so the gate stays precise.
[[2026-04-27]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No behavior, API, CLI, config, or package-structure changes. Both builder passes explicitly state "no code changes". |
| 2 | Module docstrings | No | N/A | No Python source modules created or modified. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` doc referenced in task body. |
| 5 | Diagram maintenance (describes match) | No | N/A | doc-index has no `describes` entry matching `tests/test_engine_cockpit_view_1078.py`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `tests/test_engine_cockpit_view_1078.py` | OUT (test file) | N/A |
| `serve/kanban/src/owlbear_kanban/engine.py` | OUT (unchanged source, no docstring edits) | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- `.owlbear/scratch/qr-1081-pytest.txt`
- `.owlbear/scratch/qr-1081-ruff.txt`

No docs impact: task was a test-only strengthening cycle with no source code changes. All checklist items N/A.
[[2026-04-27]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-15 (#1078) pass | quality-runner full: 71/71 passed in task suite | PASS |
| edit_task/move_task route through storage CAS; ERR_STALE on mismatch | `test_edit_task_success_path_routes_through_write_task_if_unchanged` L298 — patches CAS helper, asserts called_once | PASS |
| release_task: idempotent on unclaimed (AC-NEW-21) | `TestFromAC_CockpitViewReleaseTask` — reviewer mapped, trusted | PASS |
| sweep: returns released task IDs; idempotent; per-task CAS, skip on ERR_STALE | `TestFromAC_CockpitViewSweep` + `TestFromAC_CockpitViewSweepCAS` — reviewer mapped | PASS |
| scan_corruption: read-only, returns list[CorruptionError] | `TestFromAC_CockpitViewScanCorruption` — reviewer mapped | PASS |
| repair_storage: phase-1 + phase-2 via engine; never at startup | `test_repair_storage_phase2_ar_creation_uses_engine_create_task_method` — spy on KanbanEngine.create_task | PASS |
| compact_activity: delegates to storage.compact_activity_log | `TestFromAC_CockpitViewCompactActivity` — reviewer mapped | PASS |
| list_activity: filter by task_id, action, source, time window | `TestFromAC_CockpitViewListActivity` — reviewer mapped | PASS |
| list_sessions: derive SessionRecord; filter per D31 | `test_list_sessions_canonical_claim_action_opens_session` L882 + 2 more canonical shape tests | PASS |
| ActivityEvent.source set automatically per §3.8 | `TestFromAC_ActivityEventSource` — reviewer mapped | PASS |
| Method exposure: NO create_task, start_work, end_work, pick_tasks | `TestFromAC_CockpitViewRoleSeparation` — reviewer mapped | PASS |

### Test Results
- pytest full suite: 2625 passed, 121 failed, 4 skipped. 0 failures in task scope.
- 121 failures in pre-existing modules: test_corruption.py, test_engine_coverage_1068.py, test_storage_1050.py — not related to #1081.
- ruff: 8 violations in unrelated packages (knowledge, mcp-knowledge, mcp-memory, orchestrator). 0 in task scope.

### Architect Quality: 4/5
Original AC had 3 slightly underspecified lines (CAS routing, repair phase-2, list_sessions shapes). Architect caught and refined them effectively on the backlog re-entry cycle. Good recovery.

### Deduction Breakdown
- Uncommitted test deliverables (test-writer/builder gap): -.02
- All other criteria clean: no deductions

### Confidence: 0.98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| aa52d272 | test | tests/test_engine_cockpit_view_1078.py | #1081 |