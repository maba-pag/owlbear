---
id: 83
title: 'Research Slack integration path (replaces Teams #47)'
status: done
priority: high
created: 2026-02-27T01:39:01.6056453+01:00
updated: 2026-02-27T01:45:53.2072062+01:00
started: 2026-02-27T01:39:07.3442299+01:00
completed: 2026-02-27T01:45:53.2072062+01:00
tags:
    - phase-4
    - research
    - comms
    - slack
class: standard
---

Teams path permanently blocked (Azure AD restrictions). Pivot to Slack.

Research Slack Bot Token + Socket Mode for laptop-resident daemon. Socket Mode uses WebSocket (no public endpoint needed). Compare: Slack SDK (slack_bolt/slack_sdk) vs raw WebSocket + REST API.

Research checklist:
1. Theoretical validity: Does Socket Mode work for always-on laptop daemon?
2. Prior art: 2+ repos/articles for Slack bots with Socket Mode in Python
3. Technical feasibility: Python 3.12+, async support, auth (Bot Token vs OAuth)
4. Architecture fit: Map to ChannelPlugin protocol (send/receive/connect/disconnect)
5. Implementation approach: slack_bolt vs raw SDK vs minimal REST+WS

Deliver: docs/slack-integration-research.md + follow-up kanban tasks.
