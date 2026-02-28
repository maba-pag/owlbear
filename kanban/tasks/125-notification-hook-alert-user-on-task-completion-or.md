---
id: 125
title: Notification hook — alert user on task completion or question
status: archived
priority: important
created: 2026-02-27T14:55:15.9206698+01:00
updated: 2026-02-28T23:52:49.8716783+01:00
started: 2026-02-27T18:53:26.2783334+01:00
completed: 2026-02-28T23:52:49.8716783+01:00
tags:
    - phase-7
    - hooks
    - agent
depends_on:
    - 124
class: standard
---

SPLIT by architect review into:
- #156: Extend HookEvent enum with TASK_COMPLETE and QUESTION_PENDING
- #157: Add notification settings to OwlBearSettings
- #159: Test NotificationHook and NotificationBackend protocol
- #160: Implement NotificationHook with bell and sound backends

Original scope was too broad (multiple responsibilities). Split follows one-responsibility-per-task rule.
Research: docs/notification-hook-research.md

Future tasks (not created yet - YAGNI):
- Toast backend (windows-toasts)
- Slack notification backend
- TTS notification backend
