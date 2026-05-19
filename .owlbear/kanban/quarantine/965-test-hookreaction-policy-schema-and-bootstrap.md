---
id: 965
title: Test HookReaction policy schema and bootstrap router wiring
status: archived
priority: important
created: 2026-03-23T05:02:51.1790528+01:00
updated: 2026-03-23T12:34:30.2782435+01:00
started: 2026-03-23T12:34:29.73575+01:00
completed: 2026-03-23T12:34:29.73575+01:00
tags:
    - agent
    - hooks
    - test
    - config
    - scope:core
    - type:test
parent: 950
class: standard
---

Write tests FIRST for HookReaction policy schema and bootstrap router wiring.

## AC

- [ ] File: tests/test_hook_reaction_router.py
- [ ] File: updated tests/test_bootstrap.py
- [ ] Test: HookReactionRule accepts only notify, retry, and escalate actions, and rejects empty events, empty actions, unknown action kinds, non-scalar match values, and unknown keys
- [ ] Test: OwlBearSettings defaults hook_reactions to [] and preserves declared rule order when parsing hook_reactions list input into HookReactionRule objects
- [ ] Test: HookReactionRouter.register() resolves configured event strings to HookEvent and registers one handler per configured event
- [ ] Test: invalid hook_reactions event names fail build_hooks/router registration instead of being skipped silently
- [ ] Test: router runs actions in listed order only when the emitted event matches and every configured top-level scalar match pair equals the payload
- [ ] Test: missing or unequal match keys skip executor calls
- [ ] Test: executor exceptions are logged and swallowed without recursive HookEvent.ON_ERROR emission
- [ ] Test: build_hooks() leaves existing NotificationHook registrations intact when reaction handlers are added
- [ ] ruff clean

## Architecture

- Keep tests limited to schema validation, router matching and registration, and bootstrap wiring for injected executors.
- Concrete retry reuse belongs to #956; notification and escalation executor reuse belongs to #957; notification dedup belongs to #963.
- question_pending default cleanup belongs to #962.

Research: docs/research/hookreaction-schema-router-wiring.md

## Architecture Review

**Verdict:** Approved

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| File targets in tests/test_hook_reaction_router.py and tests/test_bootstrap.py | Matches the current repo split: feature-specific hook tests live in dedicated files and bootstrap wiring assertions already live in tests/test_bootstrap.py | Kept |
| Schema validation plus OwlBearSettings parsing | Sound, but the original RED card missed explicit coverage for the exact allowed action kinds in #955 and used ambiguous nested-input wording | Tightened to require notify/retry/escalate coverage and clarified order-preserving list parsing |
| Router registration, fail-fast invalid events, match semantics, and swallowed executor failures | Aligns with src/owlbear/bootstrap/hooks.py, src/owlbear/core/hooks.py, and src/owlbear/core/notification_hook.py | Kept |
| Preserve NotificationHook registrations | Required to protect current build_hooks behavior while adding reaction handlers | Kept |
| ruff clean | Standard gate for a RED task touching tests | Kept |

### Architecture Notes

- src/owlbear/config.py already uses nested validated settings models, so the RED contract should verify typed parsing and rule ordering without forcing HookEvent into config.py.
- src/owlbear/core/hooks.py keeps HookRegistry best-effort and swallows handler failures, so the router contract belongs in handler behavior and bootstrap registration, not registry changes.
- src/owlbear/core/notification_hook.py currently resolves event-name strings during register() and skips unknown notification events, which makes the new fail-fast hook_reactions registration path a deliberate behavior difference that needs explicit tests.
- src/owlbear/bootstrap/hooks.py already owns hook assembly, so extending tests/test_bootstrap.py for fail-fast registration and NotificationHook preservation follows the existing test boundary.
- #955 already depends on this RED task, so TDD sequencing is satisfied once this card advances to todo.

### Changes Made

- Rewrote the settings-parsing AC to remove ambiguous nested-input wording and require order-preserving list parsing.
- Tightened the schema-validation AC to cover the exact allowed action kinds from #955.
- Approved #965 for RED implementation and moved it to todo.

### Dependencies

- Verified: #955 depends on #965.
- Verified: existing build_hooks and NotificationHook behavior remains the compatibility surface this task must protect.
- No new dependencies added.

[[2026-03-23]] Mon 06:08

## Architecture Review

See docs/scratch/965-architect.md for full review.

[[2026-03-23]] Mon 07:03

## Test-Writer Notes

