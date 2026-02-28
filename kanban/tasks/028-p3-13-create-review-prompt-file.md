---
id: 28
title: 'P3-13: Create review prompt file'
status: archived
priority: medium
created: 2026-02-24T15:14:22.5909624+01:00
updated: 2026-02-27T10:00:06.9848934+01:00
started: 2026-02-26T20:31:54.2538327+01:00
completed: 2026-02-27T10:00:06.9848934+01:00
tags:
    - phase-3
    - agent
depends_on:
    - 25
class: standard
---

AC: Create .github/prompts/review.prompt.md. YAML frontmatter: agent: reviewer, description: 'Review and verify task output'. Body: prompt template with input variable for task ID or file paths. Context section: read task AC, run tests independently, check ruff, verify AC compliance with evidence. Follow pattern of existing prompt files. File: .github/prompts/review.prompt.md
