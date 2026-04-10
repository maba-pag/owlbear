---
id: 226
title: 'Test MCPServerRegistry and mcp: tool resolver'
status: archived
priority: nice-to-have
created: 2026-02-28T01:18:16.9938959+01:00
updated: 2026-02-28T23:54:08.4914867+01:00
started: 2026-02-28T01:19:14.1307965+01:00
completed: 2026-02-28T23:54:08.4914867+01:00
tags:
    - phase-10
    - mcp
    - tools
    - test
class: standard
---

TDD test task for #168. File: tests/test_mcp_registry.py (new).

AC:
- [ ] Test MCPServerRegistry() initializes with empty registry
- [ ] Test register(name, MCPServerStdio(...)) stores server config
- [ ] Test get('github') returns registered MCPServerStdio instance
- [ ] Test get('nonexistent') raises KeyError
- [ ] Test tool_resolver recognizes 'mcp:github' prefix and returns MCPServer toolset
- [ ] Test tool_resolver with 'filesystem' prefix still returns FunctionToolset (no regression)
- [ ] Test mcp_servers config field in OwlBearSettings parses JSON dict
- [ ] All mocks — no real subprocess/npx calls

File: tests/test_mcp_registry.py
