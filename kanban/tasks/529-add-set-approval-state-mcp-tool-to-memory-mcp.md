---
id: 529
title: Add set_approval_state MCP tool to memory-mcp
status: ideation
priority: needed
created: 2026-04-01T19:12:57.825057+02:00
updated: 2026-04-01T19:12:57.825057+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 525
class: standard
---

Add a 5th MCP tool to memory-mcp for approval state transitions. Per docs/research/curator-workflow-memory-mcp.md. Depends on #525.

AC:
- [ ] set_approval_state(entry_id, new_state) validates state transitions (pending to approved, pending to deleted, deleted to pending)
- [ ] Tool has correct ToolAnnotations (not readOnly, not idempotent)
- [ ] Tool excluded from pipeline agent toolsets — user-facing agents only
- [ ] Reversibility: deleted entries can be restored to pending
