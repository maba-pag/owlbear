---
id: 78
title: Implement TeamsChannel adapter (Graph API + polling)
status: done
priority: high
created: 2026-02-27T00:53:01.5038514+01:00
updated: 2026-02-27T01:38:45.5119542+01:00
started: 2026-02-27T01:38:44.5682737+01:00
completed: 2026-02-27T01:38:44.5682737+01:00
tags:
    - phase-4
    - comms
    - teams
depends_on:
    - 77
blocked: true
block_reason: 'Blocked on #77 — Azure AD app registration not possible (IT admin restriction)'
class: standard
---

Create src/owlbear/channels/teams.py conforming to ChannelPlugin Protocol. Use msgraph-sdk + msal for auth. Polling loop for receive(), Graph API POST for send(). connect() authenticates via MSAL device-flow and resolves target chat ID. See docs/teams-integration-research.md.

[[2026-02-27]] Fri 01:38
CLOSED: Teams path abandoned. Replaced by Slack tasks.
