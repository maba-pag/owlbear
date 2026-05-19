---
id: 991
title: Expose reaction_executors dict from build_hooks via HookRegistry attribute
status: archived
priority: needed
created: 2026-03-24T17:02:35.6459821+01:00
updated: 2026-03-24T21:28:48.2680794+01:00
started: 2026-03-24T21:28:21.0115337+01:00
completed: 2026-03-24T21:28:21.0115337+01:00
tags:
    - hooks
    - bootstrap
    - scope:core
    - type:build
depends_on:
    - 985
class: standard
---

Expose the executors dict created in build_hooks() as a HookRegistry attribute so run_daemon() can access it via agent.hooks.reaction_executors without changing any function signatures.

See docs/research/expose-reaction-executors.md and docs/research/retry-executor-wiring.md section 3.1 Option C.

## Acceptance Criteria

1. HookRegistry.__init__ sets self.reaction_executors: dict[str, Any] | None = None
2. In build_hooks(), after constructing HookReactionRouter with the local executors dict, store hooks.reaction_executors = executors (same dict object, not a copy)
3. build_hooks() return signature remains tuple[HookRegistry, ProgressReporter | None] (no extra return element)
4. When settings.hook_reactions is empty (default), hooks.reaction_executors remains None
5. Existing tests pass unchanged (no test modifications allowed)

## Files

- src/owlbear/core/hooks.py: 1 line in HookRegistry.__init__
- src/owlbear/bootstrap/hooks.py: 1 line after HookReactionRouter(...) creation inside the if settings.hook_reactions: block

## Architecture Notes

