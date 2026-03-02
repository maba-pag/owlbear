---
id: 418
title: Action callback routing for future structured Slack actions
status: backlog
priority: nice-to-have
created: 2026-03-01T20:20:51.8671336+01:00
updated: 2026-03-01T20:24:09.6108524+01:00
started: 2026-03-01T20:24:09.6108524+01:00
tags:
    - phase-13
    - slack
    - channels
class: standard
---

From #307 slack-structured-proposals-research.md. Add _action_callbacks: dict[str, Callable] to SlackChannel for future structured action handling beyond text bridging. Enables registering specific handlers for action_ids. AC: Callback registry allows registering handlers by action_id; unregistered actions fall through to text bridge; callbacks invoked with action payload. Depends on #307, #414.
