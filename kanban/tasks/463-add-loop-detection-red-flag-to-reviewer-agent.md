---
id: 463
title: Add loop-detection red flag to reviewer agent
status: ideation
priority: important
created: 2026-03-31T03:44:55.6845277+02:00
updated: 2026-03-31T03:44:55.6845277+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 454
class: standard
---

## Context
Add a red flag entry to reviewer.agent.md that cross-references the new Step 6.7 loop-detection check in the code-review skill.

See docs/research/reviewer-loop-pattern-detection.md for analysis.

## Acceptance Criteria
- [ ] New red flag in reviewer.agent.md: 'You have not checked builder notes for loop patterns (Step 6.7)'
- [ ] Red flag placed in the existing Red flags list alongside other review checks
- [ ] depends_on: #454 (Step 6.7 must exist before the red flag references it)
