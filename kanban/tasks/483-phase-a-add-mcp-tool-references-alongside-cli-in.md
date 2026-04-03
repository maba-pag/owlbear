---
id: 483
title: 'Phase A: Add MCP tool references alongside CLI in all agents and skills'
status: ideation
priority: needed
created: 2026-03-31T06:20:39.2789758+02:00
updated: 2026-04-03T07:07:39.1803408+02:00
tags:
    - scope:mcp
    - ' scope:agents'
    - ' scope:skills'
    - ' type:build'
    - ' phase-2'
depends_on:
    - 470
    - 471
    - 472
    - 475
    - 476
    - 477
claimed_by: researcher
claimed_at: 2026-04-03T07:07:39.1786955+02:00
class: standard
---

## Objective\n\nAdd MCP tool alternatives alongside existing CLI references in all agent files, skill files, and instructions. Both paths work simultaneously — CLI is fallback.\n\n## Acceptance Criteria\n\n- [ ] mcp-kanban/SKILL.md expanded with: agent workflow pattern (start_work → work → Channel B → end_work), per-tool parameter reference, Channel B protocol\n- [ ] All 10 skill cheatsheets updated to include MCP tool calls alongside CLI commands\n- [ ] All 10 agent files updated with MCP tool references alongside CLI examples\n- [ ] agent-common.instructions.md Channel B section adds MCP tool syntax alongside CLI\n- [ ] Each agent's tools: section includes owlbear-kanban MCP tools\n- [ ] Agents can use either MCP or CLI — both paths produce identical results\n- [ ] No existing CLI references removed (fallback preserved)\n\n## Scope\n\nFiles (~22): 10 agents, 10 skills, agent-common.instructions.md, research-docs.instructions.md\n\n## Dependencies\n\n- Depends on: #470 (start_work), #471 (end_work), #472 (list_tasks modernize), #475 (create_task status/parent), #476 (edit_task deps/parent/title), #477 (move/pick JSON + board_context removal)\n- All server improvements must be in place before MCP references can be added
