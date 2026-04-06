---
id: 651
title: 'P4-11: Create w-ideation/SKILL.md workflow'
status: research
priority: needed
created: 2026-04-06T07:03:25.0128472+02:00
updated: 2026-04-06T07:03:25.0128472+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:build'
depends_on:
    - 646
    - 647
    - 648
    - 649
    - 650
class: standard
---

## Acceptance Criteria

- [ ] `share/skills/w-ideation/SKILL.md` exists with valid YAML frontmatter
- [ ] Documents the 6-moment process flow (M0–M5) with entry/exit criteria
- [ ] Defines deliberation flow: Mediator → Voice panel → Critic loop → convergence
- [ ] Specifies Blackboard contract: Working Directory layout, file ownership, read/write rules
- [ ] Covers Brief artifact structure and handoff to pipeline
- [ ] Covers adaptive depth (trivial → tiers 1–3) decision rules
- [ ] Covers re-entry protocol (returning to existing Working Dir)
- [ ] References all voice agents by name

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 6, 7, 8, 10, 12.
This is the primary workflow skill that the Ideator agent invokes. Equivalent to w-orchestration for the pipeline.
