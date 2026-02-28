---
id: 160
title: Implement NotificationHook with bell and sound backends
status: archived
priority: important
created: 2026-02-27T19:19:37.6344637+01:00
updated: 2026-02-28T23:53:15.1886632+01:00
started: 2026-02-27T19:19:42.0975292+01:00
completed: 2026-02-28T23:53:15.1886632+01:00
tags:
    - phase-7
    - hooks
    - agent
depends_on:
    - 156
    - 157
    - 159
class: standard
---

Implement NotificationHook and initial backends (bell, winsound).

## AC
- [ ] File: src/owlbear/core/notification_hook.py
- [ ] NotificationBackend Protocol: async def notify(self, message: str, event: HookEvent) -> bool
- [ ] ConsoleBellBackend: writes backslash-a to sys.stdout, returns True
- [ ] WinSoundBackend: calls winsound.MessageBeep(winsound.MB_ICONINFORMATION), returns True on Windows, False otherwise
- [ ] NotificationHook class:
      - __init__(backends: list[NotificationBackend], notification_events: list[str])
      - async __call__(data: object): extract message from data dict, skip if event not in notification_events, dispatch to backend chain
      - register(hooks: HookRegistry): register on all HookEvent values matching notification_events
- [ ] Backend priority chain: try first backend, fall through on failure, stop on first success
- [ ] All exceptions caught and logged (error isolation)
- [ ] All tests in test_notification_hook.py pass
- [ ] ruff clean

## Architecture
- Follows existing hook pattern: __call__ + register (see context_hook.py, lint_hook.py)
- MVP backends: bell (zero deps), sound (stdlib winsound)
- Future backends: toast (windows-toasts), slack, tts — separate tasks
- Research: docs/notification-hook-research.md
