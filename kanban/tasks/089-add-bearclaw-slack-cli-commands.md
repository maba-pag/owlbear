---
id: 89
title: Add bearclaw slack CLI commands
status: ideation
priority: medium
created: 2026-02-27T01:45:19.6636728+01:00
updated: 2026-02-27T01:45:19.6636728+01:00
tags:
    - phase-4
    - comms
    - slack
    - cli
depends_on:
    - 87
class: standard
---

CLI commands for Slack integration. See docs/slack-integration-research.md.

AC:
- bearclaw slack auth: validate tokens (call auth.test API)
- bearclaw slack test: send a test message to configured channel
- bearclaw slack status: show connection state
- Proper error messages for missing/invalid tokens
