---
id: 385
title: Mandatory user-decision gate for research-driven features and architectural changes
status: docs
priority: critical
created: 2026-03-30T20:56:31.6511501+02:00
updated: 2026-03-31T07:39:39.3160461+02:00
tags:
    - research
    - ' scope:agents'
    - ' process'
    - ' quality'
claimed_by: writer
claimed_at: 2026-03-31T07:39:39.3160461+02:00
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

[[2026-03-31]] Tue 04:45
## Architecture Review
**Verdict:** Approve
**DR Verification:** docs/decisions/resolved/385-research-outcome-classification.md approved: true

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Audit decision-request workflow | Complete: research doc S3 identifies 5 gaps (G1-G5) | Verified |
| Determine mandatory vs autonomous outcomes | Complete: deterministic T3 triggers (6 factual conditions) | Verified |
| Design classification system | Complete: T1/T2/T3 with deterministic triggers in S4 | Verified |
| Propose researcher agent changes | Complete: S6 C2+C3 | Verified |
| Propose architect agent changes | Complete: S6 C4 | Verified |
| Address 5-day auto-timeout | Complete: Option A selected (T2 keeps 5d, T3 blocks indefinitely) | Verified |
| Create decision request | Complete: docs/decisions/resolved/385-research-outcome-classification.md, user-approved | Verified |
| Create follow-up tasks at ideation | Complete: #459, #460, #461, #462 (all now at todo after arch review) | Verified |

### Architecture Notes
Pure research/design task. All 8 AC items are deliverables (audit, design, propose, create), not implementation. Research doc is thorough: 9 sources, 5 identified gaps, deterministic classification triggers (not judgment-based). Decision request was approved (Option A: 3-tier). Four atomic follow-up tasks properly cover all 5 required changes (C2+C3 combined in #460 since they target the same agent workflow). No code produced, no TDD needed. Single concern: user-decision gate process.

Verified gaps exist in current files: decision-requests skill has no impact_tier field, researcher agent has no tier classification, uniform 5-day auto-resolve applies to all urgencies.

### Changes Made
- Verified all 8 AC items against research doc and kanban board
- Verified decision request approved at docs/decisions/resolved/
- Verified follow-up tasks #459-#462 exist and are properly scoped
- Approved to todo

### Dependencies
- Verified: Follow-ups #459-#462 all at todo (already architect-reviewed)
- Verified: #464 (dispatch-planning tier-aware auto-resolve) created by #459 research

[[2026-03-31]] Tue 06:04
## Test-Writer Notes
- Non-implementation task (tagged research, quality) — no tests applicable.
- Architecture Review confirmed: "No code produced, no TDD needed."
- Passing through to builder.

[[2026-03-31]] Tue 06:16
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
