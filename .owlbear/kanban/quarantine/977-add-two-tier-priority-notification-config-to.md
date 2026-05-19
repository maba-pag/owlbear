---
id: 977
title: Add two-tier priority notification config to OwlBearSettings
status: archived
priority: important
created: 2026-03-24T03:05:22.4059729+01:00
updated: 2026-03-24T04:30:47.5524091+01:00
tags:
    - config
    - hooks
    - scope:core
    - type:build
parent: 952
depends_on:
    - 955
    - 986
class: standard
---

Add two-tier priority notification config fields to OwlBearSettings.

See docs/research/two-tier-notification-config.md.

AC:

- [ ] Add _KNOWN_BACKENDS = frozenset with bell, sound, slack as module-level constant in src/owlbear/config.py, following the _ALLOWED_ACTIONS pattern.

- [ ] Add notification_urgent_events: list[str] field with default [on_error, budget_warning, question_pending].

- [ ] Add notification_urgent_backends: list[str] field with default [slack, sound, bell].

- [ ] Add notification_info_events: list[str] field with default [task_complete].

- [ ] Add notification_info_backends: list[str] field with default [bell].

- [ ] Add field_validator on both *_backends fields that rejects any value not in _KNOWN_BACKENDS with ValidationError.

- [ ] Add model_validator(mode=after) that maps deprecated fields to urgent tier when deprecated fields are in model_fields_set and new tier fields are at defaults. Scope warnings.catch_warnings() to validator body.

- [ ] Do NOT add config-time event name validation (preserves leaf-module invariant from #955/#969).

- [ ] Env vars follow standard OWLBEAR_prefix: OWLBEAR_NOTIFICATION_URGENT_EVENTS, OWLBEAR_NOTIFICATION_URGENT_BACKENDS, etc.

- [ ] Files scoped to src/owlbear/config.py only. No changes to build_hooks, notification_hook.py, or other modules (wiring deferred to #979).

- [ ] All #986 TDD RED tests pass after implementation.

- [ ] Existing TestNotificationSettingsDefaults and TestNotificationSettingsEnvOverrides tests continue to pass unchanged.

- [ ] ruff check clean on src/owlbear/config.py.

- [ ] Mark existing notification_events and notification_backends with Field deprecated pointing users to the new tiered fields.

[[2026-03-24]] Tue 04:30

## Architecture Review

**Verdict:** APPROVED

### AC Assessment

All AC lines are verifiable pass/fail. Each field, validator, and default has a specific expected value.

### Architecture Notes

- Single domain: config only. All changes scoped to src/owlbear/config.py.

- Pattern consistency: _KNOWN_BACKENDS follows _ALLOWED_ACTIONS precedent at config.py:33.

- Leaf-module invariant preserved: No config-time event name validation.

- Deprecation via Pydantic Field(deprecated=str) is the correct native mechanism.

- model_validator(mode=after) with model_fields_set is correct for cross-field migration.

- Dependency #955: archived. New dep #986 (TDD RED): created at todo.

- No failure mode map needed (config-only, no new codepaths).

- Wiring deferred to #979 (build_hooks) - clean separation.

### Changes Made

- Refined AC from prose to 14 verifiable lines

- Created #986 (TDD RED test task) at todo

- Added #986 as dependency on #977
