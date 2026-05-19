---
id: 1004
title: 'Test: assembly-time notify dedup in build_hooks (RED)'
status: archived
priority: important
created: 2026-03-26 02:35:26.940423+01:00
updated: 2026-03-26 08:32:29.692116+01:00
started: 2026-03-26 08:31:48.602129+01:00
completed: 2026-03-26 08:31:48.602129+01:00
tags:
- hooks
- scope:core
- type:test
- test
depends_on:
- 955
- 957
class: standard
archival_reason: completed
archival_refs: []
---

## Scope

Test file: tests/test_963_notify_dedup.py
Tests exercise build_hooks() assembly-time event exclusion for notify deduplication.

## Acceptance Criteria

### T-1: Legacy-only â€” no reactions

Call build_hooks() with empty hook_reactions. Assert NotificationHook receives the full notification_events list. Verify handler count on expected events matches legacy behavior.

### T-2: Reaction-only â€” unconditional notify covers all events

Configure hook_reactions with unconditional notify rules covering every event in notification_events. Assert NotificationHook receives an empty event list and registers zero handlers on those events.

### T-3: Mixed â€” unconditional notify covers subset

Configure one unconditional notify reaction for task_complete only. Assert NotificationHook receives [on_error] only (task_complete excluded).

### T-4: Conditional match rule preserved

Configure a notify reaction with a non-None match predicate for task_complete. Assert NotificationHook still receives task_complete in its events (not excluded).

### T-5: Mixed conditional and unconditional

Configure two rules for the same event: one conditional (with match), one unconditional (no match). Assert the event IS excluded from NotificationHook (unconditional rule wins).

### T-6: Debug log on exclusion

When events are excluded, assert a DEBUG log message is emitted listing the excluded event names.

### T-7: Non-notify actions ignored

Configure a reaction rule with only retry and escalate actions (no notify). Assert no events are excluded from NotificationHook.

[[2026-03-26]] Thu 02:40

## Research

Gate: PASS. All 7 checklist items validated.

### Findings

1. Dedup NOT yet implemented in build_hooks() (line ~108 in bootstrap/hooks.py). NotificationHook receives unfiltered notification_events. Tests T-2/T-3/T-5/T-6 will correctly go RED.
2. Test pattern established in test_955 and test_957: construct OwlBearSettings with hook_reactions, call build_hooks(), inspect HookRegistry.handlers for handler counts per HookEvent.
3. Configuration matrix covers: legacy-only, reaction-only (full), mixed (partial), conditional-only, mixed conditional+unconditional, logging, non-notify. No gaps.
4. Default notification_events: [task_complete, on_error]. Tests should use explicit notification_events= arg for clarity.
5. Parent research: docs/research/notify-dedup-notificationhook-vs-router.md (Option A1: assembly-time exclusion of unconditional notify rules).

### Hints for test-writer

Count handlers via len(hooks.handlers.get(HookEvent.X, [])). T-1/T-4/T-7 may pass on current HEAD (no-exclusion). T-2/T-3/T-5/T-6 must fail. Use caplog.at_level(logging.DEBUG, logger='owlbear.bootstrap.hooks') for T-6.

[[2026-03-26]] Thu 03:00

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| T-1: Legacy-only, no reactions | Testable: empty hook_reactions, full events, handler counts | Keep |
| T-2: Reaction-only, unconditional covers all | Testable: empty events to NotificationHook, zero handlers | Keep |
| T-3: Mixed, unconditional covers subset | Testable: explicit events list, verify excluded vs remaining | Keep |
| T-4: Conditional match rule preserved | Testable: non-None match means event stays in NotificationHook | Keep |
| T-5: Mixed conditional + unconditional | Testable: unconditional wins, event excluded | Keep |
| T-6: Debug log on exclusion | Testable: caplog at DEBUG level, event names in message | Keep |
| T-7: Non-notify actions ignored | Testable: retry/escalate only, no exclusion | Keep |

