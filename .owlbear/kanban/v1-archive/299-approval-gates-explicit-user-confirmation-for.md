---
id: 299
title: Approval gates — explicit user confirmation for destructive actions
status: archived
priority: needed
created: 2026-03-01T02:53:16.4350662+01:00
updated: 2026-03-01T17:09:24.762722+01:00
started: 2026-03-01T10:03:13.2170234+01:00
completed: 2026-03-01T17:09:24.762722+01:00
tags:
    - phase-12
    - agent
    - safety
class: standard
---

## Context
CommandSafetyGuard exists but only logs warnings. For a real autonomous system, destructive actions (git push, file delete, PR creation, deployment) need explicit user approval via ask_user before proceeding.

## Acceptance Criteria
- [ ] Define ApprovalPolicy: actions requiring approval (push, delete, create_pr, deploy, pip install)
- [ ] CommandSafetyGuard enhanced: when action requires approval, call ask_user tool
- [ ] If user says no -> action is cancelled, agent receives cancellation message
- [ ] If user doesn't respond within timeout -> action is cancelled (safe default)
- [ ] Approval can be pre-granted per-session ('approve all git pushes for this session')
- [ ] Approval history logged in observability events
- [ ] Unit tests for each approval/deny/timeout path
- [ ] Works across all channels (CLI prompt, Slack message, voice confirmation)
