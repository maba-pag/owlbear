---
id: 55
title: Add ingest and graph tools to mcp-knowledge server
status: todo
priority: important
created: 2026-03-26T19:12:49.2923419+01:00
updated: 2026-03-26T21:26:09.2106254+01:00
tags:
    - phase-2
    - scope:mcp
    - scope:knowledge
depends_on:
    - 77
class: standard
---

## Objective
Extend mcp-knowledge with tools for document ingestion and graph exploration.

## Acceptance Criteria
- [ ] ingest_document tool registered via @mcp.tool() with readOnlyHint=False: params text (str, required), metadata (dict | None, default None); awaits IngestPipeline.ingest_text(text, metadata=metadata) directly (method is async); returns formatted string 'Ingested: {document_id}, {chunk_count} chunks, {entity_count} entities, {edge_count} edges (status: {status})'
- [ ] ingest_document catches exceptions from IngestPipeline and returns user-friendly error string (no tracebacks, no internal paths); note: IngestPipeline.ingest_text() catches most errors internally and returns IngestResult with status='failed', but the tool must also guard against unexpected exceptions
- [ ] list_entities tool registered via @mcp.tool() with readOnlyHint=True: params entity_type (str | None, default None), offset (int, default 0), limit (int, default 50); calls GraphStore.list_entities(entity_type=EntityType(entity_type)) via asyncio.to_thread() when entity_type is not None (else no filter); applies [offset:offset+limit] slice in Python; returns bulleted list prefixed with 'Entities ({start}-{end} of {total}):' header
- [ ] list_entities validates entity_type against EntityType enum values; returns error string listing valid types when an invalid string is passed
- [ ] list_entities returns 'No entities found.' when result set is empty (after filtering)
- [ ] get_stats tool registered via @mcp.tool() with readOnlyHint=True: no params; calls GraphStore.get_counts() via asyncio.to_thread(); returns formatted string 'Knowledge base: {n} documents, {n} entities, {n} edges'
- [ ] GraphStore.get_counts() method added to knowledge engine: returns tuple[int, int, int] (doc_count, entity_count, edge_count) using three SQL COUNT(*) queries on documents, entities, edges tables (O(1), no full-table loads)
- [ ] AppContext dataclass extended with ingest_pipeline: IngestPipeline field; app_lifespan creates DocumentStore, EntityExtractor (model from OWLBEAR_MODEL env var or default), TextChunker, and IngestPipeline; assigns to AppContext.ingest_pipeline
- [ ] All tool descriptions are verb-first, concise, LLM-friendly (e.g. 'Ingest a text document into the knowledge base.', 'List entities in the knowledge graph.', 'Get knowledge base summary statistics.')
- [ ] All tests from preceding test task #77 pass GREEN

## Context
Depends on search_knowledge implementation (#54) which wires the real lifespan. See docs/research/ingest-graph-tools-mcp-knowledge.md for full findings.
Prior art: Qdrant MCP server has 2 tools, MCP Memory server has 8 tools. v1 KnowledgeToolset (v1/src/owlbear/tools/knowledge.py) has 3 tools.

### Implementation patterns to follow
- IngestPipeline.ingest_text(text, metadata, scope='global') is async (uses asyncio.gather internally) â€” await directly, no asyncio.to_thread()
- GraphStore.list_entities() and get_counts() are sync (sqlite3) â€” use asyncio.to_thread() per #54 pattern
- Entity formatting: '{name} ({entity_type}): {description}' per v1 pattern
- Error handling for ingest: try/except returning formatted error string, per v1 KnowledgeToolset._ingest_document pattern

[[2026-03-26]] Thu 21:26
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| # | Original AC | Assessment | Action |
|---|------------|------------|--------|
| 1 | ingest_document tool: accepts text + optional metadata, runs IngestPipeline | Vague: no param types, return format, or async/sync boundary specified | Rewritten with precise params, delegation call, return format |
| 2 | list_entities tool: returns entities filtered by type, with pagination | Vague: no pagination mechanism, param types, or output format | Rewritten with offset/limit params, EntityType validation, bulleted output format |
| 3 | get_stats tool: returns document count, entity count, edge count | Missing: which method? O(1) or O(n)? | Rewritten: requires get_counts() on GraphStore with SQL COUNT |
| 4 | Each tool has unit tests with mocked knowledge engine | Belongs in TDD test task, not impl task | Replaced with 'All tests from #77 pass GREEN' |
| 5 | Tool descriptions are clear and actionable for LLM consumption | Subjective, not mechanically verifiable | Rewritten: verb-first, concise, with examples |

### Architecture Notes
Research is thorough (.85). Three tools fit in one task (single domain: scope:mcp, single file: server.py). Pattern follows v1 KnowledgeToolset (v1/src/owlbear/tools/knowledge.py) and scaffold research pattern.

Key decisions:
- IngestPipeline.ingest_text() is async (uses asyncio.gather internally) so await directly, no asyncio.to_thread()
- GraphStore.list_entities() and get_counts() are sync (sqlite3) so use asyncio.to_thread() per #54 pattern
- Offset-based pagination with Python slicing (KISS, avoids modifying GraphStore.list_entities SQL)
- get_counts() uses SQL COUNT (O(1)) not len(list_*()) (O(n)) per research recommendation
- AppContext extended with ingest_pipeline field (natural extension of frozen dataclass pattern)
- EntityExtractor needs LLM model config in lifespan (OWLBEAR_MODEL env var)
- get_counts() addition to GraphStore is ancillary (not a domain violation per architecture-standards edge case rule)

Module layering: mcp-knowledge (MCP layer) depends on owlbear-knowledge (memory layer). No upward imports. Correct dependency direction.

### Failure Mode Map
| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|-------------|-----------|----------|-------------|
| ingest_document | Pipeline LLM/DB failure | Various | Yes: IngestPipeline returns status=failed | Tool returns summary with status=failed |
| ingest_document | Unexpected exception | Any | AC requires try/except | Tool returns error string |
| list_entities | Invalid entity_type string | ValueError | AC requires validation | Tool returns valid types list |
| list_entities | SQLite read error | sqlite3.Error | No (unlikely for local file) | MCP framework handles |
| get_stats | SQLite count error | sqlite3.Error | No (unlikely for local file) | MCP framework handles |

### Changes Made
- Rewrote AC from 5 vague items to 10 precise verifiable items
- Added depends_on #77 (TDD RED test task)
- Specified async/sync boundary for each tool (await vs asyncio.to_thread)
- Added EntityType validation AC for list_entities
- Added IngestPipeline lifespan wiring AC with model config
- Specified get_counts() implementation strategy (SQL COUNT)

### Dependencies
- Added: #77 (Test: Add ingest and graph tools) TDD RED phase runs first
- Transitive: #77 depends on #54 depends on #40 (scaffold)
- Verified: v1 IngestPipeline, GraphStore, EntityExtractor interfaces stable
