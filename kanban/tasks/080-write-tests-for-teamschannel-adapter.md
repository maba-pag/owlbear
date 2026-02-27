---
id: 80
title: Write tests for TeamsChannel adapter
status: ideation
priority: high
created: 2026-02-27T00:53:14.5523451+01:00
updated: 2026-02-27T01:33:56.45918+01:00
tags:
    - phase-4
    - comms
    - teams
    - test
depends_on:
    - 78
blocked: true
block_reason: 'Blocked on #77 — Azure AD app registration not possible (IT admin restriction)'
class: standard
---

Unit tests with mocked Graph client (send, receive, connect, disconnect). Test polling logic, message deduplication, auth token refresh. See docs/teams-integration-research.md.
