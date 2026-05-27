---
id: 1905
title: 'P1-01: Delete stale task-scoped knowledge test files (1888, 1881, 1895)'
status: backlog
priority: needed
created: 2026-05-28T00:34:20.691200+02:00
updated: 2026-05-28T00:34:26.188108+02:00
tags:
  - knowledge
  - cleanup
  - test
parent:
depends_on:
  - 1900
ac:
  - tests/test_mcp_knowledge_lifespan_1888.py deleted from workspace
  - tests/test_mcp_knowledge_read_tools_1881.py deleted from workspace
  - tests/test_knowledge_tool_rename_1895.py deleted from workspace
  - pytest tests/ -k 'knowledge or enrichment or search_provenance or 
    ingest_document or get_next_batch' runs without --ignore flags for the 
    deleted files and passes (0 failures, 0 errors)
proof_bundle: existing
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Delete three task-scoped test files that assert legacy symbols removed by #1900. Their AC is fully covered by `tests/test_mcp_knowledge_legacy_removal_1900.py` and the durable v2-era test suites.

## Supersession Evidence
- `test_mcp_knowledge_lifespan_1888.py` (~31 tests): constructs AppContext with `query_service`, `graph_store`, `ingest_pipeline` fields removed by #1900 AC1. Lifespan wiring now covered by #1900 AC3/AC5 tests.
- `test_mcp_knowledge_read_tools_1881.py` (~67 tests): imports `init_db`, patches `BgeM3EmbeddingProvider`, constructs legacy context objects. Read-tool wiring now validated by v2-era tool tests.
- `test_knowledge_tool_rename_1895.py` (~12 tests): asserts `_legacy_graph_stats` exists via `hasattr()`/`callable()` — that function was deleted by #1900 AC4. The rename verification (AC1, AC3, AC4) is now inherent in the codebase state.

## Scope
- In-scope: delete the three files listed above
- Out-of-scope: updating durable module-level tests (separate tasks), modifying test_server.py (separate task)

Existing proof scope: tests/test_mcp_knowledge_legacy_removal_1900.py, pytest knowledge selector without --ignore flags