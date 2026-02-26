---
id: 24
title: 'P3-09: Create builder agent'
status: done
priority: high
created: 2026-02-24T15:13:43.2456667+01:00
updated: 2026-02-26T20:35:55.6834471+01:00
started: 2026-02-26T20:31:52.4235434+01:00
completed: 2026-02-26T20:35:55.6834471+01:00
tags:
    - phase-3
    - agent
depends_on:
    - 22
class: standard
---

AC: Create .github/agents/builder.agent.md following existing agent structure. YAML frontmatter: name: builder, description: 'Code implementation from kanban tasks with TDD', argument-hint: 'Build: {task_id_or_description}', tools: full edit/execute/read/search/test suite. Persona: disciplined TDD developer. Workflow: (1) read kanban task AC, (2) write failing tests, (3) implement minimal code, (4) run pytest + ruff, (5) move task to review. Boundaries: one task at a time, must run tests before marking done, no skipping TDD, no refactoring unrelated code. Include good/bad examples and self-critique checklist. File: .github/agents/builder.agent.md
