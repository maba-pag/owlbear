---
id: 27
title: 'P3-12: Create build prompt file'
status: done
priority: medium
created: 2026-02-24T15:14:14.2817211+01:00
updated: 2026-02-26T20:38:52.0625745+01:00
started: 2026-02-26T20:31:53.7352069+01:00
completed: 2026-02-26T20:38:52.0625745+01:00
tags:
    - phase-3
    - agent
depends_on:
    - 24
class: standard
---

AC: Create .github/prompts/build.prompt.md. YAML frontmatter: agent: builder, description: 'Implement a kanban task or feature'. Body: prompt template with input variable for task ID or feature description. Context section: read task AC with kanban show, write tests first, run pytest + ruff before marking done, follow TDD workflow. Follow pattern of existing prompt files. File: .github/prompts/build.prompt.md
