---
id: 1845
title: 'P2-06: Confirmation cycle — factually-wrong to contested/disputed'
status: review
priority: needed
created: 2026-05-24T19:01:24.983062+02:00
updated: 2026-05-25T04:29:50.644661+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on:
  - 1840
  - 1841
ac:
  - 'AC1: `MemoryEntry` has `contested_by_task: str | None` (default None) field in
    both `owlbear_memory` and `owlbear_mcp_memory` packages (frontmatter-serialized).
    Engine method `record_factually_wrong(entry_id: str, task_id: str, expected_updated_at:
    str | None = None)` raises `ValidationError` if `task_id` is empty/whitespace.
    When entry state ∈ {approved, curated}: sets state to `contested` and stores `contested_by_task
    = task_id`. Entry remains in recall results.'
  - 'AC2: When entry state is `contested` and `contested_by_task` is a non-None value
    ≠ `task_id`: transitions state to `disputed` (excluded from recall). Edge case:
    `contested` with `contested_by_task = None` is treated as initial confirmation
    (stores `task_id`, remains `contested`).'
  - 'AC3: When entry state is `contested` and `contested_by_task == task_id`: returns
    entry unchanged (no mutation, no error). Calls on entries not in voteable states
    ({approved, curated, contested}) raise `TransitionError`. All AC1–AC3 logic is
    evaluated after the OCC guard in AC4.'
  - "AC4: `expected_updated_at` is a CAS guard: if non-None and does not match the
    entry's current `updated_at`, raise `ConcurrencyError` without mutating. If None,
    the check is skipped (unconditional write)."
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
