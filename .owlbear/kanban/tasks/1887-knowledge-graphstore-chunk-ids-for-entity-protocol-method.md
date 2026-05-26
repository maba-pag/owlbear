---
id: 1887
title: 'Knowledge: GraphStore — chunk_ids_for_entity protocol method'
status: backlog
priority: needed
created: 2026-05-27T00:36:20.507539+02:00
updated: 2026-05-27T00:43:37.814674+02:00
tags:
  - knowledge
  - layer-1
parent:
depends_on:
  - 1874
blocked: false
block_reason:
claimed_at: 2026-05-27T00:43:37.814674+02:00
archival_reason:
archival_refs: []
---
## Objective

Add a `chunk_ids_for_entity(entity_id: str) -> tuple[str, ...]` method to the GraphStore protocol and implement it in the SQLite store. This unblocks QueryFacade.lookup_entity (task #1880) which needs entity→chunk reverse lookup for the `related_chunks` field.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/graph.py`
- Implementation: `serve/knowledge/src/owlbear_knowledge/stores/graph.py`
- The `graph_evidence` table already has `entity_id` indexed (`idx_graph_evidence_entity_id`)
- SQL: `SELECT DISTINCT chunk_id FROM graph_evidence WHERE entity_id = ?`

## Implementation Notes

- Add protocol method with guarantees: returns distinct chunk_ids where evidence claims reference the entity_id; returns empty tuple for unknown entity_id; never raises.
- Implement in SQLite store: single query against indexed column.
- Trivial scope: ~5 LOC protocol addition, ~10 LOC implementation.

[[2026-05-27T00:43:08+02:00]]
## Research
- Research doc: .owlbear/research/1887-chunk-ids-for-entity.md
- Sources: 4 studied, 2 high-relevance (protocol file, SQLite impl)
- Recommendation: proceed as specified — add `chunk_ids_for_entity(entity_id: str) -> tuple[str, ...]` to protocol + implement via single indexed query (confidence: 0.90)
- Tier: T1 (autonomous) — symmetric to existing `claims_for_chunk`, uses already-indexed column
- Challenge: SKIP — trivial addition validated by prior #1880 research
- No follow-up tasks needed (this IS the follow-up from #1880)
