---
id: 573
title: 'P2-02: Expand mcp-kanban SKILL.md with workflow pattern + per-tool reference'
status: archived
priority: medium
created: 2026-04-03 11:14:49.209709+02:00
updated: 2026-04-03 12:39:10.226195+02:00
started: 2026-04-03 12:39:10.226195+02:00
completed: 2026-04-03 12:39:10.226195+02:00
tags:
- phase-2
- ' scope:agent-config'
- ' type:build'
parent: 483
depends_on:
- 572
class: standard
archival_reason: completed
archival_refs: []
---

## Acceptance Criteria\n\n- [ ] Agent workflow pattern section: start_work (claim+read) -> work -> Channel B via edit_task(append_body, timestamp) -> end_work (note+advance+release)\n- [ ] Per-tool parameter reference table for all 8 tools: list_tasks, show-task, create_task, move_task, edit_task, pick_task, start_work, end_work\n- [ ] Channel B protocol section with MCP edit_task examples alongside existing CLI examples\n- [ ] Error handling differences documented: ToolError (show/move/pick) vs error: prefix (list/create/edit/start/end) vs CLI exit codes\n- [ ] Compound tool advantages: start_work and end_work reduce 4-5 CLI calls to 3 MCP calls per lifecycle\n- [ ] Pitfall carryover: claim+release same-call issue applies to edit_task too, but start_work/end_work handle internally\n- [ ] Must pass mcp-kanban SKILL.md validation checks in #572\n\n## Files\n\nskills/mcp-kanban/SKILL.md\n\n## Reference\n\nSee docs/research/mcp-tool-references-alongside-cli.md sections 3a-3d for CLI-to-MCP mapping and error handling details.
