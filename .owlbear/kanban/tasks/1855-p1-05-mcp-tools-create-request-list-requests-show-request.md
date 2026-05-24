---
id: 1855
title: 'P1-05: MCP tools — create_request, list_requests, show_request'
status: backlog
priority: needed
created: 2026-05-24T20:58:39.096212+02:00
updated: 2026-05-24T21:00:29.455798+02:00
tags:
  - phase-1
  - scope:mcp-kanban
  - mcp
parent: 1850
depends_on:
  - 1854
ac:
  - create_request MCP tool registered via @mcp.tool() accepts (task_id, kind, 
    title, summary, agent, options?, body?), delegates to engine create_request,
    and returns the created request model as JSON dict.
  - list_requests MCP tool accepts (status?, task_id?), delegates to engine 
    list_requests, and returns a list of request summary dicts.
  - show_request MCP tool accepts (request_id), delegates to engine get_request,
    and returns full request detail including resolution state; raises ToolError
    when request_id is not found.
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1850 and `.owlbear/briefs/draft-decision-request-data-model/brief.md`

## Scope

**In scope:**
- Three new MCP tools: `create_request`, `list_requests`, `show_request`
- Parameter validation and forwarding to engine
- Error mapping (NotFoundError → ToolError, ValidationError → ToolError)
- No `resolve_request` MCP tool (resolution is human-only via Cockpit)

**Out of scope:**
- Engine implementation (done in P1-01 through P1-04)
- Old `create_dr` tool (retained until P2-05 removal)
- Cockpit API

## Test scope
`serve/mcp-kanban/tests/`