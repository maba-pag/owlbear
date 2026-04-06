---
id: 651
title: 'P4-11: Create w-ideation/SKILL.md workflow'
status: backlog
priority: needed
created: 2026-04-06T07:03:25.0128472+02:00
updated: 2026-04-07T01:13:12.7058585+02:00
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

[[2026-04-07]] Tue 01:13
## Research
- Research doc: .owlbear/research/w-ideation-skill-design.md
- Sources: 5 studied (all internal), 0 external
- Recommendation: Step-based SKILL.md following w-orchestration template, M1–M6 + Step 0, tables for Blackboard/depth/voice selection (confidence: .88)
- Follow-up tasks created: none (numbering alignment deferred to review phase)
- Decision requests: none

## Challenge Results
- Challenger: FALLBACK — near-trivial structural extraction from approved spec
- Confidence in original: .88
- Key challenges: moment numbering discrepancy (AC says M0–M5 vs spec/agent M1–M6)
- Researcher response: accepted — flagged for architect resolution, recommended spec-aligned M1–M6

## Key Findings
1. **Numbering conflict** — AC says M0–M5, spec+agent use M1–M6. Recommend M1–M6 + Step 0 setup.
2. **Content split clean** — w-ideation covers process flow + Blackboard + Brief + depth + re-entry; h-voice-panel (#652) covers voice mechanics.
3. **All dependencies done** — 5/5 predecessor tasks archived.
4. **T1 classification** — no new capability or architecture change.
