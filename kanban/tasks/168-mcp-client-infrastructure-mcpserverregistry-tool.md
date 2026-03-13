---
id: 168
title: 'MCP client infrastructure — MCPServerRegistry + tool_resolver mcp: prefix'
status: archived
priority: nice-to-have
created: 2026-02-27T21:35:58.6945758+01:00
updated: 2026-02-28T23:53:20.4121752+01:00
started: 2026-02-28T00:40:58.3150408+01:00
completed: 2026-02-28T23:53:20.4121752+01:00
tags:
    - phase-10
    - mcp
    - tools
class: standard
---

Create MCPServerRegistry class and extend tool_resolver to support mcp: prefix.

Files: src/owlbear/tools/mcp_registry.py (new), src/owlbear/config.py (extend), src/owlbear/core/agent_registry.py (extend _tool_resolver)

AC:
- [ ] MCPServerRegistry class in src/owlbear/tools/mcp_registry.py
- [ ] MCPServerRegistry.register(name: str, server: MCPServerStdio | MCPServerHTTP) -> None
- [ ] MCPServerRegistry.get(name: str) -> MCPServer (raises KeyError if not found)
- [ ] MCPServerRegistry.names() -> list[str]
- [ ] AgentRegistry._tool_resolver extended: names starting with 'mcp:' resolve via MCPServerRegistry.get(name[4:])
- [ ] Non-mcp: names continue to resolve as before (no regression)
- [ ] mcp_servers: dict[str, dict] | None = None field in OwlBearSettings for JSON config
- [ ] MCPServerRegistry.from_config(config: dict) class method to build from settings

Depends on: #226 (test task)
See docs/research/mcp-servers.md
