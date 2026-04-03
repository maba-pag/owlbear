---
id: 26
title: Slack notification integration
status: ideation
priority: nice-to-have
created: 2026-03-26T17:23:41.5689417+01:00
updated: 2026-04-02T23:35:00.3691204+02:00
tags:
    - phase-3
    - scope:notifications
    - type:build
depends_on:
    - 21
blocked: true
block_reason: 'Feature deferred per user decision (DR 514): no Slack available, Teams not possible'
class: standard
---

## Objective
Add Slack notification support so the orchestrator can notify on task completions, failures, and decision requests.

## Acceptance Criteria
- [ ] Notification module in packages/orchestrator/
- [ ] Send Slack message on task dispatch
- [ ] Send Slack message on task completion (success or failure)
- [ ] Send Slack message on decision requests (blocked tasks needing user input)
- [ ] Configurable: Slack token and channel via environment variables
- [ ] Optional: system works fine without Slack configured
- [ ] Unit tests with mocked Slack API

## Context
Depends on O3 (audit log). Slack notifications are a nice-to-have from v1 that we want to preserve. Lower priority than core functionality.
