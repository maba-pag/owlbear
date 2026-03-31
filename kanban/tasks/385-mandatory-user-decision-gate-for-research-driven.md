---
id: 385
title: Mandatory user-decision gate for research-driven features and architectural changes
status: backlog
priority: critical
created: 2026-03-30T20:56:31.6511501+02:00
updated: 2026-03-31T03:44:49.3450932+02:00
tags:
    - research
    - ' scope:agents'
    - ' process'
    - ' quality'
class: standard
---

## Context

Research findings and follow-up tasks currently bypass user decision-making. Agents can research a topic and create follow-up implementation tasks directly at `ideation`, which then flow through the pipeline (architect, test-writer, builder) without the user ever approving the direction. The decision-request skill exists but is optional — agents use it only "when multiple valid options exist." This creates a gap: single-option research conclusions (which are the majority) skip user oversight entirely.

The user wants mandatory human-in-the-loop approval for all wide-ranging decisions, especially when research leads to new features or architectural changes.

## Acceptance Criteria

- [ ] Audit the current decision-request workflow (`skills/decision-requests/SKILL.md`) and identify gaps where research conclusions bypass user approval
- [ ] Determine which research outcomes MUST create a decision request vs which can proceed autonomously (e.g., bug fix research vs new feature research vs architectural change)
- [ ] Design a classification system for research outcomes: "proceed autonomously" vs "requires user decision" — with clear triggers for each
- [ ] Propose changes to the researcher agent instructions and research-workflow skill to enforce mandatory decision requests for feature-impacting findings
- [ ] Propose changes to the architect agent to verify that research-driven tasks have an approved decision request before advancing past backlog
- [ ] Address the 5-day auto-timeout in the current decision-request skill — should high-impact decisions auto-resolve? Propose alternatives (e.g., block indefinitely, escalate, or auto-resolve only for low-impact)
- [ ] Create a decision request with the proposed classification system for user approval before implementation
- [ ] Create follow-up implementation tasks at ideation for agreed changes

[[2026-03-30]] Mon 21:28
## Research
[[2026-03-30]] Mon 21:28
Doc: docs/research/mandatory-user-decision-gate.md
Decision: docs/decisions/pending/385-research-outcome-classification.md

Key findings: 5 gaps in current workflow. Proposed 3-tier classification (T1 autonomous, T2 advisory, T3 mandatory) with deterministic triggers. T3 blocks indefinitely. 4 follow-up tasks pending decision approval.

[[2026-03-31]] Tue 03:40
## Research (completed)
Doc: docs/research/mandatory-user-decision-gate.md
Decision: docs/decisions/pending/385-research-outcome-classification.md (approved: Option A)

Key findings: 5 gaps in current workflow (G1-G5). Proposed 3-tier classification (T1 autonomous, T2 advisory, T3 mandatory) with deterministic triggers. T3 blocks indefinitely. Auto-timeout Option A selected (.85 confidence).

Follow-up tasks created:
- #459: Update decision-requests skill with impact_tier field
- #460: Update researcher agent and research-workflow with tier classification
- #461: Add decision-request verification to architect backlog gate
- #462: Update agent-common defer-to-user boundary with tier classification

Sources logged in docs/sources/overview.md.
