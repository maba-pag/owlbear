---
id: 169
title: GitHub MCP server integration — @modelcontextprotocol/server-github
status: archived
priority: nice-to-have
created: 2026-02-27T21:36:06.809714+01:00
updated: 2026-02-28T23:53:21.0189219+01:00
started: 2026-02-28T00:40:58.8040111+01:00
completed: 2026-02-28T23:53:21.0189219+01:00
tags:
    - phase-10
    - mcp
    - github
class: standard
---

Configure GitHub MCP server as MCPServerStdio and register with MCPServerRegistry.

File: src/owlbear/tools/mcp_servers.py (new) or extend mcp_registry.py

AC:
- [ ] Function github_mcp_server(token: str) -> MCPServerStdio that returns configured instance
- [ ] Command: npx -y @modelcontextprotocol/server-github
- [ ] env={'GITHUB_PERSONAL_ACCESS_TOKEN': token}
- [ ] tool_prefix='github' to namespace tools
- [ ] Token sourced from OwlBearSettings.github_token
- [ ] Registered as 'github' in MCPServerRegistry
- [ ] Agent definitions can reference tools=['mcp:github']

Depends on: #227 (test task), #168
See docs/mcp-servers-research.md, evaluation: .90 Adopt
