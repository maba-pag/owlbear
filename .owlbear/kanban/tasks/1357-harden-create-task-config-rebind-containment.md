---
id: 1357
title: Harden create_task config rebind containment
status: in-progress
priority: important
created: 2026-05-05T06:01:35.068451+00:00
updated: 2026-05-05T09:12:06.998080+00:00
tags:
- kanban
- security
- hardening
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Reviewer found during #1351 review that `KanbanEngine.create_task` reloads config and rebinds `self._tasks_dir` / `self._archive_dir` after `write_task` without mirroring the constructor / `refresh_config` `validate_path_containment` checks. This is hardening debt outside #1351's loop-breaker scope.

**Threat model**: The actual file write is already validated in `storage.py` (L412-423). The unguarded rebind at `engine.py:1033-1036` is a **post-write state poisoning** risk: if a symlink target changes between the initial construction and the `load_config` reload after `write_task`, the engine's cached `_tasks_dir`/`_archive_dir` could point outside `kanban_dir` for all subsequent operations in that engine instance. The config model (`models.py:115-118`) already rejects `../` and absolute paths, so the residual attack surface is specifically runtime symlink escape of board-relative path aliases.

## Acceptance Criteria

1. **Add containment validation to post-write rebind** `(td:2)`: after the `self._tasks_dir` / `self._archive_dir` rebind in `create_task` (engine.py ~L1035-1036), call `validate_path_containment(self._kanban_dir, self._tasks_dir)` and `validate_path_containment(self._kanban_dir, self._archive_dir)`. Prefer this inline 2-line fix over centralizing — `refresh_config` has different cache-clear semantics that make a shared helper non-trivial.
2. **Regression test** `(td:2)`: add a test that (a) monkeypatches `load_config` (or the post-write reload path) to return a config with a symlink-escaping `tasks_dir`/`archive_dir` after `write_task` completes, (b) asserts `PermissionError` is raised from `validate_path_containment` during the rebind, (c) would pass without the fix (i.e. proves the old code did NOT validate).
3. **Preserve normal behavior** `(td:0)`: existing tests for relative-path boards (e.g. `test_kanban_config_path_validation_1351.py`) and default-path `create_task` continue to pass; no behavioral change for contained configurations.

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One gap, one fix location |
| Interface clarity | PASS | AC specifies exact function calls and location |
| Dependency correctness | PASS | No dependencies needed; #1351 (origin) is done |
| Module layering | PASS | Fix stays within engine.py, uses existing _naming.py helper |
| TDD compliance | PASS | AC 2 specifies regression test structure |
| KISS/YAGNI | PASS | 2-line inline fix preferred; centralization explicitly deferred |
| Premise challenge | PASS | Gap confirmed by code asymmetry; defense-in-depth is justified |
| Pattern consistency | PASS | Mirrors existing __init__ and refresh_config patterns |
| Security surface | PASS | Task IS the security hardening; validate_path_containment is the established boundary check |
| Single domain | PASS | kanban engine internals only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| create_task post-write reload | Symlink escape in reloaded config paths | PermissionError (from validate_path_containment) | After fix: YES | Prevents poisoned engine state for subsequent ops |

### Challenge Results
- Challenger: reconsider (0.72)
- Key concerns: (1) state-poisoning vs write-escape distinction, (2) centralize option non-trivial, (3) test needs monkeypatch seam, (4) narrower threat model than original AC implied
- Architect response: ACCEPTED all — refined AC to clarify threat model, prefer inline fix, specify monkeypatch approach for test, narrow attack surface description

### Test Depth
- Max depth: 2
- Test-writer: PROCEED

### Verdict: APPROVE
### Action Taken: Refined AC to address challenger concerns — clarified threat model as post-write state poisoning, narrowed attack surface to symlink escape, preferred inline 2-line fix over centralization, specified monkeypatch test approach
[[2026-05-05]]
## Architecture Review

Confirmed the gap: `create_task` post-write rebind (engine.py ~L1033-1036) lacks `validate_path_containment` calls present in `__init__` and `refresh_config`. Refined AC to clarify threat model (post-write state poisoning via symlink escape, not a direct write-path vulnerability), prefer inline 2-line fix over centralization (different cache semantics), and specify monkeypatch test approach for deterministic regression coverage.

