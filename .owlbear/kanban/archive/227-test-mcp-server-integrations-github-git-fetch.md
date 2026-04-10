---
id: 227
title: Test MCP server integrations (GitHub, Git, Fetch)
status: archived
priority: nice-to-have
created: 2026-02-28T01:18:25.8043422+01:00
updated: 2026-02-28T23:54:09.210092+01:00
started: 2026-02-28T01:19:14.6142284+01:00
completed: 2026-02-28T23:54:09.210092+01:00
tags:
    - phase-10
    - mcp
    - test
class: standard
---

TDD test task for #169, #170, #171. File: tests/test_mcp_servers.py (new).

AC:
- [ ] Test GitHub MCP server config produces correct MCPServerStdio args (npx, package, env vars)
- [ ] Test Git MCP server config produces correct MCPServerStdio args
- [ ] Test Fetch MCP server config produces correct MCPServerStdio args
- [ ] Test tool_prefix is set correctly ('github', 'git', 'fetch') to avoid naming conflicts
- [ ] Test env var injection: GITHUB_PERSONAL_ACCESS_TOKEN passed from settings.github_token
- [ ] All mocks — no real npx/subprocess calls; test config wiring only

Depends on: #168
File: tests/test_mcp_servers.py
