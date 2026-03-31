---
id: 484
title: 'Phase B: Remove CLI fallback, MCP-only kanban for all agents'
status: ideation
priority: needed
created: 2026-03-31T06:20:55.32467+02:00
updated: 2026-03-31T06:20:55.32467+02:00
tags:
    - scope:mcp
    - ' scope:agents'
    - ' scope:skills'
    - ' type:build'
    - ' phase-2'
depends_on:
    - 483
class: standard
---

## Objective\n\nRemove all CLI fallback references from agent files, skill files, and instructions. MCP tools become the sole kanban interface for agents.\n\n## Acceptance Criteria\n\n- [ ] All kanban\\kanban-md.exe references removed from agent files (10 files)\n- [ ] All kanban\\kanban-md.exe references removed from skill cheatsheets (10 files)\n- [ ] agent-common.instructions.md Channel B section uses MCP-only syntax\n- [ ] PowerShell escaping guidance removed from agent-common.instructions.md (pipe escaping, arrow parsing, temp-file pattern — all obsolete with MCP)\n- [ ] research-docs.instructions.md updated to MCP-only\n- [ ] No agent references kanban-md.exe directly (grep verification: 0 matches in agents/ and skills/)\n- [ ] All pipeline agents still function correctly with MCP-only path\n\n## Scope\n\nSame ~22 files as Phase A. Historical research docs (docs/research/*.md) keep their CLI references — they're records, not instructions.\n\n## Dependencies\n\n- Depends on: #483 (Phase A complete and validated)
