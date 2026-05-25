---
id: 1845
title: 'P2-06: Confirmation cycle — factually-wrong to contested/disputed'
status: done
priority: needed
created: 2026-05-24T19:01:24.983062+02:00
updated: 2026-05-25T05:44:13.456466+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on:
  - 1840
  - 1841
ac:
  - 'AC1: `MemoryEntry` has `contested_by_task: str | None` (default None) in both
    packages (frontmatter-serialized). `record_factually_wrong(entry_id, task_id,
    expected_updated_at=None)` raises `ValidationError` if `task_id` is empty/whitespace.
    When state ∈ {approved, curated}: sets `contested`, stores `contested_by_task=task_id`,
    clears `approved_at` to None (per downgrade contract). Remains in recall. Approved
    fixtures MUST have non-null `approved_at` and assert cleared.'
  - 'AC2: When state is `contested` and `contested_by_task` is non-None ≠ `task_id`:
    transitions to `disputed` (excluded from recall). Edge: `contested` with `contested_by_task=None`
    treated as initial confirmation (stores `task_id`, remains `contested`).'
  - 'AC3: When state is `contested` and `contested_by_task == task_id`: returns entry
    unchanged (no mutation, no error). Non-voteable states ({approved, curated, contested}
    complement) raise `TransitionError`. All AC1–AC3 logic evaluated after OCC guard
    in AC4.'
  - 'AC4: `expected_updated_at` is CAS guard: if non-None and mismatches entry `updated_at`,
    raise `ConcurrencyError` without mutation. If None, check skipped (unconditional
    write).'
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

Implement the two-step confirmation cycle for factually-wrong assessments.

### In Scope
- MemoryEntry field: contested_by_task (str | None, default None)
- Engine method: record_factually_wrong(entry_id, task_id, expected_updated_at)
- First factually_wrong → contested (still recalled)
- Second from different task → disputed (excluded)
- Same-task duplicate = no-op
- Voteable state guard (approved, curated, contested)
- task_id non-empty validation

### Out of Scope
- State enum definition (P2-01)
- Assessment tool (P2-07)
- Score computation (P2-02)

## Domain
serve/memory/, serve/mcp-memory/

