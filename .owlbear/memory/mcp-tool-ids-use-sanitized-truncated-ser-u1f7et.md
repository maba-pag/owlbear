---
id: 440affd1-d42d-4be8-a016-3852f31f87bb
title: MCP tool IDs use sanitized truncated server labels
categories:
- pitfall
- tool-usage
confidence: 0.84
state: deleted
scope_agents:
- builder
- reviewer
- architect
- planner
source_agent: copilot
created_at: '2026-05-17T01:34:46.225198Z'
updated_at: '2026-05-17T03:09:57.591763Z'
approved_at: null
---

In VS Code, MCP runtime tool names use `mcp_` plus a sanitized/truncated server label, not necessarily the raw configured name. Missing MCP tools may also be deferred until discovered, so use tool discovery/search before assuming a server is unavailable.
