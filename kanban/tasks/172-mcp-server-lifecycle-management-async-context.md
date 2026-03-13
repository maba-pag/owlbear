---
id: 172
title: MCP server lifecycle management — async context manager, health checks
status: archived
priority: nice-to-have
created: 2026-02-27T21:36:35.9942091+01:00
updated: 2026-02-28T23:53:22.8897095+01:00
started: 2026-02-28T00:41:00.240558+01:00
completed: 2026-02-28T23:53:22.8897095+01:00
tags:
    - phase-10
    - mcp
    - tools
class: standard
---

Implement async context manager lifecycle, health checks, and graceful shutdown for MCPServerRegistry.

File: src/owlbear/tools/mcp_registry.py (extend)

AC:
- [ ] MCPServerRegistry.__aenter__ starts all registered MCPServer instances (calls their __aenter__)
- [ ] MCPServerRegistry.__aexit__ stops all servers gracefully (calls their __aexit__)
- [ ] health_check() -> dict[str, bool]: pings each server, returns {name: alive}
- [ ] Server start failure is logged and skipped (does not prevent other servers from starting)
- [ ] Integration point: run_daemon wraps its loop in async with registry
- [ ] Graceful shutdown on daemon stop: servers cleaned up before PID file removal

Depends on: #228 (test task), #168
See docs/research/mcp-servers.md
