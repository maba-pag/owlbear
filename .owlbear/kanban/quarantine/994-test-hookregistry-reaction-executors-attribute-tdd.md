---
id: 994
title: 'Test: HookRegistry reaction_executors attribute (TDD RED)'
status: archived
priority: needed
created: 2026-03-24T17:50:44.031777+01:00
updated: 2026-03-24T22:06:16.2062122+01:00
started: 2026-03-24T22:05:14.6352434+01:00
completed: 2026-03-24T22:05:14.6352434+01:00
tags:
    - hooks
    - bootstrap
    - scope:core
    - test
    - type:test
class: standard
---

TDD RED tests for #991. Write failing tests that verify the reaction_executors attribute on HookRegistry and its wiring in build_hooks().

## Acceptance Criteria

1. Add TestFromAC_991_HookRegistryReactionExecutors class in tests/test_hooks.py:
   - test_reaction_executors_defaults_to_none: assert HookRegistry().reaction_executors is None
   - test_reaction_executors_is_settable: assign a dict and read it back via attribute access
2. Add TestFromAC_991_BuildHooksReactionExecutors class in tests/test_bootstrap.py:
   - test_reaction_executors_is_dict_when_reactions_configured: build_hooks() with non-empty hook_reactions returns hooks where hooks.reaction_executors is a dict with keys notify, retry, escalate
   - test_reaction_executors_none_when_no_reactions: build_hooks() with empty hook_reactions returns hooks where hooks.reaction_executors is None
   - test_reaction_executors_is_same_object_passed_to_router: the dict on hooks.reaction_executors is the same object (identity check with is) passed to HookReactionRouter constructor
   - test_build_hooks_return_contract_still_two_tuple: return is still tuple of length 2 with HookRegistry first
3. All tests fail on HEAD (RED phase requirement)
4. Files: tests/test_hooks.py and tests/test_bootstrap.py
5. Ruff check passes on both test files

## Test-Writer Notes