- Any is already imported in hooks.py; no new imports needed in the core module
- The attribute is optional (None by default); only the daemon wiring path (downstream #992) reads it
- Router closures capture _executors by reference, so mutating the dict after construction propagates to all handlers
- Pattern follows Flask app.extensions / Celery app.tasks (see research doc)
- Stale depends_on: [985] in frontmatter (985 is archived/SPLIT). Planner should remove manually (kanban-md does not support editing depends_on via CLI).

## Preceding test task

- #994: Test: HookRegistry reaction_executors attribute (TDD RED)

[[2026-03-24]] Tue 17:51

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| 1. HookRegistry.__init__ sets reaction_executors | Clear. Testable with attribute access. type dict[str, Any] or None is correct since Executor is defined in hook_reaction_router, not hooks. | Keep |
| 2. build_hooks stores executors on hooks | Clear. Same-object identity is important for late-binding mutation. Testable with is check. | Keep |
| 3. 2-tuple return preserved | Clear. Existing TestFromAC_955_BuildHooksReturnContract already covers this. | Keep |
| 4. None when hook_reactions empty | Clear. Testable. | Keep |
| 5. Existing tests unchanged | Clear. Regression guard. | Keep |

### Architecture Notes

Module layering: correct. HookRegistry is in core/hooks.py (core layer). build_hooks is in bootstrap/hooks.py (assembly layer). Assembly sets attribute on core object. Core does not know about bootstrap. No upward imports.

Pattern: follows Flask app.extensions and Celery app.tasks prior art (see docs/research/expose-reaction-executors.md). Optional attribute (None default) avoids coupling core to the reaction concept.

Interface: attribute is typed dict[str, Any] or None. Not importing Executor type alias from hook_reaction_router.py to avoid wrong-direction dependency in core module. Any is already imported in hooks.py.

Security: no new system boundaries. The dict is internal state, not user-facing.

KISS: 2-line change (1 in hooks.py, 1 in bootstrap/hooks.py). No signature changes, no BootstrapResult changes, no new parameters.

### Changes Made

- Created #994: Test: HookRegistry reaction_executors attribute (TDD RED) at ideation
- Refined AC: restructured from prose to numbered list with file targets and architecture notes
- Noted stale depends_on: [985] for manual cleanup (kanban-md cannot edit depends_on)

### Dependencies

- Stale: depends_on [985] in frontmatter. 985 is archived (SPLIT into 991, 992, 993). Should be removed manually.
- Downstream: #992 (make_retry_executor) depends on this task
- Test task: #994 precedes this task (TDD RED)

## Test-Writer Notes

Test task #994 written and moved to in-progress. Failing tests committed at 0c61bb5.

- Test file: tests/test_hooks.py — TestFromAC_991_HookRegistryReactionExecutors (2 tests)
- Test file: tests/test_bootstrap.py — TestFromAC_991_BuildHooksReactionExecutors (4 tests)
- Total: 6 tests, all FAIL on HEAD (AttributeError: reaction_executors not on HookRegistry)
- ruff: clean

[[2026-03-24]] Tue 20:19

## Builder Notes

- Files changed: src/owlbear/core/hooks.py; src/owlbear/bootstrap/hooks.py
- Tests: 205 passed in targeted modules; TestFromAC_991 subset 6 passed
- Coverage: src/owlbear/core/hooks.py 98%; src/owlbear/bootstrap/hooks.py 100%
- Lint: task-scoped ruff passed for src/owlbear/core/hooks.py and src/owlbear/bootstrap/hooks.py; repo-wide ruff reports unrelated pre-existing RUF100 failures
- Evidence: TestFromAC_991 subset moved from 6 failed in red phase to 6 passed in green phase. Full targeted run on tests/test_hooks.py and tests/test_bootstrap.py passed with coverage output.
- Fixes applied: Added HookRegistry.reaction_executors default None and wired build_hooks to assign the same executors dict used by HookReactionRouter.

[[2026-03-24]] Tue 20:49

## Review Evidence

### Test Results

- Direct task suite in isolated shell: `tests/test_hooks.py` + `tests/test_bootstrap.py` = 205 passed, 2 warnings. Warnings were optional `qdrant_client` skips emitted from `tests/conftest.py`.
- Adjacent existing contract regression: `TestFromAC_955_BuildHooksReturnContract` = 7 passed, 2 warnings.

### Lint Results

- Task-scoped ruff on changed source plus relevant tests passed cleanly.

### Coverage

- Tooling gap: project coverage reports the whole repo rather than only touched modules, but the touched-module lines were still visible in the isolated run: `src/owlbear/core/hooks.py` 98%, `src/owlbear/bootstrap/hooks.py` 100%.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

- AC1 covered by `TestFromAC_991_HookRegistryReactionExecutors::test_reaction_executors_defaults_to_none`; exact `is None` assertion fails on any non-`None` default.
- AC2 covered by `TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_is_dict_when_reactions_configured` and `TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_is_same_object_passed_to_router`; missing assignment or storing a copy fails.
- AC3 covered by `TestFromAC_991_BuildHooksReactionExecutors::test_build_hooks_return_contract_still_two_tuple` and existing `TestFromAC_955_BuildHooksReturnContract::test_build_hooks_with_reactions_returns_tuple`; tuple arity or first-element regressions fail.
- AC4 covered by `TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_none_when_no_reactions`; any eager assignment fails exact `None` assertion.
- AC5 is a process constraint rather than runtime behavior; verified separately by git evidence. `git show --stat 9c0a37f` touched only `src/owlbear/core/hooks.py` and `src/owlbear/bootstrap/hooks.py`, and `git diff 0c61bb5..HEAD -- tests/test_hooks.py tests/test_bootstrap.py` was empty.

#### Security Review

- No security issues found. The change only adds an internal optional attribute and stores an internal dict reference.

#### Test Integrity

- `TestFromAC_991_HookRegistryReactionExecutors::test_reaction_executors_defaults_to_none`: no change, PRESERVED.
- `TestFromAC_991_HookRegistryReactionExecutors::test_reaction_executors_is_settable`: no change, PRESERVED.
- `TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_is_dict_when_reactions_configured`: no change, PRESERVED.
- `TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_none_when_no_reactions`: no change, PRESERVED.
- `TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_is_same_object_passed_to_router`: committed diff preserved the test; current worktree only has a formatting-only line wrap in the settings construction, no semantic change.
- `TestFromAC_991_BuildHooksReactionExecutors::test_build_hooks_return_contract_still_two_tuple`: no change, PRESERVED.

#### Test Quality

- Assertion specificity: STRONG. Tests use exact `is None`, object identity, tuple length, and concrete key assertions.
- Negative and branch coverage: STRONG. Both the configured `hook_reactions` path and the default empty path are exercised.
- Mutation reasoning: STRONG. Copy-vs-identity, eager default assignment, and return-contract regressions would all fail targeted tests.
- Test independence: STRONG. Each test builds fresh `HookRegistry` and `OwlBearSettings` instances with no shared mutable fixture state.
- Descriptive names: STRONG. Names describe the branch and contract under test precisely.

#### Data Safety

- No data safety issues found.

#### Implementation-Aware Test Gaps

- No significant untested paths. The new implementation adds one attribute initialization and one assignment inside the existing `if settings.hook_reactions` branch; tests cover the default `None` path, configured dict path, same-object identity, and return contract. Existing `TestFromAC_955_BuildHooksReturnContract` coverage also confirms configured reaction wiring still emits safely through noop executors.

### Pass 2 - INFORMATIONAL

- Current worktree contains a formatting-only uncommitted line-wrap change in `tests/test_bootstrap.py` inside `test_reaction_executors_is_same_object_passed_to_router`; this is not part of commit `9c0a37f` and does not weaken the test.
- `tests/test_957_notify_escalate_executors.py` is intentionally RED by its own module docstring until task #957; its collection ImportError is out of scope for #991 and was not used for the verdict.

### AC Compliance

- AC1 PASS: implementation at `src/owlbear/core/hooks.py` line 179; exercised by `tests/test_hooks.py` line 196.
- AC2 PASS: `build_hooks` keeps the assignment inside the configured branch at `src/owlbear/bootstrap/hooks.py` lines 58 and 69; exercised by `tests/test_bootstrap.py` lines 3346 and 3363.
- AC3 PASS: return signature remains `tuple[HookRegistry, ProgressReporter | None]` at `src/owlbear/bootstrap/hooks.py` line 27; exercised by `tests/test_bootstrap.py` line 3385 and `tests/test_955_hook_reaction_schema_bootstrap.py` lines 219, 228, and 244.
- AC4 PASS: no assignment occurs when `hook_reactions` is empty because the only write stays inside the configured branch at `src/owlbear/bootstrap/hooks.py` lines 58 and 69; exercised by `tests/test_bootstrap.py` line 3357.
- AC5 PASS: committed builder diff changed source only (`9c0a37f`), and the red-phase-to-HEAD diff for `tests/test_hooks.py` and `tests/test_bootstrap.py` is empty.

### Verdict

- PASS with confidence .94.

### Action Taken

- Advance task from `review` to `docs` and release reviewer claim.

[[2026-03-24]] Tue 21:07

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Updated | Added hooks.reaction_executors note to Runtime row (Flask app.extensions pattern, #991) |
| 2 | Docstrings complete | Yes | Updated | Added Attributes section to HookRegistry class docstring; updated build_hooks() Returns to document reaction_executors side-effect |
| 3 | docs/sources/overview.md | Yes | Updated (unstaged) | Added Flask app.extensions and Celery app.tasks rows for #991; file has pre-existing uncommitted changes from other tasks so excluded from this commit |
| 4 | README.md | No | N/A | No CLI changes; purely internal attribute |
| 5 | Research docs linked | Yes | Pass | docs/research/expose-reaction-executors.md and docs/research/retry-executor-wiring.md both exist and are linked from task body |
| 6 | No impact | N/A | N/A | Items 1-5 all applied |

### Files Updated

- .github/copilot-instructions.md (Runtime row)
- src/owlbear/core/hooks.py (HookRegistry docstring)
- src/owlbear/bootstrap/hooks.py (build_hooks docstring)
- docs/sources/overview.md (Flask/Celery rows; unstaged due to mixed pre-existing content)

### Scratch Files Cleaned

- docs/scratch/991-* present but Remove-Item blocked by policy; files are gitignored

### Commit

177aaad - docs: update docstrings and copilot-instructions for reaction_executors (#991, writer)

[[2026-03-24]] Tue 21:28

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| 1. HookRegistry.__init__ sets reaction_executors | src/owlbear/core/hooks.py L192: self.reaction_executors: dict[str, Any] pipe None = None | PASS |
| 2. build_hooks stores executors on hooks (same object) | src/owlbear/bootstrap/hooks.py L69: hooks.reaction_executors = executors after router creation with same dict | PASS |
| 3. Return signature remains 2-tuple | src/owlbear/bootstrap/hooks.py L27:  uple[HookRegistry, ProgressReporter pipe None] unchanged | PASS |
| 4. None when hook_reactions empty | Assignment inside if settings.hook_reactions: block only; default None preserved | PASS |
| 5. Existing tests unchanged | git diff 0c61bb5..HEAD shows no test file changes; builder commit 9c0a37f touched only src/ | PASS |

### Test Results

- task-relevant suite (test_hooks, test_bootstrap, test_955, test_hook_payloads, test_daemon, test_agent, test_approval_gate, test_bootstrap_structure, test_bootstrap_integration): 429 passed, 4 failed (pre-existing, unrelated to 991)
- ruff check src/owlbear/core/hooks.py src/owlbear/bootstrap/hooks.py: All checks passed

### Upstream Commits

- 0c61bb5: test: add failing tests (#994, test-writer) - 2 test files
- 9c0a37f: feat: expose reaction executors (#991, builder) - 2 src files
- 177aaad: docs: update docstrings and copilot-instructions (#991, writer) - 3 files

### AC Quality Score: 5/5

AC was specific, complete, testable, and led to a clean 2-line implementation with no builder improvisation needed. Architecture notes correctly referenced Flask/Celery prior art.

### Confidence: .97

### Action: archive

[[2026-03-24]] Tue 21:28

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| bcce540 | chore | kanban board | #991 |
