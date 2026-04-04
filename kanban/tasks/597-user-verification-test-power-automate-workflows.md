---
id: 597
title: 'User verification: test Power Automate Workflows webhook in corp Teams'
status: ideation
priority: nice-to-have
created: 2026-04-04T20:14:08.5441141+02:00
updated: 2026-04-04T20:14:08.5441141+02:00
tags:
    - phase-3
    - scope:notifications
    - scope:orchestrator
class: standard
---

## Objective
Manual user test to confirm whether Power Automate Workflows are available in the corporate M365 tenant for Teams channel notifications.

## Context
Research #592 confirmed technical feasibility but cannot verify corp availability programmatically.
See docs/research/power-automate-workflows-teams-notifications.md §3.3 for procedure.

## Acceptance Criteria
- [ ] Open Teams → channel → More options (···) → Workflows
- [ ] Search for "Post to a channel when a webhook request is received" template
- [ ] If template available: create workflow, copy webhook URL
- [ ] Test HTTP POST with Adaptive Card JSON payload via PowerShell
- [ ] If available: create a T3 decision request to reopen #514 with Teams Workflows as Option D
- [ ] If unavailable: document the blocker in task body and close

## Test Command
```powershell
$url = "<WEBHOOK_URL>"
$json = '{"type":"message","attachments":[{"contentType":"application/vnd.microsoft.card.adaptive","contentUrl":null,"content":{"$schema":"http://adaptivecards.io/schemas/adaptive-card.json","type":"AdaptiveCard","version":"1.2","body":[{"type":"TextBlock","text":"OwlBear test notification"}]}}]}'
Invoke-RestMethod -Uri $url -Method Post -ContentType 'application/json' -Body $json
```
