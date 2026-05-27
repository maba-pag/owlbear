---
id: 1899
title: 'Knowledge: Migrate consolidation logic into EnrichmentStore (Phase B1)'
status: research
priority: needed
created: 2026-05-27T17:56:11.886991+02:00
updated: 2026-05-27T18:01:50.284771+02:00
tags:
  - knowledge
  - layer-4
  - cleanup
parent:
depends_on: []
ac:
  - EnrichmentStore has get_consolidation_candidates(), 
    count_consolidation_candidates(), submit_consolidation() methods
  - reviewed_pairs table created by EnrichmentStore.ensure_tables()
  - _consolidation.py deleted from mcp-knowledge package
  - All existing MCP knowledge tests pass
blocked: false
block_reason:
claimed_at: 2026-05-27T18:01:50.284771+02:00
archival_reason:
archival_refs: []
---
## Objective
Move all `_consolidation.py` logic from mcp-knowledge into the EnrichmentStore in the knowledge package.

## Changes required
- Add `reviewed_pairs` table DDL to `EnrichmentStore.ensure_tables()`
- Move helper functions (`_stable_edge_id`, `_extract_relation`, `_validate_enrichment_edge_payload`) from mcp-knowledge `_helpers.py` into knowledge package (enrichment internals or shared utils)
- Implement new public methods on EnrichmentStore:
  - `get_consolidation_candidates(limit) → list[tuple]`
  - `count_consolidation_candidates() → int`
  - `submit_consolidation(candidate_id, edges, now_iso) → None`
- Move private helpers: `_encode_candidate_id`, `_decode_candidate_id`, `_resolve_candidate_identity`, `_validate_active_candidate_sources`, `_candidate_entity_ids`, `_resolve_phase2_edge_endpoints`, `_load_phase2_edge_provenance`
- Update server.py to call `enrichment_store.get_consolidation_candidates()`, `enrichment_store.submit_consolidation()`, `enrichment_store.count_consolidation_candidates()` instead of `_consolidation.*`
- Delete `_consolidation.py`

## Verification
- EnrichmentStore tests cover consolidation candidate querying
- EnrichmentStore tests cover phase-2 edge persistence
- `get_consolidation_candidates` MCP tool works via new path
- `store_enrichment` phase-2 branch works via new path
- `get_stats` consolidation count works via new path
- No imports from `._consolidation` remain

## Research
See .owlbear/research/mcp-knowledge-v2-migration.md §3.3