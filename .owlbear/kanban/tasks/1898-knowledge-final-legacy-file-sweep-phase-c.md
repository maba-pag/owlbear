---
id: 1898
title: 'Knowledge: Final legacy file sweep (Phase C)'
status: research
priority: needed
created: 2026-05-27T16:19:59.014229+02:00
updated: 2026-05-27T19:34:26.096054+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1897
  - 1900
ac:
  - All 12 legacy files deleted from serve/knowledge/
  - __init__.py exports only from protocols/ and stores/
  - No remaining imports of deleted modules in the codebase
  - All tests pass; old table DDL removed
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Delete all remaining legacy implementation files now that no code references them.

## Files to delete from serve/knowledge/src/owlbear_knowledge/
- source_store.py, document_store.py, graph_store.py, graph_builder.py
- status_store.py, ingest.py, query_service.py, retrieval.py
- refresh.py, protocol.py, models.py, schema.py

## Additional work
- Rewrite __init__.py to export from protocols/ and stores/ only
- Fix stores/content.py: move compute_content_hash locally (currently imports from status_store)
- Remove test_search_provenance.py if search_knowledge no longer has legacy path
- grep entire codebase for stale references

## Verification
- `uv run python -c "import owlbear_knowledge"` passes with new __init__.py
- No imports of deleted modules anywhere in workspace
- Full test suite passes
- Only new store-owned schema remains (no monolithic DDL)

## Research
See .owlbear/research/knowledge-legacy-deletion.md §3.1, §3.2

[[2026-05-27T18:18:11+02:00]]
## Research

Key findings (see .owlbear/research/knowledge-phase-c-sweep.md):
- Dependency chain broken: #1897 archived as decomposed but sub-tasks #1899/#1900 NOT done. Fixed by adding #1900 dep.
- 5 non-legacy files import from deletion targets (embeddings.py, qdrant.py, extractor.py, stores/content.py, mcp _helpers.py). Types must migrate before deletion.
- Migration plan: compute_content_hash → stores/content.py, HybridEmbedding → embeddings.py, StructuredExtractor/Entity/Edge → extractor.py.
- EntityType/RelationType conflict in _helpers.py must be resolved by Phase B2 or Phase C.
- Additional deletions identified: loader.py, test_search_provenance.py, README.md rewrite.
- Recommended sub-phasing: C1 (type migrations) then C2 (deletions).

Confidence: 0.85
No follow-up tasks created — scope already correctly defined; blocked on prerequisites.
