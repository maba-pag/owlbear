---
id: 597
title: 'User verification: test Power Automate Workflows webhook in corp Teams'
status: backlog
priority: nice-to-have
created: 2026-04-04T20:14:08.5441141+02:00
updated: 2026-04-05T01:18:35.0793334+02:00
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

[[2026-04-05]] Sun 01:18
## Research
- Validation pass on existing research: docs/research/power-automate-workflows-teams-notifications.md
- Web verification (2026-04-05): O365 Connectors retirement confirmed April 30, 2026 (25 days remaining)
- Feb 2026 update: shared channels now supported by Workflows bot; private channels still in progress
- Test payload format and procedure verified against MS devblog and support docs
- Sources: 0 new (6 from #592 already logged in docs/sources/overview.md)
- Tier: T1 (manual user verification step; conditional T3 DR to reopen #514 handled in AC)
- Follow-up tasks created: none (task is self-contained; conditional outcomes in AC)
- Decision requests: none (T3 DR is post-verification, not pre-research)

### Pipeline Note
This task requires manual user action in Teams GUI. It cannot progress through test-writer/builder stages. Architect should pass-through or flag for user handoff.

### Time Sensitivity
O365 Connectors retirement is April 30, 2026. After that date, Power Automate Workflows is the only webhook mechanism for Teams. Verification should happen before the deadline.

## Challenge Results
- Challenger: SKIPPED (validation pass on existing research, no new recommendation produced)
- Confidence in existing research: .75 (unchanged from #592)
