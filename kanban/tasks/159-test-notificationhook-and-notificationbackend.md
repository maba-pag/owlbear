---
id: 159
title: Test NotificationHook and NotificationBackend protocol
status: archived
priority: important
created: 2026-02-27T19:19:18.7549084+01:00
updated: 2026-02-28T23:53:14.5519114+01:00
started: 2026-02-27T19:19:25.2383043+01:00
completed: 2026-02-28T23:53:14.5519114+01:00
tags:
    - phase-7
    - hooks
    - test
depends_on:
    - 156
    - 157
class: standard
---

Write tests FIRST for NotificationHook and NotificationBackend protocol.

## AC
- [ ] File: tests/test_notification_hook.py
- [ ] Test: NotificationBackend protocol defines async notify(message: str, event: HookEvent) -> bool
- [ ] Test: NotificationHook.__call__ dispatches to backends in priority order
- [ ] Test: NotificationHook stops at first successful backend
- [ ] Test: NotificationHook skips events not in configured notification_events list
- [ ] Test: Backend failure falls through to next backend
- [ ] Test: All backends fail logs warning, no exception raised
- [ ] Test: NotificationHook.register() registers on all configured events
- [ ] Test: Bell backend writes backslash-a to stdout
- [ ] Test: Sound backend calls winsound.MessageBeep (mocked)
- [ ] ruff clean

Research: docs/research/notification-hook.md
