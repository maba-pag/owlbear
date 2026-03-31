---
id: 223
title: Clean up dead tools.py and test_search_knowledge.py in mcp-knowledge
status: backlog
priority: nice-to-have
created: 2026-03-30T16:48:43.7634243+02:00
updated: 2026-03-30T20:47:01.1051572+02:00
started: 2026-03-30T20:46:51.7457455+02:00
tags:
    - phase-2
    - scope:mcp
    - scope:knowledge
    - chore
class: standard
---

## Objective
Remove superseded code from packages/mcp-knowledge/.

## Acceptance Criteria
- [ ] packages/mcp-knowledge/src/owlbear_mcp_knowledge/tools.py deleted (standalone search_knowledge superseded by server.py v2 API)
- [ ] packages/mcp-knowledge/tests/test_search_knowledge.py deleted (tests the deleted tools.py module)
- [ ] No imports of owlbear_mcp_knowledge.tools remain in the codebase
- [ ] All remaining mcp-knowledge tests pass

## Context
tools.py was built during #72 pipeline using asyncio.to_thread(query_for_context). Task #152 rewrote search_knowledge in server.py to use await qs.query() with StructuredSearchResult output. tools.py is no longer registered on the FastMCP server and has no callers.
See docs/research/search-knowledge-tool-impl.md section 6 (Supersession Notice).