### Architecture Notes

- Test file: tests/test_963_notify_dedup.py. Single test file, single domain (bootstrap/hooks).
- Test pattern: established by test_955 and test_957 (construct OwlBearSettings with hook_reactions, call build_hooks(), inspect hooks.handlers dict). No new patterns needed.
- Interfaces: NotificationHook.**init** accepts notification_events: list[str]. HookReactionRule has events, actions, match fields. HookRegistry.handlers returns dict[HookEvent, list[Handler]].
- RED phase: T-1/T-4/T-7 may pass on HEAD (testing current unfiltered behavior). T-2/T-3/T-5/T-6 must fail (dedup not yet implemented). Both categories are valid RED-phase tests.
- Hint accuracy verified: len(hooks.handlers.get(HookEvent.X, [])) and caplog.at_level(logging.DEBUG, logger='owlbear.bootstrap.hooks') match actual interfaces.
- TDD pairing: #963 (impl) depends_on #1004 (this test task). Correct RED before GREEN.

### Dependencies

- Verified: #955 (schema + router) archived
- Verified: #957 (real notify executor) archived
- Verified: #963 (impl task) depends_on [#1004] - correct TDD ordering

[[2026-03-26]] Thu 03:21

## Test-Writer Notes

- Test file: tests/test_963_notify_dedup.py
- Classes: TestFromAC_NotifyDedup
- Tests per category: happy 9, edge 4, error 0, boundary 3
- Total: 16 tests â€” 6 FAIL (RED), 10 PASS (testing existing behavior)
- ruff: clean
- Spy helper: _build_and_capture() patches NotificationHook with side_effect factory to capture notification_events arg while keeping real handler registration
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| T-1: Legacy-only, full events | test_t1_legacy_only_receives_full_events, test_t1_legacy_handler_count | happy, boundary |
| T-2: All events unconditionally covered | test_t2_unconditional_covers_all_events_empty_list, test_t2_zero_notification_handlers_on_excluded_event | happy, boundary |
| T-3: Mixed partial coverage | test_t3_unconditional_subset_excludes_covered_event, test_t3_unconditional_subset_preserves_uncovered_event, test_t3_excluded_events_match_exactly | happy, edge, boundary |
| T-4: Conditional match preserved | test_t4_conditional_match_preserves_event, test_t4_conditional_match_full_events_preserved | happy, edge |
| T-5: Unconditional wins | test_t5_unconditional_wins_over_conditional, test_t5_unconditional_wins_preserves_other_event | happy, edge |
| T-6: Debug log on exclusion | test_t6_debug_log_emitted_on_exclusion, test_t6_debug_log_not_emitted_when_nothing_excluded | happy, edge |
| T-7: Non-notify actions ignored | test_t7_retry_action_does_not_exclude_events, test_t7_escalate_action_does_not_exclude_events, test_t7_non_notify_rules_preserve_all_events | happy, happy, boundary |

## Builder Notes

- Files changed: src/owlbear/bootstrap/hooks.py
- Tests: tests/test_963_notify_dedup.py now 16 passed (all AC tests green); regression checks tests/test_955_hook_reaction_schema_bootstrap.py and tests/test_957_notify_escalate_executors.py passed (68 tests)
- Coverage: src/owlbear/bootstrap/hooks.py 100.0% in scoped bootstrap coverage run (264 tests passed)
- Lint: scoped ruff check passed for src/owlbear/bootstrap/hooks.py and tests/test_963_notify_dedup.py; repository-wide ruff has unrelated pre-existing failures
- Evidence: RED verification before implementation had 6 failing TestFromAC tests; all 6 now pass
- Fixes applied: added NotificationHook event filtering for unconditional notify reactions and DEBUG logging of excluded events

[[2026-03-26]] Thu 04:45

## Review Evidence

[[2026-03-26]] Thu 04:45

