---
id: 526
title: Update agent-common for memory-mcp integration
status: ideation
priority: needed
created: 2026-04-01T16:11:31.0131309+02:00
updated: 2026-04-01T16:11:31.0131309+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 525
class: standard
---

Update agent instructions for memory-mcp auto-loading and write mechanism per docs/research/memory-mcp-server-design.md sec 3G-3H. Depends on #525.

AC:
- [ ] agent-common.instructions.md adds Step 0: call get_knowledge with agent name
- [ ] agent-common post-task reflection updated to call record_learning (dual-write with inbox during migration)
- [ ] mcp-memory skill created with tool reference and usage examples
- [ ] copilot-instructions.md memory governance updated to clarify /memories/ vs mcp-memory boundary
