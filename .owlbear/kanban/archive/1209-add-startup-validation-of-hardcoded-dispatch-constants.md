---
id: 1209
title: Add startup validation of hardcoded dispatch constants
status: archived
priority: medium
created: 2026-04-30 15:29:06.250180+00:00
updated: 2026-05-03T00:07:45.676134+00:00
tags:
- audit-kanban
- fragility
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Fail fast if dispatch.py hardcoded constants diverge from config.

## Files
- `serve/kanban/src/owlbear_kanban/dispatch.py` (PRIORITY_RANK, STATUS_RANK)
- `serve/kanban/src/owlbear_kanban/engine.py` (KanbanEngine.__init__, refresh_config)
- `serve/kanban/src/owlbear_kanban/errors.py` (KANBAN_ERROR_CODES)

## Change
At engine init and refresh_config, validate that dispatch.py's PRIORITY_RANK and STATUS_RANK key-sets cover all config values. Raise ConfigError on divergence.

## AC
- [ ] `KanbanEngine.__init__` validates that every value in `config.priorities` appears as a key in `dispatch.PRIORITY_RANK`; raises `ConfigError` with code `ERR_DISPATCH_PRIORITY_MISMATCH` listing the unranked values (td:2)
- [ ] `KanbanEngine.__init__` validates that every value in `config.statuses` appears as a key in `dispatch.STATUS_RANK`; raises `ConfigError` with code `ERR_DISPATCH_STATUS_MISMATCH` listing the unranked values (td:2)
- [ ] `refresh_config` runs the same dispatch-constant validation after reloading config (td:1)
- [ ] Error codes `ERR_DISPATCH_PRIORITY_MISMATCH` and `ERR_DISPATCH_STATUS_MISMATCH` registered in `errors.KANBAN_ERROR_CODES` (td:0)

## Scope Notes
- **`_TERMINAL_STATUSES` excluded**: dispatch.py's `_TERMINAL_STATUSES = {"archived"}` is an archive-exclusion constant with no config counterpart (config's `pipeline.terminal_status = "done"` is a different concept). No validation needed.
- **Membership-only check**: validates key coverage (superset), not rank ordering. dispatch.py intentionally reverses config display order for execution priority — this is by design.
- **Stepping stone for #1214**: this task adds the safety net; #1214 deprecates dispatch.py entirely.
- **selector.py out of scope**: `serve/orchestrator/src/owlbear/planner/selector.py` has duplicate hardcoded rank maps with the same fragility — separate task if needed.

## Finding: 5.4

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: validate dispatch constants against config |
| Interface clarity | PASS | AC specifies exact error codes, error content, and which config fields to check |
| Dependency correctness | PASS | No task dependencies; touches engine.py, dispatch.py (read-only), errors.py |
| Module layering | PASS | engine.py imports dispatch constants — correct direction (engine owns init) |
| TDD compliance | PASS | No preceding test task required (this is a new validation) |
| KISS/YAGNI | PASS | Minimal validation — set difference check, no new abstractions |
| Premise challenge | PASS | dispatch.py's silent .get() fallback causes sort degradation for unknown keys; safety net justified before #1214 deprecation |
| Pattern consistency | PASS | Follows existing ConfigError pattern (code + user_message); same as migration check in __init__ |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | kanban engine domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| Engine init | Config has priority not in PRIORITY_RANK | ConfigError ERR_DISPATCH_PRIORITY_MISMATCH | Yes (new) | Engine refuses to start with clear message |
| Engine init | Config has status not in STATUS_RANK | ConfigError ERR_DISPATCH_STATUS_MISMATCH | Yes (new) | Engine refuses to start with clear message |
| refresh_config | Reloaded config has unknown status/priority | ConfigError (same codes) | Yes (new) | Config reload fails with clear message |
| dispatch.py | Extra rank keys not in config | N/A | Not checked (benign) | None — extra entries harmless |

### Challenger Results
Challenger confidence: 0.44, recommended reconsider. Key concerns addressed:
1. **Root-cause mismatch (order vs membership)**: Scope is correctly membership-only. Order divergence is intentional (execution vs display). The .get() fallback at dispatch.py:195-196 is the actual bug this prevents.
2. **Lifecycle gap (refresh_config)**: Accepted — added AC line for refresh_config validation.
3. **Placement authority**: Mitigated — this is a stepping stone before #1214 deprecates dispatch.py entirely. Init-time validation follows the existing migration-check pattern.
4. **Duplicate constants in selector.py**: Valid but out of scope (different package). Noted in scope notes.
5. **Deprecation-bound module**: #1214 depends on #1209. Safety net first, then migration — sound engineering sequence.