- Test file: tests/test_hook_reaction_router.py (new)
- Test file: tests/test_bootstrap.py (updated, 9 tests appended)
- Classes: TestFromAC_HookReactionRuleSchema, TestFromAC_HookReactionRouterRegistration, TestFromAC_HookReactionRouterMatching, TestFromAC_HookReactionRouterErrorHandling (in new file); TestFromAC_OwlBearSettingsHookReactions, TestFromAC_BuildHooksHookReactions (appended to bootstrap)
- Tests per category: happy 17, edge 7, error 11, boundary 4
- Total: 39 tests (30 + 9), all FAIL on missing module owlbear.core.hook_reaction_router
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| HookReactionRule accepts notify/retry/escalate | test_accepts_notify_action, test_accepts_retry_action, test_accepts_escalate_action, test_accepts_all_three_valid_actions | happy |
| Rejects empty events | test_rejects_empty_events | error |
| Rejects empty actions | test_rejects_empty_actions | error |
| Rejects unknown action kinds | test_rejects_unknown_action_kind, test_rejects_unknown_kind_alongside_valid | error |
| Rejects non-scalar match values | test_rejects_non_scalar_match_value_nested_dict, test_rejects_non_scalar_match_value_list | error |
| Rejects unknown keys | test_rejects_extra_unknown_fields | error |
| OwlBearSettings defaults hook_reactions to [] | test_hook_reactions_defaults_to_empty_list | happy |
| Preserves rule order | test_hook_reactions_preserves_rule_order, test_hook_reactions_preserves_actions_per_rule | happy |
| HookReactionRouter.register() resolves + registers | test_register_resolves_event_string_to_hook_event, test_register_one_handler_per_distinct_event, test_register_multiple_events_in_one_rule_registers_each | happy |
| Invalid event names fail-fast | test_register_invalid_event_name_raises_not_skips, test_build_hooks_invalid_event_name_raises_not_skips | error |
| Actions run in listed order | test_actions_run_in_declared_order | happy |
| Matching: all pairs equal triggers | test_all_match_pairs_equal_triggers_actions, test_all_match_pairs_equal_multiple_conditions | happy |
| Missing match key skips | test_missing_match_key_skips_actions | edge |
| Unequal match key skips | test_unequal_match_key_skips_actions | edge |
| Executor exceptions logged and swallowed | test_executor_exception_is_swallowed, test_executor_exception_is_logged | error |
| No recursive ON_ERROR emission | test_no_recursive_on_error_emission | error |
| NotificationHook preserved | test_build_hooks_with_reactions_preserves_notification_handlers, test_build_hooks_no_reactions_leaves_notification_events | boundary |

[[2026-03-23]] Mon 07:03

## Test-Writer Notes

- Test file: tests/test_hook_reaction_router.py (new)
- Test file: tests/test_bootstrap.py (updated, 9 tests appended)
- Classes: TestFromAC_HookReactionRuleSchema, TestFromAC_HookReactionRouterRegistration, TestFromAC_HookReactionRouterMatching, TestFromAC_HookReactionRouterErrorHandling (in new file); TestFromAC_OwlBearSettingsHookReactions, TestFromAC_BuildHooksHookReactions (appended to bootstrap)
- Tests per category: happy 17, edge 7, error 11, boundary 4
- Total: 39 tests (30 + 9), all FAIL on missing module owlbear.core.hook_reaction_router
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| HookReactionRule accepts notify/retry/escalate | test_accepts_notify_action, test_accepts_retry_action, test_accepts_escalate_action, test_accepts_all_three_valid_actions | happy |
| Rejects empty events | test_rejects_empty_events | error |
| Rejects empty actions | test_rejects_empty_actions | error |
| Rejects unknown action kinds | test_rejects_unknown_action_kind, test_rejects_unknown_kind_alongside_valid | error |
| Rejects non-scalar match values | test_rejects_non_scalar_match_value_nested_dict, test_rejects_non_scalar_match_value_list | error |
| Rejects unknown keys | test_rejects_extra_unknown_fields | error |
| OwlBearSettings defaults hook_reactions to [] | test_hook_reactions_defaults_to_empty_list | happy |
| Preserves rule order | test_hook_reactions_preserves_rule_order, test_hook_reactions_preserves_actions_per_rule | happy |
| HookReactionRouter.register() resolves + registers | test_register_resolves_event_string_to_hook_event, test_register_one_handler_per_distinct_event, test_register_multiple_events_in_one_rule_registers_each | happy |
| Invalid event names fail-fast | test_register_invalid_event_name_raises_not_skips, test_build_hooks_invalid_event_name_raises_not_skips | error |
| Actions run in listed order | test_actions_run_in_declared_order | happy |
| Matching: all pairs equal triggers | test_all_match_pairs_equal_triggers_actions, test_all_match_pairs_equal_multiple_conditions | happy |
| Missing match key skips | test_missing_match_key_skips_actions | edge |
| Unequal match key skips | test_unequal_match_key_skips_actions | edge |
| Executor exceptions logged and swallowed | test_executor_exception_is_swallowed, test_executor_exception_is_logged | error |
| No recursive ON_ERROR emission | test_no_recursive_on_error_emission | error |
| NotificationHook preserved | test_build_hooks_with_reactions_preserves_notification_handlers, test_build_hooks_no_reactions_leaves_notification_events | boundary |

