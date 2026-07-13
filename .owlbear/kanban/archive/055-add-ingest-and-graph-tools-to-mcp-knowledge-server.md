---
id: 55
title: Add ingest and graph tools to mcp-knowledge server
status: archived
priority: medium
created: 2026-03-26 19:12:49.292342+01:00
updated: 2026-03-30 14:34:46.457312+02:00
started: 2026-03-30 14:34:39.361031+02:00
completed: 2026-03-30 14:34:39.361031+02:00
tags:
- phase-2
- scope:mcp
- scope:knowledge
depends_on:
- 77
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-29]] Sun 15:17
## Test-Writer Notes
- Test files:
  - packages/mcp-knowledge/tests/test_ingest_graph_tools.py (MCP tool contract tests)
  - packages/knowledge/tests/test_graph_store_counts.py (GraphStore.get_counts unit tests)
- Classes:
  - TestFromAC_IngestDocument (AC1-AC2, 9 tests)
  - TestFromAC_ListEntities (AC3-AC5, 11 tests)
  - TestFromAC_GetStats (AC6, 5 tests)
  - TestFromAC_AppContextExtension (AC8, 4 tests)
  - TestFromAC_ToolDescriptions (AC9, 3 tests)
  - TestFromAC_GraphStoreGetCounts (AC7, 9 tests)
- Tests per category: happy 15, edge 7, error 7, boundary 4
- Total: 41 tests, all FAIL
  - test_ingest_graph_tools.py: 32 tests, collection ERROR (ImportError - server.py not yet created)
  - test_graph_store_counts.py: 9 tests, AttributeError (get_counts not yet on GraphStore)
- ruff: clean (both files)
- AC coverage:
  - AC1 ingest_document format and delegation: 7 tests in TestFromAC_IngestDocument
  - AC2 ingest_document error handling: 3 tests in TestFromAC_IngestDocument
  - AC3 list_entities filtering/pagination/to_thread: 9 tests in TestFromAC_ListEntities
  - AC4 list_entities EntityType validation: 2 tests in TestFromAC_ListEntities
  - AC5 list_entities empty result: 2 tests in TestFromAC_ListEntities
  - AC6 get_stats format and to_thread: 5 tests in TestFromAC_GetStats
  - AC7 GraphStore.get_counts tuple return: 9 tests in TestFromAC_GraphStoreGetCounts
  - AC8 AppContext ingest_pipeline extension: 4 tests in TestFromAC_AppContextExtension
  - AC9 verb-first tool descriptions: 3 tests in TestFromAC_ToolDescriptions
  - AC10 (all prior tests pass GREEN): builder gate - no RED tests written

[[2026-03-29]] Sun 15:18
## Test-Writer Notes
- Test files:
  - packages/mcp-knowledge/tests/test_ingest_graph_tools.py (MCP tool contract tests)
  - packages/knowledge/tests/test_graph_store_counts.py (GraphStore.get_counts unit tests)
- Classes:
  - TestFromAC_IngestDocument (AC1-AC2, 9 tests)
  - TestFromAC_ListEntities (AC3-AC5, 11 tests)
  - TestFromAC_GetStats (AC6, 5 tests)
  - TestFromAC_AppContextExtension (AC8, 4 tests)
  - TestFromAC_ToolDescriptions (AC9, 3 tests)
  - TestFromAC_GraphStoreGetCounts (AC7, 9 tests)
- Tests per category: happy 15, edge 7, error 7, boundary 4
- Total: 41 tests, all FAIL
  - test_ingest_graph_tools.py: 32 tests, collection ERROR (ImportError - server.py not yet created)
  - test_graph_store_counts.py: 9 tests, AttributeError (get_counts not yet on GraphStore)
- ruff: clean (both files)
- AC coverage:
  - AC1 ingest_document format and delegation: 7 tests in TestFromAC_IngestDocument
  - AC2 ingest_document error handling: 3 tests in TestFromAC_IngestDocument
  - AC3 list_entities filtering/pagination/to_thread: 9 tests in TestFromAC_ListEntities
  - AC4 list_entities EntityType validation: 2 tests in TestFromAC_ListEntities
  - AC5 list_entities empty result: 2 tests in TestFromAC_ListEntities
  - AC6 get_stats format and to_thread: 5 tests in TestFromAC_GetStats
  - AC7 GraphStore.get_counts tuple return: 9 tests in TestFromAC_GraphStoreGetCounts
  - AC8 AppContext ingest_pipeline extension: 4 tests in TestFromAC_AppContextExtension
  - AC9 verb-first tool descriptions: 3 tests in TestFromAC_ToolDescriptions
  - AC10 (all prior tests pass GREEN): builder gate - no RED tests written

[[2026-03-29]] Sun 19:44
## Builder Notes
- Files changed: packages/knowledge/src/owlbear_knowledge/graph_store.py (get_counts added), packages/knowledge/src/owlbear_knowledge/ingest.py (new: IngestResult, DocumentStore, IngestPipeline), packages/mcp-knowledge/src/owlbear_mcp_knowledge/server.py (new), packages/mcp-knowledge/src/owlbear_mcp_knowledge/__main__.py (new)
- Tests: 44 TestFromAC tests passed; ruff clean
- Coverage: mocks-only test strategy limits coverage on ingest.py (53%) and server.py (88%)

[[2026-03-30]] Mon 03:03
## Review Evidence
See docs/scratch/55-reviewer.md for full evidence.

FAIL: readOnlyHint omitted from ingest_document (AC1), list_entities (AC3), get_stats (AC6). No tests cover readOnlyHint for any tool. MCP 1.26.0 ToolAnnotations.readOnlyHint is available. Confidence: .82