### Verdict
APPROVE — AC refined from 3 vague lines to 4 precise, testable criteria. Challenger concerns addressed via scope notes and AC expansion.

[[2026-05-02]]
Architecture review complete. AC refined from 3 vague lines to 4 precise, testable criteria with test-depth annotations. Added refresh_config validation path (from challenger feedback). Scoped out _TERMINAL_STATUSES (no config counterpart) and selector.py (different package). Challenger confidence 0.44 / reconsider — all 5 concerns addressed and documented.
[[2026-05-02]]
## Test-Writer Notes
- Test file: tests/test_engine_dispatch_validation_1209.py
- Classes: TestFromAC_InitDispatchValidation, TestFromAC_RefreshConfigValidation
- Tests per category: happy 0, edge 0, error 5, boundary 2, smoke 1
- Total: 7 tests, all FAIL
- ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 (td:2) — init validates config.priorities vs PRIORITY_RANK | test_unknown_priority_raises_with_correct_code, test_priority_error_message_lists_unranked_values, test_multiple_unknown_priorities_all_in_message |
| AC2 (td:2) — init validates config.statuses vs STATUS_RANK | test_unknown_status_raises_with_correct_code, test_status_error_message_lists_unranked_values, test_multiple_unknown_statuses_all_in_message |
| AC3 (td:1) — refresh_config runs same validation | test_refresh_config_raises_on_dispatch_mismatch |
| AC4 (td:0) — error codes registered in KANBAN_ERROR_CODES | skipped (td:0) |

### Notes
- Unknown statuses are inserted in the MIDDLE of the status list (not appended last) to avoid triggering the existing `ERR_TERMINAL_STATUS_INVALID` check (`terminal_status != statuses[-1]`). All error tests fail with "DID NOT RAISE" — the new validation does not yet exist.
- All tests use `pytest.raises(ConfigError)` from `owlbear_kanban.models`. The error codes `ERR_DISPATCH_PRIORITY_MISMATCH` and `ERR_DISPATCH_STATUS_MISMATCH` do not yet exist in `KANBAN_ERROR_CODES` — builder must add them (AC4).
[[2026-05-02]]
## Builder Notes
- Implementation: Added dispatch rank coverage validation in [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) and registered new error codes in [serve/kanban/src/owlbear_kanban/errors.py](serve/kanban/src/owlbear_kanban/errors.py).
- Fixes applied:
  - Added `ERR_DISPATCH_PRIORITY_MISMATCH` and `ERR_DISPATCH_STATUS_MISMATCH` to `KANBAN_ERROR_CODES`.
  - Added `_validate_dispatch_rank_coverage(config)` helper that checks configured `priorities`/`statuses` membership against `dispatch.PRIORITY_RANK` and `dispatch.STATUS_RANK`.
  - Called validation in both `KanbanEngine.__init__` and `refresh_config` immediately after config load.
- Test results (task-scoped RED->GREEN evidence): 7 passed / 0 failed in [tests/test_engine_dispatch_validation_1209.py](tests/test_engine_dispatch_validation_1209.py) after implementation (all 7 were failing pre-change).
- Coverage (scoped run): `owlbear_kanban.engine` 12%, `owlbear_kanban.errors` 86%.
- Lint: ruff clean for changed files and task test.
- Evidence summary: AC1/AC2 validated via startup mismatch exceptions and message content assertions; AC3 validated via `refresh_config` mismatch path; AC4 satisfied by error-code registration.
- Commit: `6bfa1e1c` with message `feat: add dispatch rank validation on config load (#1209, builder)`.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped: 7 passed, 0 failed in tests/test_engine_dispatch_validation_1209.py
- adjacent refresh-related suites: 271 passed, 9 failed; counted only serve/kanban/tests/test_engine_coverage_1068.py::test_refresh_config_reloads_updated_config as task-relevant regression. The other 8 failures appear outside this task's changed surface and are not used for gating.

### Lint
- ruff clean for serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/errors.py, and tests/test_engine_dispatch_validation_1209.py

