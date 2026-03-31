---
id: 370
title: 'Update #136 AC: bookmark tools target server.py not tools.py'
status: backlog
priority: nice-to-have
created: 2026-03-30T20:46:21.9111795+02:00
updated: 2026-03-30T23:50:41.4952989+02:00
tags:
    - phase-2
    - scope:mcp
    - scope:knowledge
    - chore
class: standard
---

## Objective
Task #136 AC line 4 references `packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py` for bookmark_source and list_bookmarks registration. This file is being deleted by #223. Update the AC to register bookmark tools as `@mcp.tool()` decorators in `server.py`, following the v2 pattern established by #152.

## Acceptance Criteria
- [ ] Task #136 AC line "bookmark_source and list_bookmarks registered as MCP tools in packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py" updated to reference server.py
- [ ] AppContext extension AC updated to match server.py pattern (lifespan_context, not standalone AppContext)

## Context
See docs/research/dead-code-mcp-knowledge-tools.md §3.3. tools.py was the v1 approach (#72); server.py is the v2 pattern (#152). Task #223 deletes tools.py.
