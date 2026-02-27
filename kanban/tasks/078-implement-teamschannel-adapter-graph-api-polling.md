---
id: 78
title: Implement TeamsChannel adapter (Graph API + polling)
status: ideation
priority: high
created: 2026-02-27T00:53:01.5038514+01:00
updated: 2026-02-27T00:53:01.5038514+01:00
tags:
    - phase-4
    - comms
    - teams
depends_on:
    - 77
class: standard
---

Create src/owlbear/channels/teams.py conforming to ChannelPlugin Protocol. Use msgraph-sdk + msal for auth. Polling loop for receive(), Graph API POST for send(). connect() authenticates via MSAL device-flow and resolves target chat ID. See docs/teams-integration-research.md.