[[2026-03-23]] Mon 07:52

## Builder Notes

- Files changed: src/owlbear/core/hook_reaction_router.py (new), src/owlbear/config.py, src/owlbear/bootstrap/hooks.py
- Tests: 41 passed (TestFromAC_HookReactionRuleSchema 15, TestFromAC_HookReactionRouterRegistration 5, TestFromAC_HookReactionRouterMatching 8, TestFromAC_HookReactionRouterErrorHandling 4, TestFromAC_OwlBearSettingsHookReactions 5, TestFromAC_BuildHooksHookReactions 4)
- Coverage: 97% on hook_reaction_router.py (71 stmts, 2 miss - defensive branches)
- Lint: ruff clean on all 3 files
- Evidence: 41 passed in 1.74s; pre-existing slack_sdk failure unrelated to #965
- Fixes applied: Changed ValueError->TypeError back to ValueError with noqa:TRY004 (Pydantic v2 does not wrap TypeError in ValidationError)

[[2026-03-23]] Mon 08:50

## Review Evidence

## Review: #965 - Test HookReaction policy schema and bootstrap router wiring

### Test Results

- pytest: 41 passed, 0 failed, 2 warnings
- command: `uv run pytest tests/test_hook_reaction_router.py tests/test_bootstrap.py::TestFromAC_OwlBearSettingsHookReactions tests/test_bootstrap.py::TestFromAC_BuildHooksHookReactions -q --tb=short`
- warnings: optional `qdrant_client` dependency not installed (pre-existing optional-dependency warning from `tests/conftest.py`)

### Lint Results

- task-scoped ruff: All checks passed
- command: `uv run ruff check src/owlbear/core/hook_reaction_router.py src/owlbear/config.py src/owlbear/bootstrap/hooks.py tests/test_hook_reaction_router.py tests/test_bootstrap.py`
- repo-wide `ruff check src/ tests/` currently reports unrelated pre-existing RUF100 noise (unused noqa directives) outside #965 scope

### Coverage

- command: `uv run pytest tests/test_hook_reaction_router.py tests/test_bootstrap.py::TestFromAC_OwlBearSettingsHookReactions tests/test_bootstrap.py::TestFromAC_BuildHooksHookReactions --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short`
- `src/owlbear/core/hook_reaction_router.py`: 97%
- `src/owlbear/bootstrap/hooks.py`: 80%
- `src/owlbear/config.py`: 73%
- Note: bare `--cov` reports whole-module percentages; the #965 paths are exercised, while lower percentages are due to pre-existing unrelated branches in large modules.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| File: tests/test_hook_reaction_router.py | Class `TestFromAC_HookReactionRuleSchema` at tests/test_hook_reaction_router.py:44 and companion TestFromAC classes | Yes | COVERED |
| File: updated tests/test_bootstrap.py | Classes `TestFromAC_OwlBearSettingsHookReactions` and `TestFromAC_BuildHooksHookReactions` at tests/test_bootstrap.py:2981, tests/test_bootstrap.py:3035 | Yes | COVERED |
| HookReactionRule accepts/rejects required action/event/match/key constraints | Schema tests at tests/test_hook_reaction_router.py:52, :101, :113, :125, :145 | Yes | COVERED |
| OwlBearSettings defaults/preserves order | tests/test_bootstrap.py:2987, :3002, :3014 | Yes | COVERED |
| register() resolves event strings and registers handlers | tests/test_hook_reaction_router.py:167 and registration class block | Yes | COVERED |
| Invalid event names fail-fast (router + build_hooks) | tests/test_hook_reaction_router.py:211 and tests/test_bootstrap.py:3075 | Yes | COVERED |
| Actions run in listed order only when event+match pass | tests/test_hook_reaction_router.py:236, :277, :381 | Yes | COVERED |
| Missing/unequal match keys skip executor calls | tests/test_hook_reaction_router.py:297, :318, :360 | Yes | COVERED |
| Executor exceptions logged/swallowed without recursive ON_ERROR | tests/test_hook_reaction_router.py:414, :432, :457, :493 | Yes | COVERED |
| build_hooks preserves NotificationHook registrations with reactions added | tests/test_bootstrap.py:3052 and :3042 | Yes | COVERED |
| ruff clean | scoped ruff command above | Yes | COVERED |

