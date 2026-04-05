---
id: 170
title: Git MCP server integration — @modelcontextprotocol/server-git
status: archived
priority: nice-to-have
created: 2026-02-27T21:36:22.2604933+01:00
updated: 2026-02-28T23:53:21.6487364+01:00
started: 2026-02-28T00:40:59.2939471+01:00
completed: 2026-02-28T23:53:21.6487364+01:00
tags:
    - phase-10
    - mcp
    - tools
class: standard
---

Configure Git MCP server as MCPServerStdio and register with MCPServerRegistry.

File: src/owlbear/tools/mcp_servers.py (extend)

AC:
- [ ] Function git_mcp_server() -> MCPServerStdio
- [ ] Command: npx -y @modelcontextprotocol/server-git
- [ ] tool_prefix='git_mcp' to avoid naming conflict with native GitLocalToolset
- [ ] No env vars needed (local-only)
- [ ] Registered as 'git' in MCPServerRegistry
- [ ] Document overlap with native GitLocalToolset in code comment

Depends on: #227 (test task), #168
See docs/research/mcp-servers.md, evaluation: .80 Consider
