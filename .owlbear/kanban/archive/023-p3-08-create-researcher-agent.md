---
id: 23
title: 'P3-08: Create researcher agent'
status: archived
priority: high
created: 2026-02-24T15:13:31.2653526+01:00
updated: 2026-02-27T10:00:03.7348889+01:00
started: 2026-02-26T20:31:51.9693309+01:00
completed: 2026-02-27T10:00:03.7348889+01:00
tags:
    - phase-3
    - agent
depends_on:
    - 22
class: standard
---

AC: Create .github/agents/researcher.agent.md following the structure of existing agents (kanban-planner, orchestrator). Include: YAML frontmatter (name: researcher, description, argument-hint: 'Research: {topic}', tools: web fetch, search, read_file, askQuestions, todo, run_in_terminal). Persona: thorough intranet/web researcher who produces structured findings. Workflow: (1) clarify scope, (2) gather sources, (3) analyze, (4) write docs/*.md per research-docs guardrails, (5) create follow-up kanban tasks. Boundaries: read-only (no code edits), must produce kanban tasks, max research doc 200 lines. Include good/bad examples and self-critique checklist. File: .github/agents/researcher.agent.md
