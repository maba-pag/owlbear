---
id: 784
title: Add two-pass review checklist with suppressions to reviewer skill
status: archived
priority: needed
created: 2026-03-13T16:47:52.3755465+01:00
updated: 2026-03-13T17:25:56.8936519+01:00
started: 2026-03-13T17:05:18.9184193+01:00
completed: 2026-03-13T17:25:56.8936519+01:00
tags:
    - research
    - scope:agent-config
    - type:docs
class: standard
---

## Goal
Adapt gstack's two-pass review checklist pattern for OwlBear's reviewer agent.

## AC
- [ ] code-review SKILL.md has a two-pass structure: Pass 1 (CRITICAL: security, injection, data safety) and Pass 2 (INFORMATIONAL: style, naming, dead code)
- [ ] Suppressions section lists patterns the reviewer should NOT flag (e.g., harmless redundancy, threshold values)
- [ ] reviewer.agent.md references the two-pass structure
- [ ] No changes to .py files

See docs/research/gstack-agent-patterns.md for prior art.

[[2026-03-13]] Fri 17:05
## Research
Doc: docs/research/two-pass-review-checklist.md

Key findings:
- gstack two-pass model (CRITICAL blocks, INFORMATIONAL doesn't) is lowest-effort, highest-ROI approach
- Google 'Nit:' prefix and Conventional Comments confirm tiered severity is industry standard
- OwlBear's existing steps 5/5a/5b/5c map cleanly to two tiers without new checks
- 9 suppression patterns identified from gstack + OwlBear-specific review history
- Confidence: .85

Follow-up: #787 (implement two-pass checklist in SKILL.md + agent.md)