- Test file: tests/test_hooks.py (TestFromAC_991_HookRegistryReactionExecutors)
- Test file: tests/test_bootstrap.py (TestFromAC_991_BuildHooksReactionExecutors)
- Classes: TestFromAC_991_HookRegistryReactionExecutors (2 tests), TestFromAC_991_BuildHooksReactionExecutors (4 tests)
- Tests per category: happy 4, edge 2, error 0, boundary 0
- Total: 6 tests, all FAIL (AttributeError: 'HookRegistry' object has no attribute 'reaction_executors')
- ruff: clean (All checks passed!)
- Commit: 0c61bb5 test: add failing tests for reaction_executors attribute (#994, test-writer)
- AC coverage:
  AC1 defaults_to_none -> test_reaction_executors_defaults_to_none
  AC1 is_settable -> test_reaction_executors_is_settable
  AC2 dict_keys -> test_reaction_executors_is_dict_when_reactions_configured
  AC2 same_object_identity -> test_reaction_executors_is_same_object_passed_to_router
  AC3 2-tuple preserved -> test_build_hooks_return_contract_still_two_tuple
  AC4 None default -> test_reaction_executors_none_when_no_reactions

[[2026-03-24]] Tue 20:42

## Builder Notes

- Files changed: None in this builder invocation (green-on-arrival). Existing local edits were already present in src/owlbear/core/hooks.py, src/owlbear/bootstrap/hooks.py, and tests/test_bootstrap.py before this build pass.
- Tests: 6 passed on the acceptance classes. Coverage: not captured for this no-change task because coverage startup was repeatedly interrupted by Windows WMI KeyboardInterrupt in this environment.
- Lint: ruff clean on task-scoped files.
- Evidence: scoped pytest reported 6 passed, 2 warnings in 2.62s; task-scoped ruff reported All checks passed.
- Fixes applied: None. HookRegistry already exposes reaction_executors with None default and build_hooks already stores the same executors dict object on hooks when reactions are configured.

[[2026-03-24]] Tue 21:16

## Review Evidence

## Review: #994 - Test: HookRegistry reaction_executors attribute (TDD RED)

### Test Results

- Scoped pytest on tests/test_hooks.py and tests/test_bootstrap.py passed: 205 passed, 0 failed, 2 warnings, 10.54s.
- Warnings were the existing optional-dependency skips for qdrant_client in tests/conftest.py.
- The first foreground pytest attempt hit a transient Python startup/import-cache failure before test collection. Re-running in an isolated shell with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and pytest_asyncio.plugin completed cleanly.

### Lint Results

- Ruff passed on tests/test_hooks.py, tests/test_bootstrap.py, src/owlbear/core/hooks.py, and src/owlbear/bootstrap/hooks.py.

### Coverage

- src/owlbear/bootstrap/hooks.py: 100%.
- src/owlbear/core/hooks.py: 98%; only lines 309-310 were missed. The reviewed reaction_executors lines are covered.
- The overall coverage total from plain coverage mode is not relevant to this card because the project source list is global. The reviewed modules themselves meet the bar.

### Pass 1 - Critical

#### Test-writer AC coverage

- AC1 default None: tests/test_hooks.py:196 maps to test_reaction_executors_defaults_to_none. This would fail if HookRegistry lacked the attribute or initialized it to anything other than None. Verdict: COVERED.
- AC1 settable: tests/test_hooks.py:201 maps to test_reaction_executors_is_settable. This would fail if the attribute were missing, immutable, or copied instead of preserving object identity. Verdict: COVERED.
- AC2 configured dict keys: tests/test_bootstrap.py:3346 maps to test_reaction_executors_is_dict_when_reactions_configured. This would fail if build_hooks omitted the dict or any of notify, retry, escalate. Verdict: COVERED.
- AC2 no reactions means None: tests/test_bootstrap.py:3357 maps to test_reaction_executors_none_when_no_reactions. This would fail if build_hooks left an empty dict or stale executors on the registry. Verdict: COVERED.
- AC2 identity with router argument: tests/test_bootstrap.py:3363 maps to test_reaction_executors_is_same_object_passed_to_router. This would fail if build_hooks copied or rebuilt the executors mapping. Verdict: COVERED.
- AC2 return contract stays two-tuple: tests/test_bootstrap.py:3385 maps to test_build_hooks_return_contract_still_two_tuple. This would fail if the return shape changed or the first element stopped being HookRegistry. Verdict: COVERED.
- AC3 historical RED requirement: corroborated by task history and git history. The test-writer note records 6 failures with AttributeError, and git log shows test commit 0c61bb5 preceding builder commit 9c0a37f that introduced the source changes.
- AC4 file scope: the required classes are present in tests/test_hooks.py:193 and tests/test_bootstrap.py:3338.
- AC5 ruff on the two test files: verified clean in the scoped Ruff run.
- Result: no MISSING and no LAX coverage findings.

#### Security review

- No security issues found. The reviewed code adds a nullable attribute to HookRegistry and stores a local executors dict in build_hooks. No secrets, subprocess input, SQL, path handling, or new dependencies are involved.

#### Test integrity

- TestFromAC_991_HookRegistryReactionExecutors::test_reaction_executors_defaults_to_none: PRESERVED.
- TestFromAC_991_HookRegistryReactionExecutors::test_reaction_executors_is_settable: PRESERVED.
- TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_is_dict_when_reactions_configured: PRESERVED.
- TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_none_when_no_reactions: PRESERVED.
- TestFromAC_991_BuildHooksReactionExecutors::test_reaction_executors_is_same_object_passed_to_router: PRESERVED. Diff versus 0c61bb5 is formatting-only reflow of the OwlBearSettings call; assertions are unchanged.
- TestFromAC_991_BuildHooksReactionExecutors::test_build_hooks_return_contract_still_two_tuple: PRESERVED.
- Result: no weakened or removed TestFromAC coverage.

#### Test quality

- Assertion specificity: STRONG. Tests check exact None identity, exact object identity, explicit keys, tuple type, and tuple length.
- Negative and branch coverage: ADEQUATE. The only meaningful branch in the reviewed implementation is configured reactions versus no reactions, and both paths are exercised.
- Mutation resistance: STRONG. Changing None to an empty dict, dropping a key, copying the executors mapping, or changing the return contract would all fail these tests.
- Test independence: STRONG. Each test creates fresh HookRegistry or OwlBearSettings state and does not depend on execution order.
- Descriptive names: STRONG. The names directly state scenario and expected behavior.

#### Data safety

- No data safety issues found. The reviewed code does not persist data, perform multi-step writes, or add concurrency-sensitive state transitions.

#### Implementation-aware test gaps

- No significant untested paths found. The implementation adds one constructor assignment in src/owlbear/core/hooks.py:191 and one conditional wiring branch in src/owlbear/bootstrap/hooks.py:63-73. The tests cover default state, configured state, no-reaction state, identity preservation, and the unchanged return contract.

### Pass 2 - Informational

- Current git status shows one local modification in tests/test_bootstrap.py. Reviewing the word diff against 0c61bb5 shows only a formatting-only reflow inside one TestFromAC method and no semantic assertion change.

### AC Compliance

- HookRegistry initializes reaction_executors to None: src/owlbear/core/hooks.py:191 plus tests/test_hooks.py:196. Status: PASS.
- HookRegistry attribute is settable and preserves identity: tests/test_hooks.py:201. Status: PASS.
- build_hooks stores a dict with notify, retry, escalate when hook_reactions is non-empty: src/owlbear/bootstrap/hooks.py:67-73 plus tests/test_bootstrap.py:3346. Status: PASS.
- build_hooks leaves reaction_executors as None when hook_reactions is empty: conditional branch at src/owlbear/bootstrap/hooks.py:62-73 plus tests/test_bootstrap.py:3357. Status: PASS.
- build_hooks stores the same object passed to HookReactionRouter: src/owlbear/bootstrap/hooks.py:67-73 plus tests/test_bootstrap.py:3363. Status: PASS.
- build_hooks still returns a two-tuple with HookRegistry first: function contract at src/owlbear/bootstrap/hooks.py:27 and tests/test_bootstrap.py:3385. Status: PASS.
- Historical RED requirement was satisfied before implementation: task note plus commit order 0c61bb5 before 9c0a37f. Status: PASS.
- Required files are in scope: tests/test_hooks.py and tests/test_bootstrap.py. Status: PASS.
- Ruff passes on both required test files: verified in scoped Ruff run. Status: PASS.

### Verdict

- PASS with confidence .93.

### Action Taken

- Review evidence appended.
- Task advanced to docs.
- Reviewer claim released.

[[2026-03-24]] Tue 21:21

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Documented via #991; no new behavior added |
| 2 | Docstrings complete | Yes | Pass | HookRegistry.reaction_executors docstring at core/hooks.py:183; build_hooks() docstring at bootstrap/hooks.py:40 accurate |
| 3 | docs/sources/overview.md | No | N/A | No external patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase |
| 6 | No impact | Yes | Pass | Test-only task; docstrings correct from #991 implementation |

### Files Updated

- None

### Scratch Files Cleaned

- docs/scratch/994-builder-notes.tmp

[[2026-03-24]] Tue 22:04

## Audit

### AC Verification

| AC | Evidence | Status |
|-----|----------|--------|
| AC1: TestFromAC in test_hooks.py (2 tests) | tests/test_hooks.py:193, defaults_to_none + is_settable present and passing | PASS |
| AC2: TestFromAC in test_bootstrap.py (4 tests) | tests/test_bootstrap.py:3338, all 4 tests present and passing | PASS |
| AC3: Tests fail on HEAD (RED phase) | Commit 0c61bb5 precedes impl 9c0a37f | PASS |
| AC4: Files test_hooks.py and test_bootstrap.py | Both exist with correct classes | PASS |
| AC5: Ruff clean | uv run ruff check: All checks passed | PASS |

### Test Results

- Full suite: 4264 passed, 35 failed (all pre-existing), 20 skipped, 0 regressions
- Task-scoped: 6/6 pass (TestFromAC_991 classes)
- Ruff: clean on all task-scoped files

### AC Quality Score: 5

AC was specific and complete: exact class names, method names, and assertion expectations prescribed. Both branches covered (reactions configured vs empty). No builder improvisation needed.

### Confidence: .97

### Action: archive

[[2026-03-24]] Tue 22:05

## Audit

### AC Verification

| AC | Evidence | Status |
|-----|----------|--------|
| AC1: TestFromAC in test_hooks.py (2 tests) | tests/test_hooks.py:193, defaults_to_none + is_settable present and passing | PASS |
| AC2: TestFromAC in test_bootstrap.py (4 tests) | tests/test_bootstrap.py:3338, all 4 tests present and passing | PASS |
| AC3: Tests fail on HEAD (RED phase) | Commit 0c61bb5 precedes impl 9c0a37f | PASS |
| AC4: Files test_hooks.py and test_bootstrap.py | Both exist with correct classes | PASS |
| AC5: Ruff clean | uv run ruff check: All checks passed | PASS |

### Test Results

- Full suite: 4264 passed, 35 failed (all pre-existing), 20 skipped, 0 regressions
- Task-scoped: 6/6 pass (TestFromAC_991 classes)
- Ruff: clean on all task-scoped files

### AC Quality Score: 5

AC was specific and complete: exact class names, method names, and assertion expectations prescribed. Both branches covered (reactions configured vs empty). No builder improvisation needed.

### Confidence: .97

### Action: archive

[[2026-03-24]] Tue 22:06

## Commits

f779acf chore: archive task #994 (#994, auditor) - kanban board files
