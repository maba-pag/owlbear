---
id: 1075
title: 'B-10: GREEN — move_task + start_work'
status: archived
priority: medium
created: 2026-04-21T10:49:32.320431+00:00
updated: 2026-04-25T15:48:52.989567+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1073
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.6, §1.7, §3.1, §3.2
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement AgentView.move_task and AgentView.start_work. Fork point: B-11 (end_work) and B-15 (CockpitView) both depend on this task.

move_task: status transitions, archival validation (D37 matrix), write-time predicate on destination (D15+D41 atomicity), skip-transition guidance (D54), archive clears claim atomically (D17).

start_work: claim semantics (no identity per D11), lazy-release on expired claims (D18+D36 via CAS), blocked/archived not claimable.

## Acceptance Criteria

- [ ] All RED tests from B-09 (#1073) pass
- [ ] move_task validates archival_reason/archival_refs per D37 full matrix — `_validate_move_archival` must enforce `ERR_ARCHIVAL_REF_SELF` (task_id ∉ archival_refs) and `ERR_ARCHIVAL_REF_CYCLE` (via existing `_has_archival_cycle` helper), matching edit_task path at engine.py:2443-2456; task-owned tests must assert both codes on the move_task path
- [ ] Write-time predicate fires on destination; failure → atomic rollback (D41)
- [ ] Archive operation clears claim atomically (D17)
- [ ] start_work sets `claimed_at = now()`, no `claimed_by` (D11)
- [ ] Expired-claim lazy-release via `storage.write_task_if_unchanged` CAS (D18+D36)
- [ ] `updated` advanced on success (D14) — includes stale-retry-success: a claim_task call that succeeds after ERR_STALE retry must produce `claimed_at` and `updated` fresher than the re-read snapshot; task-owned test must assert this (code fix at engine.py:1136 already in place, test proof missing)
- [ ] AgentView.move_task has NO `expected_updated` param (D46)
[[2026-04-25]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_move_claim_1075.py
- Classes: TestFromAC_StartWork_1075
- Tests per category: happy 0, edge 1, error 2, boundary 1
- Total: 4 tests, all FAIL
- ruff: clean

### AC coverage

| AC item | Test | Status |
|---|---|---|
| All #1073 RED tests pass | (pre-existing — all 20 pass ✓) | NOT TESTABLE AS RED |
| move_task validates archival_reason/archival_refs per D37 | (in test_engine_move_claim.py — all pass ✓) | NOT TESTABLE AS RED |
| Write-time predicate fires + rollback (D41) | (in test_engine_move_claim.py — passes ✓) | NOT TESTABLE AS RED |
| Archive clears claim atomically (D17) | (in test_engine_move_claim.py — passes ✓) | NOT TESTABLE AS RED |
| start_work sets claimed_at = now(), no claimed_by (D11) | engine.claim_task + SingleTaskResponse already satisfy this | NOT TESTABLE AS RED |
| Expired-claim lazy-release via write_task_if_unchanged CAS (D18+D36) | test_already_claimed_error_includes_claimed_at, test_expired_claim_release_uses_cas_primitive, test_expired_claim_cas_stale_retry_raises_already_claimed | FAILING ✓ |
| Fresh claim uses CAS primitive (D18+D36) | test_fresh_claim_uses_cas_primitive | FAILING ✓ |
| updated advanced on success (D14) | engine already advances updated on both paths | NOT TESTABLE AS RED |
| AgentView.move_task has NO expected_updated param (D46) | current signature already has no expected_updated | NOT TESTABLE AS RED |

### Failure summary
- test_already_claimed_error_includes_claimed_at: AssertionError — claimed_at timestamp not in user_message (generic "already claimed" message)
- test_expired_claim_release_uses_cas_primitive: AssertionError — mock_cas.called is False (plain write_task used, not CAS)
- test_fresh_claim_uses_cas_primitive: AssertionError — mock_cas.called is False (plain write_task used)
- test_expired_claim_cas_stale_retry_raises_already_claimed: DID NOT RAISE ConcurrencyError (no retry logic exists)

[[2026-04-25]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py
- Scope: `KanbanEngine.claim_task` now performs CAS writes via `storage.write_task_if_unchanged` with `ERR_STALE` re-read/retry loop; `AgentView.start_work` now includes `claimed_at` detail in `ERR_ALREADY_CLAIMED` user message when available.
- Behavioral fixes applied:
  - Fresh claim path now uses CAS primitive (D18+D36).
  - Expired-claim path now uses the same CAS primitive and re-evaluates on stale writes (D18+D36).
  - Simulated stale-on-release/claim race now resolves to `ERR_ALREADY_CLAIMED` after retry when a live claim is observed.
  - Already-claimed error now includes timestamp hint for retry-delay computation.

- Tests:
  - Task-scoped: serve/kanban/tests/test_engine_move_claim_1075.py -> 4 passed, 0 failed.
  - Durable module regression: serve/kanban/tests/test_engine_move_claim.py -> 20 passed, 0 failed.
- Lint:
  - Ruff clean for `serve/kanban/src/owlbear_kanban/engine.py`
  - Ruff clean for both scoped test files used in verification.
- Coverage evidence:
  - Scoped task run reported engine module coverage in targeted execution context; full-module percentage remains below 90% due to intentionally narrow test scope.

- Reflection:
  - Problems faced: test-side patched CAS helper expected positional args; keyword invocation caused TypeError.
  - Workaround applied: switched CAS helper invocation to positional parameters and re-ran scoped verification.
  - Pattern discovered: keeping `claimed_at` in the ValueError path provides stable data for API-layer error translation without broad exception reshaping.
  - Time sink: first verification run surfaced both semantic and lint issues; resolved in one follow-up patch.
  - Quality gap: module-level coverage remains broad-gap outside this task slice; durable regression suite still passed for claim/move behavior.
[[2026-04-25]]
## Review Evidence
### Test Results
- Scoped quality-runner: 24 passed, 0 failed, 0 skipped across serve/kanban/tests/test_engine_move_claim_1075.py and serve/kanban/tests/test_engine_move_claim.py.
- Broader kanban context: 1013 passed, 131 failed, 93 errors across serve/kanban/tests/. The failures are unrelated background fixture and signature debt: agent_map config fixtures, legacy KanbanEngine constructor kwargs, and one corruption._make_yaml reference.

### Lint
- Scoped lint clean for serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/tests/test_engine_move_claim.py, and serve/kanban/tests/test_engine_move_claim_1075.py.

### Coverage
- Scoped move and claim run: owlbear_kanban.engine 34%.
- Broader kanban-suite context: owlbear_kanban.engine 96%.
- Coverage is not the gate failure here; the failing issue is false-green AC coverage on expired-claim lazy-release.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| All RED tests from B-09 pass | serve/kanban/tests/test_engine_move_claim.py; 20 passed in the scoped quality run | Yes | COVERED |
| move_task validates archival_reason and archival_refs per D37 full matrix | serve/kanban/tests/test_engine_move_claim.py lines 196, 210, 226, 242, 258, 274 | Yes | COVERED |
| Write-time predicate fires on destination; failure is atomic rollback (D41) | serve/kanban/tests/test_engine_move_claim.py lines 307 and 323 | Yes | COVERED |
| Archive operation clears claim atomically (D17) | serve/kanban/tests/test_engine_move_claim.py lines 341 and 358 | Yes | COVERED |
| start_work sets claimed_at = now(), no claimed_by (D11) | serve/kanban/tests/test_engine_coverage_1068.py lines 1135 and 2221; serve/kanban/tests/test_engine_models.py line 225 | Yes | COVERED |
| Expired-claim lazy-release via storage.write_task_if_unchanged CAS (D18+D36) | serve/kanban/tests/test_engine_move_claim_1075.py line 196 | No. The test docstring says lazy-release first at lines 202-203, but the assertion at line 215 only checks that some CAS call happened. | LAX |
| updated advanced on success (D14) | serve/kanban/src/owlbear_kanban/engine.py lines 1087, 1100, 1155 | Yes | COVERED |
| AgentView.move_task has NO expected_updated param (D46) | serve/kanban/src/owlbear_kanban/engine.py line 2526 signature | Yes | COVERED |

#### Security Review
- No issues found in the touched paths. No new dependencies, no secret handling, no shell or SQL execution, and no user-controlled filesystem paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_StartWork_1075.test_already_claimed_error_includes_claimed_at | Current file still asserts claimed_at text in ERR_ALREADY_CLAIMED message | PRESERVED |
| TestFromAC_StartWork_1075.test_expired_claim_release_uses_cas_primitive | Current file still asserts CAS usage only; no weakening detected in the present snapshot, but the assertion is too weak for the AC | PRESERVED |
| TestFromAC_StartWork_1075.test_fresh_claim_uses_cas_primitive | Current file still asserts CAS usage on fresh claim | PRESERVED |
| TestFromAC_StartWork_1075.test_expired_claim_cas_stale_retry_raises_already_claimed | Current file still injects ERR_STALE and expects ERR_ALREADY_CLAIMED on retry | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | WEAK | serve/kanban/tests/test_engine_move_claim_1075.py line 215 uses only assert mock_cas.called, so direct CAS overwrite satisfies the test without proving lazy-release-first behavior |
| Negative and error-path coverage | ADEQUATE | Already-claimed and stale-retry failure paths are covered |
| Manual mutation reasoning | WEAK | The current engine implementation overwrites claimed_at directly at serve/kanban/src/owlbear_kanban/engine.py lines 1153-1159 and still passes the lazy-release test; this is a live false-green |
| Test independence | STRONG | tmp_path boards and local patches isolate cases |
| Descriptive names | STRONG | Names describe each contract precisely |

#### Data Safety
- No separate data-safety issue beyond the false-green contract gap. The new CAS retry logic reduces the claim race window.

#### Implementation-Aware Gaps
- The brief requires expired claims to be lazy-released first, then re-claimed through the same CAS primitive (.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md line 133).
- The implementation at serve/kanban/src/owlbear_kanban/engine.py lines 1142-1159 skips the clear step and writes the new claim directly.
- Because serve/kanban/tests/test_engine_move_claim_1075.py line 215 only checks mock_cas.called, the task-owned suite does not prove the required release-first behavior.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Broader serve/kanban/tests/ execution currently has unrelated background failures and errors, but the engine module itself measured 96% coverage in that broader context.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All RED tests from B-09 pass | Scoped quality-runner reported 24 passed and 0 failed; this includes the 20 durable move and claim tests in serve/kanban/tests/test_engine_move_claim.py | test_engine_move_claim.py | PASS |
| move_task validates archival_reason and archival_refs per D37 full matrix | serve/kanban/tests/test_engine_move_claim.py lines 196, 210, 226, 242, 258, 274 all passed in the scoped run | Durable move-task archive matrix | PASS |
| Write-time predicate fires on destination; failure is atomic rollback (D41) | serve/kanban/tests/test_engine_move_claim.py lines 307 and 323 passed in the scoped run | D15 and D41 predicate tests | PASS |
| Archive operation clears claim atomically (D17) | serve/kanban/tests/test_engine_move_claim.py lines 341 and 358 passed in the scoped run | D17 archive claim-clear tests | PASS |
| start_work sets claimed_at = now(), no claimed_by (D11) | serve/kanban/tests/test_engine_coverage_1068.py lines 1135 and 2221 assert claimed_at; serve/kanban/tests/test_engine_models.py line 225 and serve/kanban/src/owlbear_kanban/models.py lines 441 and 263 prove the SingleTaskResponse path has no claimed_by field | Pre-existing durable claim and model tests | PASS |
| Expired-claim lazy-release via storage.write_task_if_unchanged CAS (D18+D36) | .owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md line 133 requires lazy-release first through cleared_task CAS; serve/kanban/src/owlbear_kanban/engine.py lines 1142-1159 overwrite claimed_at directly; serve/kanban/tests/test_engine_move_claim_1075.py lines 202-215 only prove that some CAS call happened | test_expired_claim_release_uses_cas_primitive | FAIL |
| updated advanced on success (D14) | serve/kanban/src/owlbear_kanban/engine.py lines 1087, 1100, 1155 set updated on successful move and claim paths | Direct code proof | PASS |
| AgentView.move_task has NO expected_updated param (D46) | serve/kanban/src/owlbear_kanban/engine.py line 2526 signature has task_id, status, archival_reason, archival_refs only | Direct signature proof | PASS |

### Confidence: 0.82
### Verdict: FAIL

### Action
- Route to todo. The task-owned TestFromAC coverage is too weak on the expired-claim lazy-release contract, and the current implementation does not satisfy the release-first behavior described in the brief.
[[2026-04-25]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_move_claim_1075.py
- Classes: TestFromAC_StartWork_1075
- Tests per category: happy 0, edge 1, error 2, boundary 1, **retry-addition: 1**
- Total: 5 tests; 4 pre-existing PASS, 1 new FAIL
- ruff: clean

### Retry action
Reviewer cited `test_expired_claim_release_uses_cas_primitive` as lax — only asserting `mock_cas.called` without proving release-first (two-step) behavior.

**New test added:** `test_expired_claim_release_before_claim_two_cas_writes`

### Failure evidence
```
AssertionError: Expected ≥2 CAS writes (release then claim) for expired-claim path;
got 1 write(s) with claimed_at values: ['2026-04-25T13:33:01.761119+00:00'].
Brief §1.7 requires a release step (claimed_at=None) before the claim write.
assert 1 >= 2
```

### AC coverage update

| AC item | Test | Status |
|---|---|---|
| Expired-claim lazy-release via write_task_if_unchanged CAS (D18+D36) | test_expired_claim_release_uses_cas_primitive (CAS called ✓) + **test_expired_claim_release_before_claim_two_cas_writes (release-first — FAILING ✓)** | NOW STRONG |

### What the new test proves
The engine must issue **two** CAS writes for the expired-claim path: first with `claimed_at=None` (the lazy-release step per D18+D36), then with `claimed_at=<now>` (the new claim). Current implementation collapses both into one CAS write (direct overwrite), so `len(cas_calls) = 1 < 2` → FAIL.
[[2026-04-25]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py in KanbanEngine.claim_task to enforce expired-claim lazy-release as a two-step CAS flow (release CAS with claimed_at=None, then claim CAS), while preserving ERR_STALE re-read/retry behavior.
- Contract fix: expired-claim path now performs two CAS writes in order, satisfying Brief B §1.7 and the new TestFromAC requirement for release-before-claim sequencing.
- Files changed: serve/kanban/src/owlbear_kanban/engine.py

- Test results (quality-runner):
  - RED verification: serve/kanban/tests/test_engine_move_claim_1075.py -> 4 passed, 1 failed (expected pre-fix; failing test was release-before-claim two-CAS assertion).
  - GREEN scoped verification: serve/kanban/tests/test_engine_move_claim_1075.py + serve/kanban/tests/test_engine_move_claim.py + serve/kanban/tests/test_engine_activity.py -> 52 passed, 0 failed.
  - Expanded engine-focused context: 760 passed, 5 failed (unrelated legacy fixture/config debt in test_engine_storage.py and test_engine_crash_safety_1101.py).
- Lint: ruff clean for serve/kanban/src/owlbear_kanban/engine.py and scoped task suites.
- Coverage:
  - Scoped GREEN run (task-focused): owlbear_kanban.engine 49%.
  - Expanded engine-focused context: owlbear_kanban.engine 95%.

- Evidence summary:
  - Task-owned failing test test_expired_claim_release_before_claim_two_cas_writes now passes by observing two CAS writes with claimed_at sequence [None, <timestamp>].
  - Existing claim/race protections remain intact: fresh claim CAS, expired-claim CAS retry on ERR_STALE, and already-claimed error semantics.

- Reflection:
  - Problem faced: prior implementation used a single CAS overwrite on expired claims, which produced a false-green against weaker CAS-called-only assertions.
  - Workaround applied: split expired-claim handling into explicit release CAS then claim CAS, both inside existing retry loop.
  - Pattern discovered: keeping expected_updated separate for each CAS stage makes sequence contracts explicit and testable.
  - Time sink: coverage gate balancing required both scoped and broader evidence runs to distinguish task correctness from background suite debt.
  - Quality gap: unrelated engine-suite fixture debt still exists outside this task scope (agent_map legacy config assumptions).
[[2026-04-25]]
## Review Evidence
### Test Results
- Scoped quality-runner: 52 passed, 0 failed, 0 skipped across `serve/kanban/tests/test_engine_move_claim_1075.py`, `serve/kanban/tests/test_engine_move_claim.py`, and `serve/kanban/tests/test_engine_activity.py`.
- Full quality-runner context: 2102 passed, 169 failed, 4 skipped, 209 errors. Those failures and the unrelated lint findings are background debt outside this task's scope.

### Lint
- Scoped lint clean for `serve/kanban/src/owlbear_kanban/engine.py` and the three scoped suites.
- Full quality-runner context reported unrelated lint debt in other packages; not task-owned.

### Coverage
- Scoped task run: `owlbear_kanban.engine` 49%.
- Full quality-runner context: `owlbear_kanban.engine` 96%.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| All RED tests from B-09 pass | `serve/kanban/tests/test_engine_move_claim.py` in the scoped quality run | Yes | COVERED |
| `move_task` validates `archival_reason` and `archival_refs` per D37 full matrix | `serve/kanban/tests/test_engine_move_claim.py`:196, :210, :226, :242, :258, :274 | Yes | COVERED |
| Write-time predicate fires on destination; failure remains atomic per D41 | `serve/kanban/tests/test_engine_move_claim.py`:307 and :323 | Yes | COVERED |
| Archive operation clears claim atomically per D17 | `serve/kanban/tests/test_engine_move_claim.py`:341 and :358 | Yes | COVERED |
| `start_work` sets `claimed_at = now()`, no `claimed_by` per D11 | `serve/kanban/tests/test_engine_coverage_1068.py`:2222-2227, `serve/kanban/tests/test_engine_models.py`:201-226, `serve/kanban/src/owlbear_kanban/models.py`:263 and :315, `serve/kanban/src/owlbear_kanban/storage.py`:386, `serve/kanban/src/owlbear_kanban/engine.py`:1638-1641 | Yes | COVERED |
| Expired-claim lazy-release via `storage.write_task_if_unchanged` CAS per D18 and D36 | `serve/kanban/tests/test_engine_move_claim_1075.py`:196, :244, :297 | Yes | COVERED |
| `updated` advanced on success per D14 | `serve/kanban/tests/test_engine_coverage_1068.py`:2222-2227 covers only non-retry success; `serve/kanban/tests/test_engine_move_claim_1075.py`:244-295 covers stale retry only when it ends in `ERR_ALREADY_CLAIMED` | No. A successful retry after `ERR_STALE` can still regress `updated` without failing the current suite. | LAX |
| `AgentView.move_task` has no `expected_updated` param per D46 | `serve/kanban/src/owlbear_kanban/engine.py`:2546-2553 | Yes | COVERED |

#### Security Review
- No issues found in the touched paths. No new dependencies, no secret handling, no shell or SQL execution, and no user-controlled filesystem paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_StartWork_1075.test_already_claimed_error_includes_claimed_at` | Assertion preserved | PRESERVED |
| `TestFromAC_StartWork_1075.test_expired_claim_release_uses_cas_primitive` | Assertion preserved | PRESERVED |
| `TestFromAC_StartWork_1075.test_fresh_claim_uses_cas_primitive` | Assertion preserved | PRESERVED |
| `TestFromAC_StartWork_1075.test_expired_claim_cas_stale_retry_raises_already_claimed` | Assertion preserved | PRESERVED |
| `TestFromAC_StartWork_1075.test_expired_claim_release_before_claim_two_cas_writes` | New retry-round strengthening test added at `serve/kanban/tests/test_engine_move_claim_1075.py`:297 | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | The new two-CAS test asserts both ordering and values of the expired-claim writes. |
| Negative and error-path coverage | ADEQUATE | Blocked, archived, already-claimed, and stale-to-live-claim paths are covered in `serve/kanban/tests/test_engine_move_claim.py`:475, :495 and `serve/kanban/tests/test_engine_move_claim_1075.py`:173, :244. |
| Manual mutation reasoning | WEAK | The retry-success branch can reuse a stale timestamp and regress `updated` without failing any current test. |
| Test independence | STRONG | The task-owned suite uses isolated temp boards and local patches only. |
| Descriptive names | STRONG | Test names map directly to the D18, D36, D14, and D11 contracts. |

#### Data Safety
- No separate data-safety issue found.

#### Implementation-Aware Gaps
- `effective_now` is captured once before the retry loop at `serve/kanban/src/owlbear_kanban/engine.py`:1131.
- On both CAS stale branches the function increments `stale_retries` and loops without refreshing that timestamp at `serve/kanban/src/owlbear_kanban/engine.py`:1166-1168 and :1184-1186.
- Both the release CAS and final claim CAS then write `updated = effective_now.isoformat()` at `serve/kanban/src/owlbear_kanban/engine.py`:1158 and :1175.
- After a stale reread of a newer task, a later successful retry can therefore persist an older `updated` value and stale `claimed_at`, violating D14.
- The task-owned retry test only covers stale-retry to `ERR_ALREADY_CLAIMED` at `serve/kanban/tests/test_engine_move_claim_1075.py`:244-295. I found no proof for the stale-retry-to-success branch.

#### Builder Process Quality
| Metric | Value |
|---|---|
| `## Builder Notes` sections in task file | 2 |
| `## Review Evidence` sections before this review | 1 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Full quality-runner context still has unrelated repo failures and lint debt outside this task. They are not the reason for rejection.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All RED tests from B-09 pass | Scoped quality-runner passed the durable move and claim suite cleanly | `serve/kanban/tests/test_engine_move_claim.py` | PASS |
| `move_task` validates `archival_reason` and `archival_refs` per D37 full matrix | Archive-matrix tests at `serve/kanban/tests/test_engine_move_claim.py`:196, :210, :226, :242, :258, :274 passed in scoped review | Durable D37 suite | PASS |
| Write-time predicate fires on destination; failure remains atomic per D41 | Predicate and rollback tests at `serve/kanban/tests/test_engine_move_claim.py`:307 and :323 passed in scoped review | Durable predicate suite | PASS |
| Archive operation clears claim atomically per D17 | Archive claim-clear tests at `serve/kanban/tests/test_engine_move_claim.py`:341 and :358 passed in scoped review | Durable D17 suite | PASS |
| `start_work` sets `claimed_at = now()`, no `claimed_by` per D11 | Happy-path start-work test at `serve/kanban/tests/test_engine_coverage_1068.py`:2222-2227 plus projection and persistence stripping at `serve/kanban/tests/test_engine_models.py`:201-226, `serve/kanban/src/owlbear_kanban/models.py`:263 and :315, `serve/kanban/src/owlbear_kanban/storage.py`:386, and `serve/kanban/src/owlbear_kanban/engine.py`:1638-1641 | Durable model and interface tests | PASS |
| Expired-claim lazy-release via `storage.write_task_if_unchanged` CAS per D18 and D36 | Current task-owned suite proves CAS usage, retry-to-live-claim handling, and two-step release then claim at `serve/kanban/tests/test_engine_move_claim_1075.py`:196, :244, :297 | Task-owned retry suite | PASS |
| `updated` advanced on success per D14 | `serve/kanban/src/owlbear_kanban/engine.py`:1131, :1158, :1166-1168, :1175, :1184-1186 show stale timestamp reuse across retries; no stale-retry-success test proves monotonic `updated` advancement | No mapped proof for retry-success branch | FAIL |
| `AgentView.move_task` has no `expected_updated` param per D46 | Signature at `serve/kanban/src/owlbear_kanban/engine.py`:2546-2553 contains only `task_id`, `status`, `archival_reason`, and `archival_refs` | Direct signature proof | PASS |

### Confidence: 0.84
### Verdict: FAIL

### Action
- Route to `in-progress`.
- Builder should refresh the runtime timestamp on each stale-retry loop in the real runtime path, preserve deterministic `now` injection when explicitly supplied, and add a stale-retry-success proof that asserts `updated` and `claimed_at` advance from the reread snapshot.

### Reflection
- Problem faced: the strengthened release-first test passed, but the retry branch still had a timestamp freshness hole not exercised by the scoped suite.
- Workaround applied: compared the live retry loop against the D14 contract instead of relying on green tests alone.
- Pattern discovered: CAS retry fixes often need a second audit for timestamp reuse, not just lock or ordering correctness.
- Quality gap: the task-owned suite still lacks a stale-retry-success assertion for `updated` monotonicity.
[[2026-04-25]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py in KanbanEngine.claim_task to refresh the effective timestamp per retry iteration when `now` is not injected.
- Fix applied: moved `effective_now = now if now is not None else datetime.now(tz=UTC)` inside the retry loop so successful retries after `ERR_STALE` cannot persist stale `claimed_at`/`updated` values (D14), while preserving deterministic behavior when `now` is explicitly provided.
- Files changed: serve/kanban/src/owlbear_kanban/engine.py

- Tests (scoped quality-runner):
  - serve/kanban/tests/test_engine_move_claim_1075.py
  - serve/kanban/tests/test_engine_move_claim.py
  - serve/kanban/tests/test_engine_activity.py
  - Result: 52 passed, 0 failed, 0 skipped.
- Lint (scoped):
  - ruff check clean for serve/kanban/src/owlbear_kanban/engine.py
  - ruff check clean for scoped test files.
- Coverage:
  - owlbear_kanban.engine: 49% in scoped run (task-targeted context).

- Evidence summary:
  - Claim retry loop now recomputes runtime timestamp on each attempt when `now` is absent.
  - `now` injection remains stable for deterministic tests and callers that pass explicit timestamps.

- Reflection:
  - Problem faced: retry loop previously captured runtime time once, allowing stale timestamp reuse after CAS stale retries.
  - Workaround applied: localized timestamp refresh inside loop with branch preserving injected `now`.
  - Pattern discovered: CAS retry loops must refresh mutable runtime state per attempt unless explicitly fixed by caller input.
  - Time sink: none significant; fix was a small surgical edit plus scoped verification.
  - Quality gap: scoped coverage is below gate in isolation; broader module context historically provides higher coverage.
[[2026-04-25]]
## Review Evidence
### Test Results
- quality-runner scoped: 52 passed, 0 failed, 0 skipped across `serve/kanban/tests/test_engine_move_claim_1075.py`, `serve/kanban/tests/test_engine_move_claim.py`, and `serve/kanban/tests/test_engine_activity.py`.
- quality-runner broader engine context: 459 passed, 0 failed, 0 errors, 0 skipped across `serve/kanban/tests/test_engine_move_claim.py`, `serve/kanban/tests/test_engine_move_claim_1075.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_atomicity_1104.py`, `serve/kanban/tests/test_engine_create_edit_1070.py`, `serve/kanban/tests/test_engine_coverage_1068.py`, and `serve/kanban/tests/test_engine_models.py`.

### Lint
- Scoped ruff clean for `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_engine_move_claim_1075.py`, `serve/kanban/tests/test_engine_move_claim.py`, and `serve/kanban/tests/test_engine_activity.py`.

### Coverage
- Scoped task run: `owlbear_kanban.engine` 49%.
- Broader engine-focused context: `owlbear_kanban.engine` 89%.
- Reviewer gate remains unmet on the broader independent run (`< 90%`).

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| All RED tests from B-09 pass | quality-runner executed `serve/kanban/tests/test_engine_move_claim.py` cleanly (26 passed) | Yes | COVERED |
| `move_task` validates `archival_reason` / `archival_refs` per D37 full matrix | `serve/kanban/tests/test_engine_move_claim.py:242` and `:274` cover forbidden refs and missing refs only | No. Brief D37 also requires `ERR_ARCHIVAL_REF_SELF` and `ERR_ARCHIVAL_REF_CYCLE` at `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md:99`, `:248`, and `:249`, but `serve/kanban/src/owlbear_kanban/engine.py:1753` never checks those branches. | MISSING |
| Write-time predicate fires on destination; failure -> atomic rollback (D41) | `serve/kanban/tests/test_engine_move_claim.py:307` and `:323` | Yes | COVERED |
| Archive operation clears claim atomically (D17) | `serve/kanban/tests/test_engine_move_claim.py:341`, `:358`, and `:383` | Yes | COVERED |
| `start_work` sets `claimed_at = now()`, no `claimed_by` (D11) | `serve/kanban/tests/test_engine_coverage_1068.py:2221` and `:2227`; `serve/kanban/tests/test_engine_models.py:203` and `:225`; `serve/kanban/src/owlbear_kanban/models.py:263` and `:315`; `serve/kanban/src/owlbear_kanban/storage.py:386` | Yes | COVERED |
| Expired-claim lazy-release via `storage.write_task_if_unchanged` CAS (D18+D36) | `serve/kanban/tests/test_engine_move_claim_1075.py:196`, `:244`, and `:297`; `serve/kanban/src/owlbear_kanban/engine.py:1162` and `:1180` | Yes | COVERED |
| `updated` advanced on success (D14) | `serve/kanban/src/owlbear_kanban/engine.py:1136` refreshes retry timestamps, but the in-scope tests only prove plain expired reclaim at `serve/kanban/tests/test_engine_move_claim.py:546` and retry-to-already-claimed at `serve/kanban/tests/test_engine_move_claim_1075.py:244` / `:297` | No. Reverting the retry-timestamp refresh would still leave the current success and retry-error tests green. | LAX |
| `AgentView.move_task` has NO `expected_updated` param (D46) | `serve/kanban/src/owlbear_kanban/engine.py:2548` | Yes | COVERED |

#### Security Review
- No issues found. The touched code is local validation, CAS file writes, and error translation only. I found no shell/SQL/template execution, secret handling, path traversal, or new dependency exposure.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_StartWork_1075.test_already_claimed_error_includes_claimed_at` | No builder-side modification detected in the latest cycle | PRESERVED |
| `TestFromAC_StartWork_1075.test_expired_claim_release_uses_cas_primitive` | No builder-side modification detected in the latest cycle | PRESERVED |
| `TestFromAC_StartWork_1075.test_fresh_claim_uses_cas_primitive` | No builder-side modification detected in the latest cycle | PRESERVED |
| `TestFromAC_StartWork_1075.test_expired_claim_cas_stale_retry_raises_already_claimed` | No builder-side modification detected in the latest cycle | PRESERVED |
| `TestFromAC_StartWork_1075.test_expired_claim_release_before_claim_two_cas_writes` | No builder-side modification detected in the latest cycle | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | The claim-path tests use exact codes and CAS-sequence checks rather than truthiness assertions. |
| Negative / error-path coverage | WEAK | `move_task` still has no self-ref or cycle coverage even though D37 requires those branches at `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md:99`, `:248`, and `:249`. |
| Manual mutation reasoning | WEAK | The D14 retry freshness fix at `serve/kanban/src/owlbear_kanban/engine.py:1136` is not mutation-resistant; no stale-retry-success test would fail if that line moved back outside the loop. |
| Test independence | STRONG | The reviewed suites use isolated `tmp_path` boards and local patches only. |
| Descriptive names | STRONG | Test names map directly to the D17, D18, D36, D41, D14, and D37 contracts. |

#### Data Safety
- `move_task` can currently accept archival-ref shapes that the brief forbids. `serve/kanban/src/owlbear_kanban/engine.py:1753` validates missing/required/forbidden refs, but it never rejects self-ref or transitive cycles. The archived `edit_task` path does reject both at `serve/kanban/src/owlbear_kanban/engine.py:2443` and `:2454`, so the write paths are inconsistent.

#### Implementation-Aware Gaps
- `serve/kanban/src/owlbear_kanban/engine.py:1753` (`_validate_move_archival`) lacks `task_id` and never calls `_has_archival_cycle`, even though the helper exists at `serve/kanban/src/owlbear_kanban/engine.py:1735`.
- The stronger archived `edit_task` path already enforces `ERR_ARCHIVAL_REF_SELF` and `ERR_ARCHIVAL_REF_CYCLE` at `serve/kanban/src/owlbear_kanban/engine.py:2443` and `:2454`, which confirms the D37 rule exists in live code but is missing from `move_task`.
- The current `move_task` suite only covers `ERR_ARCHIVAL_REFS_FORBIDDEN` and `ERR_ARCHIVAL_REF_MISSING` at `serve/kanban/tests/test_engine_move_claim.py:242` and `:274`; there is no `move_task` proof for self-ref or cycle rejection.
- The latest D14 runtime fix is directionally correct at `serve/kanban/src/owlbear_kanban/engine.py:1136`, but the task-owned suite still lacks a stale-retry-success assertion for fresh `updated` / `claimed_at` values.

#### Builder Process Quality
| Metric | Value |
|---|---|
| `## Builder Notes` sections in task file | 3 |
| `## Review Evidence` sections before this review | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `AgentView.start_work` D11 looks structurally satisfied through the response/model/storage layers, but the task-owned suite still treats it as an inherited assumption rather than asserting it directly.
- `AgentView.start_work` still reconstructs the `claimed_at` hint by regex-parsing a human-readable error string at `serve/kanban/src/owlbear_kanban/engine.py:2607`. The current message-format test protects it, but the contract remains string-shape-coupled.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All RED tests from B-09 pass | quality-runner scoped run passed `serve/kanban/tests/test_engine_move_claim.py` cleanly (26 passed, 0 failed) | Durable B-09 move/claim suite | PASS |
| `move_task` validates `archival_reason` / `archival_refs` per D37 full matrix | Brief D37 requires `ERR_ARCHIVAL_REF_SELF` and `ERR_ARCHIVAL_REF_CYCLE` at `.owlbear/briefs/draft-kanban-engine-b-2026-04-20/paper-integration.md:99`, `:248`, `:249`; `serve/kanban/src/owlbear_kanban/engine.py:1753` omits both checks; only partial ref cases are covered at `serve/kanban/tests/test_engine_move_claim.py:242` and `:274` | Partial D37 move-task suite only | FAIL |
| Write-time predicate fires on destination; failure -> atomic rollback (D41) | quality-runner passed `serve/kanban/tests/test_engine_move_claim.py:307` and `:323` | Predicate / rollback tests | PASS |
| Archive operation clears claim atomically (D17) | quality-runner passed `serve/kanban/tests/test_engine_move_claim.py:341`, `:358`, and `:383` | Archive claim-clear tests | PASS |
| `start_work` sets `claimed_at = now()`, no `claimed_by` (D11) | `serve/kanban/tests/test_engine_coverage_1068.py:2221` / `:2227`, `serve/kanban/tests/test_engine_models.py:203` / `:225`, `serve/kanban/src/owlbear_kanban/models.py:263` / `:315`, and `serve/kanban/src/owlbear_kanban/storage.py:386` together prove claimed-at response projection and `claimed_by` stripping | Durable interface + model/storage proof | PASS |
| Expired-claim lazy-release via `storage.write_task_if_unchanged` CAS (D18+D36) | quality-runner passed the task-owned CAS/retry tests at `serve/kanban/tests/test_engine_move_claim_1075.py:196`, `:244`, and `:297`; live code routes through CAS at `serve/kanban/src/owlbear_kanban/engine.py:1162` and `:1180` | Task-owned CAS suite | PASS |
| `updated` advanced on success (D14) | The code now refreshes `effective_now` at `serve/kanban/src/owlbear_kanban/engine.py:1136`, but there is still no stale-retry-success proof; current tests only cover simple reclaim and retry-to-live-claim | No mapped proof for retry-success freshness | FAIL |
| `AgentView.move_task` has NO `expected_updated` param (D46) | `serve/kanban/src/owlbear_kanban/engine.py:2548` defines `move_task(task_id, status, *, archival_reason, archival_refs)` only | Direct signature proof | PASS |

### Confidence: 0.78
### Verdict: FAIL

### Action
- Route to `backlog`.
- This is the third review cycle on the live task file (2 prior `## Review Evidence` sections already present), so the loop-breaker route applies.
- Required follow-up: make `move_task` enforce the missing D37 self-ref / cycle checks, add `move_task` self/cycle tests, add a stale-retry-success D14 proof for `start_work`, and lift broader independent engine coverage above 90%.

### Reflection
- Problem faced: the latest builder change fixed a previously reported retry-timestamp runtime issue, but a deeper `move_task` archival-matrix parity gap remained hidden by the current green subset.
- Workaround applied: compared the live `move_task` validator against the authoritative brief and the stronger archived `edit_task` path instead of trusting the passing subset.
- Pattern discovered: when the brief says the same validation matrix applies at every write site, helper parity must be audited explicitly; passing one mutation path does not prove the others.
- Quality gap: the broader independent engine run reached 89% coverage, still below the 90% reviewer gate.
[[2026-04-25]]
## Architecture Review

### Context
Task returning to pipeline after loop-breaker (3 prior review cycles). Two AC items remain unsatisfied; all other AC items have passing evidence from prior cycles. AC refined to make remaining gaps unmistakable.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Both methods (move_task, start_work) were scoped together in Brief B decomposition; remaining gaps are completion of existing AC |
| Interface clarity | PASS | Refined AC now cites exact error codes, helpers, and reference implementation lines |
| Dependency correctness | PASS | #1073 (B-09 RED) is done (archived); no other active deps |
| Module layering | PASS | All changes in engine.py + task-owned test file; no upward imports |
| TDD compliance | PASS | Test file exists (test_engine_move_claim_1075.py, 5 tests); test-writer will add D37 self/cycle + D14 retry-success tests |
| KISS/YAGNI | PASS | D37 parity fix reuses existing `_has_archival_cycle` helper; D14 fix already in place (1 line) |
| Premise challenge | PASS | Brief §1.6 explicitly requires "D37 matrix (same set as edit_task)"; §3.2 lists all 5 codes |
| Pattern consistency | PASS | Follows existing edit_task validation pattern at engine.py:2443-2456 |
| Security surface | PASS | No new system boundaries; local validation and CAS file writes only |
| Single domain | PASS | scope:kanban engine domain only |

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Key challenges: (1) AC text was already clear — problem is proof-ownership, not ambiguity; (2) remaining gaps span two methods — consider split; (3) coverage gate 89% < 90%
- Architect response: REBUTTED
  - (1) Accepted diagnosis. Refined AC now explicitly requires task-owned tests for each item, preventing "inherited/not testable" marking. This is defensive specification, not a concession.
  - (2) Both fixes are completion of existing 6/8-satisfied AC. D37 parity is ~15 lines using existing helper; D14 is 1 test (code done). Pipeline overhead of 2 separate task lifecycles exceeds the fix cost. Keeping them together is justified.
  - (3) The 89% engine coverage is background suite debt (legacy fixture/config issues), not caused by this task. Task-scoped coverage is appropriate for a GREEN task.

### Remaining work for downstream
1. **D37 parity (move_task)**: Add `task_id` param to `_validate_move_archival`, add `ERR_ARCHIVAL_REF_SELF` check and `ERR_ARCHIVAL_REF_CYCLE` via existing `_has_archival_cycle` helper (engine.py:1735). Reference impl: edit_task path at engine.py:2443-2456.
2. **D14 retry-success (start_work)**: Code fix is in place (engine.py:1136 refreshes timestamp inside loop). Task-owned test needed: assert that a successful claim_task after ERR_STALE retry produces `claimed_at`/`updated` fresher than the re-read snapshot.

### Verdict: APPROVE (via REFINE)
### Action Taken: Refined AC lines for D37 and D14 to be explicit about remaining gaps and require task-owned test proof. Advanced to todo.
[[2026-04-25]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_move_claim_1075.py
- Classes: TestFromAC_StartWork_1075 (existing, +1 new), TestFromAC_MoveTask_D37_1075 (new)
- Tests per category: error 2 (D37), boundary 1 (D14 regression guard)
- Total new: 3 tests; 2 FAIL (D37), 1 PASS (D14 — implementation already in place per AC refinement)
- ruff: clean

### Retry action
Reviewer + architect cited two remaining gaps:
1. **D37 missing**: `move_task` path has no `ERR_ARCHIVAL_REF_SELF` or `ERR_ARCHIVAL_REF_CYCLE` checks in `_validate_move_archival` — task-owned tests required on move_task path.
2. **D14 missing**: no stale-retry-success proof asserting `claimed_at`/`updated` fresher than re-read snapshot.

### New tests added

**TestFromAC_MoveTask_D37_1075 (2 tests, both FAIL)**
- `test_move_task_archival_rejects_self_reference`: calls `view.move_task(1, "archived", archival_reason="deprecated", archival_refs=[1])` → expects `ValidationError(code="ERR_ARCHIVAL_REF_SELF")` — DID NOT RAISE (no self-ref check in `_validate_move_archival`)
- `test_move_task_archival_rejects_cycle`: creates task 2 with `archival_refs=[1]`, then `view.move_task(1, "archived", archival_refs=[2])` → expects `ValidationError(code="ERR_ARCHIVAL_REF_CYCLE")` — DID NOT RAISE (no `_has_archival_cycle` call in `_validate_move_archival`)

**TestFromAC_StartWork_1075 (1 test added, PASSES)**
- `test_stale_retry_success_produces_fresh_timestamps`: injects ERR_STALE on first CAS, allows retry success, asserts `claimed_at > snapshot.updated` and `updated > snapshot.updated` and `call_count == 2` — PASSES because engine.py:1136 fix already in place. Added as regression guard per architect AC refinement ("code fix at engine.py:1136 already in place, test proof missing").

### AC coverage update

| AC item | Test | Status |
|---|---|---|
| move_task validates D37 full matrix — ERR_ARCHIVAL_REF_SELF on move_task path | test_move_task_archival_rejects_self_reference | FAILING ✓ |
| move_task validates D37 full matrix — ERR_ARCHIVAL_REF_CYCLE on move_task path | test_move_task_archival_rejects_cycle | FAILING ✓ |
| updated advanced on success (D14) stale-retry-success proof | test_stale_retry_success_produces_fresh_timestamps | PASSES (regression guard, implementation in place) |

### Verification
- pytest: 2 failed, 6 passed across test_engine_move_claim_1075.py
- ruff: clean
[[2026-04-25]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/engine.py.
- Scope: enforced D37 move_task archival parity by validating `ERR_ARCHIVAL_REF_SELF` and `ERR_ARCHIVAL_REF_CYCLE` on the move_task archive path using existing `_has_archival_cycle` logic.
- Refactor: split archived-state checks into `_validate_move_archival_for_archive(...)` and simplified move_task call-site branching to keep lint clean without behavioral drift.

- Tests:
  - Task + durable scoped run: serve/kanban/tests/test_engine_move_claim_1075.py + serve/kanban/tests/test_engine_move_claim.py -> 28 passed, 0 failed.
  - Broader engine-focused run: move/claim/activity/atomicity/create-edit/coverage/models set -> 462 passed, 0 failed.
- Lint:
  - `uv run ruff check` clean for serve/kanban/src/owlbear_kanban/engine.py and both move/claim task files.
- Coverage:
  - Scoped move/claim run: owlbear_kanban.engine 30.7% (task-focused slice).
  - Broader engine-focused run: owlbear_kanban.engine 87.6%.

- Evidence summary:
  - New task-owned D37 tests for move_task self-reference and cycle rejection now pass.
  - Existing claim/retry D14 guard remains passing in the same task file.

- Reflection:
  - Problem faced: direct signature extension on `_validate_move_archival` triggered ruff arg-count/complexity checks.
  - Workaround applied: moved archive-specific checks into a focused helper and kept non-archive field rejection at the move_task branch.
  - Pattern discovered: parity fixes are safest when reusing the stronger existing path (`edit_task`) and isolating shared checks in small helpers.
  - Quality gap: broader engine coverage in this pass is 87.6%, below the nominal 90% target despite full green for the selected stable engine suites.
[[2026-04-25]]
## Review Evidence
### Test Results
- quality-runner independent engine-focused run: 501 passed, 0 failed, 0 skipped across serve/kanban/tests/test_engine_move_claim_1075.py, serve/kanban/tests/test_engine_move_claim.py, serve/kanban/tests/test_engine_activity.py, serve/kanban/tests/test_engine_atomicity_1104.py, serve/kanban/tests/test_engine_create_edit_1070.py, serve/kanban/tests/test_engine_coverage_1068.py, serve/kanban/tests/test_engine_models.py, tests/test_engine_activity_session_1063.py, and tests/test_engine_coverage_1113.py.

### Lint
- quality-runner reported clean=true with 0 violations for serve/kanban/src/owlbear_kanban/engine.py and the in-scope engine suites.

### Coverage
- quality-runner broader engine-focused run: owlbear_kanban.engine 90%.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| All RED tests from B-09 (#1073) pass | quality-runner passed serve/kanban/tests/test_engine_move_claim.py in the independent run | Yes | COVERED |
| move_task validates archival_reason/archival_refs per D37 full matrix, including ERR_ARCHIVAL_REF_SELF and ERR_ARCHIVAL_REF_CYCLE on the move_task path | serve/kanban/tests/test_engine_move_claim_1075.py:414 and :440 with live checks at serve/kanban/src/owlbear_kanban/engine.py:1753, :1797, :1807 | Yes | COVERED |
| Write-time predicate fires on destination; failure is atomic rollback (D41) | serve/kanban/tests/test_engine_move_claim.py:307 and :323 | Yes | COVERED |
| Archive operation clears claim atomically (D17) | serve/kanban/tests/test_engine_move_claim.py:341, :358, :383 | Yes | COVERED |
| start_work sets claimed_at = now(), no claimed_by (D11) | serve/kanban/tests/test_engine_coverage_1068.py:2221, :2227; serve/kanban/tests/test_engine_models.py:226, :232; serve/kanban/src/owlbear_kanban/storage.py:386 | Yes | COVERED |
| Expired-claim lazy-release via storage.write_task_if_unchanged CAS (D18+D36) | serve/kanban/tests/test_engine_move_claim_1075.py:196, :244, :297 and serve/kanban/src/owlbear_kanban/engine.py:1162, :1180 | Yes | COVERED |
| updated advanced on success (D14), including stale-retry-success freshness against the re-read snapshot | serve/kanban/tests/test_engine_move_claim_1075.py:343 captures the original snapshot at :364, injects ERR_STALE without mutating the file at :369, and only compares result timestamps to the pre-attempt snapshot at :388 and :392 | No. Reverting the retry-loop timestamp refresh at serve/kanban/src/owlbear_kanban/engine.py:1136 would still leave this test green because no fresher retry snapshot is created or asserted. | LAX |
| AgentView.move_task has NO expected_updated param (D46) | serve/kanban/src/owlbear_kanban/engine.py:2549 | Yes | COVERED |

#### Security Review
- No issues found. The touched paths validate local task data, route claim writes through CAS, and do not introduce shell, SQL, template, or path-construction sinks.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_StartWork_1075 methods at serve/kanban/tests/test_engine_move_claim_1075.py:173, :196, :244, :297, :343 | No builder-side assertion changes detected in the latest cycle | PRESERVED |
| TestFromAC_MoveTask_D37_1075 methods at serve/kanban/tests/test_engine_move_claim_1075.py:414 and :440 | No builder-side assertion changes detected in the latest cycle | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Exact error-code and CAS-sequence assertions are used throughout the move/claim suites, including serve/kanban/tests/test_engine_move_claim.py:321, :338, :356 and serve/kanban/tests/test_engine_move_claim_1075.py:435, :470. |
| Negative and error-path coverage | STRONG | The in-scope suites cover D37 self/cycle rejection, D41 rollback, D17 archive persistence, blocked and archived claim rejection, and stale-to-already-claimed retry behavior. |
| Manual mutation reasoning | WEAK | The D14 freshness test at serve/kanban/tests/test_engine_move_claim_1075.py:343, :364, :369, :388, :392 never creates a fresher retry snapshot, so moving effective_now back outside the retry loop at serve/kanban/src/owlbear_kanban/engine.py:1136 would still pass. |
| Test independence | STRONG | tmp_path boards and local patches isolate the cases. |
| Descriptive names | STRONG | Test names map directly to D17, D18, D36, D37, D41, and D14 contracts. |

#### Data Safety
- No issues found in the primary AC paths. Archive clears claim fields before persistence, and claim acquisition now uses CAS for both expired-claim release and final claim writes.

#### Implementation-Aware Gaps
- The latest runtime fix at serve/kanban/src/owlbear_kanban/engine.py:1136 is directionally correct, and D37 parity is now implemented at serve/kanban/src/owlbear_kanban/engine.py:1753, :1797, :1807.
- The remaining gap is proof quality only: serve/kanban/tests/test_engine_move_claim_1075.py:343 does not establish a fresher re-read snapshot after ERR_STALE. The refined AC requires freshness relative to that retry snapshot, not merely relative to the original task file.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections in the live task file | 4 |
| Review Evidence sections already present before this review | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- D11 no-claimed_by proof is spread across the start_work happy-path interface test, TaskFull model-field tests, and the storage serialization strip, rather than a single task-owned end-to-end assertion.
- Some RED-phase prose in the move/claim suites still describes earlier deficiencies that the current code no longer has. This is stale documentation only and not a gate issue.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| All RED tests from B-09 (#1073) pass | quality-runner passed the independent engine-focused suite cleanly, including serve/kanban/tests/test_engine_move_claim.py | serve/kanban/tests/test_engine_move_claim.py | PASS |
| move_task validates archival_reason/archival_refs per D37 full matrix | Self and cycle tests at serve/kanban/tests/test_engine_move_claim_1075.py:414 and :440 now match live validation at serve/kanban/src/owlbear_kanban/engine.py:1753, :1797, :1807 | TestFromAC_MoveTask_D37_1075 | PASS |
| Write-time predicate fires on destination; failure is atomic rollback (D41) | quality-runner passed serve/kanban/tests/test_engine_move_claim.py:307 and :323 | Durable predicate / rollback tests | PASS |
| Archive operation clears claim atomically (D17) | quality-runner passed serve/kanban/tests/test_engine_move_claim.py:341, :358, :383 | Durable D17 archive claim-clear tests | PASS |
| start_work sets claimed_at = now(), no claimed_by (D11) | serve/kanban/tests/test_engine_coverage_1068.py:2221, :2227 proves claimed_at on start_work response; serve/kanban/tests/test_engine_models.py:226, :232 and serve/kanban/src/owlbear_kanban/storage.py:386 prove claimed_by is not on the response surface or disk format | Durable interface, model, and storage proofs | PASS |
| Expired-claim lazy-release via storage.write_task_if_unchanged CAS (D18+D36) | quality-runner passed serve/kanban/tests/test_engine_move_claim_1075.py:196, :244, :297 and live code routes release and claim through CAS at serve/kanban/src/owlbear_kanban/engine.py:1162 and :1180 | Task-owned CAS suite | PASS |
| updated advanced on success (D14), including stale-retry-success freshness against the re-read snapshot | The only task-owned D14 test at serve/kanban/tests/test_engine_move_claim_1075.py:343 compares result timestamps only to the original snapshot captured at :364 and never mutates the file during the stale side effect at :369, so it does not prove freshness against a re-read snapshot | test_stale_retry_success_produces_fresh_timestamps | FAIL |
| AgentView.move_task has NO expected_updated param (D46) | serve/kanban/src/owlbear_kanban/engine.py:2549 defines move_task(task_id, status, *, archival_reason, archival_refs) only | Direct signature proof | PASS |

### Confidence: 0.86
### Verdict: FAIL

### Action
- Route to backlog. There are already 3 Review Evidence sections in .owlbear/kanban/tasks/1075-b-10-green-move-task-start-work.md at lines 97, 233, and 353, so this is a 3rd+ review failure and the loop-breaker route applies.
- Required follow-up: rewrite serve/kanban/tests/test_engine_move_claim_1075.py:343 so the first ERR_STALE path mutates the task to a newer updated value before retry, then assert the successful result timestamps are fresher than that re-read snapshot.
- D37 parity is satisfied in the latest implementation; I did not find a new live runtime defect in the builder's current engine.py changes.

### Reflection
- Green tests were not enough here; the remaining blocker is proof quality against the refined D14 AC.
- Mutation reasoning on the D14 test was necessary because the live implementation fix at serve/kanban/src/owlbear_kanban/engine.py:1136 looks correct.
- Stale-retry freshness tests must create a newer retry snapshot or they only prove monotonicity against the original file state.
- D11 proof still spans interface, model, and storage layers rather than one task-owned end-to-end check.
[[2026-04-25]]
## Architecture Review

### Context
Task returning to pipeline after loop-breaker (4 prior review cycles, 4 Review Evidence sections). Two issues identified across cycles: D37 archival parity (NOW FIXED — engine.py:1753-1810 validates self-ref and cycle) and D14 stale-retry-success test proof (STILL WEAK — test compares against original snapshot, not re-read snapshot). This review addresses why the D14 gap persisted and provides a prescriptive AC refinement.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | move_task + start_work scoped together per Brief B decomposition |
| Interface clarity | PASS | Refined D14 AC now prescribes exact test mechanism (see below) |
| Dependency correctness | PASS | #1073 archived (done); no other active deps |
| Module layering | PASS | All changes in engine.py + task-owned test file; no upward imports |
| TDD compliance | PASS | Test file exists (test_engine_move_claim_1075.py, 8 tests); test-writer will add D14 retry-success test |
| KISS/YAGNI | PASS | D37 fix reuses existing `_has_archival_cycle` helper; D14 code fix is 1 line already in place |
| Premise challenge | PASS | Brief §1.6/§1.7/§3.1/§3.2 explicitly require these methods |
| Pattern consistency | PASS | Follows existing CAS pattern, error taxonomy, edit_task validation pattern |
| Security surface | PASS | No new system boundaries; local validation and CAS file writes only |
| Single domain | PASS | scope:kanban engine domain only |

### AC REFINEMENT — D14 (supersedes original AC line 7)

Previous AC said: "fresher than the re-read snapshot; task-owned test must assert this"
Problem: test-writer interpreted "re-read snapshot" as the original file (updated=2026-01-01) — since datetime.now() >> 2026-01-01, the test passes trivially even if the fix is reverted.

**Refined D14 AC (authoritative):**
`updated` advanced on success (D14) — stale-retry-success proof: task-owned test must:
(a) NOT inject `now` (test the runtime datetime.now refresh path);
(b) Patch `datetime.now` in the engine module to return controlled timestamps per call — T1 on the first loop iteration, T3 on the retry iteration, where T1 < T_concurrent < T3;
(c) Within the ERR_STALE side-effect callback, write the task file with `updated = T_concurrent` (simulating a concurrent update) before the retry re-reads;
(d) Assert `result.claimed_at >= T3` AND `result.updated >= T3` — proving freshness against the re-read snapshot (T_concurrent), not merely the original;
(e) Mutation guard: if `effective_now` were captured once before the loop (reverting engine.py:1136), both iterations would use T1, and since T1 < T_concurrent the assertion `result.updated >= T3` fails.

This prescribes the HOW, not just the WHAT. The test-writer can derive the test mechanically.

### Challenge Results
- Challenger: reconsider (confidence 0.31)
- Key challenges: (1) same remedy as previous refinement; (2) overrides live FAIL review; (3) D11 distributed proof
- Architect response: REBUTTED
  - (1) Previous refinement specified WHAT ("fresher than re-read snapshot"). This refinement specifies HOW (concurrent file mutation in callback, datetime.now mock with T1/T_concurrent/T3, assertion against T_concurrent). Categorically different — test-writer can now derive the test mechanically.
  - (2) The FAIL is on D14 test proof quality. REFINE→APPROVE means the AC is tightened and the task goes to `todo` for the test-writer to write the correct test. The FAIL finding is incorporated into the AC. This is exactly what the REFINE verdict is for.
  - (3) D11 distributed proof was accepted in all 4 review cycles (PASS by every reviewer). Model has no claimed_by field, storage strips it, interface confirms claimed_at. A redundant end-to-end assertion for D11 is YAGNI.
  - (4) "Proof-ownership" diagnosis accepted. The previous AC told the test-writer what to prove but not how, leading to 4 cycles of weak tests. This refinement breaks the loop by prescribing the mechanism.

### Verdict: APPROVE (via REFINE)
### Action Taken: Refined D14 AC to prescribe exact test mechanism (concurrent update + datetime mock + re-read comparison). Advanced to todo.
[[2026-04-25]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_move_claim_1075.py
- Classes: TestFromAC_StartWork_1075 (existing +1), TestFromAC_MoveTask_D37_1075 (existing)
- Tests per category: **retry-addition: 1** (regression guard)
- Total: 9 tests; 8 pre-existing PASS, 1 new PASS (regression guard)
- ruff: clean

### Retry action
Reviewer + architect cited `test_stale_retry_success_produces_fresh_timestamps` as lax — it compares result timestamps only against the original file timestamp (2026-01-01), so it passes trivially whether or not `engine.py:1136` is in place.

**New test added:** `test_stale_retry_success_timestamps_fresher_than_concurrent_update`

### Mechanism (architect AC refinement — prescribes HOW)
- t1 < t_concurrent < t3 (controlled via `_MockDatetime` subclass patching `owlbear_kanban.engine.datetime`)
- ERR_STALE callback writes `updated = t_concurrent` to disk (simulates concurrent edit)
- Engine re-reads: `task.updated = t_concurrent`; retry `effective_now = t3` (refreshed inside loop)
- Assertions: `result.claimed_at >= t3` AND `result.updated >= t3`

### Mutation guard proof
If `effective_now` were captured before the loop (reverting `engine.py:1136`): both iterations use `t1`. The second CAS succeeds (disk has `t_concurrent` matching `expected_updated`), but `result.updated = t1 < t3` → assertion fails → regression caught.

### Why PASSES (not FAILS)
Implementation fix at `engine.py:1136` is already in place. This is a regression guard per the architect's AC refinement ("code fix at engine.py:1136 already in place, test proof missing") — same pattern accepted in previous test-writer cycle for the two-CAS ordering test.

### AC coverage update
| AC item | Test | Status |
|---|---|---|
| updated advanced on success (D14) — stale-retry-success freshness against re-read snapshot | test_stale_retry_success_produces_fresh_timestamps (weaker, PASS) + **test_stale_retry_success_timestamps_fresher_than_concurrent_update (mutation-resistant, PASS)** | NOW STRONG |
[[2026-04-25]]
## Builder Notes
- Implementation: no code changes in this cycle; existing implementation in serve/kanban/src/owlbear_kanban/engine.py already satisfies current TestFromAC contracts for #1075.
- Tests (task-scoped): 29 passed, 0 failed across serve/kanban/tests/test_engine_move_claim_1075.py and serve/kanban/tests/test_engine_move_claim.py.
- Tests (broader engine-focused verification): 502 passed, 0 failed, 0 skipped across:
  - serve/kanban/tests/test_engine_move_claim_1075.py
  - serve/kanban/tests/test_engine_move_claim.py
  - serve/kanban/tests/test_engine_activity.py
  - serve/kanban/tests/test_engine_atomicity_1104.py
  - serve/kanban/tests/test_engine_create_edit_1070.py
  - serve/kanban/tests/test_engine_coverage_1068.py
  - serve/kanban/tests/test_engine_models.py
  - tests/test_engine_activity_session_1063.py
  - tests/test_engine_coverage_1113.py
- Coverage: owlbear_kanban.engine = 90% in the broader verification run.
- Ruff: clean for serve/kanban/src/owlbear_kanban/engine.py and scoped move/claim test files.
- Evidence summary: D37 move_task archival matrix checks, D18+D36 CAS claim/retry semantics, and D14 stale-retry-success freshness proofs are all green in the current task-owned + durable suite set.

- Reflection:
  - Problem faced: this task has extensive prior cycles; the risk was re-editing already-correct code instead of validating the latest gate state.
  - Workaround applied: ran both narrow and broader quality-runner scopes to separate task correctness from coverage-gate requirements.
  - Pattern discovered: when retry-proof tests are newly strengthened, a no-diff GREEN completion can be correct if independent broader verification also clears coverage/lint gates.
  - Quality gap: task-only coverage remains intentionally low due to narrow scope; broader targeted suite is required to satisfy the module coverage gate.

[[2026-04-25]]
## Review Evidence
### Test Results
- quality-runner scoped: 29 passed, 0 failed, 0 skipped across serve/kanban/tests/test_engine_move_claim_1075.py and serve/kanban/tests/test_engine_move_claim.py.
- quality-runner broader engine-focused run: 502 passed, 0 failed, 0 skipped across the nine engine suites named in the latest builder note.

### Lint
- quality-runner reported clean=true with 0 violations for serve/kanban/src/owlbear_kanban/engine.py and the in-scope engine suites.

### Coverage
- Scoped task run: owlbear_kanban.engine 36%.
- Broader engine-focused run: owlbear_kanban.engine 90%.
- Reviewer module gate satisfied on the broader independent run.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| All RED tests from B-09 (#1073) pass | serve/kanban/tests/test_engine_move_claim.py in the scoped quality-runner pass set | Yes | COVERED |
| move_task validates archival_reason and archival_refs per D37 full matrix, including ERR_ARCHIVAL_REF_SELF and ERR_ARCHIVAL_REF_CYCLE on the move_task path | serve/kanban/tests/test_engine_move_claim.py:226, :242, :258, :274 plus serve/kanban/tests/test_engine_move_claim_1075.py:495 and :521 | Yes | COVERED |
| Write-time predicate fires on destination; failure remains atomic per D41 | serve/kanban/tests/test_engine_move_claim.py:307 and :323 | Yes | COVERED |
| Archive operation clears claim atomically per D17 | serve/kanban/tests/test_engine_move_claim.py:341 and :358 | Yes | COVERED |
| start_work sets claimed_at = now(), no claimed_by per D11 | serve/kanban/tests/test_engine_coverage_1068.py:2221, serve/kanban/tests/test_engine_models.py:203 and :225, serve/kanban/src/owlbear_kanban/models.py:263, :315, :441, serve/kanban/src/owlbear_kanban/storage.py:386, serve/kanban/src/owlbear_kanban/engine.py:1175 and :1639 | Yes | COVERED |
| Expired-claim lazy-release via storage.write_task_if_unchanged CAS per D18 and D36 | serve/kanban/tests/test_engine_move_claim_1075.py:196 and :297 plus serve/kanban/src/owlbear_kanban/engine.py:1162 and :1180 | Yes | COVERED |
| updated advanced on success per D14, including stale-retry-success freshness against the reread snapshot | serve/kanban/tests/test_engine_move_claim_1075.py:400, :467, :472 plus serve/kanban/src/owlbear_kanban/engine.py:1136 and :1177 | Yes | COVERED |
| AgentView.move_task has no expected_updated param per D46 | serve/kanban/src/owlbear_kanban/engine.py:2549 | Yes | COVERED |

#### Security Review
- No issues found. The touched paths validate local task data, route claims through CAS writes, and do not introduce shell, SQL, template, secret, or path-construction sinks.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_StartWork_1075 pre-existing claim tests in serve/kanban/tests/test_engine_move_claim_1075.py | No builder-side assertion changes detected in the latest cycle; the latest builder note states no code changes | PRESERVED |
| TestFromAC_StartWork_1075.test_stale_retry_success_timestamps_fresher_than_concurrent_update at serve/kanban/tests/test_engine_move_claim_1075.py:400 | Added by the latest test-writer cycle; no builder-side modification detected | PRESERVED |
| TestFromAC_MoveTask_D37_1075 tests at serve/kanban/tests/test_engine_move_claim_1075.py:495 and :521 | No builder-side modification detected in the latest cycle | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact error-code, CAS-sequence, and timestamp-threshold assertions are used at serve/kanban/tests/test_engine_move_claim_1075.py:297, :400, :495, :521 and serve/kanban/tests/test_engine_move_claim.py:307, :323, :341. |
| Negative and error-path coverage | STRONG | Blocked and archived start_work guards are covered at serve/kanban/tests/test_engine_move_claim.py:475 and :495; D37 archive validation and D41 rollback are covered at :226, :242, :258, :274, :307, :323. |
| Manual mutation reasoning | STRONG | The D14 mutation-resistant test at serve/kanban/tests/test_engine_move_claim_1075.py:400 with assertions at :467 and :472 fails if effective_now is moved back outside the retry loop; the two-step CAS test at :297 fails if expired-claim handling collapses to a single write. |
| Test independence | STRONG | The reviewed suites use isolated tmp_path boards and local patches only. |
| Descriptive names | STRONG | Test names map directly to D11, D14, D17, D18, D36, D37, D41, and D46 contracts. |

#### Data Safety
- No issues found. Expired-claim release and final claim writes both route through CAS, and archive persistence continues to clear claim fields before the file move.

#### Implementation-Aware Gaps
- No significant untested path found in the task scope. The live code and the independent runs cover D37 self and cycle rejection, D41 rollback, D17 archive persistence, D18 and D36 CAS claim flow, D14 stale-retry freshness, and the blocked and archived start_work guards.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections in task file | 5 |
| Review Evidence sections before this review | 4 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- Some RED-phase explanatory prose in serve/kanban/tests/test_engine_move_claim_1075.py still describes earlier broken behavior. The assertions are current, so this is non-blocking documentation drift only.
- D11 proof remains distributed across response, model, and storage layers rather than one task-owned end-to-end assertion. The latest architecture refinement accepted that proof shape explicitly.

### Deductions
- 0.02 for distributed D11 proof instead of a single task-owned end-to-end assertion.
- 0.02 for stale explanatory prose in the task-owned test file.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All RED tests from B-09 (#1073) pass | quality-runner passed serve/kanban/tests/test_engine_move_claim.py in both the scoped and broader independent runs | Durable B-09 move and claim suite | PASS |
| move_task validates archival_reason and archival_refs per D37 full matrix | Durable D37 matrix tests at serve/kanban/tests/test_engine_move_claim.py:226, :242, :258, :274 plus task-owned self and cycle tests at serve/kanban/tests/test_engine_move_claim_1075.py:495 and :521 match live validation at serve/kanban/src/owlbear_kanban/engine.py:1799 and :1809 | Durable D37 suite plus TestFromAC_MoveTask_D37_1075 | PASS |
| Write-time predicate fires on destination; failure is atomic rollback (D41) | quality-runner passed serve/kanban/tests/test_engine_move_claim.py:307 and :323 | Predicate failure and rollback tests | PASS |
| Archive operation clears claim atomically (D17) | quality-runner passed serve/kanban/tests/test_engine_move_claim.py:341 and :358 | Archive claim-clear and persistence tests | PASS |
| start_work sets claimed_at = now(), no claimed_by (D11) | Happy-path start_work proof at serve/kanban/tests/test_engine_coverage_1068.py:2221 plus response and persistence shape at serve/kanban/tests/test_engine_models.py:203 and :225, serve/kanban/src/owlbear_kanban/models.py:263, :315, :441, serve/kanban/src/owlbear_kanban/storage.py:386, and serve/kanban/src/owlbear_kanban/engine.py:1175 and :1639 | Durable interface, model, and storage proofs | PASS |
| Expired-claim lazy-release via storage.write_task_if_unchanged CAS (D18 and D36) | quality-runner passed serve/kanban/tests/test_engine_move_claim_1075.py:196 and :297, and the live implementation performs both release and claim CAS writes at serve/kanban/src/owlbear_kanban/engine.py:1162 and :1180 | Task-owned CAS suite | PASS |
| updated advanced on success (D14), including stale-retry-success freshness against the reread snapshot | quality-runner passed serve/kanban/tests/test_engine_move_claim_1075.py:400 with timestamp assertions at :467 and :472, and the live retry loop refreshes effective_now at serve/kanban/src/owlbear_kanban/engine.py:1136 before writing updated at :1177 | Mutation-resistant D14 retry-success test | PASS |
| AgentView.move_task has no expected_updated param (D46) | The live AgentView signature at serve/kanban/src/owlbear_kanban/engine.py:2549 contains task_id, status, archival_reason, and archival_refs only | Direct signature proof | PASS |

### Confidence: 0.96
### Verdict: PASS
### Action
- Advance to docs. The latest architecture refinement is satisfied, I found no blocking implementation defect, no test-integrity breach, and the broader independent engine run clears the 90% module coverage gate.
[[2026-04-25]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified / N/A | `serve/kanban/README.md` method table entries for `move_task` and `start_work` are accurate; no prose makes incorrect claims. D37 archival validation and CAS semantics are implementation details not exposed in the summary table. |
| 2 | Module docstrings | Yes | Verified | `KanbanEngine.claim_task` docstring accurate (CAS is implementation detail). `KanbanEngine.move_task` docstring accurate. `KanbanEngine.start_work` docstring accurate (delegates to `claim_task`). `AgentView.move_task` and `AgentView.start_work` had no docstrings before this task and none were added (implementation discipline). `_validate_move_archival_for_archive` is a private helper — no docstring required. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body. |
| 4 | Research doc | No | N/A | No research phase for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `kanban.excalidraw` (`describes: serve/kanban/src/**`) and `mcp-topology.excalidraw` (`describes: serve/kanban/src/**`) — both footers updated from `2026-04-25 (ae0236ed)` to `2026-04-25 (675362f3)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No deleted files. No orphaned IN-scope docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Verified — no docstring edits needed |
| `serve/kanban/tests/test_engine_move_claim_1075.py` | OUT (test file) | N/A |
| `serve/kanban/tests/test_engine_move_claim.py` | OUT (test file) | N/A |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer updated
- `share/diagrams/mcp-topology.excalidraw` — footer updated

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-04-25]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-09 (#1073) pass | Full-suite QR: 2110 passed, 0 task-scoped failures; reviewer confirmed 502/0 engine suite | PASS |
| move_task validates D37 full matrix (ERR_ARCHIVAL_REF_SELF + ERR_ARCHIVAL_REF_CYCLE) | Code verified at engine.py:1797,1807; task tests at test_engine_move_claim_1075.py:495,521 | PASS |
| Write-time predicate fires + atomic rollback (D41) | Reviewer mapped to test_engine_move_claim.py:307,323; QR passed | PASS |
| Archive clears claim atomically (D17) | Reviewer mapped to test_engine_move_claim.py:341,358; QR passed | PASS |
| start_work sets claimed_at=now(), no claimed_by (D11) | Distributed proof: engine.py:1175,1639 + models.py:263,315 + storage.py:386; accepted by 5 review cycles + architect | PASS |
| Expired-claim lazy-release via CAS (D18+D36) | Two-step CAS at engine.py:1162,1180; tests at test_engine_move_claim_1075.py:196,244,297 | PASS |
| updated advanced on success (D14) — stale-retry-success freshness | Timestamp refresh at engine.py:1136; mutation-resistant test at test_engine_move_claim_1075.py:400 with T1/T_concurrent/T3 mechanism | PASS |
| AgentView.move_task has NO expected_updated (D46) | Signature at engine.py:2550: (task_id, status, *, archival_reason, archival_refs) | PASS |

### Test Results
- Full suite (quality-runner): 2110 passed, 165 failed, 4 skipped — zero task-scoped failures; all 165 failures are background debt (KanbanEngine agent_name constructor kwargs ~150, agent_map config ~23, misc)
- Scoped engine suite (reviewer evidence): 502 passed, 0 failed
- ruff: 0 violations in task-scoped files; 8 violations in unrelated packages

### Architect Quality: 3/5
Original AC was specific about contracts (D37, D14, D18+D36, D46) but left proof-quality ambiguity — "stale-retry-success freshness" wasn't prescriptive enough. Led to 5 review cycles and 2 architect refinements. Second refinement prescribed exact test mechanism (T1/T_concurrent/T3 + concurrent file mutation + datetime mock). The architect corrected well when flagged, but the original AC should have prescribed proof methodology for CAS retry contracts upfront.

### Deduction Breakdown
- AC quality 3/5: -0.03
- No task-scoped test failures: -0.00
- No task-scoped lint violations: -0.00
- Reviewer evidence present and detailed (5th cycle, PASS): -0.00
- All 8 AC lines have specific evidence: -0.00

### Confidence: 0.97
### Action: archive