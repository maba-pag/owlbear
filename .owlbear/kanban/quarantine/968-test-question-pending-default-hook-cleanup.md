---
id: 968
title: Test question_pending default hook cleanup
status: archived
priority: important
created: 2026-03-23T05:57:31.9141051+01:00
updated: 2026-03-23T15:06:26.5188315+01:00
started: 2026-03-23T15:05:58.3977154+01:00
completed: 2026-03-23T15:05:58.3977154+01:00
tags:
    - agent
    - hooks
    - test
    - config
    - scope:core
    - type:test
parent: 955
class: standard
---

Write tests FIRST for #962 question_pending default hook cleanup.

## AC

- [ ] File: updated tests/test_config.py
- [ ] File: updated tests/test_bootstrap.py
- [ ] Test: default `OwlBearSettings().notification_events` is exactly `[task_complete, on_error]`
- [ ] Test: explicit `question_pending` remains accepted when `notification_events` is supplied via `OWLBEAR_NOTIFICATION_EVENTS` and when `OwlBearSettings(notification_events=[...])` is constructed directly
- [ ] Test: `build_hooks(OwlBearSettings(), workspace_root=None)` registers `NotificationHook` handlers for `HookEvent.TASK_COMPLETE` and `HookEvent.ON_ERROR`, and does not register `HookEvent.QUESTION_PENDING`
- [ ] Test: a source-inspection regression derives the set of `HookEvent` members passed as the first argument to `.emit(...)` call sites under `src/owlbear` and asserts `OwlBearSettings().notification_events` stays a subset of that live emitted-event set
- [ ] Test: `build_hooks(OwlBearSettings(notification_events=[task_complete, question_pending]), workspace_root=None)` still registers a `HookEvent.QUESTION_PENDING` handler
- [ ] ruff clean

## Architecture

- Keep the cleanup scoped to dead defaults and current-runtime surfaces only.
- Do not add a `QUESTION_PENDING` emitter; that belongs to #967.
- Do not delete `HookEvent.QUESTION_PENDING` or edit generic `QUESTION_PENDING` emit/register coverage in `tests/test_hooks.py` or `tests/test_notification_hook.py`.
- Keep the emitted-event regression tied to live `.emit(...)` call sites under `src/owlbear`, not to docs or research files.

Research: docs/research/question-pending-default-hook-surface.md

[[2026-03-23]] Mon 06:59

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| File: updated tests/test_config.py | Correct seam for the runtime default and explicit settings-construction assertions in `src/owlbear/config.py`. | Keep |
| File: updated tests/test_bootstrap.py | Correct seam for `build_hooks()` registration behavior in `src/owlbear/bootstrap/hooks.py`. | Keep |
| Default notification_events excludes question_pending but explicit config still accepts it | Sound requirement, but the original wording bundled two assertions loosely. | Rewrote into exact default-list and explicit-configuration acceptance checks. |
| build_hooks() default registration omits QUESTION_PENDING | Precise and aligned with the NotificationHook wiring path. | Kept and tightened to exact `HookEvent` assertions. |
| Regression inventories HookEvent members passed to `.emit(...)` in `src/owlbear` | Right invariant, but it needed a mechanical proof seam instead of a free-form inventory. | Rewrote as a source-inspection regression over `.emit(...)` call sites under `src/owlbear`. |
| QUESTION_PENDING enum and explicit NotificationHook registration coverage remain unchanged for non-default configurations | Too vague as written because â€œcoverage remains unchangedâ€ is not an executable RED contract. | Rewrote as an explicit `build_hooks()` assertion for non-default `notification_events=[task_complete, question_pending]`. |
| ruff clean | Standard quality gate for a test-only diff. | Keep |

### Architecture Notes

