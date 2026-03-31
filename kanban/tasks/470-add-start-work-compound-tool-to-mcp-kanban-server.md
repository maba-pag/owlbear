---
id: 470
title: Add start_work compound tool to mcp-kanban server
status: in-progress
priority: needed
created: 2026-03-31T05:21:07.0515037+02:00
updated: 2026-03-31T07:31:10.6204+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
class: standard
---

## Acceptance Criteria\n\n- [ ] New `start_work(task_id, claim?)` tool in `server.py`\n- [ ] If no claim provided, generate one via `kanban-md agent-name` subprocess call\n- [ ] Claim the task at its current status (no status change)\n- [ ] Return JSON: task details (full, like show_task) + `claim_name` field with the name used\n- [ ] Compound operation: single tool call replaces claim + show (2 tool calls -> 1)\n- [ ] Tests cover: auto-generated claim, explicit claim, already-claimed error, JSON response\n- [ ] Tool respects KANBAN_TOOLS_EXCLUDE if implemented (#473)\n- [ ] Update mcp-kanban SKILL.md to document the new tool\n\n## Design Notes\n\n- Every pipeline agent calls this before starting work on a dispatched task\n- No status move: the task is already in the correct status when dispatched\n- The auto-generated claim name lets agents release their claim at end_work without needing to know their name in advance

[[2026-03-31]] Tue 06:14
## Research
Research doc: docs/research/start-work-compound-tool.md

Key findings (.90 confidence):
- Implementation: standard @mcp.tool() with 2-3 sequential _run_kanban calls (agent-name, edit --claim, show --json)
- Parse show JSON, inject claim_name field, return merged JSON string
- ~30 LOC implementation + ~60 LOC tests
- No special FastMCP compound construct needed
- agent-name generates unique two-word names (e.g. cedar-cloud)
- Claim conflict returns rc!=0 with descriptive stderr - surface as error string
- No new follow-up tasks needed - #470 AC is well-scoped, #471/#473 are independent siblings
