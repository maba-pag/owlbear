---
id: 626
title: 'Restore #574 pipeline protocol MCP callouts — 8 failing tests'
status: archived
priority: medium
created: 2026-04-05T07:41:36.8412878+02:00
updated: 2026-04-05T07:41:47.0396401+02:00
started: 2026-04-05T07:41:47.0396401+02:00
completed: 2026-04-05T07:41:47.0396401+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:fix'
class: standard
---

## Acceptance Criteria\n\n- [ ] All 8 tests in tests/test_mcp_tool_references_574.py pass\n- [ ] MCP callout blocks restored in share/skills/r-pipeline-protocol/SKILL.md for: Channel B (append_body, timestamp), Resolved decision (show_task), Follow-up task quality (create_task), Blocking convention (unblock), Handoff (edit_task), Reading rules (show_task)\n- [ ] Callout format matches existing MCP notes pattern in the file\n\n## Context\n\nTask #574 (archived) added 9 MCP callout blocks to instructions/agent-common.instructions.md (commit 4f929da). During v2 reorganization, that file became share/skills/r-pipeline-protocol/SKILL.md but the MCP callouts were NOT carried over. The #574 acceptance tests (8 assertions) now fail.\n\nPreferred action: unarchive #574 and send back through pipeline. If not feasible, this task covers the same work.\n\n## Files\n\nshare/skills/r-pipeline-protocol/SKILL.md, tests/test_mcp_tool_references_574.py\n\n## Research\n\nFrom .owlbear/research/575-agent-mcp-lifecycle-audit.md section 3d.
