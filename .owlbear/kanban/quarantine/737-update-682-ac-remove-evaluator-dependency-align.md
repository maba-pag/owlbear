---
id: 737
title: 'Update #682 AC: remove evaluator dependency, align with 3-step orchestrator'
status: archived
priority: needed
created: 2026-03-10T21:03:20.0025282+01:00
updated: 2026-03-10T22:34:17.1345531+01:00
started: 2026-03-10T22:34:17.1345531+01:00
completed: 2026-03-10T22:34:17.1345531+01:00
tags:
    - scope:copilot
    - agent
    - phase-agent-arch
class: standard
---

## Context

Task #682 (Orchestrator rewrite) has stale AC that references an 8-step workflow with evaluator (Step 4). The evaluator was superseded (see #681, docs/research/evaluator-agent-final-disposition.md). The committed orchestrator already uses a 3-step plan/dispatch/loop design.

## Acceptance Criteria

- [ ] #682 AC updated: remove Step 4 (Evaluate) and Step 5 (Execute evaluator verdicts)
- [ ] #682 AC aligns with the current 3-step orchestrator design (plan/dispatch/re-plan)
- [ ] #682 depends_on no longer includes #681
- [ ] #682 body references current orchestration SKILL.md as source of truth
