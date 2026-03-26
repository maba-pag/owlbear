---
id: 21
title: Build audit log
status: ideation
priority: important
created: 2026-03-26T17:22:35.5978869+01:00
updated: 2026-03-26T17:22:35.5978869+01:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 19
class: standard
---

## Objective
Build a lightweight audit log that records orchestrator actions for self-improvement analysis.

## Acceptance Criteria
- [ ] Module in packages/orchestrator/src/owlbear/audit/
- [ ] Log each dispatch: timestamp, task ID, agent, prompt summary, duration
- [ ] Log each completion: outcome (success/failure), files changed, errors
- [ ] JSONL format, one file per day or per session
- [ ] No approval gates - log is for analysis only
- [ ] Queryable: filter by date range, agent, outcome
- [ ] Unit tests for log write and query

## Context
Depends on O1 (ACP client). The audit log replaces v1's complex SecurityAuditLog. It is strictly for self-improvement - no gates, no blocking.
