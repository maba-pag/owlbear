---
id: 986
title: 'Test: Two-tier priority notification config (TDD RED)'
status: archived
priority: important
created: 2026-03-24T04:26:04.845651+01:00
updated: 2026-03-26T15:53:44.2521144+01:00
tags:
    - config
    - hooks
    - scope:core
    - type:test
    - test
parent: 952
depends_on:
    - 955
class: standard
---

TDD RED tests for #977. Write failing tests that verify:\n- [ ] notification_urgent_events field exists on OwlBearSettings with default [on_error, budget_warning, question_pending]\n- [ ] notification_urgent_backends field exists on OwlBearSettings with default [slack, sound, bell]\n- [ ] notification_info_events field exists on OwlBearSettings with default [task_complete]\n- [ ] notification_info_backends field exists on OwlBearSettings with default [bell]\n- [ ] _KNOWN_BACKENDS frozenset equals {bell, sound, slack} in config module\n- [ ] notification_urgent_backends rejects unknown backend names via ValidationError\n- [ ] notification_info_backends rejects unknown backend names via ValidationError\n- [ ] Old notification_events and notification_backends fields carry Field(deprecated=...) metadata\n- [ ] model_validator maps old fields to urgent tier when old fields are in model_fields_set and new fields are at defaults\n- [ ] model_validator ignores old fields when new fields are explicitly set\n- [ ] Env vars OWLBEAR_NOTIFICATION_URGENT_EVENTS and OWLBEAR_NOTIFICATION_URGENT_BACKENDS override defaults\n- [ ] No config-time event name validation (arbitrary event name strings accepted)\n- [ ] Existing tests for notification_events and notification_backends still pass unchanged\nFiles: tests/test_config.py (add TestFromAC classes)

[[2026-03-26]] Thu 15:53

## Builder Notes

- Files changed: src/owlbear/config.py
- Tests: 32 passed across scoped regression slices; AC class TestFromAC_TwoTierNotificationConfig now fully green (19 passed)
- Coverage: src/owlbear/config.py at 77 percent from scoped test_config coverage run
- Lint: ruff check src/owlbear/config.py passed
- Evidence: task-scoped AC pytest run moved from 19 failed to 19 passed; legacy notification default and env override tests remained green
- Fixes applied: Added two-tier notification fields, known-backend validation for urgent and info tiers, deprecated metadata on legacy fields, and model-level mapping from legacy fields to urgent tier when new tier fields are not explicitly set
