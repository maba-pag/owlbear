---
id: 484
title: 'Phase B: Remove CLI fallback, MCP-only kanban for all agents'
status: backlog
priority: needed
created: 2026-03-31T06:20:55.32467+02:00
updated: 2026-04-03T16:43:36.4643177+02:00
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

[[2026-04-03]] Fri 16:43
## Research\nDoc: docs/research/phase-b-mcp-only-kanban-migration.md\n\nKey findings:\n- 144 CLI refs across 27 files (11 agents, 13 skills, 2 instructions, 1 copilot-instructions)\n- AC undercounts: says 10 agents/10 skills, actual is 11/13. Architect should correct.\n- MCP coverage gaps: no delete_task or handoff tools. Architect must decide: add to MCP or document as terminal-only exceptions.\n- copilot-instructions.md should be in scope (loaded by all agents)\n- PS escaping section in agent-common becomes fully obsolete\n\nSubtasks created:\n- #580 P2-B1: Agent files MCP-only (11 files, 44 refs)\n- #581 P2-B2: Skill cheatsheet tables (8 files, ~82 refs)\n- #582 P2-B3: Inline-ref skills (5 files, ~13 refs)\n- #583 P2-B4: Instruction files rewrite (2 files, 8 refs)\n- #584 P2-B5: copilot-instructions.md MCP-primary (~7 refs)\n\n## Challenge Results\n- Challenger recommendation: block (confidence in original: .55)\n- Key challenges: AC undercounting (accepted), delete/handoff MCP gaps (accepted), copilot-instructions exclusion (accepted), dependency timing (accepted), T2 reclassification (rebutted)\n- Researcher response: revised confidence .80 to .70, expanded scope to include copilot-instructions, documented MCP gaps for architect decision, maintained T1 classification (pre-approved user plan)
