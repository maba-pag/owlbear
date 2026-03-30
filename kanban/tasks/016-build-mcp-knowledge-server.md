---
id: 16
title: Build mcp-knowledge server
status: todo
priority: needed
created: 2026-03-26T17:21:28.0951097+01:00
updated: 2026-03-30T08:06:23.0903348+02:00
tags:
    - phase-1
    - scope:mcp
    - type:build
depends_on:
    - 2
    - 15
    - 152
class: standard
---

## Objective
Build the mcp-knowledge MCP server Phase A (non-ingest tools). Extends the existing server.py (created by #55) with search_knowledge (v2 API), list_sources, and knowledge://stats resource.

## Acceptance Criteria

### Server structure (packages/mcp-knowledge/src/owlbear_mcp_knowledge/)
- [ ] server.py: FastMCP("owlbear-knowledge", lifespan=app_lifespan) following mcp-kanban server.py pattern (already exists from #55; extend, do not replace)
- [ ] AppContext dataclass with fields: query_service (KnowledgeQueryService or None), graph_store (GraphStore), source_store (KnowledgeSourceStore), ingest_pipeline (IngestPipeline | None, already wired by #55 — preserve)
- [ ] app_lifespan: reads OWLBEAR_KB_PATH env var (default "data/knowledge/knowledge.db"), constructs GraphStore(conn) + KnowledgeSourceStore(conn) + QdrantVectorStore + BgeM3EmbeddingProvider + KnowledgeQueryService(vector_store, graph_store, embedding_provider); preserves existing IngestPipeline wiring from #55 (DocumentStore, EntityExtractor, TextChunker); yields AppContext, closes conn in finally block
- [ ] __main__.py: from .server import mcp; mcp.run() (already exists from #55)
- [ ] stdio transport (no SSE/HTTP)

### Tools (all registered via @mcp.tool(), verb-first docstrings)
- [ ] search_knowledge(ctx, query: str, limit: int = 5) returns str: awaits KnowledgeQueryService.query(query, top_k=limit) directly (method is async; underlying sync calls acceptable for stdio single-user context); formats list[StructuredSearchResult] as bullet list "- {title} ({score:.2f}): {snippet[:200]}"; returns "No relevant knowledge found." when result is empty; returns "Knowledge service not available." when query_service is None
- [ ] list_entities: already implemented by #55 (no changes needed unless #55 review requires fixes)
- [ ] list_sources(ctx, scope: str or None = None) returns str: calls KnowledgeSourceStore.list_all(scope=scope) via asyncio.to_thread (sync method); formats as bullet list "- {name} ({source_type}): scope={scope}"; returns "No sources found." when empty
- [ ] get_stats: already implemented by #55 (no changes needed unless #55 review requires fixes)

### Resource
- [ ] knowledge://stats read-only resource returning same format as get_stats

### Package configuration
- [ ] pyproject.toml: add owlbear-knowledge dependency; dev dep: owlbear-knowledge = {path = "../knowledge", editable = true}

### Integration
- [ ] Register server in .vscode/mcp.json (create file if absent)
- [ ] Update SKILL.md in skills/knowledge-ops/ with MCP tool descriptions (currently documents PydanticAI runtime tools; update to reflect MCP server tools)

### Tests
- [ ] test_server.py (7 tests from #104) pass GREEN
- [ ] list_entities + get_stats tests from test_ingest_graph_tools.py pass GREEN
- [ ] Ingest-related tests from test_ingest_graph_tools.py pass GREEN (IngestPipeline/DocumentStore implemented by #55)
- [ ] Preceding test task #152 tests (list_sources, knowledge://stats, search v2 API) pass GREEN
- [ ] ruff clean on packages/mcp-knowledge/

### Excluded from scope (Phase B)
- ingest_document tool: already implemented by #55; no changes in this task
- IngestPipeline wiring in lifespan: already wired by #55; preserve as-is
- Existing tools.py has search_knowledge against wrong API (query_for_context); builder replaces with server.py search_knowledge implementation using v2 query() API; tools.py may be deleted or kept as empty module

## Architecture notes
- CRITICAL API correction: KnowledgeQueryService v2 has async query() returning list[StructuredSearchResult], NOT sync query_for_context(). Existing server.py search_knowledge calls query_for_context which does not exist in v2. Builder must replace with v2 query() call.
- KnowledgeQueryService.query() is async but calls sync embed/search internally. In MCP tool context: await directly. GraphStore and KnowledgeSourceStore methods are sync: use asyncio.to_thread.
- KnowledgeSourceStore.list_all(scope) returns list[KnowledgeSource]. KnowledgeSource fields: id, name, source_type, config, scope, enabled, priority. No direct url field; format uses scope.
- server.py already exists from #55 with ingest_document, list_entities, get_stats, AppContext(query_service, graph_store, ingest_pipeline). Builder extends it — adds source_store to AppContext, adds list_sources tool, adds knowledge://stats resource, replaces search_knowledge with v2 API.
- #54 (blocked, API mismatch) scope subsumed by #16 Phase A with corrected API.

## Context
Depends on #2 (MCP SDK, archived), #15 (knowledge engine, archived), #152 (test task for Phase A remaining tools). #149 (GraphStore.get_counts) removed as dependency — already implemented. Research: docs/research/build-mcp-knowledge-server.md.

[[2026-03-29]] Sun 19:22

## Architecture Review
**Verdict:** REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| MCP server in packages/mcp-knowledge/ | Correct location, follows mcp-kanban | Keep |
| Tool: knowledge_search | Wrong API name, no interface spec | Rewritten: search_knowledge with v2 query() API |
| Tool: knowledge_ingest | Blocked on #33 | Excluded, deferred to #150 |
| Tool: knowledge_list_sources | Missing from sub-tasks | Added with precise interface |
| Resource: knowledge://stats | Missing from sub-tasks | Added with format spec |
| Config for KB location | Vague | Rewritten: OWLBEAR_KB_PATH env var |
| Imports from owlbear_knowledge | Correct dependency direction | Keep |
| Register in mcp.json | .vscode/mcp.json doesn't exist yet | Keep, note create-if-absent |
| SKILL.md | Not in any sub-task | Keep |

### Architecture Notes
API mismatch (critical): v2 KnowledgeQueryService has async query() returning list[StructuredSearchResult], not sync query_for_context(). Existing tools.py and test_search_knowledge.py (#72) against wrong API. #54 blocked for same reason. #152 test task corrects this.

Module layering: mcp-knowledge depends on owlbear-knowledge. Correct direction. No upward imports.

Pattern: Follow mcp-kanban server.py exactly. Everything in server.py.

Overlap: #55 (in-progress) creates server.py with graph tools. #54 (blocked) covers search. Builder checks for existing server.py. Planner coordinates.

### Changes Made
- Rewrote AC to Phase A scope with 20+ precise verifiable items
- Excluded ingest (deferred to #150)
- Corrected API: query_for_context to v2 async query()
- Added depends_on: #149 (get_counts), #152 (test task)
- Created #152: Test task for list_sources, knowledge://stats, search v2 API
- Specified xfail strategy for blocked ingest tests

### Dependencies
- Verified: #2 (MCP SDK) archived
- Verified: #15 (knowledge engine) archived
- Added: #149 (GraphStore.get_counts) at ideation
- Added: #152 (TDD RED test task) at backlog
- Noted: #55 (in-progress) potential conflict on server.py
- Noted: #54 (blocked) scope subsumed by #16 Phase A

[[2026-03-30]] Mon 08:02
## Architecture Review (cycle 2)
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| server.py extend from #55 | Correct: server.py exists, builder extends | Clarified in objective |
| AppContext with source_store + ingest_pipeline | Previously missing ingest_pipeline (from #55) | Added ingest_pipeline field |
| app_lifespan preserves #55 wiring | Previously didn't mention #55's IngestPipeline | Added preservation note |
| search_knowledge v2 query() | Correct: awaits async query(), formats StructuredSearchResult | Kept, added NOTE about replacing query_for_context |
| list_entities from #55 | Already implemented by #55 | Marked as no-change |
| list_sources format {url} | KnowledgeSource has no url field | Fixed to scope={scope} |
| get_stats from #55 | Already implemented by #55 | Marked as no-change |
| knowledge://stats resource | Correct interface | Kept |
| pyproject.toml dep | Missing owlbear-knowledge | Kept |
| .vscode/mcp.json | File doesn't exist yet | Kept |
| SKILL.md update | Exists but documents v1 PydanticAI tools | Clarified: update existing file |
| xfail ingest tests | #55 implemented IngestPipeline/DocumentStore | Removed xfail, tests should pass GREEN |
| #149 dependency | get_counts already implemented (9 tests passing) | Removed from depends_on |
| #152 test task | Was blocked with empty body | Populated with 17 verifiable AC items, unblocked to backlog |

### Architecture Notes
server.py already exists from #55 with ingest_document, list_entities, get_stats, AppContext(query_service, graph_store, ingest_pipeline). Phase A remaining work is surgical: (1) replace search_knowledge query_for_context call with v2 async query(), (2) add list_sources tool, (3) add knowledge://stats resource, (4) add KnowledgeSourceStore to AppContext and lifespan, (5) fix pyproject.toml deps, (6) register in mcp.json, (7) update SKILL.md.

Module layering: mcp-knowledge depends on owlbear-knowledge. Correct direction. No upward imports.

KnowledgeSourceStore.list_all(scope) returns list[KnowledgeSource]. Model has name, source_type, scope fields (no url). Format corrected accordingly.

query_for_context() does not exist in v2 query_service.py. Current server.py would fail at runtime. Migration to v2 query() API is mandatory.

### Changes Made (this cycle)
- Objective: clarified extends #55, not creates from scratch
- AppContext: added ingest_pipeline (IngestPipeline | None) field, preserved from #55
- app_lifespan: added note to preserve #55's IngestPipeline wiring
- list_entities/get_stats: marked as already implemented by #55
- list_sources format: fixed {url} to scope={scope}
- SKILL.md: clarified update existing file (not create new)
- Tests: removed xfail for ingest (implemented by #55)
- Removed #149 from depends_on (redundant, get_counts exists with 9 passing tests)
- Populated #152 with 17 concrete AC items covering search v2, list_sources, knowledge://stats
- Unblocked #152 to backlog

### Dependencies
- Verified: #2 (MCP SDK) archived
- Verified: #15 (knowledge engine) archived
- Removed: #149 (GraphStore.get_counts) redundant, already implemented
- Fixed: #152 (TDD RED test task) populated with AC, unblocked to backlog
- Noted: #55 server.py is the base that #16 extends
