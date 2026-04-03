---
id: 531
title: Build approve_memory CLI wrapper for set_approval_state
status: ideation
priority: important
created: 2026-04-01T19:13:11.4079479+02:00
updated: 2026-04-01T19:13:11.4079479+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 525
class: standard
---

CLI script wrapping set_approval_state MCP tool for user batch approval. Per docs/research/curator-workflow-memory-mcp.md.

AC:
- [ ] scripts/approve_memory.py lists pending entries with content preview
- [ ] Interactive mode: user selects entries to approve/reject
- [ ] Batch mode: approve by ID list
- [ ] Calls set_approval_state MCP tool (not direct SQLite)
- [ ] Shows curator recommendations from curation report if available
