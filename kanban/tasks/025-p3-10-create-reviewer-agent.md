---
id: 25
title: 'P3-10: Create reviewer agent'
status: done
priority: high
created: 2026-02-24T15:13:53.7692576+01:00
updated: 2026-02-26T20:37:41.1708939+01:00
started: 2026-02-26T20:31:52.8557297+01:00
completed: 2026-02-26T20:37:41.1708939+01:00
tags:
    - phase-3
    - agent
depends_on:
    - 22
class: standard
---

AC: Create .github/agents/reviewer.agent.md following existing agent structure. YAML frontmatter: name: reviewer, description: 'Read-only quality verification', argument-hint: 'Review: {task_id_or_file_paths}', tools: read-only (readFile, search, problems, runTests, terminalLastCommand, todo) + execute (runTests only). Persona: skeptical quality reviewer who never trusts self-reports. Workflow: (1) read task AC, (2) run pytest independently, (3) run ruff check, (4) read changed files, (5) verify AC compliance line by line, (6) report pass/fail with evidence. Boundaries: NEVER edit files, NEVER create files, only verify. Include good/bad examples and self-critique checklist. File: .github/agents/reviewer.agent.md
