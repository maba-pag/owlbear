---
id: 564
title: Update agent-common and research-docs instructions with MCP alternatives
status: archived
priority: medium
created: 2026-04-03 07:46:10.769223+02:00
updated: 2026-04-03 12:38:57.236346+02:00
started: 2026-04-03 12:38:57.236346+02:00
completed: 2026-04-03 12:38:57.236346+02:00
tags:
- phase-2
- ' scope:agent-config'
- ' type:build'
parent: 483
depends_on:
- 562
- 563
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria\n\n- [ ] agent-common.instructions.md Channel B section: add MCP edit_task(append_body=..., timestamp=true) alongside CLI `kanban-md edit -a ... -t`\n- [ ] agent-common.instructions.md task coordination: add start_work/end_work MCP examples alongside CLI claim/release patterns\n- [ ] agent-common.instructions.md handoff/blocked section: add end_work(outcome='block', block_reason=...) alongside CLI handoff command\n- [ ] agent-common.instructions.md inter-agent communication: add MCP syntax for Channel B write pattern\n- [ ] research-docs.instructions.md: add MCP alternatives for any kanban CLI references\n- [ ] All ~16 CLI references in agent-common have MCP alternatives added\n- [ ] No existing CLI references removed — MCP is additive\n- [ ] Must pass #562 validation test\n\n## Scope\n\n2 files: instructions/agent-common.instructions.md, instructions/research-docs.instructions.md. Agent-common has ~16 kanban-md references across 6+ sections.\n\n## Notes\n\nResearch (section 3e) identified agent-common scope is broader than the original AC stated. Reference mcp-kanban SKILL.md (#563) for canonical MCP syntax.
