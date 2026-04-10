---
id: 171
title: Fetch MCP server integration — @modelcontextprotocol/server-fetch
status: archived
priority: nice-to-have
created: 2026-02-27T21:36:28.9281625+01:00
updated: 2026-02-28T23:53:22.2595825+01:00
started: 2026-02-28T00:40:59.7626051+01:00
completed: 2026-02-28T23:53:22.2595825+01:00
tags:
    - phase-10
    - mcp
    - tools
class: standard
---

Configure Fetch MCP server as MCPServerStdio and register with MCPServerRegistry.

File: src/owlbear/tools/mcp_servers.py (extend)

AC:
- [ ] Function fetch_mcp_server() -> MCPServerStdio
- [ ] Command: npx -y @modelcontextprotocol/server-fetch
- [ ] tool_prefix='fetch' to namespace tools
- [ ] No env vars needed
- [ ] Registered as 'fetch' in MCPServerRegistry
- [ ] Robots.txt-aware (server handles this natively)

Depends on: #227 (test task), #168
See docs/research/mcp-servers.md, evaluation: .75 Consider