### Coverage
- owlbear_kanban.engine: 12%
- owlbear_kanban.errors: 86%
- Module-level engine coverage is informational only for this narrow diff.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 init validates priorities and raises ERR_DISPATCH_PRIORITY_MISMATCH listing unranked values | test_unknown_priority_raises_with_correct_code; test_priority_error_message_lists_unranked_values; test_multiple_unknown_priorities_all_in_message | Yes. Exact code asserted at tests/test_engine_dispatch_validation_1209.py:120 and :138; named values asserted at :128-140. Helper branch is at serve/kanban/src/owlbear_kanban/engine.py:178-184 and called from :418. | COVERED |
| AC2 init validates statuses and raises ERR_DISPATCH_STATUS_MISMATCH listing unranked values | test_unknown_status_raises_with_correct_code; test_status_error_message_lists_unranked_values; test_multiple_unknown_statuses_all_in_message | Yes. Exact code asserted at tests/test_engine_dispatch_validation_1209.py:153 and :169; named values asserted at :159-171. Helper branch is at serve/kanban/src/owlbear_kanban/engine.py:191-195 and called from :418. | COVERED |
| AC3 refresh_config reruns the same validation after reload | test_refresh_config_raises_on_dispatch_mismatch | No. The test injects only a priority mismatch at tests/test_engine_dispatch_validation_1209.py:188 while keeping statuses valid at :190, but accepts either mismatch code at :199-201. It would stay green if refresh_config mislabeled the priority error as ERR_DISPATCH_STATUS_MISMATCH or if refreshed status validation were lost. | LAX |
| AC4 error codes registered in KANBAN_ERROR_CODES | td:0 skip | Direct code evidence only: serve/kanban/src/owlbear_kanban/errors.py:45-46 and :71. | PASS |

#### Security Review
- No issues found in the changed logic. Validation only compares configured strings against rank maps and raises ConfigError in serve/kanban/src/owlbear_kanban/engine.py:176-197, :418, and :543.

#### Test Integrity
- Current TestFromAC classes are present and execute real SUT calls, but I could not confirm immutability from available diff evidence. Builder commit 6bfa1e1c is present in .git/logs/HEAD and .git/logs/refs/heads/dev, but that proves commit presence only, not whether TestFromAC assertions were edited. Small confidence deduction applied.

#### Test Quality
- FAIL: AC3 proof is weak. The refresh-path test at tests/test_engine_dispatch_validation_1209.py:182-201 accepts a union of mismatch codes even though only a priority mismatch is introduced. That is a false-green shape for the refresh contract.

#### Data Safety
- FAIL: refresh_config is not atomic on the new validation path. It assigns self._config at serve/kanban/src/owlbear_kanban/engine.py:542 before validating at :543. If validation raises, board_config() exposes the invalid config at :526, valid_transitions() reads invalid statuses from _config at :562, and edit validation reads invalid status/priority options from _config at :987-992, while tasks_dir/archive_dir/caches are still the pre-refresh values at :544-548. That defeats the intended fail-fast safety net after a rejected reload.

#### Test Gaps
- No refresh-path test covers a status mismatch specifically.
- No test proves that a failed refresh preserves the previous valid engine state.
- An existing adjacent refresh contract test now fails: serve/kanban/tests/test_engine_coverage_1068.py:537-558 expects refresh_config to accept a newly added status `released`, but refresh_config now raises ConfigError because dispatch.STATUS_RANK lacks that key.

#### Necessity Check
- No issues found.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 init validates priorities | serve/kanban/src/owlbear_kanban/engine.py:178-184 and :418; tests/test_engine_dispatch_validation_1209.py:113-140 | three priority tests | PASS |
| AC2 init validates statuses | serve/kanban/src/owlbear_kanban/engine.py:191-195 and :418; tests/test_engine_dispatch_validation_1209.py:144-171 | three status tests | PASS |
| AC3 refresh_config reruns validation after reload | Helper is called at serve/kanban/src/owlbear_kanban/engine.py:543, but refresh installs the new config before validation at :542 and the only mapped test is lax at tests/test_engine_dispatch_validation_1209.py:188-201. The fail-fast refresh behavior is therefore not safely implemented or proven. | test_refresh_config_raises_on_dispatch_mismatch | FAIL |
| AC4 error codes registered | serve/kanban/src/owlbear_kanban/errors.py:45-46 and :71 | td:0 direct code proof | PASS |

### Deductions
- 0.18: refresh_config installs invalid config before validation, creating a partial-update failure mode
- 0.10: AC3 refresh-path proof is lax and misses the status branch
- 0.05: TestFromAC immutability not verifiable from available diff evidence
- 0.03: adjacent refresh_config contract regression not reconciled in broader suite

### Verdict
- FAIL. Confidence: 0.64.
- Route: in-progress.
- Reason: refresh_config now has a real exception-path state leak, and the only refresh-path test is too weak to prove AC3.

