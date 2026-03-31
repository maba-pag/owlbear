---
id: 469
title: Expand Challenger to researcher agent (Phase 2)
status: ideation
priority: important
created: 2026-03-31T05:04:58.6728448+02:00
updated: 2026-03-31T05:04:58.6728448+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 467
class: standard
---

Extend Challenger invocation to the researcher agent per docs/research/challenger-subagent-design.md S3h.

AC:
- [ ] researcher.agent.md frontmatter agents: includes challenger
- [ ] research-workflow SKILL.md has challenge step before finalizing recommendation
- [ ] Mandatory before DONE signal for tasks with recommendations
- [ ] Challenge input includes: proposed recommendation, evidence summary, confidence score
- [ ] Researcher integrates challenge before writing final research doc section 4

Depends on: #467 (challenger.agent.md) and #468 (arch-review integration)
