---
id: 486
title: 'Phase C: Consolidate kanban references to central skill + minimal agent config'
status: ideation
priority: needed
created: 2026-03-31T06:21:08.9537277+02:00
updated: 2026-03-31T06:21:08.9537277+02:00
tags:
    - scope:mcp
    - ' scope:agents'
    - ' scope:skills'
    - ' type:build'
    - ' phase-2'
depends_on:
    - 484
class: standard
---

## Objective\n\nConsolidate kanban references from ~20 files to a central skill + minimal per-agent config. Eliminate DRY violations.\n\n## Acceptance Criteria\n\n- [ ] mcp-kanban/SKILL.md is the single source of truth for all kanban tool operations, agent workflow pattern, and Channel B protocol\n- [ ] Each skill's kanban cheatsheet replaced with 1-2 line reference: `See mcp-kanban skill. Section header: ## {X}`\n- [ ] Each agent file has a compact kanban config block (~4 lines): section header, rejection target, follow-up behavior\n- [ ] agent-common.instructions.md Channel B section references mcp-kanban skill instead of duplicating tool syntax\n- [ ] Section-header-to-agent mapping table remains in agent-common (single reference point)\n- [ ] Grep verification: no duplicated kanban tool parameter docs outside mcp-kanban/SKILL.md\n- [ ] All pipeline agents still function correctly after consolidation\n\n## Design\n\nPer-agent kanban config (replaces 15-line cheatsheets):\n```markdown\n## Kanban protocol\n- Section header: ## Builder Notes\n- On reject: end_work(outcome=\"block\", block_reason=\"...\")\n- Follow-ups: none\n- See mcp-kanban skill for tool workflows\n```\n\n## Dependencies\n\n- Depends on: #484 (Phase B — CLI references already removed, MCP-only)
