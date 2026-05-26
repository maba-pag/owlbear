---
id: 1876
title: 'Knowledge: EnrichmentStore — extractions & purge'
status: research
priority: needed
created: 2026-05-25T19:04:07.626934+02:00
updated: 2026-05-26T00:40:35.899411+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on:
  - 1875
  - 1873
ac:
  - submit_extractions(chunk_id, entities, relations) resolves local_ref strings
    to entity IDs via Graph.upsert_entity; transitions chunk to COMPLETED
  - Relations reference entities by local_ref; resolution maps local_ref to 
    entity_id from same submission
  - suggest_intra_doc_edges(document_id) returns SuggestedEdge tuples for 
    entities appearing in multiple chunks of same document
  - purge_source(source_id) removes all enrichment state for that source; 
    returns EnrichmentPurgeResult
  - Submit raises LookupError if chunk_id is not in IN_PROGRESS state
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Implement extraction submission with local_ref entity cross-referencing, intra-document edge suggestion, and source purge. Completes the EnrichmentStore protocol.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/enrichment.py`
- Design decisions: CP20 (local_ref cross-referencing), D52/D64 (submit_extractions idempotency + non-guarantees)
- Depends on: EnrichmentStore queue (task #1875) for tables; GraphStore entities (task #1873) for upsert_entity
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/enrichment.py` (extends same module)

## Implementation Notes

- submit_extractions is the bridge between Enrichment and Graph: it calls Graph.upsert_entity for each extracted entity
- local_ref: agent assigns temporary names to entities within a batch; resolution maps these to stable entity IDs after upsert
- Relations reference source/target entities by local_ref; resolved to actual IDs before calling Graph.upsert_edge
- Steps 1-3 of submit_extractions are idempotent; step 4 (state transition) only on success (D52)
- suggest_intra_doc_edges: heuristic for entities co-occurring across chunks of same document
- purge_source: removes queue entries + batch records for source (used in delete cascade)