---
id: 659
title: Update h-agent-structure user-invocable example to not list deprecated skill
status: backlog
priority: nice-to-have
created: 2026-04-06T07:23:34.6813674+02:00
updated: 2026-04-06T15:12:25.0919229+02:00
tags:
    - phase-4
    - ' scope:ideator'
    - ' type:chore'
depends_on:
    - 643
class: standard
---

## Acceptance Criteria

- [ ] `share/skills/h-agent-structure/SKILL.md` line 182 no longer lists `w-project-scoping` as an active `user-invocable` example
- [ ] Replacement example or annotation added (e.g., use `w-retro` or `h-excalidraw-diagram` as sole examples)

## Context

Research: `.owlbear/research/deprecate-w-project-scoping.md`
Current text at L182: `Set true only for skills users invoke directly via / menu (e.g., w-project-scoping, w-retro, h-excalidraw-diagram).`
After w-project-scoping is deprecated, this example should not suggest it as a model reference.
Parent task: #643

[[2026-04-06]] Mon 15:12
## Research
- Work already completed by parent task #643 (commit `98727c1`, archived with 1.00 audit confidence)
- The architect's refined AC for #643 explicitly subsumed #659: "tasks #658 and #659 are redundant (subsumed by this refined AC)"
- Verified current file state: `share/skills/h-agent-structure/SKILL.md` L182 lists only `w-retro` and `h-excalidraw-diagram` — `w-project-scoping` already removed
- Research doc: `.owlbear/research/deprecate-w-project-scoping.md` (from parent #643)
- Sources: 1 studied (parent task #643 body with full pipeline trail)
- Recommendation: No further action needed (confidence: .98)
- Follow-up tasks created: none — both ACs already satisfied
- Decision requests: none (T1 autonomous, already resolved)
- Tier: T1 — Autonomous (redundant task, work subsumed by parent)

## Challenge Results
- Challenger: SKIPPED — task is already complete, no recommendation to challenge
- Confidence in original: .98
