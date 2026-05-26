---
id: 1874
title: 'Knowledge: GraphStore — evidence, aliases & traversal'
status: in-progress
priority: needed
created: 2026-05-25T19:03:39.489495+02:00
updated: 2026-05-26T01:59:51.708001+02:00
tags:
  - knowledge
  - layer-1
  - greenfield
parent:
depends_on:
  - 1873
ac:
  - add_evidence(EvidenceInput) links chunk to entity/edge; model_validator 
    enforces claim_type XOR; idempotent for same (chunk_id, claim_type, 
    target_id) identity — returns existing/updated EvidenceRecord
  - claims_for_chunk(chunk_id) returns ChunkClaims with entity_ids, edge_ids, 
    evidence_ids referencing that chunk; empty ChunkClaims for unknown chunk_id
  - 'invalidate_evidence_by_chunks(chunk_ids) hard-deletes matching evidence records;
    entities/edges with zero remaining evidence are orphaned and deleted (cascade:
    aliases of orphaned entities and edges referencing orphaned entities also deleted);
    returns EvidenceInvalidationResult with invalidated_evidence_ids, orphaned_entity_ids,
    orphaned_edge_ids; idempotent for absent chunk_ids'
  - add_alias(EntityAliasInput) stores canonicalized alternate name for entity; 
    find_entities resolves aliases transparently; raises LookupError for missing
    entity_id; raises ValueError if canonical alias is empty after 
    canonicalization or conflicts with different entity's canonical_name; 
    idempotent for same (entity_id, canonical_alias)
  - traverse(TraversalQuery) multi-hop traversal from query.entity_id; respects 
    max_hops, relation_types filter; total result size <= query.limit; no 
    duplicate entities or edges in result; raises LookupError if seed entity 
    does not exist
  - stats() returns GraphStats(entities, edges, evidence_claims, aliases) 
    reflecting current graph_* table counts
  - ensure_tables creates graph_evidence (indexes on chunk_id, entity_id, 
    edge_id) and graph_aliases (UNIQUE entity_id+canonical_alias, index on 
    canonical_alias); FK constraints reference graph_entities/graph_edges; 
    idempotent
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Implement evidence provenance tracking (which chunks support which entities/edges), alias management, and multi-hop traversal with depth limiting. Completes the GraphStore protocol.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/graph.py`
- Design decisions: CP18 (aliases for non-canonical names), D61 (TraversalDirection, AdjacencyQuery.direction)
- Depends on: GraphStore entities & edges (task #1873) for base tables
- Target file: `serve/knowledge/src/owlbear_knowledge/stores/graph.py` (extends same module)

## Implementation Notes

- Evidence: links a chunk_id to either an entity_id OR edge_id (XOR enforced by EvidenceInput model_validator)
- Invalidation: hard-delete per protocol guarantee ("All evidence records … are deleted"). Orphan cascade: entities/edges with zero remaining evidence are deleted along with their aliases and connected edges.
- Aliases: alternate names for entities; stored in graph_aliases table; find_entities searches aliases too (already wired in #1873 via `_has_aliases_table` guard)
- Traverse: multi-hop from seed entity; respects max_hops, relation_types filter, limit. Algorithm choice (BFS/DFS) is implementation detail per protocol.
- Orphan cascade order: collect affected IDs → delete evidence → identify zero-evidence entities/edges → delete aliases of orphaned entities → delete edges referencing orphaned entities → delete orphaned entities/edges → report all deleted IDs
- FK constraint note: graph_evidence and graph_aliases reference graph_entities/graph_edges. Builder must ensure cascade cleanup happens before entity/edge deletion to avoid FK violations (whether via code-level ordering or ON DELETE CASCADE).

## Research

Doc: .owlbear/research/1874-graphstore-evidence-aliases-traversal.md

Key findings: hard-delete for evidence (protocol authoritative), deterministic evidence IDs with upsert semantic, traversal reusing get_adjacent() with seed pre-validation, alias conflicts checked against graph_entities.canonical_name per protocol.

Proof bundle: behavioral

[[2026-05-26T01:37:32+02:00]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All 6 methods belong to GraphStore protocol; single module completing existing impl |
| Interface clarity | PASS | Protocol defines precise inputs/outputs/errors; AC now mirrors protocol contracts exactly |
| Dependency correctness | PASS | #1873 archived (done); no other deps needed |
| Module layering | PASS | Graph imports no other knowledge module internals; owns graph_* tables exclusively |
| TDD compliance | PASS | Flows through test-writer at todo |
| KISS/YAGNI | PASS | Research chose simplest approaches (COUNT-based orphan detection, get_adjacent reuse) |
| Premise challenge | PASS | Completes existing protocol with NotImplementedError stubs; clearly needed |
| Pattern consistency | PASS | Extends #1873 patterns (uuid5, sqlite Row, BEGIN IMMEDIATE transactions) |
| Security surface | PASS | Internal module, no external boundaries |
| Single domain | PASS | Knowledge domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| add_evidence with invalid XOR | claim_type mismatch | ValueError (model_validator) | Yes — Pydantic | Immediate user feedback |
| traverse with non-existent seed | Missing entity | LookupError | Yes — pre-validation | Clear error, no partial state |
| add_alias with missing entity | FK target absent | LookupError | Yes — explicit check | Clear error |
| add_alias canonical conflict | Alias name = other entity | ValueError | Yes — query check | Clear error |
| orphan cascade with FK deps | Delete order violation | IntegrityError (if misordered) | Addressed — AC specifies cascade order |
| invalidate with empty chunk_ids | No-op | None (idempotent) | Yes | No impact |

### Design Diverge
- Trigger: skipped — single valid approach (protocol-driven implementation extending existing #1873 patterns)

### Challenge Results
- Challenger: reconsider (confidence 0.56)
- Findings: (1) critical: FK cascade in orphan deletion unspecified; (2) moderate: contradictory body notes (soft-delete vs hard-delete); (3) moderate: AC over-constraining implementation (BFS/UUID5); (4) moderate: alias contract omissions
- Architect response: accepted all findings. AC rewritten to: remove BFS/UUID5 (impl details), specify orphan cascade explicitly (aliases + connected edges), add missing alias error behaviors, align field names with protocol. Body rewritten to remove contradictions.

### Proof-Bundle Validation
- Planner assignment: (none — null)
- Final bundle: behavioral
- Existing proof scope: N/A
- Test-writer: PROCEED

Rationale: 6 protocol methods with failure modes, cascading deletion logic, and integration behaviors warrant full TDD.

### Verdict: APPROVE
### Action Taken: Refined AC (7 lines) to match protocol signatures/semantics exactly, added orphan cascade specification, removed implementation-detail constraints (BFS/UUID5). Rewrote body to eliminate contradictions. Set proof_bundle=behavioral. Advanced to todo.

[[2026-05-26T01:59:51+02:00]]
## Test-Writer Notes
- Test file: tests/test_graph_store_1874.py
- Classes: TestFromAC_AddEvidence, TestFromAC_ClaimsForChunk, TestFromAC_InvalidateEvidenceByChunks, TestFromAC_AddAlias, TestFromAC_Traverse, TestFromAC_Stats, TestFromAC_EnsureTablesExtended
- Tests per category: happy 28, edge 11, error 7, boundary 4
- Total: 50 tests, all FAIL (NotImplementedError for new methods; AssertionError for ensure_tables table checks)
- ruff: clean

### AC Coverage
| AC | Tests | Coverage |
|----|-------|----------|
| AC1 add_evidence | 5 | entity claim, edge claim, idempotency, confidence boundaries |
| AC2 claims_for_chunk | 6 | entity_ids, edge_ids, evidence_ids, empty for unknown, mixed claims |
| AC3 invalidate_evidence_by_chunks | 10 | hard-delete, orphan entity/edge, cascade aliases+edges, no-orphan case, idempotent, empty tuple |
| AC4 add_alias | 7 | canonical form, find_entities resolution, idempotency, LookupError, ValueError (empty/conflict) |
| AC5 traverse | 11 | single/multi-hop, max_hops limit, relation_types filter, result size limit, no duplicates, LookupError, empty seed |
| AC6 stats | 6 | all-zero empty store, entity/edge/evidence/alias counts |
| AC7 ensure_tables | 5 | graph_evidence created, graph_aliases created, idempotent, chunk_id index, UNIQUE constraint |