- Scoped pytest: 84 passed across tests/test_963_notify_dedup.py, tests/test_955_hook_reaction_schema_bootstrap.py, and tests/test_957_notify_escalate_executors.py. AC file alone: 16 passed. Scoped ruff: clean.

[[2026-03-26]] Thu 04:45

- Critical finding 1: T-6 coverage is insufficient. tests/test_963_notify_dedup.py:223 and :243 miss the path where an unconditional notify rule targets an event outside notification_events. src/owlbear/bootstrap/hooks.py:75 and :94 log an exclusion message even when no NotificationHook event was removed. Reviewer probe reproduced: Excluded NotificationHook events handled by unconditional notify reactions: [].

[[2026-03-26]] Thu 04:45

- Critical finding 2: tests/test_963_notify_dedup.py is untracked in git, so TestFromAC preservation cannot be verified from history.

[[2026-03-26]] Thu 04:45

- Verdict: FAIL. T-1, T-2, T-3, T-4, T-5, and T-7 are covered and passing. T-6 remains insufficiently tested, and the task cannot pass review while the TestFromAC file is still untracked.

[[2026-03-26]] Thu 05:37

## Test-Writer Notes (retry)

- Retry reason: reviewer cited missing tests (T-6 uncovered path)
- Gap: unconditional notify rule targeting an event outside notification_events caused logger.debug to emit an empty exclusion list, existing T-6 tests did not cover this path
- Added: 2 new failing tests in TestFromAC_NotifyDedup
- test_t6_out_of_scope_notify_rule_no_exclusion_log (edge)
- test_t6_log_does_not_show_empty_exclusion_list (boundary)
- Preserved: 16 existing tests (all PASS)
- Verified: 16 passed, 2 failed
- ruff: clean

[[2026-03-26]] Thu 06:34

## Builder Notes

- Files changed: src/owlbear/bootstrap/hooks.py
- Tests: Task file passed 18 of 18; focused hook suite passed 97 of 97.
- Coverage: src/owlbear/bootstrap/hooks.py at 97 percent.
- Lint: Scoped lint check passed for src/owlbear/bootstrap/hooks.py and tests/test_963_notify_dedup.py. Repository-wide lint has pre-existing unrelated findings.
- Evidence: Red phase reproduced with 2 failures in test_t6_out_of_scope_notify_rule_no_exclusion_log and test_t6_log_does_not_show_empty_exclusion_list. Green phase passed after patch.
- Fixes applied: Added a removed-events guard in notification dedup logic so exclusion debug logs are emitted only when at least one configured NotificationHook event is actually removed.

[[2026-03-26]] Thu 07:29

## Review Evidence

### Review: #1004 — Test: assembly-time notify dedup in build_hooks (RED)

### Test Results

- pytest: 18 passed, 0 failed in tests/test_963_notify_dedup.py; focused hook regression slice: 86 passed, 0 failed.
- Evidence: the retry tests test_t6_out_of_scope_notify_rule_no_exclusion_log and test_t6_log_does_not_show_empty_exclusion_list both passed in the task-file run, closing the prior review failure.

### Lint Results

- ruff: All checks passed for src/owlbear/bootstrap/hooks.py and tests/test_963_notify_dedup.py.

### Coverage

- src/owlbear/bootstrap/hooks.py: 85% in the reviewer 3-file coverage slice.
- Note: uncovered lines 111-133, 168-170, and 206-207 are outside the notify-dedup path under review and map to _build_security_audit_sink, lessons-hook wiring, and workspace observability wiring. The dedup and logging branch at lines 75-100 is exercised by T-1 through T-7.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

