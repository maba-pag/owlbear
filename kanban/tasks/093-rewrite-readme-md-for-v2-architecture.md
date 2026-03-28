---
id: 93
title: Rewrite README.md for v2 architecture
status: ideation
priority: needed
created: 2026-03-28T01:48:37.0476424+01:00
updated: 2026-03-28T01:48:37.0476424+01:00
tags:
    - phase-1
    - scope:docs
    - type:docs
depends_on:
    - 28
class: standard
---

Rewrite README.md per docs/research/readme-v2-rewrite.md. Use the recommended structure: title, overview, prerequisites, quick start, directory layout, how it works, development, license. Target ~60 lines.

AC:
- [ ] Title: On-demand AI development system built on GitHub Copilot
- [ ] Overview: 2-3 sentences, no v1 references
- [ ] Prerequisites: Python 3.12+, uv, VS Code + Copilot, Copilot CLI
- [ ] Quick Start: git clone, uv sync, kanban setup, open VS Code
- [ ] Directory layout table matching copilot-instructions.md
- [ ] How It Works: agents, skills, MCP servers, orchestrator
- [ ] Development: uv sync, pytest, ruff (keep existing commands)
- [ ] No v1 references: no daemon, bearclaw, PydanticAI, Slack, approval gates, browser automation, Qdrant
- [ ] Total length under 80 lines
- [ ] License section preserved