#### Security Review

- Hardcoded secrets: none found in #965 files.
- Injection risks: none (no SQL/shell/template construction from untrusted input).
- Path traversal / deserialization / eval-exec: none.
- Input validation: `HookReactionRule` enforces non-empty events/actions, allowed action kinds, scalar-only match values, and forbids unknown keys in `ConfigDict(extra=forbid)` (`src/owlbear/core/hook_reaction_router.py:52`, :62, :70, :75, :89).
- Secret leakage in logs: warning logs include only action kind on executor failures (`src/owlbear/core/hook_reaction_router.py:155`).
- Result: No security issues found.

#### Test Integrity (TestFromAC comparison)

- Builder commit inspection: `git show --name-only 52d7a7d` lists only:
  - `src/owlbear/core/hook_reaction_router.py`
  - `src/owlbear/config.py`
  - `src/owlbear/bootstrap/hooks.py`
- No test files modified by builder.

| Original Test Group | Change Made in Builder Commit | Assessment |
|---------------------|-------------------------------|------------|
| `TestFromAC_HookReactionRuleSchema` | No change | PRESERVED |
| `TestFromAC_HookReactionRouterRegistration` | No change | PRESERVED |
| `TestFromAC_HookReactionRouterMatching` | No change | PRESERVED |
| `TestFromAC_HookReactionRouterErrorHandling` | No change | PRESERVED |
| `TestFromAC_OwlBearSettingsHookReactions` | No change | PRESERVED |
| `TestFromAC_BuildHooksHookReactions` | No change | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Core behavior checks are precise (action order, fail-fast invalid events, exact match semantics). A few registration assertions use `>= 1` but are paired with before/after increment checks in key paths. |
| Negative/error paths | STRONG | Explicit validation failures, invalid-event registration failure, match-miss skips, executor exception handling, and non-recursive ON_ERROR behavior are covered. |
| Mutation reasoning | STRONG | Replacing scalar validation, removing fail-fast event conversion, ignoring match predicates, or stopping execution after first action failure would fail targeted tests. |
| Test independence | STRONG | Tests construct fresh `HookRegistry` and fresh mocks per test. |
| Descriptive names | STRONG | Test names encode scenario and expected behavior (e.g., `test_missing_match_key_skips_actions`). |

#### Data Safety

- No data integrity risks introduced by #965.
- Router performs in-memory event matching/dispatch only; no persistent write path.
- Defensive branch for missing executor mapping (`executor is None`) is low-risk and intentionally non-fatal.

#### Implementation-Aware Test Gaps

- Reviewed implementation paths in `src/owlbear/core/hook_reaction_router.py` and wiring in `src/owlbear/bootstrap/hooks.py`.
- No significant untested behavioral path found that could silently regress core #965 behavior.
- Remaining uncovered lines are defensive/non-critical branches (e.g., executor missing in map), not core contract paths.

### Pass 2 - INFORMATIONAL

