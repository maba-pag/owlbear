---
id: 9
title: Port skills to agentskills.io format
status: ideation
priority: needed
created: 2026-03-26T17:19:53.9934892+01:00
updated: 2026-03-26T17:56:09.6619586+01:00
tags:
    - phase-1
    - scope:skills
    - type:build
depends_on:
    - 3
class: standard
---

## Objective
Port v1 skills from .github/skills/ to v2 skills/ directory using the agentskills.io open standard format.

## Acceptance Criteria
- [ ] Port tdd-workflow skill
- [ ] Port tdd-red skill
- [ ] Port code-review skill
- [ ] Port research-workflow skill
- [ ] Port kanban-md skill
- [ ] Port architecture-standards skill
- [ ] Port arch-review skill
- [ ] Port docs-gate skill
- [ ] Port task-verification skill
- [ ] Port task-decomposition skill
- [ ] Port dispatch-planning skill
- [ ] Port pytest-and-linting skill
- [ ] Port remaining skills (visual-output, excalidraw, etc.)
- [ ] Each skill follows agentskills.io directory structure
- [ ] Skills auto-load by relevance in VS Code
- [ ] Test at least 3 skills in VS Code Copilot Chat

## Context
Depends on R3 (agentskills.io spec validation) for format requirements. V1 has 15+ skills. Some may need restructuring.

[[2026-03-26]] Thu 17:56
## Additional AC
- [ ] Write v2 skills to skills/ at repo root (not .github/skills/)
- [ ] Update .vscode/settings.json chat.agentSkillsLocations to include skills/
- [ ] After v2 skills verified working, delete .github/skills/
