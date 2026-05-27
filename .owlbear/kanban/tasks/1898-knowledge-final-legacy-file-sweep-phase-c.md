---
id: 1898
title: 'Knowledge: Final legacy file sweep (Phase C)'
status: research
priority: needed
created: 2026-05-27T16:19:59.014229+02:00
updated: 2026-05-27T16:19:59.014229+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on:
  - 1897
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