[[2026-03-30]] Mon 03:28
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL - readOnlyHint missing for AC1, AC3, AC6
- Added: 3 failing tests in TestFromAC_ToolReadOnlyHints
- Preserved: 35 existing tests (all PASS)
- ruff: clean, commit: 122c6dc

[[2026-03-30]] Mon 06:40
## Test-Writer Notes (retry #2)\n- Situation: task stuck in todo after retry cycle; builder commit d2daab6 already fixed readOnlyHint\n- All 47 tests pass (TestFromAC_ToolReadOnlyHints 3/3 PASS + 44 prior tests PASS)\n- No new tests needed: implementation complete, advancing to in-progress for builder verification\n- ruff: clean

[[2026-03-30]] Mon 07:15
## Builder Notes (verification pass)
- Verification pass: all prior implementation committed in d2daab6 (readOnlyHint fix) and e307df5 (initial feat)
- Files changed: server.py, graph_store.py, ingest.py
- Tests: 47 passed (all TestFromAC classes)
- Coverage: server.py 88%, ingest.py 44% (mocks-only strategy per test-writer notes)
- Lint: ruff clean
- readOnlyHint: ingest_document=False, list_entities=True, get_stats=True

[[2026-03-30]] Mon 07:40
## Review Evidence
See docs/scratch/55-reviewer.md for full evidence.

FAIL: TestFromAC_ListEntities::test_entity_type_filter_passed_when_provided is LAX -- asserts to_thread called once but not that entity_type kwarg is forwarded. No compensating TestBuilderDiscovered test. Confidence: .87

[[2026-03-30]] Mon 10:15
## Builder Notes (verification pass #2)
- Retry reason: reviewer FAIL - test_entity_type_filter_passed_when_provided was LAX (only checked to_thread call count, not kwarg forwarding)
- Fix: added TestBuilderDiscovered::test_entity_type_kwarg_forwarded_as_enum_to_to_thread
- Verifies asyncio.to_thread is called with entity_type=EntityType("concept") kwarg when entity_type string is provided
- No source code changes needed - implementation was already correct
- Files changed: packages/mcp-knowledge/tests/test_ingest_graph_tools.py only
- Tests: 39 passed (38 existing + 1 new TestBuilderDiscovered)
- Lint: ruff clean on changed file
- Commit: 75bfa8a

[[2026-03-30]] Mon 13:21
## Review Evidence
See docs/scratch/55-reviewer.md for full evidence (previous cycles).

**Retry #3 Review (2026-03-30)**
- pytest: 48 passed (39 test_ingest_graph_tools.py + 9 test_graph_store_counts.py), 0 failed
- ruff: All checks passed

**Test-Writer AC Coverage**
All 9 AC lines COVERED. TestBuilderDiscovered::test_entity_type_kwarg_forwarded_as_enum_to_to_thread compensates for LAX test_entity_type_filter_passed_when_provided.

**Security**: Clean. No hardcoded credentials, enum-validated entity_type, no SQL injection vectors.

**TestFromAC Integrity**: All original TestFromAC tests preserved. Builder only added TestBuilderDiscovered class.

**Test Quality**: Assertion specificity ADEQUATE, error paths STRONG, descriptive names STRONG.

**AC Compliance**: All 10 AC lines PASS including readOnlyHint for all 3 tools, entity_type enum kwarg forwarding, real SQLite COUNT verification.

**Pass 2 (Informational)**: Unreachable knowledge_stats() function in server.py (same logic as get_stats but no @mcp.tool decorator) â€” dead code, not a defect.

**Verdict: PASS. Confidence: .92**

[[2026-03-30]] Mon 13:21
## Review Evidence (Retry #3, 2026-03-30)

pytest: 48 passed (39 test_ingest_graph_tools.py + 9 test_graph_store_counts.py), 0 failed. ruff: clean.

AC Coverage: All 9 AC lines COVERED. TestBuilderDiscovered::test_entity_type_kwarg_forwarded_as_enum_to_to_thread compensates for LAX test_entity_type_filter_passed_when_provided (checks entity_type kwarg == EntityType('concept')).

TestFromAC Integrity: All original TestFromAC tests preserved unchanged. Builder added only TestBuilderDiscovered.

Security: Clean. Enum-validated entity_type, no SQL injection, no hardcoded secrets, no traceback leakage.

Test Quality: Assertion specificity ADEQUATE, error paths STRONG, names STRONG.

AC Compliance: All 10 AC lines PASS including readOnlyHint for all 3 tools, entity_type enum kwarg forwarding, real SQLite COUNT verification, IngestPipeline lifespan wiring.

Informational: Unreachable knowledge_stats() in server.py (dead code, same logic as get_stats but no decorator). Not a defect.

Verdict: PASS. Confidence .92

[[2026-03-30]] Mon 14:05
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | mcp-knowledge described as 'MCP server exposing knowledge operations' - still accurate |
| 2 | Docstrings | Yes | Pass | server.py module + 5 tools have docstrings; graph_store.get_counts() documented; ingest.py IngestPipeline/IngestResult/ingest_text() documented |
| 3 | docs/sources/overview.md | Yes | Pass | Section for Task #55 present with 3 entries: Qdrant MCP, MCP Memory, FastMCP Tools |
| 4 | README.md | No | N/A | No CLI commands changed |
| 5 | Research doc | Yes | Pass | docs/research/ingest-graph-tools-mcp-knowledge.md exists and linked in task body |
| 6 | Scratch files | None | Pass | docs/scratch/55-reviewer.md absent; no scratch files remain |

### Files Updated
- None

### Scratch Files Cleaned
- None (already absent)