- `src/owlbear/config.py` is the single runtime source of the default `notification_events` contract, so #968 should pin the default there and separately prove that explicit env/direct configuration can still opt into `question_pending`.
- `src/owlbear/bootstrap/hooks.py` passes `settings.notification_events` directly into `NotificationHook(...).register(hooks)`, which makes default-vs-explicit registration behavior the correct concern for `tests/test_bootstrap.py`.
- `src/owlbear/core/hooks.py` still defines `HookEvent.QUESTION_PENDING`, and existing generic coverage in `tests/test_hooks.py` plus `tests/test_notification_hook.py` already proves explicit emit/register behavior. This RED task should preserve that contract without drifting into the emitter work reserved for #967.
- `tests/test_emit_pre_tool_use.py` already establishes source-inspection as an accepted regression style in this repo, so deriving live emitted events from `.emit(...)` call sites is consistent with existing test patterns.
- TDD sequencing is correct: #962 now depends on this RED task, and #967 remains the later feature task that introduces real `QUESTION_PENDING` emitters instead of speculative defaults.

### Changes Made

- Claimed #968 as `rose-rapid`.
- Rewrote #968 AC to separate default settings, explicit configuration, default hook registration, live-emitter subset regression, and non-default registration requirements.
- Appended this Architecture Review section.
- Prepared #968 for the todo column.

### Dependencies

- Added/Removed/Verified: verified #962 depends on #968 as its RED predecessor; verified #967 remains the follow-on emitter task; verified existing explicit `QUESTION_PENDING` coverage already lives in `tests/test_hooks.py` and `tests/test_notification_hook.py`.

[[2026-03-23]] Mon 08:02

## Test-Writer Notes

- Test file: tests/test_config.py (class TestFromAC_QuestionPendingDefaultCleanup)
- Test file: tests/test_bootstrap.py (class TestFromAC_QuestionPendingDefaultHook)
- Classes: TestFromAC_QuestionPendingDefaultCleanup, TestFromAC_QuestionPendingDefaultHook
- Tests per category: happy 1, edge 3, error 0, boundary 2
- Total: 6 tests, all FAIL
- ruff: new additions clean (8 pre-existing RUF100 in test_config.py are unrelated)
- AC coverage:

  | AC Line | Test(s) | Category |
  |---------|---------|----------|
  | Default notification_events == [task_complete, on_error] | test_default_notification_events_excludes_question_pending | happy |
  | Explicit question_pending via env var | test_env_var_question_pending_explicit_opt_in_while_default_excludes_it | edge |
  | Explicit question_pending via direct constructor | test_direct_constructor_question_pending_explicit_opt_in_while_default_excludes_it | edge |
  | Source-inspection regression | test_default_notification_events_subset_of_live_emitted_hook_events | boundary |
  | build_hooks default: TASK_COMPLETE+ON_ERROR registered, QUESTION_PENDING not | test_default_build_hooks_registers_task_complete_and_on_error_not_question_pending | boundary |
  | build_hooks explicit question_pending still registers | test_explicit_question_pending_config_registers_handler_while_default_excludes_it | edge |

[[2026-03-23]] Mon 08:44

## Builder Notes

- Files changed: src/owlbear/config.py, tests/test_config.py, tests/test_bootstrap.py
- Tests: 6 passed (TestFromAC_QuestionPendingDefaultCleanup x4, TestFromAC_QuestionPendingDefaultHook x2)
- Lint: ruff clean on changed code (8 pre-existing RUF100 in test_config.py unrelated, noted by test-writer)
- Evidence: 6 FAILED -> 6 PASSED; broad suite 251 passed (1 pre-existing Slack skip)
- Fixes applied: Changed notification_events default from ['task_complete','question_pending','on_error'] to ['task_complete','on_error'] in config.py; updated two old conflicting non-TestFromAC assertions in test_config.py and test_bootstrap.py to match new default

[[2026-03-23]] Mon 11:57

## Review Evidence

### Review: #968 - Test question_pending default hook cleanup

### Test Results

