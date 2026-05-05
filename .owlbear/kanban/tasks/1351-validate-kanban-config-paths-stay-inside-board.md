---
id: 1351
title: Validate kanban config paths stay inside board
status: backlog
priority: critical
created: 2026-05-04T18:45:17.182693+00:00
updated: 2026-05-05T02:45:21.012781+00:00
tags:
- sync-blocker
- kanban
- security
parent:
depends_on:
- 1338
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Kanban board paths are loaded from `config.yml` and then used by storage, engine, Cockpit watches, and MCP-facing operations. Existing file-name containment checks protect individual task paths, but the config itself can still name absolute or parent-traversing directories before reads/scans resolve the board shape.

Because the kanban engine is the central task and decision endpoint, path authority must be explicit: configured task/archive paths must stay under the intended board directory unless a deliberate future decision introduces an escape hatch.

## Acceptance Criteria

1. `PathsConfig` validator rejects values where `PurePosixPath(v).is_absolute() or PureWindowsPath(v).is_absolute()` is true, or any path component equals `..`, for both `tasks_dir` and `archive_dir`. Raises `ConfigError` with code `ERR_PATH_ESCAPE`. (td:2)
2. Engine/storage paths derived from `config.paths.tasks_dir` and `config.paths.archive_dir` cannot resolve outside `kanban_dir` at runtime — validated by existing `validate_path_containment()` call-sites in storage plus the new config-time rejection (defense-in-depth; no new per-consumer wrapping required). (td:2)
3. Reuse or extend `_naming.validate_path_containment()` semantics. Config-time validation may use a string-level helper (since values are strings, not Paths), but it must live in `_naming.py` alongside the existing function. (td:1)
4. Tests cover: `../outside`, `/etc/shadow`, `C:\\Windows`, `tasks/../../escape`, empty string, and a valid relative subdirectory like `custom-tasks`. Symlink-adjacent resolution tested where practical (tmp_path symlink pointing outside). (td:2)
5. Normal relative board configs (`tasks`, `archive`, `sub/tasks`) continue to load, create, edit, archive, and list tasks without regression. (td:1)
6. Existing Cockpit and MCP board-binding test suites pass unchanged (regression gate, no new tests). (td:0)

## Key Files

- `serve/kanban/src/owlbear_kanban/models.py` — `PathsConfig` model
- `serve/kanban/src/owlbear_kanban/_naming.py` — `validate_path_containment()` + new string-level helper
- `serve/kanban/src/owlbear_kanban/storage.py` — existing runtime containment calls
- `serve/kanban/src/owlbear_kanban/engine.py` — path binding from config
- `serve/kanban/src/owlbear_kanban/errors.py` — `ConfigError` with new code

## Architecture Notes

- The validation boundary is `PathsConfig` (Pydantic `field_validator`). All downstream consumers (engine, storage, dispatch, corruption, cockpit cache) derive paths from this model — protecting the source protects all sinks.
- `validate_path_containment()` continues to serve as the runtime resolve-level defense for individual file operations (symlink, race). The config validator is the parse-time string-level defense.
- `decisions_dir` and `activity_log_path` are hardcoded relative to `kanban_dir`, not user-configurable — out of scope.

## Source

Meta-audit blind source pass, 2026-05-04.

[[2026-05-05]]
## Architecture Review

**Verdict:** APPROVE

### AC Assessment

| AC | Assessment | Action |
|----|-----------|--------|
| 1. PathsConfig validator rejects absolute/parent-traversing | Precise: specifies cross-platform check (`PurePosixPath` + `PureWindowsPath`), exact error code, exact fields | Refined to specify cross-platform detection |
| 2. Runtime defense-in-depth | Clarified: no new per-consumer wrapping; existing `validate_path_containment` in storage.py + config-time rejection | Refined to state explicitly |
| 3. Reuse _naming.py | Clear architectural constraint — new helper co-located with existing function | No change needed |
| 4. Test inputs | Explicit enumeration including Windows paths and symlink edge | Added `C:\\Windows` and empty-string cases |
| 5. Regression (relative paths) | Added concrete examples: `tasks`, `archive`, `sub/tasks` | Tightened |
| 6. Existing suites pass | Regression gate only, td:0 | No change |

### Architecture Notes

