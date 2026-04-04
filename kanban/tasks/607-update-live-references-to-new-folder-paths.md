---
id: 607
title: Update live references to new folder paths
status: backlog
priority: needed
created: 2026-04-04T20:31:40.9085909+02:00
updated: 2026-04-04T20:31:40.9085909+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
depends_on:
    - 600
    - 601
    - 602
    - 603
parent: 598
class: standard
---

## Summary

Update all agent hook command paths from scripts/hooks/ to .owlbear/hooks/. Update all live references in agents, skills, instructions, README, and copilot-instructions.md that point to old folder paths.

## Acceptance Criteria

- [ ] AC1: builder.agent.md hook path updated to .owlbear/hooks/lint-changed.ps1
- [ ] AC2: fix-attempt.agent.md hook path updated to .owlbear/hooks/lint-changed.ps1 (if applicable)
- [ ] AC3: reviewer.agent.md hook path updated to .owlbear/hooks/deny-writes.ps1
- [ ] AC4: All agent files referencing .github/skills/ updated to share/skills/
- [ ] AC5: All skill files referencing .github/agents/ updated to share/agents/
- [ ] AC6: All instruction files referencing old paths updated
- [ ] AC7: README.md directory layout table updated with new structure
- [ ] AC8: copilot-instructions.md directory structure table updated
- [ ] AC9: No live (non-historical) file references .github/agents/, .github/skills/, .github/instructions/, .github/prompts/, packages/, data/, kanban/, docs/decisions/, docs/research/, scripts/hooks/
- [ ] AC10: ruff config per-file-ignores updated for .owlbear/scripts/ paths

## Notes

Do NOT update historical docs (archived tasks, old research, resolved decisions). They document historical state.
Scan with: grep -r '.github/agents\|.github/skills\|packages/\|data/knowledge\|scripts/hooks' across live files.
