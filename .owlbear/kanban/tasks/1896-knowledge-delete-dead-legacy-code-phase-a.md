---
id: 1896
title: 'Knowledge: Delete dead legacy code (Phase A)'
status: backlog
priority: needed
created: 2026-05-27T16:19:40.136779+02:00
updated: 2026-05-27T16:24:27.695759+02:00
tags:
  - knowledge
  - cleanup
  - layer-4
parent:
depends_on:
  - 1881
  - 1882
ac:
  - Listed files deleted from the repository
  - No remaining imports of deleted modules
  - All tests pass after deletion
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Delete confirmed dead code — files with zero runtime consumers.

## Files to delete
- `serve/mcp-knowledge/src/owlbear_mcp_knowledge/_enrichment.py` (no importers)
- `serve/knowledge/src/owlbear_knowledge/loader.py` (only legacy consumers)
- 9 legacy-only test files:
  - tests/test_manifest_loader_1578.py
  - tests/test_ingest_1656.py
  - tests/test_query_service.py
  - tests/test_browser_fetcher_wiring.py
  - tests/test_qdrant_source_identity.py
  - tests/test_enrichment_schema.py
  - tests/test_schema_bookmark_drop_1583.py
  - tests/test_schema_constraint_enforcement_1586.py
  - tests/test_enrichment_persistence_1557.py

## Verification
- `uv run python -c "import owlbear_knowledge"` passes
- `uv run python -c "import owlbear_mcp_knowledge"` passes
- Full test suite passes

## Research
See .owlbear/research/knowledge-legacy-deletion.md §3.4, §3.5

[[2026-05-27T16:24:27+02:00]]
## Research
Validation pass — existing research doc `.owlbear/research/knowledge-legacy-deletion.md` §3.4–3.5 confirmed current.

**Verified:**
- All 11 target files still exist
- `_enrichment.py` (mcp): zero importers
- `loader.py`: only imported by `test_manifest_loader_1578.py` (also in deletion list)
- 9 test files: self-referential comments only, no external consumers

**Tier:** T1 — autonomous dead-code deletion, no decisions needed.
**Confidence:** 0.92 — straightforward grep-verified deletions with no runtime impact.