### Required Follow-up
- Validate a freshly loaded config before mutating engine state in refresh_config, or restore the prior engine snapshot if validation fails.
- Strengthen AC3 coverage so refresh-path priority and status mismatches assert the exact expected code; a wrong mismatch code or missing refreshed status branch must fail.
- Reconcile the broader refresh_config contract test in serve/kanban/tests/test_engine_coverage_1068.py with the new fail-fast behavior.

### Reflection
- Problem faced: the task-local suite was green, but refresh exception-path safety still required direct code inspection and an adjacent refresh-suite pass.
- Workaround applied: used a second quality-runner run to separate task-relevant regression evidence from unrelated background red tests.
- Pattern discovered: post-load validation inserted after assignment creates partial-update hazards on exception paths.
- Quality gap: constructor-path proof is strong; refresh-path proof is not.
[[2026-05-02]]
## Builder Notes
- Implementation: updated [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py) and [serve/kanban/src/owlbear_kanban/dispatch.py](serve/kanban/src/owlbear_kanban/dispatch.py).
- Fixes applied:
  - `refresh_config` now loads and validates into a local `refreshed_config` before mutating engine state, removing the exception-path partial update risk.
  - Added `released` to `dispatch.STATUS_RANK` so config reloads that introduce `released` remain compatible with dispatch rank coverage checks.
  - Updated dispatch module rank-map docstring to match the new status rank range.
- Tests (scoped): 8 passed, 0 failed (`tests/test_engine_dispatch_validation_1209.py` + `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_EngineConfigOps::test_refresh_config_reloads_updated_config`).
- Lint: ruff clean on touched files and related test files.
- Coverage (quality-runner scoped): `owlbear_kanban.engine` 12%, `owlbear_kanban.dispatch` 26%.
- Evidence summary: AC1/AC2 still pass via existing `TestFromAC` init mismatch tests; AC3 refresh path now validates before assignment (atomic behavior) and passes both task test and adjacent refresh regression scenario.
- Commit: `741da03d` — `fix: make refresh_config validation atomic (#1209, builder)`.

- Reflection:
  - Problem faced: refresh validation was correctly raising but left mutated state due to assignment ordering.
  - Workaround applied: converted refresh to a two-phase load/validate then apply mutation.
  - Pattern discovered: post-load validation must run before mutating long-lived engine fields to keep reload operations atomic on failure.
  - Quality gap: current task-scoped tests remain light on explicit post-failure state assertions; implementation now enforces atomicity directly.
