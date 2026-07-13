---
id: 40
title: Scaffold mcp-knowledge MCP server package
status: archived
priority: medium
created: 2026-03-26 18:50:00.925995+01:00
updated: 2026-03-27 22:15:35.276006+01:00
started: 2026-03-27 22:15:35.276006+01:00
completed: 2026-03-27 22:15:35.276006+01:00
tags:
- phase-1
- scope:mcp
- scope:build
depends_on:
- 7
- 66
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Create packages/mcp-knowledge/ with a working FastMCP server exposing a placeholder knowledge tool via stdio transport.

## Acceptance Criteria
- [ ] packages/mcp-knowledge/pyproject.toml: name=owlbear-mcp-knowledge, build-system uses uv_build (>=0.11.1,<0.12), requires-python >=3.12, runtime dep on mcp (>=1.26,<2)
- [ ] packages/mcp-knowledge/src/mcp_knowledge/__init__.py re-exports the mcp FastMCP instance from server module
- [ ] packages/mcp-knowledge/src/mcp_knowledge/__main__.py calls mcp.run() (stdio transport, no extra args)
- [ ] packages/mcp-knowledge/src/mcp_knowledge/server.py creates mcp = FastMCP('owlbear-knowledge', lifespan=app_lifespan) and registers tools
- [ ] app_lifespan is an @asynccontextmanager yielding a frozen @dataclass AppContext with stub fields (query_service: Any = None); no real DB connections (deferred to #54)
- [ ] search_knowledge(query: str, limit: int = 5) registered via @mcp.tool(), returns static string 'Not yet implemented' (real impl deferred to #54)
- [ ] .vscode/mcp.json entry: owlbear-knowledge with type=stdio, command=uv, args=['run','--directory','${workspaceFolder}','python','-m','mcp_knowledge']
- [ ] All tests from preceding test task #66 pass GREEN

## Context
See docs/research/mcp-python-sdk.md for SDK patterns.
See docs/research/scaffold-mcp-knowledge.md for scaffold blueprint.
See docs/research/monorepo-tooling.md for uv workspace conventions.
Knowledge engine integration deferred to #54 (real search) and #55 (ingest/graph tools).

## Research
Doc: docs/research/scaffold-mcp-knowledge.md
Feasibility: confirmed (.90) for all AC items. FastMCP v1 lifespan pattern compatible with sync GraphStore + async QdrantVectorStore.
Risk: packages/ dir and root pyproject.toml do not exist yet (depends on #7).

[[2026-03-26]] Thu 19:59
## Architecture Review
**Verdict:** REFINE

### AC Assessment
AC1 (package structure): Missing src/ layout, __init__.py, pyproject.toml field details. Rewritten with full path and field specs.
AC2 (FastMCP stdio): Clear and verifiable. Kept.
AC3 (placeholder tool): 'placeholder' was undefined. Rewritten: returns static string.
AC4 (lifespan): Contradicted scaffold scope (referenced real DB connections). Rewritten: stub AppContext with None fields.
AC5 (mcp.json): Clear. Kept.
AC6 (tests): Vague and belongs in TDD test task. Replaced with 'All tests from #66 pass GREEN'.

### Architecture Notes
Research is thorough (.90 confidence). Pattern follows Qdrant MCP server and MCP Memory server conventions. Stdio transport is correct for single-user laptop-resident use. v1 knowledge engine interfaces verified: GraphStore (sync sqlite3), QdrantVectorStore (sync client with lazy collection init), KnowledgeQueryService (sync with hybrid search), BgeM3EmbeddingProvider (sync with lazy model load). All are suitable for lifespan-managed injection once real integration begins (#54/#55).

Critical gap: packages/ dir and root pyproject.toml do not exist. Task #7 (Create monorepo skeleton) must complete first. Added depends_on #7.

### Changes Made
- Rewrote AC: 6 vague items refined to 8 precise verifiable items
- Added depends_on #7 (monorepo skeleton)
- Added depends_on #66 (TDD RED test task)
- Created test task #66 at backlog with depends_on #7
- Removed 'Tests for tool functions' from impl AC (moved to #66)

### Dependencies
- Added: #7 (Create monorepo skeleton) required for packages/ dir and root pyproject.toml
- Added: #66 (Test: Scaffold mcp-knowledge) TDD RED phase must run first
- Verified: #54 and #55 correctly listed as follow-ups (not blockers)
