---
id: 652
title: 'P4-12: Create h-voice-panel/SKILL.md handbook'
status: backlog
priority: needed
created: 2026-04-06T07:03:34.3182692+02:00
updated: 2026-04-07T01:18:37.7949437+02:00
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

- [ ] `share/skills/h-voice-panel/SKILL.md` exists with valid YAML frontmatter
- [ ] Characterizes each voice: domain, persona, temperature guidance, output format
- [ ] Documents invocation patterns: parallel batch, sequential deep-dive
- [ ] Defines Critic-loop rules: when to challenge, convergence threshold, max rounds
- [ ] Covers disagreement resolution: surface to user, user decides
- [ ] Covers Mediator synthesis rules: how voices merge into decisions
- [ ] References all voice agents by name

## Context

Spec: `.owlbear/research/thinking-companion-framework.md` - Sections 7, 12.
Handbook companion to w-ideation. Provides the reference material that voice agents and the Mediator consult for behavioral rules.

[[2026-04-07]] Tue 01:18
## Research
- Research doc: .owlbear/research/voice-panel-handbook.md
- Sources: 8 studied, 5 high-relevance (≥0.85)
- Recommendation: 8-section handbook consolidating voice characterizations, invocation patterns, Critic-loop rules, voice selection logic, disagreement resolution, and synthesis rules from spec §7/§12 + 6 agent files (confidence: 0.88)
- Follow-up tasks created: none — task #652 itself covers the build
- Decision requests: none (T1 — autonomous)

## Challenge Results
- Challenger: proceed (adjusted)
- Confidence in original: 0.88 (down from 0.90)
- Key challenges: (1) Voice selection logic table missing from proposed 7-section outline — accepted, added 8th section; (2) "convergence threshold" AC term maps to qualitative Critic exit condition, not numeric — accepted, noted as interpretation
- Researcher response: accepted both — revised structure to 8 sections, documented AC interpretation for convergence threshold
