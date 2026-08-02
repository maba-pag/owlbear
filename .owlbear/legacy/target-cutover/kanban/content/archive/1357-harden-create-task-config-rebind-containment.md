---
id: 1357
title: Harden create_task config rebind containment
status: archived
priority: medium
created: 2026-05-05T06:01:35.068451+00:00
updated: 2026-05-05T10:20:18.153457+00:00
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
[[2026-05-05]]
## Builder Notes
- Implementation: reordered `create_task` post-write reload handling in `serve/kanban/src/owlbear_kanban/engine.py` so reloaded `tasks_dir`/`archive_dir` candidates are validated for containment before mutating cached engine state.
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`
- Fix summary: replaced direct rebind sequence with `reloaded_config` + candidate path locals; call `validate_path_containment(self._kanban_dir, reloaded_tasks_dir)` and `validate_path_containment(self._kanban_dir, reloaded_archive_dir)` first; only assign `_config`, `_tasks_dir`, `_archive_dir` after both checks pass.
- Tests (scoped quality-runner): 38 passed, 0 failed, 0 skipped
  - `tests/test_engine_rebind_containment_1357.py`
  - `tests/test_kanban_config_path_validation_1351.py`
  - `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_EngineCreateTask`
  - `serve/kanban/tests/test_engine_crash_safety_1101.py::TestFromAC_EngineCrashSafety::test_ac3_create_task_contract_preserved_with_new_routing`
  - `serve/kanban/tests/test_engine_create_edit_1070.py::TestFromAC_CreateTask::test_create_task_uses_entry_status_not_defaults_status`
- Lint (scoped quality-runner): clean
  - `serve/kanban/src/owlbear_kanban/engine.py`
  - `tests/test_engine_rebind_containment_1357.py`
  - `tests/test_kanban_config_path_validation_1351.py`
- Coverage:
  - scoped run over narrow task tests: `owlbear_kanban.engine` 20%
  - broad context measurement over `serve/kanban/tests` + task tests: `owlbear_kanban.engine` 92% (pytest exit non-zero due unrelated pre-existing failures outside #1357 scope)
- Evidence summary: reviewer concern addressed directly — no poisoned path values are assigned to cached engine fields before containment checks succeed.
- Commit: `e1fa8fbc` (`fix: harden create_task rebind containment ordering (#1357, builder)`)

## Post-task Reflection
- Problem faced: prior ordering let `_tasks_dir`/`_archive_dir` become poisoned transiently before raising `PermissionError`.
- Workaround applied: validated candidate reloaded paths first, then atomically updated cached config/path fields.
- Pattern discovered: post-write config reloads should use validate-then-assign sequencing for long-lived cached path state.
- Time sink: obtaining high module coverage requires very broad suites that currently include unrelated baseline failures.
- Quality gap: task-scoped tests assert exception-path behavior strongly but still do not fully encode "engine remains safe after exception" state assertions.
[[2026-05-05]]
## Review Evidence
### Scope
- Current review cycle: second review attempt; the task file already contains one prior `## Review Evidence` section.
- Builder commit `e1fa8fbc` is present in `.git/logs/HEAD` and `.git/logs/refs/heads/dev`; changed-file scope was reconstructed as `serve/kanban/src/owlbear_kanban/engine.py` from the builder notes.
- No commit diff / dirty-tree status tool was available in this review surface, so ownership, contamination, and TestFromAC immutability checks carry a small confidence deduction.

### Test Results
- `quality-runner` scoped run: `38 passed, 0 failed, 0 skipped` across:
  - `tests/test_engine_rebind_containment_1357.py`
  - `tests/test_kanban_config_path_validation_1351.py`
  - `serve/kanban/tests/test_engine_coverage_1068.py::TestFromAC_EngineCreateTask`
  - `serve/kanban/tests/test_engine_crash_safety_1101.py::TestFromAC_EngineCrashSafety::test_ac3_create_task_contract_preserved_with_new_routing`
  - `serve/kanban/tests/test_engine_create_edit_1070.py::TestFromAC_CreateTask::test_create_task_uses_entry_status_not_defaults_status`

### Lint Results
- `quality-runner`: `ruff` clean for:
  - `serve/kanban/src/owlbear_kanban/engine.py`
  - `tests/test_engine_rebind_containment_1357.py`
  - `tests/test_kanban_config_path_validation_1351.py`
- VS Code diagnostics: no errors in the reviewed source/test files.

### Coverage Data
- `quality-runner` scoped coverage: `owlbear_kanban.engine` = `20%` overall.
- Gate decision: PASS for diff-scoped coverage. The changed lines are exercised directly on the exception path by `tests/test_engine_rebind_containment_1357.py:132`, `:162`, and `:222`, and on the preserved success path by existing create-task regressions at `serve/kanban/tests/test_engine_coverage_1068.py:874` and `:932`, `serve/kanban/tests/test_engine_crash_safety_1101.py:207`, and `serve/kanban/tests/test_engine_create_edit_1070.py:179`. Low module-wide percentage is informational only for this narrow diff.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 — add containment validation to post-write rebind | `create_task` now writes the task at `serve/kanban/src/owlbear_kanban/engine.py:1029`, reloads config at `:1030`, validates the candidate rebind paths against `self._kanban_dir` at `:1033-1034`, and only then assigns `_config`, `_tasks_dir`, and `_archive_dir` at `:1036-1038`. This is stronger than the prior assignment-before-validation behavior and removes the poisoned-state issue from the earlier review. | `tests/test_engine_rebind_containment_1357.py:132`, `:162`, plus the same suite's both-dir and parent-boundary cases | PASS |
| AC2 — regression test proves post-write poisoned reload is caught during rebind | The task-local suite patches `owlbear_kanban.engine.load_config` so the second load returns poisoned paths. In live code the second load is the post-write reload (`serve/kanban/src/owlbear_kanban/engine.py:1029-1030`), and `tests/test_engine_rebind_containment_1357.py:222` with `:259` proves that both `load_config` calls complete before the `PermissionError` is observed. Without the new containment checks at `serve/kanban/src/owlbear_kanban/engine.py:1033-1034`, these tests would not raise. | `tests/test_engine_rebind_containment_1357.py:132`, `:162`, `:222`, `:259` | PASS |
| AC3 — preserve normal behavior for contained configurations | Existing adjacent proof stayed green in the scoped run: relative-path-board/runtime containment tests at `tests/test_kanban_config_path_validation_1351.py:232`, `:352`, and `:375`; default-path create-task regressions at `serve/kanban/tests/test_engine_coverage_1068.py:874` and `:932`; create-task contract regression at `serve/kanban/tests/test_engine_crash_safety_1101.py:207`; entry-status create-task regression at `serve/kanban/tests/test_engine_create_edit_1070.py:179`. AC3 is `(td:0)` and asks that existing proof stay green; it does. | passing suites above | PASS |

### Test-Writer Audit
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 | `tests/test_engine_rebind_containment_1357.py:132`, `:162`, `:192`, `:263` | Yes. Removing either containment check removes the `PermissionError` source for the corresponding poisoned-path case. | COVERED |
| AC2 | `tests/test_engine_rebind_containment_1357.py:222`, `:259` plus `serve/kanban/src/owlbear_kanban/engine.py:1029-1034` | Yes for the accepted contract: the poisoned config is injected on the post-write reload path in the live implementation, and the exception is produced by the new rebind containment checks. | COVERED |
| AC3 | Existing passing suites listed above | Yes for the `(td:0)` contract actually written: existing relative-path-board and default create-task behavior remain green. | COVERED |

### Code-Reader Synthesis
- I agree with the code-reader that the prior poisoned-state implementation defect is fixed: the engine no longer mutates cached path fields before containment validation succeeds.
- I am **not** carrying forward the code-reader's write-escape / data-safety failure as a blocking issue. Direct inspection shows `write_task` already enforces board-root containment at `serve/kanban/src/owlbear_kanban/storage.py:422-423`, which matches the task context's explicit threat model: this task was about post-write state poisoning, not direct write-path escape.
- I am **not** failing on the lack of a new non-default `create_task` success test. AC3 is explicitly `(td:0)` and requires existing adjacent proof to remain green; demanding new positive-path coverage would invent a stronger requirement than the current AC.

### Deductions
- `-0.04` No direct `git diff` / `git status` surface was available, so changed-file ownership, dirty-tree contamination, and TestFromAC immutability were reconstructed from commit-log presence, builder notes, and current file state rather than a commit diff.

### Verdict
- PASS -> `docs`
- Confidence: `0.94`
- Reason: scoped tests are green, lint and editor diagnostics are clean, the hardening fix validates candidate rebind paths before cached state is mutated, and the remaining concerns from the prior rejection are either resolved or outside the refined AC.
[[2026-05-05]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/kanban/README.md` references `create_task` with description "Allocate next ID and write a new task file" — still accurate; external API contract unchanged by internal hardening. |
| 2 | Module docstrings | Yes | Updated | `create_task` in `engine.py` was missing `PermissionError` in its `Raises` section. Added entry: post-write config reload yields an escaping path → `PermissionError`; cached state not mutated. |
| 3 | External attribution | No | N/A | No external patterns used. |
| 4 | Research doc | No | N/A | No research doc was produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` has `describes: serve/kanban/src/**` — matches changed `engine.py`. Footer updated from `76e620fb` → `d528f5a`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation requested. |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected. |

### Scope Classification
- `serve/kanban/src/owlbear_kanban/engine.py` — IN-scope (docstrings)
- `tests/test_engine_rebind_containment_1357.py` — OUT-scope (test file)
- `tests/test_kanban_config_path_validation_1351.py` — OUT-scope (test file)

### Files Updated
- `serve/kanban/src/owlbear_kanban/engine.py` — added `PermissionError` to `create_task` docstring
- `share/diagrams/kanban.excalidraw` — footer updated to `2026-05-05 (d528f5a)`

### Commit
`dc544cfe` — docs: document PermissionError in create_task, update kanban diagram footer (#1357, doc-writer)

### Scratch Files
None found for task #1357.
[[2026-05-05]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 - containment validation before rebind | engine.py:1030-1038: validate_path_containment on reloaded_tasks_dir/reloaded_archive_dir before self._config/_tasks_dir/_archive_dir assignment | PASS |
| AC2 - regression test proves poisoned reload caught | 5/5 tests pass in test_engine_rebind_containment_1357.py; monkeypatch injects poisoned config on 2nd load_config call; PermissionError raised before any cached state mutation | PASS |
| AC3 - preserve normal behavior | 277 adjacent tests pass (config validation, crash safety, create-edit); 4 failures are pre-existing background issues unrelated to #1357 | PASS |

### Test Results
- pytest: 5 passed (task-scoped), 277 passed / 4 failed (adjacent; failures pre-existing in test_engine_coverage_1068.py unrelated to containment)
- ruff: clean

### Architect Quality: 5/5
Specific AC with exact function calls, file locations, clear threat model refined by challenger, appropriate TD assignments. Led to clean two-line implementation path.

### Deduction Breakdown
- No deductions. All AC lines have specific test and code evidence. Lint clean. Reviewer evidence detailed (two-cycle). No task-scoped suite failures.

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| fb31e098 | test | tests/test_engine_rebind_containment_1357.py | #1357 |
| ad980c4f | fix | serve/kanban/src/owlbear_kanban/engine.py | #1357 |
| e1fa8fbc | fix | serve/kanban/src/owlbear_kanban/engine.py | #1357 |
| dc544cfe | docs | serve/kanban/src/owlbear_kanban/engine.py, share/diagrams/kanban.excalidraw | #1357 |