- `uv run pytest tests/test_config.py::TestFromAC_QuestionPendingDefaultCleanup tests/test_bootstrap.py::TestFromAC_QuestionPendingDefaultHook -vv --tb=short`: 6 passed, 0 failed (2 optional-dependency warnings from `tests/conftest.py`).
- Passed tests:
  - `TestFromAC_QuestionPendingDefaultCleanup::test_default_notification_events_excludes_question_pending`
  - `TestFromAC_QuestionPendingDefaultCleanup::test_env_var_question_pending_explicit_opt_in_while_default_excludes_it`
  - `TestFromAC_QuestionPendingDefaultCleanup::test_direct_constructor_question_pending_explicit_opt_in_while_default_excludes_it`
  - `TestFromAC_QuestionPendingDefaultCleanup::test_default_notification_events_subset_of_live_emitted_hook_events`
  - `TestFromAC_QuestionPendingDefaultHook::test_default_build_hooks_registers_task_complete_and_on_error_not_question_pending`
  - `TestFromAC_QuestionPendingDefaultHook::test_explicit_question_pending_config_registers_handler_while_default_excludes_it`
- Context run: `uv run pytest tests/test_config.py tests/test_bootstrap.py -q --tb=short` -> 251 passed, 5 failed. Failures are unrelated baseline issues (`slack_sdk` extra missing and #966 RED tests in `TestFromAC_BootstrapHookWorkerSupervisorWiring`).

### Lint Results

- `uv run ruff check src/ tests/` -> 232 `RUF100` baseline findings (repository-wide, pre-existing).
- `uv run ruff check src/owlbear/config.py tests/test_config.py tests/test_bootstrap.py` -> 8 `RUF100` findings at `tests/test_config.py` lines 480/502/530/556/583/599/609/631; these are pre-existing and outside #968 diff.
- Diff evidence (`git show 3b4f263`) confirms #968 introduced no new lint findings.

### Coverage

- `uv run pytest ... --cov --cov-report=term-missing --cov-fail-under=0` on the 6 AC tests: scoped behavior is covered; module totals remain below 90 (`src/owlbear/config.py` 73%, `src/owlbear/bootstrap/hooks.py` 74%) due existing untested paths outside #968.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| default `OwlBearSettings().notification_events` is exactly `[task_complete, on_error]` | `TestFromAC_QuestionPendingDefaultCleanup::test_default_notification_events_excludes_question_pending` | Yes (exact list equality) | COVERED |
| explicit `question_pending` accepted via env override | `...::test_env_var_question_pending_explicit_opt_in_while_default_excludes_it` | Yes (`question_pending` must appear after env override) | COVERED |
| explicit `question_pending` accepted via direct constructor | `...::test_direct_constructor_question_pending_explicit_opt_in_while_default_excludes_it` | Yes (`question_pending` must appear in constructor-configured list) | COVERED |
| default build_hooks registers TASK_COMPLETE + ON_ERROR and not QUESTION_PENDING | `TestFromAC_QuestionPendingDefaultHook::test_default_build_hooks_registers_task_complete_and_on_error_not_question_pending` | Yes (handler presence/absence assertions) | COVERED |
| emitted-event subset regression from `.emit(...)` under `src/owlbear` | `...::test_default_notification_events_subset_of_live_emitted_hook_events` | Yes (fails if default contains non-emitted event) | COVERED |
| explicit build_hooks config still registers QUESTION_PENDING | `...::test_explicit_question_pending_config_registers_handler_while_default_excludes_it` | Yes (requires QUESTION_PENDING handler in explicit config) | COVERED |

#### Security Review

- No security issues found in the #968 diff (`src/owlbear/config.py` default-list change + test updates only).

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `...::test_default_notification_events_excludes_question_pending` | No change | PRESERVED |
| `...::test_env_var_question_pending_explicit_opt_in_while_default_excludes_it` | No change | PRESERVED |
| `...::test_direct_constructor_question_pending_explicit_opt_in_while_default_excludes_it` | No change | PRESERVED |
| `...::test_default_notification_events_subset_of_live_emitted_hook_events` | No change | PRESERVED |
| `...::test_default_build_hooks_registers_task_complete_and_on_error_not_question_pending` | No change | PRESERVED |
| `...::test_explicit_question_pending_config_registers_handler_while_default_excludes_it` | No change | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact list equality, explicit handler count checks, subset-of-emitted invariant |
| Negative/error paths | ADEQUATE | Guard assertions ensure default excludes `question_pending`; behavior is config-path not exception-path |
| Mutation reasoning | STRONG | Re-adding `question_pending` default or removing explicit registration breaks mapped tests |
| Test independence | STRONG | Tests instantiate fresh settings/hooks and avoid shared mutable state |
| Descriptive names | STRONG | Method names encode scenario + expected outcome |

#### Data Safety

- No data safety issues found for this change scope.

#### Implementation-Aware Test Gaps

- No significant untested paths introduced by #968. `build_hooks` already routes `settings.notification_events` directly into `NotificationHook(...).register(hooks)` and both default and explicit paths are exercised.

### Pass 2 - INFORMATIONAL

- Repo baseline currently contains unrelated lint debt and unrelated failing tests in `tests/test_bootstrap.py`; neither is introduced by #968.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| File: updated `tests/test_config.py` | `git show --stat 3b4f263` includes `tests/test_config.py`; AC class at line 646 | N/A | PASS |
| File: updated `tests/test_bootstrap.py` | `git show --stat 3b4f263` includes `tests/test_bootstrap.py`; AC class at line 3099 | N/A | PASS |
| default events exactly `[task_complete, on_error]` | `src/owlbear/config.py:252` default list; test pass in verbose pytest output | `...excludes_question_pending` | PASS |
| explicit env and direct constructor accept `question_pending` | Passing tests at `tests/test_config.py` lines 653 and 668 | `...env_var...`, `...direct_constructor...` | PASS |
| default build_hooks omits QUESTION_PENDING and includes TASK_COMPLETE/ON_ERROR | Passing test at `tests/test_bootstrap.py:3104`; `build_hooks` uses `notification_events=settings.notification_events` at `src/owlbear/bootstrap/hooks.py:52` | `...default_build_hooks...` | PASS |
| source-inspection emitted-event subset regression | Passing AST-based test at `tests/test_config.py:678` scanning `.emit(...)` callsites under `src/owlbear` | `...subset_of_live_emitted_hook_events` | PASS |
| explicit config registers QUESTION_PENDING handler | Passing test at `tests/test_bootstrap.py:3114` | `...explicit_question_pending_config...` | PASS |
| ruff clean | No new #968 lint findings in diff; baseline RUF100 debt remains pre-existing | lint commands above | PASS |

### Verdict: PASS

- Confidence: .91

### Action Taken

- `kanban\kanban-md.exe edit 968 --status docs --release`

[[2026-03-23]] Mon 15:05

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| File: updated tests/test_config.py | git show --stat 3b4f263 confirms file; TestFromAC class at L646 | PASS |
| File: updated tests/test_bootstrap.py | git show --stat 3b4f263 confirms file; TestFromAC class at L3099 | PASS |
| Default notification_events == [task_complete, on_error] | config.py:252 default list; test_default_notification_events_excludes_question_pending passes | PASS |
| Explicit question_pending via env + constructor | tests at L653, L668 pass; guard assertions confirm default excludes it | PASS |
| build_hooks default omits QUESTION_PENDING | test at L3104 passes; handler count == 0 for QUESTION_PENDING | PASS |
| Source-inspection emitted-event subset regression | AST-based test at L678 scans .emit() sites under src/owlbear | PASS |
| Explicit config registers QUESTION_PENDING handler | test at L3114 passes; handler count >= 1 | PASS |
| ruff clean | No new findings in #968 diff; 9 pre-existing (8 RUF100, 1 I001) | PASS |

### Test Results

- pytest (full suite): 3921 passed, 92 failed (all pre-existing), 20 skipped
- #968-specific: 6/6 passed
- ruff: clean on #968 diff

### Architect Quality

- AC specificity: precise, measurable, one-to-one test mapping
- Edge coverage: env var, direct constructor, source-inspection regression all specified
- Design direction: correctly identified config.py + bootstrap/hooks.py seams
- AC quality score: 5/5

### Upstream Commits

- 37b63a5 test: add failing tests (#968, test-writer)
- 3b4f263 feat: remove question_pending from default notification_events (#968, builder)

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 15:05

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| File: updated tests/test_config.py | git show --stat 3b4f263 confirms file; TestFromAC class at L646 | PASS |
| File: updated tests/test_bootstrap.py | git show --stat 3b4f263 confirms file; TestFromAC class at L3099 | PASS |
| Default notification_events == [task_complete, on_error] | config.py:252 default list; test_default_notification_events_excludes_question_pending passes | PASS |
| Explicit question_pending via env + constructor | tests at L653, L668 pass; guard assertions confirm default excludes it | PASS |
| build_hooks default omits QUESTION_PENDING | test at L3104 passes; handler count == 0 for QUESTION_PENDING | PASS |
| Source-inspection emitted-event subset regression | AST-based test at L678 scans .emit() sites under src/owlbear | PASS |
| Explicit config registers QUESTION_PENDING handler | test at L3114 passes; handler count >= 1 | PASS |
| ruff clean | No new findings in #968 diff; 9 pre-existing (8 RUF100, 1 I001) | PASS |

### Test Results

- pytest (full suite): 3921 passed, 92 failed (all pre-existing), 20 skipped
- #968-specific: 6/6 passed
- ruff: clean on #968 diff

### Architect Quality

- AC specificity: precise, measurable, one-to-one test mapping
- Edge coverage: env var, direct constructor, source-inspection regression all specified
- Design direction: correctly identified config.py + bootstrap/hooks.py seams
- AC quality score: 5/5

### Upstream Commits

- 37b63a5 test: add failing tests (#968, test-writer)
- 3b4f263 feat: remove question_pending from default notification_events (#968, builder)

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 15:05

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| File: updated tests/test_config.py | git show --stat 3b4f263 confirms file; TestFromAC class at L646 | PASS |
| File: updated tests/test_bootstrap.py | git show --stat 3b4f263 confirms file; TestFromAC class at L3099 | PASS |
| Default notification_events == [task_complete, on_error] | config.py:252 default list; test_default_notification_events_excludes_question_pending passes | PASS |
| Explicit question_pending via env + constructor | tests at L653, L668 pass; guard assertions confirm default excludes it | PASS |
| build_hooks default omits QUESTION_PENDING | test at L3104 passes; handler count == 0 for QUESTION_PENDING | PASS |
| Source-inspection emitted-event subset regression | AST-based test at L678 scans .emit() sites under src/owlbear | PASS |
| Explicit config registers QUESTION_PENDING handler | test at L3114 passes; handler count >= 1 | PASS |
| ruff clean | No new findings in #968 diff; 9 pre-existing (8 RUF100, 1 I001) | PASS |

### Test Results

- pytest (full suite): 3921 passed, 92 failed (all pre-existing), 20 skipped
- #968-specific: 6/6 passed
- ruff: clean on #968 diff

### Architect Quality

- AC specificity: precise, measurable, one-to-one test mapping
- Edge coverage: env var, direct constructor, source-inspection regression all specified
- Design direction: correctly identified config.py + bootstrap/hooks.py seams
- AC quality score: 5/5

### Upstream Commits

- 37b63a5 test: add failing tests (#968, test-writer)
- 3b4f263 feat: remove question_pending from default notification_events (#968, builder)

### Confidence: .97

### Action: archive

[[2026-03-23]] Mon 15:06

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0840f9f | chore | kanban/tasks/968-*.md | #968 |
