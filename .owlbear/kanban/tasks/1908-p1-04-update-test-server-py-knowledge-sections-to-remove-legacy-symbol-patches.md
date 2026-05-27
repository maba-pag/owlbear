---
id: 1908
title: 'P1-04: Update test_server.py knowledge sections to remove legacy symbol patches'
status: backlog
priority: needed
created: 2026-05-28T00:34:20.763020+02:00
updated: 2026-05-28T00:34:26.233594+02:00
tags:
  - knowledge
  - cleanup
  - test
parent:
depends_on:
  - 1900
ac:
  - test_server.py no longer patches init_db, GraphStore, 
    BgeM3EmbeddingProvider, KnowledgeQueryService, or GraphAugmentedRetriever in
    owlbear_mcp_knowledge.server
  - test_server.py no longer accesses ctx.query_service, ctx.ingest_pipeline, or
    ctx.structured_extractor (removed AppContext fields)
  - pytest tests/test_server.py passes (0 failures, 0 errors)
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Update the knowledge-related merged sections in `tests/test_server.py` that patch legacy symbols removed by #1900.

## Current State
Two merged knowledge sections patch removed symbols:
1. **Section from test_server_1170.py** (line ~1240): `mock_lifespan_deps` autouse fixture patches `init_db`, `GraphStore`, `QdrantVectorStore`, `BgeM3EmbeddingProvider`, `KnowledgeQueryService`, `GraphAugmentedRetriever`. `TestFromAC_LifespanNoCopilotAuth` accesses `ctx.query_service`, `ctx.ingest_pipeline`, `ctx.structured_extractor`.
2. **Section from test_server_1358.py** (line ~1450): `mock_lifespan_deps_1358` autouse fixture patches the same 6 legacy symbols.

## Direction
- Remove patches for symbols no longer in server.py (`init_db`, `GraphStore`, `BgeM3EmbeddingProvider`, `KnowledgeQueryService`, `GraphAugmentedRetriever`)
- Retain `QdrantVectorStore` patch (still present in v2 lifespan)
- Delete or rewrite tests that assert removed AppContext fields (query_service, ingest_pipeline, structured_extractor)
- Evaluate whether the remaining assertions (copilot_auth removal, API key branch removal, EntityExtractor/IntraDocGraphBuilder extractor=None) are still valid in the v2-only server — delete those superseded by #1900 AC1/AC6

## Scope
- In-scope: the two knowledge-related merged sections in `tests/test_server.py`
- Out-of-scope: the mcp-kanban section at the top of test_server.py, other test files