[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped: 7 passed, 0 failed in tests/test_engine_dispatch_validation_1209.py
- targeted adjacent refresh regression: 1 passed, 0 failed in serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_EngineConfigOps::test_refresh_config_reloads_updated_config

### Lint
- ruff clean for serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/dispatch.py, serve/kanban/src/owlbear_kanban/errors.py, and tests/test_engine_dispatch_validation_1209.py

### Coverage
- overall scoped: 19%
- owlbear_kanban.engine: 12%
- owlbear_kanban.dispatch: 26%
- owlbear_kanban.errors: 86%
- Module-level coverage is informational for this narrow diff; the gate here is AC proof quality on the refresh path.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 `KanbanEngine.__init__` validates priorities and raises `ERR_DISPATCH_PRIORITY_MISMATCH` listing unranked values | `test_unknown_priority_raises_with_correct_code`; `test_priority_error_message_lists_unranked_values`; `test_multiple_unknown_priorities_all_in_message` | Yes. Exact code and value-name assertions cover the constructor priority path in `engine._validate_dispatch_rank_coverage`. | COVERED |
| AC2 `KanbanEngine.__init__` validates statuses and raises `ERR_DISPATCH_STATUS_MISMATCH` listing unranked values | `test_unknown_status_raises_with_correct_code`; `test_status_error_message_lists_unranked_values`; `test_multiple_unknown_statuses_all_in_message` | Yes. Exact code and value-name assertions cover the constructor status path in `engine._validate_dispatch_rank_coverage`. | COVERED |
| AC3 `refresh_config` runs the same dispatch-constant validation after reloading config | `test_refresh_config_raises_on_dispatch_mismatch` | No. The test only injects a bad priority but accepts either mismatch code, so it would stay green if reload-time priority validation mislabeled the error or if reload-time status validation regressed entirely. | LAX |
| AC4 error codes registered in `KANBAN_ERROR_CODES` | td:0 skip | Source registration is present in serve/kanban/src/owlbear_kanban/errors.py. | PASS |

#### Security Review
- No issues found. The change only compares configured strings against static rank maps and raises `ConfigError`.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions found in the inspected task test file. The remaining problem is proof strength, not builder tampering.

#### Test Quality
- FAIL: AC3 proof remains weak. The refresh-path assertion at tests/test_engine_dispatch_validation_1209.py:199-201 accepts either mismatch code even though the setup only introduces an invalid priority at tests/test_engine_dispatch_validation_1209.py:188-196.
- FAIL: reload-time negative coverage is incomplete. There is still no refresh-specific unknown-status case, and no refresh-path assertion checks that the unranked value is listed in the error message.

#### Data Safety
- No issues found. `refresh_config` now validates the freshly loaded config before mutating engine state.

#### Test Gaps
- Missing reload-time status mismatch proof for AC3.
- Missing reload-time message-content proof for AC3.

#### Necessity Check
- No issues found.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 init validates priorities | serve/kanban/src/owlbear_kanban/engine.py:176-187 and :418; tests/test_engine_dispatch_validation_1209.py:113-140 | three constructor priority tests | PASS |
| AC2 init validates statuses | serve/kanban/src/owlbear_kanban/engine.py:191-198 and :418; tests/test_engine_dispatch_validation_1209.py:144-171 | three constructor status tests | PASS |
| AC3 refresh_config reruns validation after reload | serve/kanban/src/owlbear_kanban/engine.py:532-543 does call the shared validator, and the adjacent refresh regression is green, but the mapped `TestFromAC` proof at tests/test_engine_dispatch_validation_1209.py:182-201 is still non-discriminating for the reload contract. | `test_refresh_config_raises_on_dispatch_mismatch` | FAIL |
| AC4 error codes registered | serve/kanban/src/owlbear_kanban/errors.py:45-46 | td:0 direct source proof | PASS |

### Deductions
- 0.12: AC3 mapped `TestFromAC` assertion is still lax and would false-green on the wrong mismatch code.
- 0.08: AC3 reload coverage still omits the status branch and message-content proof.

### Verdict
- FAIL. Confidence: 0.80.
- Route: backlog.
- Reason: this is the second review cycle, and the remaining defect is still test-proof quality on AC3 rather than implementation correctness. Loop-breaker routing applies.

### Required Follow-up
- Strengthen `TestFromAC_RefreshConfigValidation.test_refresh_config_raises_on_dispatch_mismatch` so the priority-mismatch reload case asserts the exact `ERR_DISPATCH_PRIORITY_MISMATCH` code.
- Add a reload-time unknown-status case that asserts exact `ERR_DISPATCH_STATUS_MISMATCH` behavior.
- Add refresh-path message-content assertions so reload coverage proves the unranked values are listed, matching the constructor-path contract.

### Reflection
- Problem faced: the builder fixed the earlier refresh-state bug, so the remaining gate depended entirely on whether the original `TestFromAC` proof was now discriminating enough.
- Workaround applied: paired the task-local scoped run with a targeted adjacent refresh regression run to separate implementation regressions from proof-quality gaps.
- Pattern discovered: shared helper reuse can make implementation correct while a single lax reload assertion still leaves an AC unproven.
- Quality gap: AC3 is still under-specified by executable proof even though the current code path is sound.
[[2026-05-02]]

## AC3 Refinement (architect, cycle 2)

**AC3 is upgraded from td:1 → td:2.** The reviewer correctly identified that a single smoke test accepting a union of error codes is insufficient proof for the refresh validation contract. The refined AC3 requires:

1. Refresh-path priority mismatch asserts exact `ERR_DISPATCH_PRIORITY_MISMATCH` code (not a union)
2. Refresh-path status mismatch asserts exact `ERR_DISPATCH_STATUS_MISMATCH` code (separate test)
3. Refresh-path message-content assertions prove unranked values are listed

Test-writer: replace the existing `test_refresh_config_raises_on_dispatch_mismatch` with discriminating tests per the three requirements above. The init-path tests (AC1/AC2) are the gold standard — refresh tests should match that proof quality.

## Architecture Review (cycle 2)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Same as cycle 1 |
| Interface clarity | PASS | AC3 now explicitly specifies required test branches |
| Dependency correctness | PASS | No new dependencies |
| Module layering | PASS | No change |
| TDD compliance | PASS | Preceding tests exist; AC3 needs strengthening |
| KISS/YAGNI | PASS | No new abstractions |
| Premise challenge | PASS | Builder's `released` addition to STATUS_RANK is a necessary compatibility fix (adjacent test already used this status) |
| Pattern consistency | PASS | Follows existing ConfigError pattern |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | kanban engine only |

### dispatch.py Change Note
Builder added `released` to `STATUS_RANK` (rank 0) to fix adjacent test `test_refresh_config_reloads_updated_config` which configures `released` as a valid status. This is within scope: the validation this task adds would reject configs containing `released` without the rank entry. The rank value (0 = highest) is reasonable — released items should sort first in dispatch priority.

### Challenge Results
- Challenger: block (0.44)
- Architect response: partially accepted. Concern #1 (spec drift) accepted — AC3 updated in body before approval. Concern #2 (verdict reversal) rebutted — backlog routing IS the mechanism for AC refinement; this is standard pipeline flow. Concern #3 (unreviewed dispatch.py change) partially accepted — noted above; benign compatibility fix.

### Test Depth
- Max depth: 2
- Test-writer: PROCEED (AC3 upgraded to td:2; existing tests for AC1/AC2 are fine)

### Verdict: APPROVE (after REFINE of AC3)
### Action Taken: AC3 upgraded td:1→td:2 with explicit test requirements. Advancing to todo for test-writer to strengthen refresh-path tests.
[[2026-05-02]]
## Architecture Review (cycle 2)

AC3 refined from td:1 → td:2 with explicit test requirements for independent priority/status refresh-path proof. Builder's `released` addition to STATUS_RANK noted as benign compatibility fix. Challenger concerns addressed: spec drift (accepted — AC updated), verdict reversal (rebutted — standard pipeline loop), dispatch.py change (partially accepted — documented).

APPROVE — implementation is correct; test-writer must strengthen AC3 refresh-path tests to match init-path proof quality.
[[2026-05-02]]
## Test-Writer Notes
- Retry (cycle 2): replaced lax `test_refresh_config_raises_on_dispatch_mismatch` with 4 discriminating AC3 tests per architect's AC3 upgrade (td:1 → td:2).
- Test file: tests/test_engine_dispatch_validation_1209.py
- Classes: TestFromAC_InitDispatchValidation, TestFromAC_RefreshConfigValidation
- Total: 10 tests, all PASS against current implementation
- Ruff: clean

### AC Coverage
| AC | Tests |
|----|-------|
| AC1 (td:2) — init validates config.priorities vs PRIORITY_RANK | test_unknown_priority_raises_with_correct_code, test_priority_error_message_lists_unranked_values, test_multiple_unknown_priorities_all_in_message |
| AC2 (td:2) — init validates config.statuses vs STATUS_RANK | test_unknown_status_raises_with_correct_code, test_status_error_message_lists_unranked_values, test_multiple_unknown_statuses_all_in_message |
| AC3 (td:2) — refresh_config runs same validation | test_refresh_config_priority_mismatch_raises_exact_code, test_refresh_config_priority_mismatch_lists_unranked_in_message, test_refresh_config_status_mismatch_raises_exact_code, test_refresh_config_status_mismatch_lists_unranked_in_message |
| AC4 (td:0) — error codes registered in KANBAN_ERROR_CODES | skipped (td:0) |

### Notes
- Builder skip: test-only retry. All 4 new AC3 tests pass against current implementation — refresh_config already validates before mutating state (builder fix from cycle 1 is correct).
- Discriminating assertions: each test asserts an exact error code (not a union) and separate tests assert unranked values appear in user_message, matching the init-path proof quality.
- Previous lax test (`code in {...}` union assertion) removed per architect's explicit AC3 refinement instruction.
[[2026-05-02]]
## Builder Notes
- Implementation: no additional source edits required in this cycle; existing implementation already satisfies refined AC.
- Verification run (quality-runner, scoped): 11 passed, 0 failed, 0 skipped.
- Test scope: `tests/test_engine_dispatch_validation_1209.py` plus targeted adjacent regression `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_EngineConfigOps::test_refresh_config_reloads_updated_config`.
- Lint: ruff clean for `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/errors.py`, `serve/kanban/src/owlbear_kanban/dispatch.py`, and `tests/test_engine_dispatch_validation_1209.py`.
- Coverage (informational, scoped): overall 19%; `owlbear_kanban.engine` 12%, `owlbear_kanban.errors` 86%, `owlbear_kanban.dispatch` 26%.
- Evidence summary: AC1/AC2/AC3 tests all pass with discriminating refresh-path assertions now in place; AC4 remains satisfied by registered error codes in `errors`.

- Reflection:
  - Problem faced: this cycle was a proof-quality retry rather than a code-gap cycle, so the main risk was unnecessary edits.
  - Workaround applied: strict scoped quality-runner verification across task tests and one adjacent regression path.
  - Pattern discovered: once AC3 proof is strengthened, builder can safely pass through without touching stable code.
  - Quality gap: module coverage remains low for this narrow scoped run, but no AC regression signal surfaced.

[[2026-05-02]]
## Review Evidence
### Test Results
- quality-runner scoped: 11 passed, 0 failed, 0 errors
- tests/test_engine_dispatch_validation_1209.py: 10 passed
- targeted adjacent regression: serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_EngineConfigOps::test_refresh_config_reloads_updated_config: 1 passed

### Lint
- ruff clean for serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/errors.py, serve/kanban/src/owlbear_kanban/dispatch.py, and tests/test_engine_dispatch_validation_1209.py
- VS Code diagnostics: no errors in reviewed source/test files

### Coverage
- overall scoped: 19%
- owlbear_kanban.engine: 12%
- owlbear_kanban.errors: 86%
- owlbear_kanban.dispatch: 26%
- Module-level coverage is informational for this narrow diff; changed paths are directly exercised by task tests and one adjacent regression test.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 `KanbanEngine.__init__` validates priorities and raises `ERR_DISPATCH_PRIORITY_MISMATCH` listing unranked values | `test_unknown_priority_raises_with_correct_code`; `test_priority_error_message_lists_unranked_values`; `test_multiple_unknown_priorities_all_in_message` | Yes. Constructor calls the shared validator and the tests assert the exact code plus offending value names. | COVERED |
| AC2 `KanbanEngine.__init__` validates statuses and raises `ERR_DISPATCH_STATUS_MISMATCH` listing unranked values | `test_unknown_status_raises_with_correct_code`; `test_status_error_message_lists_unranked_values`; `test_multiple_unknown_statuses_all_in_message` | Yes. Constructor calls the shared validator and the tests assert the exact code plus offending value names. | COVERED |
| AC3 `refresh_config` runs the same dispatch-constant validation after reloading config | `test_refresh_config_priority_mismatch_raises_exact_code`; `test_refresh_config_priority_mismatch_lists_unranked_in_message`; `test_refresh_config_status_mismatch_raises_exact_code`; `test_refresh_config_status_mismatch_lists_unranked_in_message` | Yes. Refresh uses the same validator before mutating engine state, and the refresh tests separately prove exact code and message-content behavior for both priority and status mismatch branches. | COVERED |
| AC4 error codes registered in `KANBAN_ERROR_CODES` | td:0 direct source proof | Yes. `ERR_DISPATCH_PRIORITY_MISMATCH` and `ERR_DISPATCH_STATUS_MISMATCH` are present in `KANBAN_ERROR_CODES`; the mismatch tests would also fail if those codes were unregistered because `KanbanError.__init__` rejects unknown codes. | PASS |

#### Security Review
- No issues found. The change only performs membership checks against static rank maps and raises `ConfigError` with registered codes.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions are evident in the current task test file. Current assertions are exact-code and explicit offending-value checks for both constructor and refresh paths.
- Small confidence deduction: full diff-based immutability was not reconstructed in this read-only review context.

#### Test Quality
- STRONG. Assertions are discriminating, negative-path focused, and split by exact code vs message content for both priority and status branches. Fresh tmp_path board setup keeps tests independent.

#### Data Safety
- PASS. `refresh_config` validates the freshly loaded config before mutating `_config`, paths, or caches, so the previously identified partial-update failure mode is closed.

#### Test Gaps
- No AC-blocking gaps found.
- Residual risk outside current AC: `create_task()` reloads config from disk and stores it on the engine without dispatch-rank validation. This path was not changed by this task and does not block PASS for the refined AC.

#### Necessity Check
- No issues found.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 init validates priorities | engine.py lines 176-186 and 417-418; tests/test_engine_dispatch_validation_1209.py lines 116-143 | three constructor priority tests | PASS |
| AC2 init validates statuses | engine.py lines 191-197 and 417-418; tests/test_engine_dispatch_validation_1209.py lines 147-174 | three constructor status tests | PASS |
| AC3 refresh_config reruns validation after reload | engine.py lines 532-543; tests/test_engine_dispatch_validation_1209.py lines 207-270; adjacent regression test_engine_coverage_1068.py lines 537-554 | four refresh-path tests + one adjacent regression | PASS |
| AC4 error codes registered | errors.py lines 7-46 and 70-75 | td:0 direct source proof | PASS |

### Deductions
- 0.03: full diff-based TestFromAC immutability could not be reconstructed in read-only review context
- 0.03: residual out-of-scope config reload path remains in `create_task()`

### Verdict
- PASS. Confidence: 0.94.
- Action: advance to docs.

### Reflection
- Pattern discovered: the architect's AC3 refinement converted the previous false-green refresh proof into discriminating exact-code and message-content checks.
- Quality gap: module-level coverage remains low on scoped modules, but the changed validation paths are directly proven and the targeted adjacent refresh regression stays green.
- Residual risk: `create_task()` still reloads config without dispatch-rank validation; this is outside the current AC and should be considered separately if dispatch.py remains in service before #1214 lands.
[[2026-05-02]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | serve/kanban/README.md lists KanbanEngine methods and config but does not reference dispatch rank maps or ERR_DISPATCH_* codes; root READMEs are implementation-agnostic. No prose update needed. |
| 2 | Module docstrings | Yes | Verified | `_validate_dispatch_rank_coverage` has accurate docstring; `refresh_config` docstring describes two-phase reload correctly; `errors.py` module docstring unchanged and accurate; `dispatch.py` module docstring updated by builder to `released=0 (highest) → research=7 (lowest)` — accurate. All public API unchanged. |
| 3 | External attribution | No | N/A | No external patterns referenced in task body or builder notes. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes `serve/kanban/src/**`) footer updated from `2026-05-02 (f74ea565)` to `2026-05-03 (5a7f802e)`. `share/diagrams/mcp-topology.excalidraw` (also describes `serve/kanban/src/**`) footer updated from `2026-05-03 (800c51db)` to `2026-05-03 (5a7f802e)`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation requested. |
| 7 | Deletion detection | No | N/A | No files deleted in this task. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/src/owlbear_kanban/engine.py | IN (docstrings) | Verified — accurate |
| serve/kanban/src/owlbear_kanban/errors.py | IN (docstrings) | Verified — accurate |
| serve/kanban/src/owlbear_kanban/dispatch.py | IN (docstrings) | Verified — accurate |
| tests/test_engine_dispatch_validation_1209.py | OUT | Test file — no doc action |
| share/diagrams/kanban.excalidraw | IN | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN | Footer updated |

### Files Updated
- share/diagrams/kanban.excalidraw (footer: `2026-05-03 (5a7f802e)`)
- share/diagrams/mcp-topology.excalidraw (footer: `2026-05-03 (5a7f802e)`)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no 1209-* scratch files found)

