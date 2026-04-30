---
id: 1197
title: Remove Mock from MCP server production code
status: backlog
priority: needed
created: '2026-04-30 15:28:53.011300+00:00'
updated: '2026-04-30 15:32:04.109014+00:00'
tags:
- audit-kanban
- mcp-server
- safety
parent:
depends_on:
- 1198
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove unittest.mock.Mock from MCP server production code.

## Files
- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- MCP server tests

## Change
Remove `from unittest.mock import Mock` import and Mock scoring logic in `_agent_view_for()`. Replace with proper DI — AgentView factory or protocol. Update tests.

## AC
- [ ] No Mock import in production server code
- [ ] AgentView creation uses proper DI pattern
- [ ] MCP server tests updated and passing

## Finding: 4.2
