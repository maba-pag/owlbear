---
id: 963
title: Deduplicate notify delivery between NotificationHook and HookReactionRouter
status: archived
priority: important
created: 2026-03-23T04:16:01.8423826+01:00
updated: 2026-03-26T16:05:20.8907785+01:00
tags:
    - agent
    - hooks
    - config
    - scope:core
    - type:build
parent: 957
depends_on:
    - 955
    - 957
    - 1004
class: standard
---

See docs/research/notify-dedup-notificationhook-vs-router.md for full research context.

## Scope

Files scoped: src/owlbear/bootstrap/hooks.py only (plus tests).
Domain: bootstrap.

## Acceptance Criteria

### AC-1: Assembly-time event exclusion

When `build_hooks()` constructs `NotificationHook`, it computes the set of events covered by any `HookReactionRule` whose `actions` list includes `notify` AND whose `match` predicate is `None` (unconditional). Those events are removed from the `notification_events` list passed to `NotificationHook.__init__`.

### AC-2: Legacy-only configuration preserved

When `settings.hook_reactions` is empty (default), `NotificationHook` receives the full `settings.notification_events` list unmodified. Behavior is identical to the current codebase.

### AC-3: Reaction-only configuration

When every event in `settings.notification_events` is covered by an unconditional notify reaction rule, `NotificationHook` receives an empty event list and registers zero handlers.

### AC-4: Mixed configuration â€” unconditional rule

When a subset of `notification_events` is covered by unconditional notify reaction rules, only the uncovered events remain in the list passed to `NotificationHook`.

### AC-5: Conditional match rules preserved on legacy path

When a `HookReactionRule` has a non-None `match` predicate AND includes `notify` in actions, that event is NOT excluded from `NotificationHook.notification_events`. Both paths coexist for conditional rules.

### AC-6: Debug logging on exclusion

When events are excluded from the legacy path, a `DEBUG`-level log message is emitted listing the excluded event names.

### AC-7: No new types or modules

Implementation is contained within `build_hooks()` in `src/owlbear/bootstrap/hooks.py`. No new classes, protocols, or modules are introduced.

## Architecture Notes

- Pattern: follows existing `build_hooks()` assembly pattern â€” compute derived config, then wire components.
- Interface: `NotificationHook.__init__` signature is unchanged; only the argument value changes.
- Invariant: `HookReactionRouter` registration is unchanged; only `NotificationHook` event list is filtered.

[[2026-03-26]] Thu 02:36

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| AC-1: Assembly-time event exclusion | Precise: what to compute, where, how | Keep |
| AC-2: Legacy-only preserved | Testable: empty reactions means full events | Keep |
| AC-3: Reaction-only config | Testable: all covered means empty list, zero handlers | Keep |
| AC-4: Mixed unconditional | Testable: subset exclusion, remainder verified | Keep |
| AC-5: Conditional match preserved | Testable: non-None match means no exclusion | Keep |
| AC-6: Debug logging | Testable: caplog at DEBUG level | Keep |
| AC-7: No new types | Testable: no new files or classes introduced | Keep |

### Architecture Notes

- Implementation site: build_hooks() in src/owlbear/bootstrap/hooks.py, before NotificationHook construction (line ~117).
- Pattern: compute reaction_notify_events set from settings.hook_reactions, filter notification_events, pass filtered list. Matches existing assembly pattern.
- NotificationHook.**init** signature unchanged. HookReactionRouter wiring unchanged.
- Research doc (Option A1) is sound: unconditional rules suppress legacy; conditional rules coexist. Matches Prometheus AlertManager routing-tree pattern.
- ~15 lines of implementation. No new modules, types, or protocols needed.

### Changes Made

- Refined AC from vague prose to 7 testable acceptance criteria
- Created test task #1004 (TDD RED) for assembly-time notify dedup tests
- Added #1004 to depends_on

### Dependencies

- Verified: #955 (schema + router) archived
- Verified: #957 (real notify executor) archived
- Added: #1004 (test task, TDD RED) must complete before builder starts #963

[[2026-03-26]] Thu 16:05

## Builder Notes

- Files changed: none (green on arrival).
- Tests: tests/test_963_notify_dedup.py scoped run passed (18 passed, 0 failed).
- Coverage: scoped run reports src/owlbear/bootstrap/hooks.py at 61 percent; no code was changed in this builder pass.
- Lint: ruff check passed for src/owlbear/bootstrap/hooks.py and tests/test_963_notify_dedup.py.
- Evidence: initial scoped pytest startup was interrupted once; immediate rerun passed all tests.
- Fixes applied: none; implementation already present and AC behavior verified.
