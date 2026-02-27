---
id: 84
title: Create Slack workspace + OwlBear app setup guide
status: done
priority: medium
created: 2026-02-27T01:44:49.3690874+01:00
updated: 2026-02-27T02:40:07.5339008+01:00
started: 2026-02-27T02:14:17.5673349+01:00
completed: 2026-02-27T02:40:07.5339008+01:00
tags:
    - phase-4
    - comms
    - slack
    - docs
class: standard
---

Manual setup steps for Slack integration. See docs/slack-integration-research.md.

AC:
- Document: create free Slack workspace
- Document: create Slack app with manifest (socket_mode_enabled: true)
- Document: enable Socket Mode, generate app-level token (xapp-)
- Document: add bot scopes (chat:write, im:history), install to workspace, get bot token (xoxb-)
- Document: subscribe to message.im event
