---
id: 597
title: 'User verification: test Power Automate Workflows webhook in corp Teams'
status: in-progress
priority: nice-to-have
created: 2026-04-04T20:14:08.5441141+02:00
updated: 2026-04-05T20:52:40.7535764+02:00
tags:
    - phase-3
    - scope:notifications
    - scope:orchestrator
    - type:test
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

[[2026-04-05]] Sun 20:23
## Architecture Review

### Refinement Applied
- Research doc path corrected: actual location is .owlbear/research/power-automate-workflows-teams-notifications.md (task body references docs/research/... which does not exist)
- Added pass-through tag type:test (non-implementation task: manual user verification)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: manual verification of Teams Workflows corp availability |
| Interface clarity | N/A | Manual user task; no code interfaces |
| Dependency correctness | PASS | No depends_on listed; correct — #592 research is upstream context, not a blocking dep |
| Module layering | N/A | No code changes |
| TDD compliance | N/A | Non-impl task; type:test pass-through tag added |
| KISS/YAGNI | PASS | Minimal scope: test one thing, report result |
| Premise challenge | PASS | Valid: #592 research identified this manual step as the only way to resolve corp availability unknown |
| Pattern consistency | PASS | Follows established verification pattern; conditional outcomes mirror research recommendation |
| Security surface | PASS | Webhook URL created by user in Teams GUI, used only in local PowerShell test. No secrets stored in code |
| Single domain | PASS | Notifications domain only |

### Failure Mode Map
N/A — no code changes; manual user task.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in session
- Architect response: accepted fallback; pure manual-verification task with no code architecture decisions to challenge

### Notes
- Research doc (.owlbear/research/power-automate-workflows-teams-notifications.md) is thorough and well-sourced. Procedure in section 3.3 maps directly to AC.
- Time-sensitive: O365 Connectors retire April 30, 2026 (25 days). Task should be prioritized for user action.
- #514 decision resolved as "Defer / do nothing" — conditional DR in AC line 5 would reopen this if Workflows proves available.
- AC line 5 relies on user knowing how to trigger a T3 DR (via scribe agent or direct request). Acceptable for pipeline-aware user.

### Verdict: APPROVE
### Action: Pass-through tag type:test added. Advanced to todo.

[[2026-04-05]] Sun 20:52
## Test-Writer Notes\n- Non-implementation task (tagged type:test) — no tests applicable.\n- AC describes manual user verification steps in Teams GUI; no Python interfaces exist.\n- Passing through to builder.