Both packages have duplicated MemoryEntry models and explicit frontmatter serialization. Field addition must be mirrored in both packages (same pattern as #1840, #1841).

[[2026-05-25T01:47:27+02:00]]
## Research
- Research doc: .owlbear/research/memory-confirmation-cycle-factually-wrong.md
- Sources: 8 studied, 5 high-relevance (codebase)
- Recommendation: T1 implementation — single `record_factually_wrong()` engine method following resolve()/approve() pattern (confidence: 0.92)
- Key findings: straightforward extension of #1840 state machine; 6 files across 2 packages; one AC4 discrepancy (ConflictError vs ConcurrencyError) flagged for architect
- Challenge: SKIP — prescriptive ACs, trivial extension
- No new follow-up tasks needed (decomposition complete in parent #1839)

[[2026-05-25T02:19:16+02:00]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: confirmation cycle transitions (single engine method) |
| Interface clarity | PASS | State-based preconditions, explicit types, edge cases defined |
| Dependency correctness | PASS | #1840 (states) and #1841 (model fields) both archived |
| Module layering | PASS | Engine in serve/memory, field sync in serve/mcp-memory — same dual-package pattern as #1840/#1841 |
| TDD compliance | PASS | behavioral bundle, test-writer handles RED |
| KISS/YAGNI | PASS | Single method following resolve()/approve() pattern; optional OCC justified by caller (#1846 assess_memories batch) |
| Premise challenge | PASS | Required by parent Brief — confirmation cycle prevents single-agent nuclear blocks |
| Pattern consistency | PASS | Follows _validate_occ + state guard + model_copy + _write_updated_entry pattern. Optional OCC is documented deviation (first mutator to allow it) |
| Security surface | PASS | No new system boundaries; task_id validation added (matches source_agent pattern) |
| Single domain | PASS | serve/memory + serve/mcp-memory (same domain, dual-package sync) |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| record_factually_wrong from non-voteable state | Invalid source state | TransitionError | Yes | Clear error |
| OCC mismatch (when provided) | Concurrent mutation | ConcurrencyError | Yes | Retry with fresh state |
| Empty/whitespace task_id | Invalid identity | ValidationError | Yes | Prevents collapsed confirmations |
| Contested entry with contested_by_task=None | Edge case from manual/legacy | AC2 edge clause | Yes | Treated as initial confirmation |

### Design Diverge
- Trigger: skipped — single valid approach (follow resolve()/approve() pattern with optional OCC per research recommendation), no competing criteria

### Challenge Results
- Challenger: reconsider (confidence 0.58)
- Issues raised: (1) AC3/AC4 ordering ambiguity, (2) call-ordinal wording vs state-based, (3) cross-package verification gap, (4) missing task_id validation
- Architect response: ACCEPTED all 4 — refined all AC lines to state-based preconditions, clarified OCC evaluation order, added dual-package scope to domain section, added task_id validation requirement. Confidence in refined AC: 0.91

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined all 4 AC lines (state-based wording, ConcurrencyError, OCC ordering, task_id validation, dual-package scope, contested_by_task=None edge case). Updated Domain section. Advanced to todo.

[[2026-05-25T02:46:48+02:00]]
## Test-Writer Notes
- Test file: tests/test_confirmation_cycle_1845.py
- Classes: TestFromAC_ConfirmationCycle
- Tests per category: happy 9, edge 2, error 7, boundary 4
- Total: 22 tests, all FAIL
- ruff: clean

AC coverage:
| AC | Tests |
|----|-------|
| AC1 — field in both packages (default None) | test_owlbear_memory_entry_has_contested_by_task_default_none, test_owlbear_mcp_memory_entry_has_contested_by_task_default_none |
| AC1 — frontmatter serialization roundtrip | test_contested_by_task_survives_storage_roundtrip_owlbear_memory, test_contested_by_task_survives_storage_roundtrip_owlbear_mcp_memory |
| AC1 — approved/curated → contested + contested_by_task stored | test_approved_entry_transitions_to_contested, test_curated_entry_transitions_to_contested, test_contested_by_task_stored_on_initial_call |
| AC1 — contested entry remains in recall | test_contested_entry_remains_in_recall_results |
| AC1 — empty/whitespace task_id raises ValidationError | test_empty_task_id_raises_validation_error, test_whitespace_task_id_raises_validation_error |
| AC2 — different task → disputed | test_different_task_id_on_contested_transitions_to_disputed |
| AC2 edge — contested_by_task=None treated as initial | test_contested_with_none_contested_by_task_treated_as_initial_confirmation |
| AC3 — same task_id → no mutation | test_same_task_id_on_contested_returns_entry_unchanged |
| AC3 — non-voteable states raise TransitionError | test_pending_state_raises_transition_error, test_disputed_state_raises_transition_error, test_stale_state_raises_transition_error, test_deleted_state_raises_transition_error |
| AC4 — OCC mismatch raises ConcurrencyError without mutation | test_occ_mismatch_raises_concurrency_error, test_occ_mismatch_does_not_mutate_entry |
| AC4 — None skips OCC check | test_occ_none_skips_check_and_proceeds |
| AC4 — matching OCC proceeds | test_occ_match_allows_transition |
| AC4 + AC3 — OCC evaluated before state guard | test_occ_evaluated_before_state_guard |

Failure modes: AttributeError ('MemoryEngine' has no attribute 'record_factually_wrong'), AttributeError ('MemoryEntry' has no attribute 'contested_by_task'), ValidationError (extra_forbidden for contested_by_task field not yet in model).

[[2026-05-25T03:29:52+02:00]]
## Builder Notes
- Implementation: added `contested_by_task: str | None = None` to both duplicated `MemoryEntry` models, added frontmatter serialization for `contested_by_task` in both storage engines, and implemented `MemoryEngine.record_factually_wrong(entry_id, task_id, expected_updated_at=None)` in `serve/memory`.
- Files changed:
  - `serve/memory/src/owlbear_memory/models.py`
  - `serve/memory/src/owlbear_memory/storage.py`
  - `serve/memory/src/owlbear_memory/engine.py`
  - `serve/mcp-memory/src/owlbear_mcp_memory/models.py`
  - `serve/mcp-memory/src/owlbear_mcp_memory/engine.py`
- AC behavior implemented:
  - Empty/whitespace `task_id` raises `ValidationError`.
  - OCC (`expected_updated_at`) is evaluated first when provided; mismatch raises `ConcurrencyError` with no mutation.
  - `approved|curated -> contested` with `contested_by_task=task_id`.
  - `contested` + same `task_id` is no-op (returns unchanged entry).
  - `contested` + different `task_id` transitions to `disputed`.
  - `contested` + `contested_by_task=None` treated as initial confirmation (`contested`, stores `task_id`).
  - Non-voteable states raise `TransitionError`.
- Test results (quality-runner, scoped): 22 passed / 0 failed (`tests/test_confirmation_cycle_1845.py`).
- ruff (quality-runner scoped lint): clean.
- Coverage (quality-runner scoped run): reported overall 31% for selected package set in this scoped gate.
- Module-level durable test file check for `confirmation_cycle`: none found (`tests/test_confirmation_cycle.py` absent), skipped per workflow.
- Commit: `adde92bd` with only the 5 source files above.

[[2026-05-25T04:18:58+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1845 -> todo | AC4 ordering proof is incomplete for the invalid `task_id` branch.
- Builder evidence reviewed first: scoped quality-runner run reported 22 passed / 0 failed for `tests/test_confirmation_cycle_1845.py`, scoped ruff clean, and implementation summary matched the changed source files.
- Challenger cross-check: upheld FAIL -> todo on proof-sufficiency grounds (confidence 0.84); no stronger implementation defect found.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC3 + AC4 | The test suite does not prove the architect-refined ordering clause that all AC1-AC3 logic runs after the OCC guard. Current tests prove OCC beats the state guard, but no test combines OCC mismatch with empty/whitespace `task_id`, so an implementation that validates `task_id` before `_validate_occ()` would still pass. | AC wording in task frontmatter (`All AC1–AC3 logic is evaluated after the OCC guard in AC4`); code currently orders OCC before validation in `serve/memory/src/owlbear_memory/engine.py:238-245`; tests only cover invalid `task_id` in `tests/test_confirmation_cycle_1845.py:219-231` and OCC/state ordering in `tests/test_confirmation_cycle_1845.py:299-344` | todo |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Add a test that calls `record_factually_wrong()` with both an OCC mismatch and an empty/whitespace `task_id`, and assert `ConcurrencyError` wins before `ValidationError`. | tests/test_confirmation_cycle_1845.py | AC3/AC4 ordering clause; current split coverage at `tests/test_confirmation_cycle_1845.py:219-231` and `tests/test_confirmation_cycle_1845.py:299-344` |

## Observations
- AC1 and AC2 implementation evidence is otherwise coherent: `contested_by_task` exists in both models and both write paths (`serve/memory/src/owlbear_memory/models.py:38-58`, `serve/memory/src/owlbear_memory/storage.py:70-84`, `serve/mcp-memory/src/owlbear_mcp_memory/models.py:48-62`, `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:96-107`), and `record_factually_wrong()` matches the expected state transitions in `serve/memory/src/owlbear_memory/engine.py:231-272`.
- Recall semantics are already proven by durable tests outside this task-local file: contested inclusion and disputed exclusion are covered in `tests/test_memory_state_machine_1840.py:357-425`, with an additional disputed-exclusion regression in `tests/test_recall_slots_1843.py:1022-1077`. The blocking issue is therefore narrow proof coverage for AC4 ordering, not a broader recall defect.
- Adjacent non-blocking note: `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:89-120` still omits `contested_by_task` from `_entry_to_dict()`. I did not treat that as blocking because #1845 AC requires duplicated models plus frontmatter serialization, and current public tool/docs expectations do not yet require that field in dict responses.

[[2026-05-25T04:29:50+02:00]]
## Test-Writer Notes
- Retry: added 2 tests for reviewer gap (AC3+AC4 ordering clause: OCC mismatch beats ValidationError for empty/whitespace task_id).
- New tests: `test_occ_mismatch_beats_empty_task_id_validation`, `test_occ_mismatch_beats_whitespace_task_id_validation`.
- All 24 tests pass against current implementation (implementation already orders OCC before task_id validation at engine.py:238-245).
- Builder skip: test-only retry, all tests green.
- ruff: clean.

[[2026-05-25T05:01:44+02:00]]
## Review Evidence
- Verdict: FAIL
- FAIL #1845 -> backlog | AC1 approved->contested handling leaves `approved_at` semantics inconsistent, and the retry proof would not catch it.
- Builder evidence reviewed first: the original builder packet provided scoped quality-runner proof (22 passed / 0 failed in `tests/test_confirmation_cycle_1845.py`, scoped ruff clean, implementation summary for 5 source files). The retry note then added two AC3/AC4 ordering tests and reported 24 task-local tests green with builder skip.
- Challenger cross-check: reconsider on the approved-entry downgrade path (confidence 0.67). I agree the prior OCC-ordering blocker is closed, but one blocking issue remains.

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC1 | The new approved->contested branch preserves `approved_at`, creating an ambiguous downgraded state and diverging from the established downgrade contract that clears approval timestamps when leaving `approved`. | AC1 requires approved entries to transition to `contested`; `record_factually_wrong()` updates only `state`, `contested_by_task`, and `updated_at` in `serve/memory/src/owlbear_memory/engine.py:247-255`; existing downgrade logic explicitly clears `approved_at` in `serve/memory/src/owlbear_memory/engine.py:192-193`, with proof in `tests/test_memory_engine_1668.py:185-197`; published field semantics say `approved_at` is "Set on approve, cleared on downgrade/delete" in `serve/mcp-memory/README.md:89`. | backlog |
| 2 | AC1 | The retry suite would not catch that regression because every approved fixture in #1845 defaults `approved_at` to `None`, so the happy-path tests prove state change but not approval-metadata correctness for realistic approved entries. | Approved fixtures default `approved_at` to `None` in `tests/test_confirmation_cycle_1845.py:56` and `tests/test_confirmation_cycle_1845.py:78`; approved-path tests only assert state / `contested_by_task` in `tests/test_confirmation_cycle_1845.py:190-209`. | backlog |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Clarify the approved-entry downgrade contract for `record_factually_wrong()` and reissue the task so approved->contested behavior is explicit about `approved_at` alignment with existing downgrade semantics. | serve/memory/src/owlbear_memory/engine.py, tests/test_confirmation_cycle_1845.py, serve/mcp-memory/README.md | Finding #1; `serve/memory/src/owlbear_memory/engine.py:247-255`, `serve/memory/src/owlbear_memory/engine.py:192-193`, `tests/test_memory_engine_1668.py:185-197`, `serve/mcp-memory/README.md:89` |
| 2 | architect | Require proof with an approved fixture that has non-null `approved_at`, so the chosen contract is executable and cannot false-green on a downgraded approved entry. | tests/test_confirmation_cycle_1845.py | Finding #2; `tests/test_confirmation_cycle_1845.py:56`, `tests/test_confirmation_cycle_1845.py:78`, `tests/test_confirmation_cycle_1845.py:190-209` |

## Observations
- The prior AC3/AC4 ordering blocker is fixed: new tests in `tests/test_confirmation_cycle_1845.py:345-362` now prove OCC mismatch beats empty/whitespace `task_id` validation, matching code order in `serve/memory/src/owlbear_memory/engine.py:240-243`.
- AC1 field duplication/frontmatter sync is otherwise coherent across `serve/memory/src/owlbear_memory/models.py:58`, `serve/memory/src/owlbear_memory/storage.py:84`, `serve/mcp-memory/src/owlbear_mcp_memory/models.py:62`, and `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:107`.
- Recall-state proof is composite but adequate: `tests/test_confirmation_cycle_1845.py:211-216` covers the contested transition surface, and durable recall tests at `tests/test_memory_state_machine_1840.py:357-383` still verify contested inclusion and disputed exclusion on the actual recall API.
- Adjacent non-blocking note: `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:89-105` still omits `contested_by_task` from dict serialization, but #1845 AC is limited to duplicated models, frontmatter serialization, and `record_factually_wrong()` behavior.

[[2026-05-25T05:09:55+02:00]]
## Architecture Review (re-review after FAIL)
### Evaluation
Re-review scope limited to reviewer findings — prior full evaluation (all 13 criteria PASS) remains valid.

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Interface clarity | PASS (refined) | AC1 now explicitly requires `approved_at` clearing on approved->contested, matching documented downgrade contract (`serve/mcp-memory/README.md:89`) and existing `edit()` behavior (`engine.py:192-193`, proved by `tests/test_memory_engine_1668.py:185-197`) |
| Pattern consistency | PASS (refined) | AC1 fixture requirement ensures approved-path tests use non-null `approved_at`, preventing false-green on downgrade verification |

### Reviewer Findings Addressed
| # | Finding | Resolution |
|---|---------|------------|
| 1 | `approved_at` preserved on approved->contested violates downgrade contract | AC1 refined: explicitly requires `approved_at` cleared to None |
| 2 | Test fixtures default `approved_at=None` masking the bug | AC1 refined: approved fixtures MUST have non-null `approved_at` and assert it is cleared |

### Proof-Bundle Validation
- Planner assignment: behavioral
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

### Challenge Results
- Challenger: SKIPPED — re-review of narrow refinement (prior challenge accepted all structural issues; new finding is a contract alignment fix with documented evidence)

### Verdict: APPROVE
### Action Taken: Refined AC1 to require `approved_at` clearing on downgrade and non-null fixtures. Advanced to todo.

[[2026-05-25T05:19:28+02:00]]
## Test-Writer Notes
- Retry: added 2 tests for reviewer gap (AC1 approved_at clearing contract with non-null fixture).
- New tests: `test_approved_entry_clears_approved_at_on_contested_transition`, `test_approved_at_cleared_persisted_after_contested_transition`.
- Added constant `_TS_APPROVED = "2026-05-20T08:00:00+00:00"` for non-null approved_at fixtures.
- Both new tests FAIL: AssertionError: assert '2026-05-20T08:00:00+00:00' is None (implementation does not clear approved_at).
- 24 existing tests PASS unchanged.
- ruff: clean.

[[2026-05-25T05:30:00+02:00]]
## Builder Notes
- Implementation: updated `serve/memory/src/owlbear_memory/engine.py` in `record_factually_wrong()` to clear `approved_at` when transitioning `approved|curated -> contested`.
- Files changed: `serve/memory/src/owlbear_memory/engine.py` (single-line behavioral fix).
- RED verification (quality-runner): `tests/test_confirmation_cycle_1845.py` had 24 passed / 2 failed before fix.
  - Failing tests: `test_approved_entry_clears_approved_at_on_contested_transition`, `test_approved_at_cleared_persisted_after_contested_transition`.
- GREEN verification (quality-runner): `tests/test_confirmation_cycle_1845.py` => 26 passed / 0 failed, lint clean.
- Additional scoped regression and coverage verification (quality-runner):
  - Test paths: `tests/test_confirmation_cycle_1845.py`, `tests/test_memory_engine_1668.py`, `tests/test_memory_state_machine_1840.py`, `tests/test_slot_efficiency_1844.py`, `tests/test_memory_migration_1842.py`
  - Result: 180 passed / 0 failed
  - Coverage: 96% on `owlbear_memory.engine`
  - Lint: clean
- Durable module-level note: `tests/test_confirmation_cycle.py` does not exist (legacy naming in this repo); used durable adjacent engine/state/migration suites for regression signal.
- Approach: minimal surgical change to align approved->contested downgrade path with AC1 and existing downgrade contract semantics while preserving all existing transition/OCC behavior.
- Commit: `6c3474ce` (`fix: clear approved_at on factually-wrong downgrade (#1845, builder)`).

[[2026-05-25T05:39:03+02:00]]
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1845 -> docs | AC mapped to code and evidence sufficient.
- Builder evidence reviewed first: quality-runner reported `26 passed / 0 failed` for `tests/test_confirmation_cycle_1845.py`, scoped lint clean, plus adjacent regression proof of `180 passed / 0 failed` with `96%` coverage on `owlbear_memory.engine`.
- Challenger cross-check: `proceed` with confidence `0.83`; no remaining blocking findings identified.
- AC evidence map:

| AC | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC1 | `serve/memory/src/owlbear_memory/models.py:58`, `serve/mcp-memory/src/owlbear_mcp_memory/models.py:62`, `serve/memory/src/owlbear_memory/storage.py:84`, `serve/mcp-memory/src/owlbear_mcp_memory/engine.py:107`, `serve/memory/src/owlbear_memory/engine.py:244-252` | `tests/test_confirmation_cycle_1845.py:116`, `tests/test_confirmation_cycle_1845.py:130`, `tests/test_confirmation_cycle_1845.py:144`, `tests/test_confirmation_cycle_1845.py:151`, `tests/test_confirmation_cycle_1845.py:181`, `tests/test_confirmation_cycle_1845.py:188`, `tests/test_confirmation_cycle_1845.py:195`, `tests/test_confirmation_cycle_1845.py:212`, `tests/test_confirmation_cycle_1845.py:220`, `tests/test_confirmation_cycle_1845.py:230`, `tests/test_confirmation_cycle_1845.py:239`, `tests/test_confirmation_cycle_1845.py:246`, plus durable recall proof at `tests/test_memory_state_machine_1840.py:357` | PASS |
| AC2 | `serve/memory/src/owlbear_memory/engine.py:258-268` | `tests/test_confirmation_cycle_1845.py:256`, `tests/test_confirmation_cycle_1845.py:263`, plus disputed recall exclusion at `tests/test_memory_state_machine_1840.py:370` | PASS |
| AC3 | `serve/memory/src/owlbear_memory/engine.py:241-272` | `tests/test_confirmation_cycle_1845.py:277`, `tests/test_confirmation_cycle_1845.py:286`, `tests/test_confirmation_cycle_1845.py:293`, `tests/test_confirmation_cycle_1845.py:300`, `tests/test_confirmation_cycle_1845.py:307`, `tests/test_confirmation_cycle_1845.py:354`, `tests/test_confirmation_cycle_1845.py:364`, `tests/test_confirmation_cycle_1845.py:374` | PASS |
| AC4 | `serve/memory/src/owlbear_memory/engine.py:241-244` | `tests/test_confirmation_cycle_1845.py:318`, `tests/test_confirmation_cycle_1845.py:327`, `tests/test_confirmation_cycle_1845.py:338`, `tests/test_confirmation_cycle_1845.py:345`, `tests/test_confirmation_cycle_1845.py:354`, `tests/test_confirmation_cycle_1845.py:364`, `tests/test_confirmation_cycle_1845.py:374` | PASS |
- Current editor diagnostics on the touched source and task-local test file: no errors found.

## Observations
- Non-blocking: `serve/mcp-memory/src/owlbear_mcp_memory/tools.py:89-105` still omits `contested_by_task` from `_entry_to_dict()`. I did not treat this as blocking because AC1 is scoped to duplicated models, frontmatter serialization, and `record_factually_wrong()` behavior, and the builder evidence fully covers that contract.
- Review scope was reconstructed from builder notes and direct file inspection. Shell-level `git diff` / `git status` checks were not available in this tool environment.

[[2026-05-25T05:44:13+02:00]]
## Docs Gate

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | FIXED | `serve/memory/README.md` and `serve/mcp-memory/README.md` both missing `contested_by_task` field, `record_factually_wrong` method, state machine transitions, and OCC note — all task-caused gaps. Updated inline. |
| 2. External Attribution | N/A | Builder notes cite codebase-only sources; no external attribution needed. |
| 3. Research Doc | PASS | `.owlbear/research/memory-confirmation-cycle-factually-wrong.md` referenced in task body under `## Research`. |
| 4. Deletion Detection | N/A | No symbols removed; new field and method added only. |

### Files Updated

- `serve/memory/README.md`: added `contested_by_task` to MemoryEntry table; added `record_factually_wrong` to engine method table; added 4 state machine rows (approved→contested, curated→contested, contested same-task no-op, contested different-task→disputed); updated OCC paragraph to cover optional `expected_updated_at`.
- `serve/mcp-memory/README.md`: added `contested_by_task` to Entry Schema table.

Commit: `552e7b68`

### Scratch Cleanup
No scratch files created for this task.

### Verdict
DONE #1845 -> done | docs gate passed
