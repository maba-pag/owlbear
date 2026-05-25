---
id: 1874
title: 'Knowledge: GraphStore — evidence, aliases & traversal'
status: research
priority: needed
created: 2026-05-25T19:03:39.489495+02:00
updated: 2026-05-25T19:03:39.489495+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on:
  - 1873
ac:
  - record_evidence(EvidenceInput) validates XOR (entity_id for ENTITY, edge_id 
    for EDGE via model_validator); links chunk to entity/edge
  - claims_for_chunk(chunk_id) returns ChunkClaims — all entities and edges that
    chunk provides evidence for
  - invalidate_evidence_by_chunks(chunk_ids) marks evidence as invalidated; 
    returns EvidenceInvalidationResult with counts
  - add_alias(EntityAliasInput) stores alternate name for entity; aliases 
    searchable via find_entities
  - traverse(TraversalQuery) performs BFS from start_entity_id; respects 
    max_hops, direction, relation_types filter; returns TraversalResult
  - stats() returns GraphStats with entity_count, edge_count, evidence_count, 
    alias_count
  - 'Table DDL: graph_evidence, graph_aliases; ensure_tables idempotent'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Implement evidence provenance tracking (which chunks support which entities/edges), alias management, and BFS traversal with depth limiting. Completes the GraphStore protocol.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/graph.py`
- Design decisions: CP18 (aliases for non-canonical names), D61 (TraversalDirection, AdjacencyQuery.direction)
- Depends on: GraphStore entities & edges (task #1873) for base tables
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/graph.py` (extends same module)

## Implementation Notes

- Evidence: links a chunk_id to either an entity_id OR edge_id (XOR enforced by EvidenceInput model_validator)
- Invalidation: when chunks are deleted, their evidence is marked invalidated (not deleted — preserves history)
- Aliases: alternate names for entities; stored in graph_aliases table; find_entities searches aliases too
- Traverse: BFS from start entity; respects max_hops (= depth), direction, relation_types filter
- TraversalResult includes visited entities + edges + path information