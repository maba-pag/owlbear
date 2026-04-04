---
id: 592
title: Evaluate Power Automate Workflows availability for Teams notifications
status: backlog
priority: nice-to-have
created: 2026-04-04T18:01:47.4587011+02:00
updated: 2026-04-04T20:14:52.7003257+02:00
tags:
    - phase-3
    - scope:notifications
    - scope:orchestrator
    - type:research
class: standard
---

## Objective
Determine whether Power Automate Workflows (Teams webhook trigger) are available in the corporate environment as an alternative to Slack for orchestrator notifications.

## Context
Decision #514 deferred the notification feature because Slack is unavailable and Teams integration wasn't possible due to corp policy. Microsoft 365 Connectors are being deprecated; Power Automate Workflows with the "When a Teams webhook request is received" trigger is the replacement. This may or may not be available under current corp policy.

See docs/research/notifier-protocol-344-duplicate-assessment.md §3.3 for comparison table.

## Acceptance Criteria
- [ ] Confirm whether Power Automate Workflows are enabled in the corporate M365 tenant
- [ ] Test creating a webhook trigger workflow and posting a message via HTTP POST
- [ ] If available: create a decision request to reopen #514 with Teams Workflows as Option D
- [ ] If unavailable: document the blocker and close

[[2026-04-04]] Sat 20:14
## Research
- Research doc: docs/research/power-automate-workflows-teams-notifications.md
- Sources: 6 studied, 4 high-relevance
- Recommendation: Proceed with user verification of corp availability, then reopen #514 if available (confidence: .75)
- Follow-up tasks created: #597 (user verification: test Workflows webhook in corp Teams) at ideation
- Decision requests: none (pending user verification — DR to reopen #514 is AC of #597)

## Challenge Results
- Challenger: FALLBACK — challenger agent not available for corp-environment verification research
- Confidence in original: .75
- Key challenges: corp availability is the critical unknown; cannot be resolved by code analysis
- Researcher response: accepted — created #597 as manual verification step