`| AC Line`| Mapped Test `| Would Fail If AC Violated?`| Verdict `|
`|---------`|-------------`|---------------------------`|---------`|
`| T-1 legacy-only, no reactions`| TestFromAC_NotifyDedup::test_t1_legacy_only_receives_full_events; test_t1_legacy_handler_count `| Yes — exact event set and handler counts would fail if legacy behavior changed`| COVERED `|
`| T-2 unconditional notify covers all events `| TestFromAC_NotifyDedup::test_t2_unconditional_covers_all_events_empty_list; test_t2_zero_notification_handlers_on_excluded_event`| Yes — exact empty list and single remaining router handler would fail if exclusion did not happen `| COVERED`|
`| T-3 unconditional notify covers subset`| TestFromAC_NotifyDedup::test_t3_unconditional_subset_excludes_covered_event; test_t3_unconditional_subset_preserves_uncovered_event; test_t3_excluded_events_match_exactly `| Yes — exact inclusion and exclusion of task_complete and on_error is asserted`| COVERED `|
`| T-4 conditional match rule preserved `| TestFromAC_NotifyDedup::test_t4_conditional_match_preserves_event; test_t4_conditional_match_full_events_preserved`| Yes — conditional-only rules must keep the full notification list `| COVERED`|
`| T-5 conditional plus unconditional notify`| TestFromAC_NotifyDedup::test_t5_unconditional_wins_over_conditional; test_t5_unconditional_wins_preserves_other_event `| Yes — unconditional win and unaffected sibling event are both asserted`| COVERED `|
`| T-6 debug log on exclusion `| TestFromAC_NotifyDedup::test_t6_debug_log_emitted_on_exclusion; test_t6_debug_log_not_emitted_when_nothing_excluded; test_t6_out_of_scope_notify_rule_no_exclusion_log; test_t6_log_does_not_show_empty_exclusion_list`| Yes — positive log emission and both false-positive log cases would fail if the guard regressed `| COVERED`|
`| T-7 non-notify actions ignored`| TestFromAC_NotifyDedup::test_t7_retry_action_does_not_exclude_events; test_t7_escalate_action_does_not_exclude_events; test_t7_non_notify_rules_preserve_all_events `| Yes — retry and escalate rules must leave the notification list unchanged`| COVERED `|

#### Security Review

- No security issues found. The change filters notification_events in memory and guards a DEBUG log in src/owlbear/bootstrap/hooks.py lines 75-100; no external input is executed, persisted, or interpolated into unsafe sinks.

#### Test Integrity

`| Original Test`| Change Made `| Assessment`|
`|---------------`|-------------`|------------`|
`| TestFromAC_NotifyDedup::*`| git diff fa98ca4..HEAD -- tests/test_963_notify_dedup.py is empty; after the retry commit, only src/owlbear/bootstrap/hooks.py changed `| PRESERVED`|
`| test_t6_out_of_scope_notify_rule_no_exclusion_log; test_t6_log_does_not_show_empty_exclusion_list`| git blame lines 267-318 attributes both tests to test-writer commit fa98ca46, not the builder fix commit `| PRESERVED`|

#### Test Quality

`| Dimension`| Rating `| Evidence`|
`|-----------`|--------`|----------`|
`| Assertion specificity`| STRONG `| Tests assert exact event lists, exact handler counts, and exact absence or presence of exclusion logs rather than loose truthiness checks`|
`| Negative or error paths`| STRONG `| Conditional-only, non-notify-only, and out-of-scope notify rules are all exercised in addition to the positive exclusion cases`|
`| Mutation reasoning`| STRONG `| Removing the removed_events guard would fail the two retry T-6 tests; breaking unconditional filtering would fail T-2, T-3, and T-5`|
`| Test independence`| STRONG `| Each test builds fresh OwlBearSettings and HookRegistry instances; caplog and patch usage is local to each test`|
`| Descriptive names`| STRONG `| Test names describe the scenario and expected outcome precisely across T-1 through T-7`|

#### Data Safety

- No data safety issues found. The new logic derives a filtered event list from settings and does not introduce shared mutable state, persistence, or partial-write paths.

#### Implementation-Aware Test Gaps

- No significant untested paths found in _notification_events_for_hook.
- The only new retry behavior is the removed_events guard at lines 93-95 in src/owlbear/bootstrap/hooks.py; the out-of-scope and empty-list T-6 tests at lines 267-318 in tests/test_963_notify_dedup.py exercise that branch directly.
- Related hook-routing regressions remain covered by the focused 86-test slice spanning tests/test_955_hook_reaction_schema_bootstrap.py, tests/test_957_notify_escalate_executors.py, and tests/test_963_notify_dedup.py.

### Pass 2 — INFORMATIONAL

- No informational findings.

### AC Compliance

`| AC Line`| Evidence `| Mapped Test`| Status `|
`|---------`|----------`|-------------`|--------`|
`| T-1`| Task-file pytest passed; legacy helper captured both task_complete and on_error and handler count stayed at one per event `| test_t1_legacy_only_receives_full_events; test_t1_legacy_handler_count`| PASS `|
`| T-2 `| Task-file pytest passed; full unconditional coverage produced an empty NotificationHook event list and a single remaining router handler`| test_t2_unconditional_covers_all_events_empty_list; test_t2_zero_notification_handlers_on_excluded_event `| PASS`|
`| T-3`| Task-file pytest passed; task_complete was excluded while on_error remained, matching the exact subset expectation `| test_t3_unconditional_subset_excludes_covered_event; test_t3_unconditional_subset_preserves_uncovered_event; test_t3_excluded_events_match_exactly`| PASS `|
`| T-4 `| Task-file pytest passed; conditional notify rules kept task_complete and the full event list intact`| test_t4_conditional_match_preserves_event; test_t4_conditional_match_full_events_preserved `| PASS`|
`| T-5`| Task-file pytest passed; the unconditional notify rule won over the conditional rule while on_error remained unaffected `| test_t5_unconditional_wins_over_conditional; test_t5_unconditional_wins_preserves_other_event`| PASS `|
`| T-6 `| Task-file pytest passed; src/owlbear/bootstrap/hooks.py lines 93-99 now guard the exclusion log so only actually removed events are logged`| test_t6_debug_log_emitted_on_exclusion; test_t6_debug_log_not_emitted_when_nothing_excluded; test_t6_out_of_scope_notify_rule_no_exclusion_log; test_t6_log_does_not_show_empty_exclusion_list `| PASS`|
`| T-7`| Task-file pytest passed; retry-only and escalate-only reactions left the notification events unchanged `| test_t7_retry_action_does_not_exclude_events; test_t7_escalate_action_does_not_exclude_events; test_t7_non_notify_rules_preserve_all_events`| PASS `|

