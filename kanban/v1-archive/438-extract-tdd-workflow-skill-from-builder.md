---
id: 438
title: Extract tdd-workflow skill from builder
status: archived
priority: needed
created: 2026-03-03T17:25:33.4596758+01:00
updated: 2026-03-04T07:58:17.9242243+01:00
started: 2026-03-03T18:03:32.8110782+01:00
completed: 2026-03-04T07:58:17.9242243+01:00
tags:
    - agent-refactor
    - skills
    - phase-refactor
class: standard
---

Extract TDD workflow into .github/skills/tdd-workflow/SKILL.md. Content: read AC, write failing test, see it fail, implement minimum code, verify with pytest+ruff, advance. Currently 80+ lines inline in builder.agent.md. Builder references skill instead of inlining. See docs/agent-quality-analysis.md section 6.1.
