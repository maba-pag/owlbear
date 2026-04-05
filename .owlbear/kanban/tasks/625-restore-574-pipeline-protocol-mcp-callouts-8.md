---
id: 625
title: 'Restore #574 pipeline protocol MCP callouts — 8 failing tests'
status: ideation
priority: needed
created: 2026-04-05T07:41:30.2992757+02:00
updated: 2026-04-05T07:41:30.2992757+02:00
tags:
    - phase-2
    - ' scope:agent-config'
    - ' type:fix'
class: standard
---

## Acceptance Criteria

- [ ] All 8 tests in tests/test_mcp_tool_references_574.py pass
- [ ] MCP callout blocks restored in share/skills/r-pipeline-protocol/SKILL.md for:
  - Channel B: `append_body`, `timestamp` parameter names
  - Resolved decision pre-flight: `show_task`
  - Follow-up task quality: `create_task`
  - Channel B section: `append_body`
  - Blocking convention: `unblock`
  - Handoff/blocked: `edit_task`
  - Reading rules: `show_task`
- [ ] Callout format matches existing MCP notes pattern in the file

## Context

Task #574 (archived) added 9 MCP callout blocks to instructions/agent-common.instructions.md (commit 4f929da). During v2 reorganization, that file became share/skills/r-pipeline-protocol/SKILL.md but the MCP callouts were NOT carried over. The #574 acceptance tests (8 assertions) now fail.

Preferred action: unarchive #574 and send back through pipeline. If that's not feasible, this task covers the same work.

## Files

share/skills/r-pipeline-protocol/SKILL.md, tests/test_mcp_tool_references_574.py

## Research

From .owlbear/research/575-agent-mcp-lifecycle-audit.md section 3d.
