---
id: 157
title: Add notification settings to OwlBearSettings
status: archived
priority: important
created: 2026-02-27T19:18:52.9845585+01:00
updated: 2026-02-28T23:53:13.3816677+01:00
started: 2026-02-27T19:18:57.7821938+01:00
completed: 2026-02-28T23:53:13.3816677+01:00
tags:
    - phase-7
    - hooks
    - config
depends_on:
    - 156
class: standard
---

Add notification configuration fields to OwlBearSettings in src/owlbear/config.py.

## AC
- [ ] New fields on OwlBearSettings:
      - notification_events: list[str] = ['task_complete', 'question_pending', 'on_error']
      - notification_backends: list[str] = ['bell', 'sound'] (priority order)
- [ ] Env var override: OWLBEAR_NOTIFICATION_EVENTS, OWLBEAR_NOTIFICATION_BACKENDS
- [ ] Tests: default values correct, env var override works, custom list accepted
- [ ] Existing config tests still pass
- [ ] ruff clean

## Architecture
- Follows existing OwlBearSettings pattern (pydantic-settings, OWLBEAR_ prefix)
- notification_events values correspond to HookEvent enum names (lowercase)
- notification_backends values: 'bell' (stdout \\a), 'sound' (winsound.MessageBeep), future: 'toast', 'slack', 'tts'
- Research: docs/notification-hook-research.md section 3.7
