---
id: 1862
title: 'P2-05: Remove old create_dr MCP tool and engine function'
status: backlog
priority: important
created: 2026-05-24T20:59:51.125636+02:00
updated: 2026-05-24T21:00:29.559976+02:00
tags:
  - phase-2
  - scope:mcp-kanban
  - cleanup
parent: 1850
depends_on:
  - 1855
  - 1861
ac:
  - create_dr function and @mcp.tool() registration are removed from 
    serve/mcp-kanban/src/owlbear_mcp_kanban/server.py; calling the tool via MCP 
    returns a "tool not found" error.
  - Engine function create_dr in serve/kanban/src/owlbear_kanban/decisions.py is
    removed; imports of create_dr from other modules raise ImportError or are 
    updated to use create_request.
  - Tests in serve/mcp-kanban/tests/test_mcp_create_dr.py are removed; a 
    regression test verifies that "create_dr" is absent from the MCP tool 
    registry.
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
- Remove `create_dr` MCP tool from server.py
- Remove `create_dr` engine function from decisions.py
- Remove or update test file `test_mcp_create_dr.py`
- Update imports that reference old `create_dr`
- Add regression test confirming tool absence

**Out of scope:**
- Old Cockpit resolve flow (P2-06)
- New structured tools (already shipped in P1-05)

## Downstream impact
- `serve/mcp-kanban/tests/test_mcp_create_dr.py` — remove
- `serve/cockpit/src/owlbear_cockpit/routes/decisions.py` — may import `create_dr` helpers; update references
- Any agent instructions referencing `create_dr` tool name

## Test scope
`serve/mcp-kanban/tests/`