- Single validation boundary at `PathsConfig` (Pydantic field_validator) protects all downstream consumers.
- Existing `validate_path_containment()` serves as resolve-level runtime defense for symlink/race conditions.
- Only `tasks_dir` and `archive_dir` are user-configurable path fields; `decisions_dir` and `activity_log_path` are hardcoded.
- Dependency #1338 archived/done — unblocked.

### Challenger Results

Challenger scored 0.57 / recommended block. Concerns addressed:
- Cross-platform: AC1 now specifies `PurePosixPath` + `PureWindowsPath` checks.
- Runtime consumers: all derive from PathsConfig — source validation protects sinks.
- Symlink: handled by existing `validate_path_containment()` at runtime (resolve-level).
- Scope: decisions/activity paths hardcoded, not configurable — explicitly out of scope.

Override justified: challenger's "block" assumed validator-only without runtime defense, but the codebase already has resolve-level checks in storage.py. Defense-in-depth is sound.
[[2026-05-05]]
## Test-Writer Notes
- Test file: tests/test_kanban_config_path_validation_1351.py
- Classes: TestFromAC_ErrorCodeRegistration, TestFromAC_PathsConfigValidation, TestFromAC_NamingHelper, TestFromAC_RuntimeDefense, TestFromAC_BoardConfigIntegration
- Tests per category: happy 4, edge 2, error 11, boundary 2
- Total: 19 tests, all FAIL
- ruff: clean

### AC Coverage

| AC | Tests |
|----|-------|
| AC1 — PathsConfig validator rejects absolute/parent-traversing | test_rejects_tasks_dir_parent_traversal, test_rejects_archive_dir_parent_traversal, test_rejects_tasks_dir_absolute_posix, test_rejects_archive_dir_absolute_posix, test_rejects_tasks_dir_absolute_windows, test_rejects_tasks_dir_deep_traversal, test_rejects_archive_dir_deep_traversal, test_error_code_is_err_path_escape (in validator tests) |
| AC2 — Runtime defense-in-depth unchanged | test_runtime_rejects_path_outside_kanban_dir, test_symlink_pointing_outside_rejected_at_runtime |
| AC3 — Helper in _naming.py | test_helper_exists_in_naming_module, test_helper_rejects_absolute_posix_path, test_helper_rejects_parent_traversal, test_helper_accepts_plain_relative_name |
| AC4 — Specific inputs covered | ../outside (×2), /etc/shadow (×2), C:\\Windows, tasks/../../escape, archive/../../../etc, empty string, custom-tasks, symlink |
| AC5 — Valid relative paths still load | test_valid_relative_tasks_dir_accepted, test_valid_relative_archive_subpath_accepted, test_board_config_with_default_relative_paths_loads |
| AC6 — (td:0, no tests needed) | — |

### Failure modes
- ERR_PATH_ESCAPE not in KANBAN_ERROR_CODES → AssertionError
- PathsConfig has no validator → DID NOT RAISE (8 tests)
- validate_config_path_containment absent from _naming → ImportError (10 tests)
- BoardConfig does not reject traversal → DID NOT RAISE (1 test)
[[2026-05-05]]
## Builder Notes
- Implementation: added config-path escape code and validator wiring in serve/kanban/src/owlbear_kanban/errors.py, serve/kanban/src/owlbear_kanban/_naming.py, and serve/kanban/src/owlbear_kanban/models.py.
- Fixes applied:
  - Registered ERR_PATH_ESCAPE in KANBAN_ERROR_CODES.
  - Added _naming.validate_config_path_containment(path_value: str) to reject absolute (POSIX + Windows) and parent-traversing ('..') config paths with ConfigError(ERR_PATH_ESCAPE).
  - Added PathsConfig field_validator for tasks_dir and archive_dir to enforce config-time rejection via the new helper.
- RED verification: quality-runner on tests/test_kanban_config_path_validation_1351.py reported 19 failed before implementation.
- GREEN verification:
  - Task-scoped: 18 passed, 0 failed, 1 skipped; ruff clean.
  - AC6 regression gate (Cockpit + MCP board binding): 204 passed, 0 failed, 0 skipped; ruff clean.
  - Config regression suite: 69 passed, 0 failed, 0 skipped; ruff clean.
