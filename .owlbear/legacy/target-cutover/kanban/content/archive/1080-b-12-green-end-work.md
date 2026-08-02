---
id: 1080
title: 'B-12: GREEN — end_work'
status: archived
priority: medium
created: 2026-04-21 10:50:32.621365+00:00
updated: 2026-04-26T16:07:05.580652+00:00
tags:
- phase:engine
- brief:b
- scope:kanban
- tdd:green
parent: 1044
depends_on:
- 1077
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief B (#1044) — paper-integration.md §1.8, §3.7
Module: `serve/kanban/src/owlbear_kanban/engine.py`

Implement AgentView.end_work — the 4-outcome lifecycle endpoint (success, reject, release, block per D52). This is the most complex single method in the engine.

Outcomes: success (auto-advance, auto-archive from terminal per D51), reject (move_to required, archival path available), release (idempotent no-op on unclaimed per D55), block (block_reason required, optional move_to per D52).

Forbidden-parameter matrix enforced deterministically before any state mutation (D41). Multiple errors → leftmost-row, leftmost-column precedence.

## Acceptance Criteria

- [ ] All RED tests from B-11 (#1077) pass
- [ ] 4 outcomes dispatched correctly: success, reject, release, block
- [ ] Forbidden-parameter matrix: deterministic error precedence per §1.8 table
- [ ] success: auto-advance one step; from terminal → archive completed/[] (D51)
- [ ] reject: move_to required; archival path with full D37 validation
- [ ] release: idempotent on unclaimed (pure no-op per D55)
- [ ] block: block_reason required; optional move_to with predicate (D15+D41)
- [ ] All mutations atomic — (a) predicate/validation failure → nothing written; (b) archive `_move_file` OSError → full pre-mutation snapshot restored including status, body, claimed_at, archival_reason, archival_refs (D41)
- [ ] Note prepended with ISO 8601 timestamp (D20)
- [ ] Guidance emitted for block (AR/DR suggestion) and skip-transition (D54)

## Architect Guidance (loop-breaker cycle)

This task returns from a 3rd review-fail loop-breaker. Implementation is complete; the remaining gap is **reject-to-archived rollback proof density**.

### What the test-writer must add

The success-path rollback tests already assert body restoration (`tests/test_engine_end_work_1080.py:270-295`). The reject-to-archived path only asserts status and claimed_at (`tests/test_engine_end_work_1080.py:347-402`). Add assertions to the existing reject-to-archived rollback tests proving:

1. **Body restoration**: the prepended note must NOT appear in the restored record (mirror success-path test at line 270)
2. **archival_reason restoration**: must be None (original value), not the caller-supplied reason
3. **archival_refs restoration**: must be original (empty/None), not the caller-supplied refs

The engine mutates these fields before `_move_file` at `serve/kanban/src/owlbear_kanban/engine.py:1364-1367` (archival) and `:1434` (note). The rollback at `:1456-1461` writes the complete `original` snapshot, so all fields ARE restored — the tests just need to prove it.

### What is already done (do not re-implement)

- Archive `_move_file` rollback code in engine.py (builder pass 2)
- GAP-1 fault-injection tests (9 tests in `TestFromAC_EndWorkArchiveRollback`)
- GAP-2 exact D54 guidance tests (6 tests in `TestFromAC_GuidanceExact`)
- All 47 original end_work tests remain green

### Informational

- `tests/test_engine_end_work_1080.py:18` has a stale RED-phase banner ("All new tests are expected to FAIL") — should be corrected during the test-writer pass.
[[2026-04-26]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | end_work GREEN phase only |
| Interface clarity | PASS | AC specifies all 4 outcomes, parameters, validation, atomicity, timestamps, guidance |
| Dependency correctness | PASS | depends_on 1077 (B-11 RED) — archived/done |
| Module layering | PASS | engine.py is the target module, no upward imports |
| TDD compliance | PASS | Test file exists at tests/test_engine_end_work_1080.py |
| KISS/YAGNI | PASS | Minimal scope — only end_work method |
| Premise challenge | PASS | Core engine lifecycle method, must exist |
| Pattern consistency | PASS | Follows existing engine.py atomicity patterns (move_task rollback at engine.py:1121-1126) |
| Security surface | PASS | No new system boundaries; archive rollback is internal path |
| Single domain | PASS | Kanban engine domain only |

### AC Refinement
Tightened AC line 8 from "predicate/validation failure → nothing written" to explicitly include I/O-failure rollback with full snapshot field list. The reviewer's 3 cycles flagged a reject-to-archived rollback proof gap that the original AC text didn't unambiguously require — the test-writer needs explicit field list to target.

Added `## Architect Guidance (loop-breaker cycle)` section with specific test-writer instructions: add body, archival_reason, and archival_refs assertions to the reject-to-archived rollback tests.

### Challenge Results
- Challenger: reconsider (confidence 0.57)
- Key challenges: (1) AC line "predicate/validation failure" doesn't cover I/O-failure rollback; (2) success-path proof doesn't substitute for reject-path proof due to different archival field mutations; (3) reject rollback assertions only check status + claimed_at, not body/archival_reason
- Architect response: accepted — refined AC to make I/O-failure rollback an explicit requirement with named fields, and added architect guidance with specific test-writer instructions

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC line 8 to explicitly cover archive _move_file OSError rollback with full field list (status, body, claimed_at, archival_reason, archival_refs). Added architect guidance section for test-writer. Advancing to todo.
[[2026-04-26]]
## Test-Writer Notes

**Test file:** `tests/test_engine_end_work_1080.py`
**Class:** `TestFromAC_EndWorkArchiveRollback` (loop-breaker additions)

### Loop-breaker cycle 3 — what was added

Per architect guidance, added 3 proof tests to `TestFromAC_EndWorkArchiveRollback` targeting the reject-to-archived rollback field restoration gap cited in the 3rd review-fail:

| New test | Field proven | Contract |
|----------|-------------|---------|
| `test_reject_to_archived_move_failure_restores_original_body` | body | prepended note NOT present after rollback; original content preserved |
| `test_reject_to_archived_move_failure_restores_archival_reason` | archival_reason | None (original) after rollback, not caller-supplied 'dropped' |
| `test_reject_to_archived_move_failure_restores_archival_refs` | archival_refs | [] (original) after rollback, not caller-supplied [2] |

Also corrected stale RED-phase banner at module docstring line 18.

### Test status
- **3 new proof tests: all PASS** — architect confirmed rollback is complete; tests are GREEN proofs per loop-breaker directive ("tests just need to prove it")
- **15 existing tests: all PASS** — no regressions
- **Total: 18 tests, 0 failed, ruff clean**

### AC coverage (reject-to-archived rollback field list from AC line 8)
| AC field | Proven by |
|----------|----------|
| status | `test_reject_to_archived_move_failure_restores_original_status` (existing) |
| body | `test_reject_to_archived_move_failure_restores_original_body` (new) |
| claimed_at | `test_reject_to_archived_move_failure_restores_claimed_at` (existing) |
| archival_reason | `test_reject_to_archived_move_failure_restores_archival_reason` (new) |
| archival_refs | `test_reject_to_archived_move_failure_restores_archival_refs` (new) |
[[2026-04-26]]
## Builder Notes
- Implementation: validated existing `end_work` GREEN implementation in `serve/kanban/src/owlbear_kanban/engine.py` (no additional code edits required in this pass).
- Task test suite: `tests/test_engine_end_work_1080.py` -> 18 passed, 0 failed (quality-runner scoped).
- Regression-focused scoped suite: `serve/kanban/tests/test_engine_end_work_1077.py`, `serve/kanban/tests/test_engine_atomicity_1104.py`, `serve/kanban/tests/test_engine_move_claim.py`, `tests/test_engine_end_work_fail_1125.py` plus task file -> 109 passed, 0 failed (quality-runner scoped).
- Lint: clean for `serve/kanban/src/owlbear_kanban/engine.py` and task-scoped tests.
- Coverage evidence: broad quality-runner pass reports `owlbear_kanban.engine` at 94% (task-scoped-only runs underrepresent large-module coverage).
- AC evidence summary: all 4 outcomes and deterministic parameter validation remain green via RED-origin suites; reject-to-archived rollback proof density is covered by the added TestFromAC rollback assertions (body, archival_reason, archival_refs restoration on `_move_file` failure).

### Reflection
- Scoped quality runs provide stable signal for this task; broad full-suite run currently contains unrelated repository failures.
- Loop-breaker gap was proof density, not implementation logic; validating test coverage of rollback fields closed the acceptance gap.
- Separate broad context from task gate evidence to avoid false negatives from unrelated suites.
[[2026-04-26]]
## Review Evidence

### Test Results
- quality-runner scoped task/regression set: 109 passed, 0 failed, 0 skipped
- supporting shared-behavior suites: 99 passed, 0 failed; `serve/kanban/tests/test_list_sessions.py` had 46 fixture errors from an unrelated `KanbanEngine.__init__(agent_name=...)` mismatch and was not used for gate evidence

### Lint
- clean for `serve/kanban/src/owlbear_kanban/engine.py` and all scoped/supporting test files reviewed here

### Coverage
- `owlbear_kanban.engine`: 47% on the task/regression set
- `owlbear_kanban.engine`: 58% on the broader shared-behavior set
- Reviewer deduction: `engine.py` is a large shared module, so verdict is based on path-specific proof rather than raw module percentage alone

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|----------------|----------------------------|---------|
| All RED tests from B-11 (#1077) pass | `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_end_work_fail_1125.py` | Yes | COVERED |
| 4 outcomes dispatched correctly: success, reject, release, block | `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_end_work_fail_1125.py`, `tests/test_engine_release_note_1127.py` | Yes | COVERED |
| Forbidden-parameter matrix: deterministic error precedence per §1.8 table | `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_end_work_fail_1125.py` | Yes | COVERED |
| success: auto-advance one step; from terminal archive completed/[] (D51) | `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_end_work_1080.py` | Yes | COVERED |
| reject: move_to required; archival path with full D37 validation | `serve/kanban/tests/test_engine_end_work_1077.py` plus shared `_validate_move_archival_for_archive` suites in `serve/kanban/tests/test_engine_move_claim.py`, `serve/kanban/tests/test_engine_move_claim_1075.py`, `serve/kanban/tests/test_engine_create_edit_1070.py` | Yes | COVERED |
| release: idempotent on unclaimed (pure no-op per D55) | `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_release_note_1127.py` | Yes | COVERED |
| block: block_reason required; optional move_to with predicate (D15+D41) | `serve/kanban/tests/test_engine_end_work_1077.py` | Yes | COVERED |
| All mutations atomic — predicate/validation failures write nothing; archive `_move_file` OSError restores status, body, claimed_at, archival_reason, archival_refs | `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_end_work_1080.py`, `serve/kanban/tests/test_engine_atomicity_1104.py` | Yes | COVERED |
| Note prepended with ISO 8601 timestamp (D20) | `serve/kanban/tests/test_engine_end_work_1077.py`, `tests/test_engine_release_note_1127.py` | Yes | COVERED |
| Guidance emitted for block and skip-transition (D54) | `tests/test_engine_end_work_1080.py` | Yes | COVERED |

#### Security Review
- No issues found in the reviewed validation, rollback, archive-move, and guidance paths.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_EndWorkArchiveRollback` | Added reject-to-archived rollback proofs for body, archival_reason, archival_refs | STRENGTHENED |
| `TestFromAC_GuidanceExact` | Replaced weak substring guidance checks with exact-list equality | STRENGTHENED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | exact guidance equality and direct rollback field assertions |
| Negative/error-path coverage | ADEQUATE | `_move_file` OSError, predicate failures, forbidden params, unclaimed paths covered |
| Manual mutation reasoning | ADEQUATE | helper validation branches and rollback/guidance drift are exercised by task plus shared suites |
| Test independence | STRONG | isolated temp boards per test |
| Descriptive names | STRONG | AC-specific test naming throughout |

#### Data Safety
- No blocking data-safety issue found. The owned `_move_file` rollback path is directly exercised in `tests/test_engine_end_work_1080.py`, and broader emit-failure rollback is exercised in `serve/kanban/tests/test_engine_atomicity_1104.py`.

#### Implementation-Aware Gaps
- No blocking gaps remain. The latest Architect Guidance explicitly narrowed the loop-breaker gap to reject-to-archived rollback proof density; the new `tests/test_engine_end_work_1080.py` coverage closes that gap.
- Code-reader concern about D37 branch density did not block signoff after broader verification: `AgentView.end_work` calls `_validate_move_archival_for_archive` on reject-to-archived, and the shared helper branches are green in the move/edit archival suites listed above.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_list_sessions.py` is currently unusable as corroborating evidence because its fixture passes `agent_name=` into `KanbanEngine.__init__()`. This did not affect the 1080 gate because release-path semantics are already covered by `tests/test_engine_release_note_1127.py` and `tests/test_engine_activity_session_1063.py`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| All RED tests from B-11 (#1077) pass | scoped quality-runner task/regression run reported 109 passed, 0 failed | `test_engine_end_work_1077.py`, `test_engine_end_work_fail_1125.py` | PASS |
| 4 outcomes dispatched correctly | success/reject/block behavior green in `1077`; fail behavior green in `1125`; release-specific action semantics green in `1127` | `test_engine_end_work_1077.py`, `test_engine_end_work_fail_1125.py`, `test_engine_release_note_1127.py` | PASS |
| Forbidden-parameter matrix | outcome-specific validation branches exercised across `1077` and `1125` | `test_engine_end_work_1077.py`, `test_engine_end_work_fail_1125.py` | PASS |
| success auto-advance / terminal archive | success and archive paths green; rollback branch directly fault-injected in `1080` | `test_engine_end_work_1077.py`, `test_engine_end_work_1080.py` | PASS |
| reject move_to required / D37 validation | reject-to-archived entry coverage in `1077`; shared helper branches covered in move/edit archival suites | `test_engine_end_work_1077.py`, `test_engine_move_claim.py`, `test_engine_move_claim_1075.py`, `test_engine_create_edit_1070.py` | PASS |
| release idempotent on unclaimed | unclaimed no-op and claimed release note/activity semantics are green | `test_engine_end_work_1077.py`, `test_engine_release_note_1127.py` | PASS |
| block requires reason / optional move_to with predicate | block reason, move_to, predicate success/failure paths green | `test_engine_end_work_1077.py` | PASS |
| mutations atomic | predicate failures and archive `_move_file` rollback directly proved; broader emit rollback also green | `test_engine_end_work_1077.py`, `test_engine_end_work_1080.py`, `test_engine_atomicity_1104.py` | PASS |
| note prepended with ISO 8601 timestamp | timestamp assertions green for end_work and claimed release note | `test_engine_end_work_1077.py`, `test_engine_release_note_1127.py` | PASS |
| guidance emitted for block and skip-transition | exact-list D54 assertions green | `test_engine_end_work_1080.py` | PASS |

### Deductions
- 0.03: scoped `engine.py` coverage remains low, so signoff depends on path-specific evidence rather than raw module percentage
- 0.02: one unrelated corroborating suite (`serve/kanban/tests/test_list_sessions.py`) is currently broken at fixture setup and could not be used
- 0.02: D37 archival validation evidence for reject-to-archived is shared-helper based rather than fully end_work-owned, but the helper is directly invoked by this path and the latest architect refinement narrowed the gating issue to rollback proof density

### Verdict
PASS with confidence 0.91

### Action
Advance to docs.
[[2026-04-26]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Updated | `serve/kanban/README.md` — `end_work` row description was incomplete ("Append outcome note and advance or reject"); corrected to match the docstring and actual 4-outcome contract (success, fail, block, reject) |
| 2 | Module docstrings | No | N/A | No Python modules modified in this pass (engine.py untouched; only `tests/test_engine_end_work_1080.py` changed) |
| 3 | External attribution | No | N/A | No external patterns referenced |
| 4 | Research doc | No | N/A | No research doc produced for this task |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` describes `serve/kanban/src/**`; changed files are under `tests/` — no match |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| `tests/test_engine_end_work_1080.py` | OUT (test file) | N/A |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstrings) | Verified accurate — no changes in this pass |
| `serve/kanban/README.md` | IN | Updated: end_work row description corrected |

### Files Updated
- `serve/kanban/README.md` — end_work description row

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found (`1080-*` pattern: no matches)
[[2026-04-26]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| All RED tests from B-11 (#1077) pass | scoped run: 132 passed, 0 failed (includes 1077 suite) | PASS |
| 4 outcomes dispatched correctly | test_engine_end_work_1077.py, test_engine_end_work_fail_1125.py, test_engine_release_note_1127.py all green | PASS |
| Forbidden-parameter matrix | test_engine_end_work_1077.py, test_engine_end_work_fail_1125.py green | PASS |
| success: auto-advance / terminal archive | test_engine_end_work_1077.py, test_engine_end_work_1080.py green | PASS |
| reject: move_to required / D37 validation | test_engine_end_work_1077.py, shared archival suites green | PASS |
| release: idempotent on unclaimed | test_engine_end_work_1077.py, test_engine_release_note_1127.py green | PASS |
| block: block_reason required / optional move_to | test_engine_end_work_1077.py green | PASS |
| mutations atomic (rollback fields) | test_engine_end_work_1080.py (3 new rollback proofs), test_engine_atomicity_1104.py green | PASS |
| Note prepended with ISO 8601 timestamp | test_engine_end_work_1077.py, test_engine_release_note_1127.py green | PASS |
| Guidance emitted for block/skip-transition | test_engine_end_work_1080.py exact-list assertions green | PASS |

### Test Results
- pytest (scoped task+regression): 132 passed, 0 failed
- pytest (full suite): 2251 passed, 173 failed, 209 errors — all failures from pre-existing `KanbanEngine.__init__(agent_name=...)` fixture mismatch in cockpit/session tests, NOT introduced by 1080
- ruff: clean

### Architect Quality: 4/5
AC was specific across all 10 lines. Loop-breaker refinement of AC line 8 (explicit rollback field list) was appropriate and effective. Minor gap: original AC didn't specify I/O-failure rollback fields, requiring a loop-breaker cycle to close.

### Deduction Breakdown
- Uncommitted deliverables (3 proof tests + banner fix not committed by upstream): -.02
- Full-suite pre-existing failures (not task-introduced): no deduction
- Reviewer evidence present and detailed (PASS at 0.91): no deduction
- AC quality 4/5: no deduction
- All 10 AC lines have specific evidence: no deduction

### Confidence: 0.98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 3976bdfd | test | tests/test_engine_end_work_1080.py | #1080 |
| 039e7f40 | docs | serve/kanban/README.md | #1080 |
| bbf0be93 | test | tests/test_engine_end_work_1080.py | #1080 |