---
id: 565
title: Update pipeline agent files with MCP tool references alongside CLI
status: archived
priority: medium
created: 2026-04-03 07:46:22.191013+02:00
updated: 2026-04-03 12:39:01.257788+02:00
started: 2026-04-03 12:39:01.257788+02:00
completed: 2026-04-03 12:39:01.257788+02:00
tags:
- phase-2
- ' scope:agent-config'
- ' type:build'
parent: 483
depends_on:
- 562
- 564
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria\n\n- [ ] All 10 pipeline agent files updated: builder, reviewer, writer, auditor, architect, researcher, test-writer, planner, kanban-planner, curator\n- [ ] Each agent shows the MCP workflow pattern (start_work → edit_task Channel B → end_work) alongside existing CLI workflow\n- [ ] Agent-specific MCP examples: e.g., reviewer uses end_work(outcome='fail') for rejection, auditor uses end_work(outcome='success') for archive\n- [ ] MCP tool references match patterns defined in agent-common (#564) and mcp-kanban SKILL.md (#563)\n- [ ] tools: YAML section already has owlbear-kanban/* (verified — no changes needed there)\n- [ ] No existing CLI references removed — MCP is additive\n- [ ] Must pass #562 validation test\n\n## Scope\n\n10 files: agents/{builder,reviewer,writer,auditor,architect,researcher,test-writer,planner,kanban-planner,curator}.agent.md. Body-text changes only, not YAML frontmatter.\n\n## Notes\n\nAC item 5 from parent (tools: section) is already satisfied for all 10 agents. This task covers body-text guidance teaching agents when/how to use MCP tools. See research section 3b for the compound tool workflow pattern.