### Verdict: PASS

### Action Taken

- Appended review evidence.

[[2026-03-26]] Thu 08:31

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| T-1: Legacy-only, no reactions | 2 tests pass: full events + handler count verified | PASS |
| T-2: Unconditional covers all | 2 tests pass: empty list + single router handler | PASS |
| T-3: Mixed subset | 3 tests pass: excluded, preserved, exact set | PASS |
| T-4: Conditional match preserved | 2 tests pass: event retained, full list intact | PASS |
| T-5: Unconditional wins | 2 tests pass: excluded + sibling preserved | PASS |
| T-6: Debug log on exclusion | 4 tests pass: emitted, not emitted, out-of-scope, no empty list | PASS |
| T-7: Non-notify actions ignored | 3 tests pass: retry, escalate, combined | PASS |

### Test Results

- pytest: 18 passed, 0 failed (task file); 4500 passed, 89 failed full suite (all pre-existing)
- ruff: clean on src/owlbear/bootstrap/hooks.py and tests/test_963_notify_dedup.py

### AC Quality Score: 4/5

AC was specific and testable across all 7 criteria. Minor gap: T-6 edge cases (out-of-scope notify, empty exclusion list) surfaced during review, not in original AC.

### Confidence: .97

### Action: archive

[[2026-03-26]] Thu 08:32

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| c85c33b | chore | kanban board + activity | #1004 |
