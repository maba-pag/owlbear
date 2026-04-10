---
id: 156
title: Extend HookEvent enum with TASK_COMPLETE and QUESTION_PENDING
status: archived
priority: important
created: 2026-02-27T19:18:33.2414892+01:00
updated: 2026-02-28T23:53:12.7624745+01:00
started: 2026-02-27T19:18:41.1742783+01:00
completed: 2026-02-28T23:53:12.7624745+01:00
tags:
    - phase-7
    - hooks
class: standard
---

Add two new events to HookEvent StrEnum in src/owlbear/core/hooks.py.

## AC
- [ ] Add TASK_COMPLETE = 'task_complete' to HookEvent enum
- [ ] Add QUESTION_PENDING = 'question_pending' to HookEvent enum
- [ ] Placement: after SUBAGENT_COMPLETE (end of enum)
- [ ] Update __all__ in core/__init__.py if HookEvent is re-exported (verify)
- [ ] Tests: verify new enum members exist, are StrEnum values, emit/register works
- [ ] Existing tests still pass (no behavioral change)
- [ ] ruff clean

## Architecture
- Minimal change: 2 lines added to the enum in hooks.py
- These events are emitted by future code (NotificationHook, agent turn completion)
- No hook *consumes* these yet — this just makes them available
