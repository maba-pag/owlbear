---
id: 1892
title: 'Knowledge: MCP wire store_enrichment phase-1 to submit_extractions'
status: research
priority: needed
created: 2026-05-27T01:00:59.321864+02:00
updated: 2026-05-27T01:00:59.321864+02:00
tags:
  - knowledge
  - layer-3
parent:
depends_on:
  - 1888
ac:
  - Phase-1 path (chunk_id provided) calls EnrichmentStore.submit_extractions()
  - Input entity dicts validated/parsed into ExtractedEntity with local_ref, 
    name, entity_type, description, confidence
  - Input edge dicts validated/parsed into ExtractedRelation with source_ref, 
    target_ref, relation_type, weight
  - Phase-2 path (candidate_id provided) remains on _persist_phase2_enrichment 
    helper (unchanged)
  - LookupError from submit_extractions raised as ToolError
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Replace _persist_phase1_enrichment() in `store_enrichment` with EnrichmentStore.submit_extractions(). Parse input entity/edge dicts into ExtractedEntity and ExtractedRelation models. Keep phase-2 (candidate_id) path on old helper.

Research: see `.owlbear/research/mcp-knowledge-write-ops-wiring.md`