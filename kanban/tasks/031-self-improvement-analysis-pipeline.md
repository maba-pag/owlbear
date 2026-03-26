---
id: 31
title: Self-improvement analysis pipeline
status: ideation
priority: important
created: 2026-03-26T18:05:35.1098126+01:00
updated: 2026-03-26T18:05:35.1098126+01:00
tags:
    - phase-2
    - scope:orchestrator
    - type:build
depends_on:
    - 21
class: standard
---

## Objective
Build analysis on top of the audit log to generate improvement proposals for agents, skills, and workflows.

## Acceptance Criteria
- [ ] Read audit log data (dispatch history, outcomes, durations, errors)
- [ ] Detect patterns: high error rates per agent, slow tasks, repeated failures
- [ ] Generate improvement proposals (which agent, what to change, evidence)
- [ ] Output as structured data (JSON or markdown report)
- [ ] No autonomous mutation - proposals are review artifacts only
- [ ] Triggerable via CLI: owlbear analyze (not automatic)
- [ ] Unit tests for analysis logic

## Context
Depends on O3 (audit log). v1 had ImprovementProposals module that analyzed EventStore data. v2 simplifies to: read audit log, find patterns, suggest changes. Human reviews and applies.
