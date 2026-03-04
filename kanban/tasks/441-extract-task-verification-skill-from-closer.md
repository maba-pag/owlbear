---
id: 441
title: Extract task-verification skill from closer
status: archived
priority: needed
created: 2026-03-03T17:25:54.425773+01:00
updated: 2026-03-04T07:58:19.8199829+01:00
started: 2026-03-03T18:03:34.7423052+01:00
completed: 2026-03-04T07:58:19.8199829+01:00
tags:
    - agent-refactor
    - skills
    - phase-refactor
class: standard
---

Extract verification protocol into .github/skills/task-verification/SKILL.md. Content: check AC with evidence, score confidence, archive task, commit and push. Currently 60+ lines inline in closer.agent.md. See docs/agent-quality-analysis.md section 6.1.