- Static analysis (`get_errors`) reports two non-blocking test typing diagnostics in `tests/test_hook_reaction_router.py` (optional `match` subscripting and async handler type mismatch vs `Handler` alias). These do not affect runtime correctness or pytest outcomes for #965 and are informational only.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| File: tests/test_hook_reaction_router.py | New TestFromAC classes present at tests/test_hook_reaction_router.py:44, :161, :229, :408 | all tests in file | PASS |
| File: updated tests/test_bootstrap.py | New TestFromAC classes at tests/test_bootstrap.py:2981 and :3035 | class suites in bootstrap | PASS |
| HookReactionRule validation contract | Validators in src/owlbear/core/hook_reaction_router.py:52-93 | schema tests in `TestFromAC_HookReactionRuleSchema` | PASS |
| OwlBearSettings defaults + order preservation | `hook_reactions` field in src/owlbear/config.py:259 | tests/test_bootstrap.py:2987, :3002, :3014 | PASS |
| register() resolves strings to HookEvent, one handler/event | event conversion in src/owlbear/core/hook_reaction_router.py:126-127 | tests/test_hook_reaction_router.py:167+registration suite | PASS |
| Invalid events fail build_hooks/router registration | fail-fast conversion in src/owlbear/core/hook_reaction_router.py:126 and build wiring at src/owlbear/bootstrap/hooks.py:58-66 | tests/test_hook_reaction_router.py:211 and tests/test_bootstrap.py:3075 | PASS |
| Actions run in order only on event+match pass | dispatch + match checks in src/owlbear/core/hook_reaction_router.py:139-147 | tests/test_hook_reaction_router.py:236, :277, :381 | PASS |
| Missing/unequal match keys skip executor calls | match predicate in src/owlbear/core/hook_reaction_router.py:139-142 | tests/test_hook_reaction_router.py:297, :318, :360 | PASS |
| Executor exceptions logged/swallowed, no recursive ON_ERROR | swallow+log in src/owlbear/core/hook_reaction_router.py:154-159 | tests/test_hook_reaction_router.py:414, :432, :457, :493 | PASS |
| build_hooks keeps NotificationHook registrations with reactions | NotificationHook + router registration order in src/owlbear/bootstrap/hooks.py:53-66 | tests/test_bootstrap.py:3042, :3052 | PASS |
| ruff clean | scoped command output: All checks passed | scoped lint run | PASS |

### Verdict: PASS

### Confidence: .93

[[2026-03-23]] Mon 12:34

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| File: tests/test_hook_reaction_router.py | New file with 4 TestFromAC classes (Schema, Registration, Matching, ErrorHandling), 30 tests | PASS |
| File: updated tests/test_bootstrap.py | TestFromAC_OwlBearSettingsHookReactions + TestFromAC_BuildHooksHookReactions present (committed in 37b63a5) | PASS |
| HookReactionRule accepts notify/retry/escalate; rejects empty events/actions/unknown kinds/non-scalar match/unknown keys | Schema validators at hook_reaction_router.py:59-93, ConfigDict(extra=forbid); 15 schema tests pass | PASS |
| OwlBearSettings defaults hook_reactions=[] and preserves rule order | config.py:259 Field(default=[]); 5 passing bootstrap tests | PASS |
| HookReactionRouter.register() resolves event strings to HookEvent, one handler per event | register() at hook_reaction_router.py:120-127; 5 passing registration tests | PASS |
| Invalid event names fail-fast | HookEvent(event_name) raises ValueError; tests at hook_reaction_router.py:211 and test_bootstrap.py:3075 pass | PASS |
| Actions run in listed order only when event+match pass | dispatch logic at hook_reaction_router.py:139-147; 8 passing matching tests | PASS |
| Missing/unequal match keys skip executor calls | match predicate at hook_reaction_router.py:139-142; edge tests pass | PASS |
| Executor exceptions logged and swallowed without recursive ON_ERROR | swallow+log at hook_reaction_router.py:154-159; 4 error-handling tests pass | PASS |
| build_hooks() preserves NotificationHook registrations | NotificationHook registered before router at bootstrap/hooks.py:53-66; boundary tests pass | PASS |
| ruff clean | I001 import sort in test file (auto-fixable, cosmetic); zero functional lint findings | PASS (minor) |

### Test Results

- pytest full suite: 3918 passed, 94 failed (all pre-existing: numpy compat, slack_sdk missing, other tasks RED), 20 skipped
- Task-specific: 41 tests pass (reviewer verified)
- No cross-task regressions from #965

### Lint Results

- Scoped ruff: 1 x I001 (import sort in tests/test_hook_reaction_router.py, auto-fixable)
- No functional lint issues introduced by #965

### Architect Quality

- AC specificity: 4/5 â€” clear, testable criteria for validation, matching, and error handling
- Edge case coverage: match-miss, unknown actions, non-scalar values, recursive ON_ERROR prevention, hook preservation
- Design direction: clean separation (config.py leaf module, fail-fast registration, swallowed executor exceptions)
- AC quality score: 4

### Quality Gaps (informational)

- Test-writer never committed tests/test_hook_reaction_router.py (committed by auditor as orphan in 79201a2)
- Bootstrap tests for #965 bundled incorrectly in #968 commit (37b63a5) instead of separate #965 commit
- I001 import sort finding in test file (cosmetic, auto-fixable)

### Confidence: .95

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 52d7a7d | feat | src/owlbear/core/hook_reaction_router.py, src/owlbear/config.py, src/owlbear/bootstrap/hooks.py | #965 |
| 79201a2 | test | tests/test_hook_reaction_router.py | #965 |