Commit: `3bffa98a` — `docs: update diagram footers for dispatch validation (#1209, doc-writer)`

[[2026-05-03]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 init validates priorities, raises ERR_DISPATCH_PRIORITY_MISMATCH listing unranked | engine.py:176-187 validator + :418 call site; test_engine_dispatch_validation_1209.py:116-143 (3 tests: exact code, message content, multiple values) | PASS |
| AC2 init validates statuses, raises ERR_DISPATCH_STATUS_MISMATCH listing unranked | engine.py:191-198 validator + :418 call site; test_engine_dispatch_validation_1209.py:147-174 (3 tests: exact code, message content, multiple values) | PASS |
| AC3 refresh_config runs same validation after reload | engine.py:536-537 loads then validates before mutation at :539; test_engine_dispatch_validation_1209.py:207-270 (4 discriminating tests: priority code, priority message, status code, status message); adjacent regression 1/1 green | PASS |
| AC4 error codes registered in KANBAN_ERROR_CODES | errors.py:45-46 both codes present in frozenset; KanbanError.__init__ rejects unknown codes as safety net | PASS |

### Test Results
- pytest (task-scoped): 10 passed, 0 failed
- pytest (adjacent regression): 1 passed, 0 failed
- pytest (full suite): 3718 passed, 128 failed, 4 skipped — 0 failures task-relevant (accessor migration debt, status advancement, frontend/storage, permissions)
- ruff: 1 violation in copilot_auth.py:106 (T201) — not task-related; task files clean

### Architect Quality: 4/5
AC was precise with test-depth annotations, scope notes, failure mode map, and challenger results. Minor gap: AC3 initially td:1, required upgrade to td:2 after reviewer found proof weakness. Architect responded well in cycle 2, demonstrating good pipeline-signal processing.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 have specific evidence) → 0.00
- Lint violations in task scope: 0 → 0.00
- AC quality ≤ 3: no (4/5) → 0.00
- Missing reviewer evidence: no (detailed, PASS) → 0.00
- Full-suite failures in task scope: 0 → 0.00
- Commit integrity: 4 commits properly tagged (#1209, agent roles, correct types) → 0.00
- Docs gate: diagram footers updated, committed → 0.00
- Pipeline cycles: 3 cycles total; implementation correct by cycle 2, test proof strengthened in cycle 3 — informational, no deduction

### Confidence: 0.98
### Action: archive