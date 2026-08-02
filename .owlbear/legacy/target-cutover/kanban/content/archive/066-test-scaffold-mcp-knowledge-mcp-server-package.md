---
id: 66
title: 'Test: Scaffold mcp-knowledge MCP server package'
status: archived
priority: medium
created: 2026-03-26 19:58:25.019009+01:00
updated: 2026-03-27 22:15:47.186772+01:00
started: 2026-03-27 22:15:47.186772+01:00
completed: 2026-03-27 22:15:47.186772+01:00
tags:
- phase-1
- scope:mcp
- scope:build
- test
depends_on:
- 7
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Write failing tests (TDD RED) for the mcp-knowledge scaffold before the builder implements #40.

## Acceptance Criteria
- [ ] packages/mcp-knowledge/tests/test_server.py exists with pytest tests
- [ ] Test: from mcp_knowledge.server import mcp succeeds and mcp is a FastMCP instance
- [ ] Test: from mcp_knowledge import mcp re-export works
- [ ] Test: mcp_knowledge.__main__ module is importable
- [ ] Test: app_lifespan context manager yields a frozen dataclass AppContext with a query_service attribute
- [ ] Test: calling search_knowledge tool function with query='test' returns a str
- [ ] Test: calling search_knowledge with query='test', limit=3 accepts the limit parameter
- [ ] All tests FAIL at this point (RED phase)
- [ ] Tests use pytest only; no real SQLite, Qdrant, or network dependencies

## Context
Preceding test task for #40. See docs/research/scaffold-mcp-knowledge.md section 4.6 for testing strategy.
Depends on #7 (monorepo skeleton must exist for package paths).