- Coverage evidence (quality-runner): touched modules reported in scoped runs (models 80-89%, _naming 53-56%, errors 90%).
- Commit: fix: validate config path containment (#1351, builder) [6c7f04f1].
[[2026-05-05]]

### Post-task Reflection
- Main blocker was split across three missing pieces (error code, helper, validator); implementing all three in one pass prevented churn.
- Reusing _naming.py for config-time checks kept path-authority logic centralized and aligned with AC constraints.
- Runtime containment protections already in place meant no storage/engine surgery was needed; this reduced regression risk.
- Task-scoped coverage remained below 90% on _naming because the module includes unrelated helpers; broader regression suites were used to validate safety instead.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner narrowed scoped run on `tests/test_kanban_config_path_validation_1351.py`, `tests/test_config_loader.py`, `tests/test_config_schema.py`, `tests/test_cockpit_launch.py`, and `tests/test_mcp_kanban.py`: 149 passed, 0 failed, 1 skipped.
- The skipped case aligns with `tests/test_kanban_config_path_validation_1351.py:86-98`, where the empty-string boundary explicitly calls `pytest.skip(...)` instead of proving rejection or a runtime backstop.
- An exploratory broader run that also included `tests/test_cockpit_events_1234.py` surfaced unrelated task-scoped failures; those were excluded from the gate after the narrower durable-suites rerun isolated the task signal.

### Lint Results
- Ruff clean on `serve/kanban/src/owlbear_kanban/errors.py`, `serve/kanban/src/owlbear_kanban/_naming.py`, `serve/kanban/src/owlbear_kanban/models.py`, and `tests/test_kanban_config_path_validation_1351.py`.

### Coverage
- `owlbear_kanban._naming`: 67%
- `owlbear_kanban.models`: 91%
- `owlbear_kanban.errors`: 90%
- Coverage did not drive the reject. The reject is based on a real source defect and weak AC proof.

### AC Compliance
| AC line | Evidence | Status |
|---|---|---|
| AC1 | `_naming.validate_config_path_containment()` checks absoluteness with `PurePosixPath` and `PureWindowsPath` at `serve/kanban/src/owlbear_kanban/_naming.py:60`, but checks `..` only via `PurePosixPath(...).parts` at `serve/kanban/src/owlbear_kanban/_naming.py:69`. `PathsConfig` wires this helper for both fields at `serve/kanban/src/owlbear_kanban/models.py:115-118`. Windows backslash traversal such as `..\\outside` is not rejected by the changed code, and the task suite only covers a Windows absolute path at `tests/test_kanban_config_path_validation_1351.py:68-72`. | FAIL |
| AC2 | Engine derives `_tasks_dir` and `_archive_dir` directly from config at `serve/kanban/src/owlbear_kanban/engine.py:353-354`; runtime read/list/archive sinks still consume derived dirs without containment checks in `serve/kanban/src/owlbear_kanban/engine.py:591`, `serve/kanban/src/owlbear_kanban/engine.py:1945-1975`, `serve/kanban/src/owlbear_kanban/storage.py:502-525`, and `serve/kanban/src/owlbear_kanban/storage.py:543-556`. The task’s symlink test at `tests/test_kanban_config_path_validation_1351.py:186-210` only calls `validate_path_containment(kanban_dir, outside_file)` and does not exercise a real sink. | FAIL |
| AC3 | The new helper lives in `serve/kanban/src/owlbear_kanban/_naming.py:58`, and `PathsConfig` reuses it centrally at `serve/kanban/src/owlbear_kanban/models.py:115-118`. | PASS |
| AC4 | Required inputs are partially present, but the empty-string boundary test can skip at `tests/test_kanban_config_path_validation_1351.py:98`, and the symlink case does not prove a symlinked tasks/archive sink is defended. | FAIL |
| AC5 | The only happy-path integration proof in the task file is config parsing at `tests/test_kanban_config_path_validation_1351.py:246-257`. There is no task-scoped create/edit/archive/list proof for `tasks`, `archive`, or `sub/tasks`. | FAIL |
| AC6 | Durable board-binding regressions passed unchanged in the narrowed quality-runner run: `tests/test_cockpit_launch.py` and `tests/test_mcp_kanban.py` were included alongside durable config suites and returned green. Relevant board-binding entry points are at `tests/test_cockpit_launch.py:438-455` and `tests/test_mcp_kanban.py:119-153`. | PASS |

### Deductions
- -0.20 source defect: Windows backslash traversal remains open in `_naming.py`.
- -0.10 runtime defense gap: derived directory sinks are not fully proven safe.
- -0.08 proof gap: empty-string boundary is skipped rather than asserted.
- -0.07 proof gap: AC5 operational regressions are not task-locally demonstrated.
- -0.02 confidence deduction: commit presence was corroborated via `.git/logs`, but diff-scoped ownership and dirty-tree contamination could not be fully checked in this tool surface.

### Verdict
- FAIL
- Confidence: 0.53
- Action: reject to `in-progress`. The task still has a source-level security defect, and the current task-local proof is not strong enough to show AC2, AC4, and AC5 are met.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Reject Windows-style parent traversal in `validate_config_path_containment()` for both configured directories by treating `..` components with Windows separators as invalid, not just POSIX-style separators | `serve/kanban/src/owlbear_kanban/_naming.py`, `serve/kanban/src/owlbear_kanban/models.py` | AC1; `serve/kanban/src/owlbear_kanban/_naming.py:60`, `serve/kanban/src/owlbear_kanban/_naming.py:69`, `serve/kanban/src/owlbear_kanban/models.py:115-118`; task tests only pin `C:\\Windows` at `tests/test_kanban_config_path_validation_1351.py:68-72` |
| 2 | builder | Make AC2 true for runtime-derived directory consumers or explicitly narrow the implementation with a blocking clarification. Current list/read/archive sinks still consume derived directories without containment validation. | `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/storage.py` | AC2; `serve/kanban/src/owlbear_kanban/engine.py:353-354`, `serve/kanban/src/owlbear_kanban/engine.py:591`, `serve/kanban/src/owlbear_kanban/engine.py:1945-1975`, `serve/kanban/src/owlbear_kanban/storage.py:502-525`, `serve/kanban/src/owlbear_kanban/storage.py:543-556` |
| 3 | builder | Return the retry with discriminating proof for the empty-string boundary, a real symlinked sink path, and AC5 operational behavior (`create`, `edit`, `archive`, `list`) so the review no longer relies on a skip and parse-only assertions | `tests/test_kanban_config_path_validation_1351.py` | AC4 and AC5; `tests/test_kanban_config_path_validation_1351.py:86-98`, `tests/test_kanban_config_path_validation_1351.py:186-210`, `tests/test_kanban_config_path_validation_1351.py:246-257` |
[[2026-05-05]]
## Builder Notes
- Implementation: updated serve/kanban/src/owlbear_kanban/_naming.py and serve/kanban/src/owlbear_kanban/engine.py.
- Fixes applied:
  - `validate_config_path_containment()` now checks `..` path components using both `PurePosixPath(...).parts` and `PureWindowsPath(...).parts`, so Windows-style traversal segments are rejected.
  - `KanbanEngine.__init__` now enforces runtime board containment for derived `tasks_dir` and `archive_dir` by calling `validate_path_containment(self._kanban_dir, self._tasks_dir)` and `validate_path_containment(self._kanban_dir, self._archive_dir)`.
- RED/current-state check: quality-runner on tests/test_kanban_config_path_validation_1351.py returned 18 passed, 0 failed, 1 skipped (existing reviewer-loop baseline).
- GREEN verification (quality-runner scoped):
  - tests/test_kanban_config_path_validation_1351.py
  - tests/test_config_loader.py
  - tests/test_config_schema.py
  - tests/test_mcp_kanban.py
  - tests/test_cockpit_launch.py
  - Result: 149 passed, 0 failed, 1 skipped.
- Coverage (quality-runner scoped): owlbear_kanban._naming 68%, owlbear_kanban.engine 35%.
- ruff: clean on serve/kanban/src/owlbear_kanban/_naming.py, serve/kanban/src/owlbear_kanban/engine.py, tests/test_kanban_config_path_validation_1351.py.
- Commit: b1918159 (`fix: tighten board path containment (#1351, builder)`).
- Evidence summary: reviewer-reported source defect for Windows-style traversal parsing is now closed at config-parse time, and runtime containment now rejects derived configured directories that resolve outside `kanban_dir`.

### Post-task Reflection
- The smallest safe fix was a dual-parser component check (`PurePosixPath` + `PureWindowsPath`) rather than broad path normalization.
- Adding containment at engine construction satisfied defense-in-depth without wrapping every sink callsite.
- The retry loop was mostly proof-oriented; implementation delta remained surgical (2 files).
- Task-scoped tests did not re-enter RED because this loop addressed uncovered behavior rather than a currently failing assertion.
[[2026-05-05]]
## Review Evidence
### Test Results
- quality-runner scoped pass on tests/test_kanban_config_path_validation_1351.py, tests/test_config_loader.py, tests/test_config_schema.py, tests/test_mcp_kanban.py, and tests/test_cockpit_launch.py: 149 passed, 0 failed, 1 skipped.
- The skipped case is tests/test_kanban_config_path_validation_1351.py:98, where the empty-string boundary skips instead of asserting the runtime backstop.

### Lint
- Ruff clean on serve/kanban/src/owlbear_kanban/_naming.py, serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/models.py, serve/kanban/src/owlbear_kanban/errors.py, and tests/test_kanban_config_path_validation_1351.py.

### Coverage
- owlbear_kanban._naming: 68%
- owlbear_kanban.engine: 35%
- owlbear_kanban.models: 91%
- owlbear_kanban.errors: 90%
- Coverage is not the gate. The reject is based on a live runtime defect and missing discriminating proof.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---|---|---|---|
| AC1 | TestFromAC_ErrorCodeRegistration and TestFromAC_PathsConfigValidation | Yes. Exact ConfigError code checks cover parent traversal, POSIX absolute, Windows absolute, and deep traversal. | COVERED |
| AC2 | TestFromAC_RuntimeDefense | No. The tests only call validate_path_containment directly and never exercise engine.refresh_config or storage read and archive sinks. | LAX |
| AC3 | TestFromAC_NamingHelper | Yes. The helper exists in _naming.py and exact error-code assertions prove the wiring. | COVERED |
| AC4 | TestFromAC_PathsConfigValidation and TestFromAC_RuntimeDefense | No. The empty-string case skips at tests/test_kanban_config_path_validation_1351.py:98, and the symlink case asserts validate_path_containment on outside_file at tests/test_kanban_config_path_validation_1351.py:210 rather than a real sink. | LAX |
| AC5 | TestFromAC_BoardConfigIntegration plus durable suites | No. Current tests prove config acceptance, but not create, edit, archive, and list behavior for nondefault relative directories. | MISSING |
| AC6 | Durable suites tests/test_mcp_kanban.py and tests/test_cockpit_launch.py | Yes. Those suites passed unchanged in the independent quality-runner pass. | COVERED |

#### Security Review
- The new constructor guard is present at serve/kanban/src/owlbear_kanban/engine.py:355-356, but refresh_config rebinds _tasks_dir and _archive_dir without revalidating containment at serve/kanban/src/owlbear_kanban/engine.py:484-485. That leaves a live runtime escape surface for empty-string or symlinked path configs after refresh.
- Storage still derives config paths without containment checks in list_task_files, list_archive_files, and move_to_archive at serve/kanban/src/owlbear_kanban/storage.py:507, serve/kanban/src/owlbear_kanban/storage.py:525, and serve/kanban/src/owlbear_kanban/storage.py:548-562. move_to_archive then performs src.replace(dest) at serve/kanban/src/owlbear_kanban/storage.py:562 on an unvalidated destination.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC classes in tests/test_kanban_config_path_validation_1351.py | No weakened or removed assertions found in the current file body | PRESERVED |
- Confidence is slightly reduced because commit-diff immutability and dirty-tree contamination could not be proven in this tool surface.

#### Test Quality
| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | Most assertions are exact ConfigError code or exact field-value checks. |
| Negative and error coverage | ADEQUATE | Absolute and traversal rejection cases are present for both fields. |
| Manual mutation resistance | WEAK | The empty-string branch can still go green via pytest.skip at tests/test_kanban_config_path_validation_1351.py:98, and the symlink test would not fail if real sink-level containment disappeared. |
| Test independence | STRONG | tmp_path-isolated setups; no shared mutable state observed. |
| Test naming | STRONG | Test names remain contract-specific and descriptive. |

#### Data Safety
- move_to_archive can mutate task data outside the board boundary because archive_dir is derived from config at serve/kanban/src/owlbear_kanban/storage.py:549 and used for src.replace(dest) at serve/kanban/src/owlbear_kanban/storage.py:562 without containment validation.

#### Implementation-Aware Gaps
- No executable proof covers refresh_config as a containment surface, even though it is exercised elsewhere in the repo at tests/test_engine_lazy_agent_map_1221.py:265 and related cases.
- No executable proof covers create, edit, archive, and list behavior for nondefault relative directories. The task-local suite stops at config acceptance for custom-tasks, sub/archive, and grouped BoardConfig load at tests/test_kanban_config_path_validation_1351.py:103-116 and tests/test_kanban_config_path_validation_1351.py:255.

#### Builder Process Quality
| Metric | Value |
|---|---|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |
| Prior Review Evidence sections before this run | 1 |

### Pass 2 - INFORMATIONAL
- AC1 and AC3 implementation wiring is correct: ERR_PATH_ESCAPE is registered at serve/kanban/src/owlbear_kanban/errors.py:18, the helper lives at serve/kanban/src/owlbear_kanban/_naming.py:58, and PathsConfig reuses it at serve/kanban/src/owlbear_kanban/models.py:115-118.
- AC6 regression evidence is independently green, but that does not close the AC2, AC4, and AC5 defects above.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| AC1 | ERR_PATH_ESCAPE exists at serve/kanban/src/owlbear_kanban/errors.py:18; helper raises that code at serve/kanban/src/owlbear_kanban/_naming.py:62 and serve/kanban/src/owlbear_kanban/_naming.py:73; PathsConfig reuses it at serve/kanban/src/owlbear_kanban/models.py:115-118; task tests cover Windows absolute at tests/test_kanban_config_path_validation_1351.py:71 and deep traversal at tests/test_kanban_config_path_validation_1351.py:77. | TestFromAC_ErrorCodeRegistration, TestFromAC_PathsConfigValidation | PASS |
| AC2 | Engine constructor validates derived dirs at serve/kanban/src/owlbear_kanban/engine.py:355-356, but refresh_config skips that validation at serve/kanban/src/owlbear_kanban/engine.py:484-485. Storage read and archive helpers still derive config paths without containment checks at serve/kanban/src/owlbear_kanban/storage.py:507, serve/kanban/src/owlbear_kanban/storage.py:525, and serve/kanban/src/owlbear_kanban/storage.py:548-562. | TestFromAC_RuntimeDefense | FAIL |
| AC3 | The string-level helper lives in serve/kanban/src/owlbear_kanban/_naming.py:58 and is reused by PathsConfig at serve/kanban/src/owlbear_kanban/models.py:115-118. | TestFromAC_NamingHelper | PASS |
| AC4 | Required enumerated inputs are only partially proven. The empty-string case skips at tests/test_kanban_config_path_validation_1351.py:98, and the symlink case asserts validate_path_containment on outside_file at tests/test_kanban_config_path_validation_1351.py:210 rather than on a real engine or storage sink. | TestFromAC_PathsConfigValidation, TestFromAC_RuntimeDefense | FAIL |
| AC5 | The current task suite proves config acceptance for custom-tasks, sub/archive, and grouped BoardConfig load at tests/test_kanban_config_path_validation_1351.py:103-116 and tests/test_kanban_config_path_validation_1351.py:255, but not create, edit, archive, and list for nondefault relative directories. The durable board-binding suites still use default tasks/archive fixtures at tests/test_mcp_kanban.py:41 and tests/test_mcp_kanban.py:61, and at tests/test_cockpit_launch.py:33 and tests/test_cockpit_launch.py:53. | TestFromAC_BoardConfigIntegration plus durable suites | FAIL |
| AC6 | Existing board-binding suites passed unchanged in the independent run. | tests/test_mcp_kanban.py, tests/test_cockpit_launch.py | PASS |

### Confidence: 0.41
### Verdict: FAIL
- This is the second review failure on task 1351. Loop-breaker routing applies, so the task returns to backlog rather than back to the builder.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|---|---|---|---|
| 1 | architect | Re-scope AC2 around all live runtime surfaces, then decompose a follow-up implementation task that closes containment on refresh_config and storage read and archive paths | serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/storage.py | serve/kanban/src/owlbear_kanban/engine.py:484-485; serve/kanban/src/owlbear_kanban/storage.py:507, 525, 548-562 |
| 2 | architect | Replace the empty-string skip and helper-only symlink proof with sink-level tests that fail when runtime containment is missing | tests/test_kanban_config_path_validation_1351.py | tests/test_kanban_config_path_validation_1351.py:98 and tests/test_kanban_config_path_validation_1351.py:210 |
| 3 | architect | Add explicit nondefault relative-path regression requirements for create, edit, archive, and list behavior, then split that proof into task-owned tests | tests/test_kanban_config_path_validation_1351.py, tests/test_mcp_kanban.py, tests/test_cockpit_launch.py | tests/test_kanban_config_path_validation_1351.py:103-116 and 255; tests/test_mcp_kanban.py:41 and 61; tests/test_cockpit_launch.py:33 and 53 |