Challenger raised valid concerns at 0.72 confidence — all accepted and incorporated into AC refinement. All 10 architecture criteria PASS.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_engine_rebind_containment_1357.py
- Classes: TestFromAC_CreateTaskRebindContainment
- Tests per category: happy 0, edge 1, error 3, boundary 1
- Total: 5 tests, all FAIL
- ruff: clean

**AC coverage:**
| AC line | Test(s) |
|---------|---------|
| AC1 (td:2) — validate_path_containment after tasks_dir rebind | test_symlink_escaping_tasks_dir_raises_permission_error, test_both_dirs_poisoned_raises_permission_error, test_symlink_to_parent_of_kanban_dir_raises_permission_error |
| AC1 (td:2) — validate_path_containment after archive_dir rebind | test_symlink_escaping_archive_dir_raises_permission_error, test_both_dirs_poisoned_raises_permission_error |
| AC2 (td:2) — monkeypatch load_config post-write, assert PermissionError, prove old code gap | all 5 tests; test_permission_error_raised_after_both_load_config_calls explicitly proves poison arrives at rebind path (AC2c) |
| AC3 (td:0) — normal behavior preserved | skipped per td:0 rule |

**Approach:** monkeypatch `owlbear_kanban.engine.load_config` with a 2-call side_effect — first call returns real config (pre-write validation), second returns a mock config with a symlink-escaping path (post-write rebind). Filesystem symlinks (kanban_dir/escape_* → outside_dir) make validate_path_containment detect the escape via .resolve().
[[2026-05-05]]
## Builder Notes
- Implementation: Added post-write containment checks in `create_task` after config rebind for both `_tasks_dir` and `_archive_dir`.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`
- Tests: 27 passed, 0 failed
  - `tests/test_engine_rebind_containment_1357.py`: 6 passed
  - `tests/test_kanban_config_path_validation_1351.py`: 21 passed
- Coverage: `owlbear_kanban.engine` 17% in scoped run
- ruff: clean
- Evidence summary: RED verified first (all 5 TestFromAC failures reproduced as DID NOT RAISE PermissionError), then GREEN verified after the 2-line fix.
- Commit: `ad980c4f` (`fix: harden create_task rebind containment (#1357, builder)`)

## Post-task Reflection
- Problem faced: `create_task` had a post-write config reload path that rebounded directories without containment re-validation.
- Workaround applied: mirrored existing constructor/refresh defense with an inline two-call validation at the exact rebind site.
- Pattern discovered: runtime path-containment checks must be re-applied after any config reload that mutates cached path fields.
- Time sink: none significant; AC/test seam was precise and deterministic.
- Quality gap: scoped module-level coverage for `owlbear_kanban.engine` remains low due module breadth, though targeted regression and hardening tests are all green.
[[2026-05-05]]
## Review Evidence
### Scope
- Builder commit `ad980c4f` is present in `.git/logs/HEAD`; changed-file scope was reconstructed from builder notes as `serve/kanban/src/owlbear_kanban/engine.py` because commit diff / dirty-tree status were not available in the current tool surface.

### Test Results
- `quality-runner` broad context run: 277 passed, 4 failed, 0 skipped. All 4 failures were unrelated background failures in `serve/kanban/tests/test_engine_coverage_1068.py`, not task-1357 regressions.
- `quality-runner` narrow isolation run: 38 passed, 0 failed, 0 skipped across:
  - `tests/test_engine_rebind_containment_1357.py`
  - `tests/test_kanban_config_path_validation_1351.py`
  - `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_EngineCreateTask`
  - `serve/kanban/tests/test_engine_crash_safety_1101.py::TestFromAC_EngineCrashSafety::test_ac3_create_task_contract_preserved_with_new_routing`
  - `serve/kanban/tests/test_engine_create_edit_1070.py::TestFromAC_CreateTask::test_create_task_uses_entry_status_not_defaults_status`

### Lint Results
- `ruff` clean for `serve/kanban/src/owlbear_kanban/engine.py`, `tests/test_engine_rebind_containment_1357.py`, and `tests/test_kanban_config_path_validation_1351.py`.

### Coverage Data
- Broad adjacent run: `owlbear_kanban.engine` 84% overall. The changed lines in `create_task` are exercised directly by the task suite; module-level coverage is not the gating issue here.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 — add containment validation to post-write rebind | `create_task` reloads config and assigns `_config`, `_tasks_dir`, and `_archive_dir` before validating them at `serve/kanban/src/owlbear_kanban/engine.py:1030-1035`. Later engine operations still read those cached fields directly at `serve/kanban/src/owlbear_kanban/engine.py:1706` and `serve/kanban/src/owlbear_kanban/engine.py:1978`. A `PermissionError` therefore raises after the instance is already rebound to poisoned paths. | `tests/test_engine_rebind_containment_1357.py:132`, `tests/test_engine_rebind_containment_1357.py:162`, `tests/test_engine_rebind_containment_1357.py:263` | FAIL |
| AC2 — regression test proves post-write poisoned reload is caught during rebind | The new tests do prove `PermissionError` on poisoned rebinds. But the timing proof at `tests/test_engine_rebind_containment_1357.py:222` only asserts two `load_config` calls; it never observes `write_task` completion or verifies that the same engine instance remains safe after the exception. | `tests/test_engine_rebind_containment_1357.py:132`, `tests/test_engine_rebind_containment_1357.py:162`, `tests/test_engine_rebind_containment_1357.py:222`, `tests/test_engine_rebind_containment_1357.py:263` | FAIL |
| AC3 — preserve normal behavior for contained configurations | Existing default-path create_task tests stayed green at `serve/kanban/tests/test_engine_coverage_1068.py:874`, `serve/kanban/tests/test_engine_coverage_1068.py:881`, and `serve/kanban/tests/test_engine_coverage_1068.py:932`; crash-safety regression stayed green at `serve/kanban/tests/test_engine_crash_safety_1101.py:207`; entry-status create_task stayed green at `serve/kanban/tests/test_engine_create_edit_1070.py:179`; related relative-path board tests stayed green at `tests/test_kanban_config_path_validation_1351.py:259`, `tests/test_kanban_config_path_validation_1351.py:352`, and `tests/test_kanban_config_path_validation_1351.py:375`. But there is still no create_task success-path proof on a contained non-default `sub/tasks` / `sub/archive` board, so the broader “no behavioral change for contained configurations” claim is unproven. | passing suites above | FAIL |

### Test-Writer Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 | `tests/test_engine_rebind_containment_1357.py:132`, `tests/test_engine_rebind_containment_1357.py:162`, `tests/test_engine_rebind_containment_1357.py:263` | Yes for the exception-path behavior | COVERED |
| AC2 | `tests/test_engine_rebind_containment_1357.py:222` | Only partially; two `load_config` calls do not prove `write_task` completed or that cached state stayed safe | LAX |
| AC3 | existing passing suites above | No; current evidence does not exercise create_task on a contained non-default board | MISSING |

### Deductions
- `-0.12` implementation still leaves the long-lived engine instance rebound to escaping paths before the guard fires.
- `-0.05` regression proof does not observe post-write state safety or `write_task` completion.
- `-0.03` contained non-default create_task success path remains unproven.
- `-0.02` no diff/dirty-tree check was available in this tool surface; commit presence was verified via `.git/logs/HEAD` only.

### Verdict
- FAIL -> `in-progress`
- Confidence: `0.78`
- Reason: implementation miss plus proof gap. The new guard raises, but it does so after mutating cached engine state, so the task does not fully contain the post-write poisoning risk described in the task context.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Validate reloaded candidate paths before assigning them to `_config`, `_tasks_dir`, or `_archive_dir`, or roll back the cached fields on `PermissionError` so the engine instance cannot remain poisoned after a failed `create_task` | `serve/kanban/src/owlbear_kanban/engine.py` | post-reload assignments precede validation at `serve/kanban/src/owlbear_kanban/engine.py:1030-1035`; later operations consume cached dirs at `serve/kanban/src/owlbear_kanban/engine.py:1706` and `serve/kanban/src/owlbear_kanban/engine.py:1978` |
| 2 | builder | Strengthen the regression suite to prove the failure occurs after `write_task` and that the same engine instance remains safe after the exception; add a success-path `create_task` check on a contained non-default board (`sub/tasks`, `sub/archive`) if AC3 is meant to cover that behavior | `tests/test_engine_rebind_containment_1357.py`, `tests/test_kanban_config_path_validation_1351.py` or a task-scoped create_task suite | timing proof only checks two `load_config` calls at `tests/test_engine_rebind_containment_1357.py:222`; no contained non-default create_task success test exists |