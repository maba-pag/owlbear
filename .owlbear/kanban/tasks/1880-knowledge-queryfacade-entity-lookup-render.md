---
id: 1880
title: 'Knowledge: QueryFacade — entity lookup & render'
status: research
priority: needed
created: 2026-05-25T19:05:09.183316+02:00
updated: 2026-05-25T19:05:09.183316+02:00
tags:
  - knowledge
  - layer-2
parent:
depends_on:
  - 1879
  - 1874
ac:
  - lookup_entity(EntityLookupRequest) validates XOR (entity_id OR entity_name, 
    not both) via model_validator
  - Resolves entity by ID (direct) or name (canonical lookup + optional 
    entity_type disambiguation)
  - Returns EntityLookupResult with entity record + neighbourhood (traversal 
    within expand_hops)
  - render_context(ContextRenderRequest) formats query/entity results as 
    LLM-ready text within max_chars budget
  - Render output respects max_chars; sets truncated=True when budget exceeded; 
    includes provenance when requested
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Entity-first query (find entity by id/name/type, expand neighbourhood) and context rendering for LLM consumption. Completes the QueryFacade protocol.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/query.py`
- Depends on: QueryFacade search (#1879) for base infrastructure; GraphStore (#1873, #1874) for entity operations
- Target file: `serve/knowledge/src/owlbear_knowledge/query_facade.py` (extends same module)

## Implementation Notes

- lookup_entity: resolve by entity_id (direct get_entity) or entity_name (find_entities with canonical lookup)
- When entity_name used without entity_type, and multiple entities match, selection strategy is implementation-defined
- Neighbourhood expansion: Graph.traverse from resolved entity, expand_hops → max_hops
- related_chunks: find chunks that provide evidence for the entity (via Graph.claims → chunk lookups)
- render_context: format QueryResult or EntityLookupResult into structured text for LLM prompt insertion
- Rendering respects max_chars budget; truncates with flag; includes source attribution when include_provenance=True