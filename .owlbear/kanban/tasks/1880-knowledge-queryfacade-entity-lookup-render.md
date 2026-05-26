---
id: 1880
title: 'Knowledge: QueryFacade — entity lookup & render'
status: backlog
priority: needed
created: 2026-05-25T19:05:09.183316+02:00
updated: 2026-05-27T00:36:40.808263+02:00
tags:
  - knowledge
  - layer-2
parent:
depends_on:
  - 1879
  - 1874
  - 1887
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

[[2026-05-27T00:36:34+02:00]]
## Research

Completed research for QueryFacade entity lookup & render.

**Key findings:**
- `lookup_entity`: straightforward composition of `get_entity`/`find_entities` + `traverse`, EXCEPT `related_chunks` requires a new `chunk_ids_for_entity` protocol method on GraphStore (created as #1887)
- `render_context`: structured markdown-like sections (Entity, Relationships, Sources) with char budget tracking; truncation sets flag, prioritises entity desc > neighbours > chunks
- Both methods are synchronous, matching protocol signatures
- XOR validation on request handled by model_validator (already in protocol)
- Error contract: LookupError for missing entities, ValueError for empty render request

**Trade-off matrix:** See `.owlbear/research/1880-queryfacade-entity-render.md` §3
**Confidence:** 0.85
**Tier:** T1 (autonomous) — composition of existing protocol modules + one trivial protocol addition
**Follow-ups:** #1887 (chunk_ids_for_entity prerequisite)

[[2026-05-27T00:36:40+02:00]]
## Research

Key findings: lookup_entity is composition of get_entity/find_entities + traverse; render_context uses structured markdown sections with char budget. Protocol gap identified: need `chunk_ids_for_entity` on GraphStore (created #1887 as prerequisite). Confidence: 0.85. Tier: T1.

Doc: .owlbear/research/1880-queryfacade-entity-render.md
Follow-up: #1887 (GraphStore chunk_ids_for_entity)
