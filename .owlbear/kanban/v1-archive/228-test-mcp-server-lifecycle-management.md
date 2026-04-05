---
id: 228
title: Test MCP server lifecycle management
status: archived
priority: nice-to-have
created: 2026-02-28T01:18:34.0855676+01:00
updated: 2026-02-28T23:54:10.0251664+01:00
started: 2026-02-28T01:19:15.1081239+01:00
completed: 2026-02-28T23:54:10.0251664+01:00
tags:
    - phase-10
    - mcp
    - tools
    - test
class: standard
---

TDD test task for #172. File: tests/test_mcp_registry.py (extend).

AC:
- [ ] Test MCPServerRegistry async context manager starts all registered servers on __aenter__
- [ ] Test MCPServerRegistry.__aexit__ stops all servers gracefully
- [ ] Test health_check() returns status dict per server
- [ ] Test integration with run_daemon: registry lifecycle wraps daemon loop
- [ ] Test server crash during operation is logged, not propagated
- [ ] All mocks — mock MCPServerStdio.__aenter__/__aexit__

Depends on: #168
File: tests/test_mcp_registry.py
