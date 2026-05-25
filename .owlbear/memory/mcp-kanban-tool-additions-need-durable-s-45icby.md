---
id: 9ca815b3-f861-4784-b26a-34b4e7d936d7
title: mcp-kanban tool additions need durable surface-contract proof
categories:
- pitfall
- process
- domain-knowledge
confidence: 0.9
state: curated
scope_agents:
- reviewer
- builder
- test-writer
- architect
source_agent: reviewer
created_at: '2026-05-25T19:47:04.634270Z'
updated_at: '2026-05-25T20:46:47.483601Z'
approved_at: null
---

When reviewing mcp-kanban tasks that add or remove MCP tools, check serve/mcp-kanban/tests/test_mcp_surface_contract.py. Its EXPECTED_TOOLS snapshot is an authoritative deployment contract; task-local green tests can false-green if the snapshot is not updated with server.py registrations.
