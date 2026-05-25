---
id: 1879
title: 'Knowledge: QueryFacade — search'
status: research
priority: needed
created: 2026-05-25T19:04:53.456937+02:00
updated: 2026-05-25T19:04:53.456937+02:00
tags:
  - knowledge
  - layer-2
parent:
depends_on:
  - 1872
  - 1874
ac:
  - search(QueryRequest) calls Content.search with query text + scope filter
  - 'When include_graph=True: expands results via Graph.traverse from entities mentioned
    in returned chunks'
  - graph_hops mapped directly to TraversalQuery.max_hops — no separate depth 
    concept (CP16)
  - Results include provenance (source_id, document_id, chunk_id, exact_text) 
    for each hit
  - Scope filters Content only; graph expansion is global (D53)
  - Returns QueryResult with scored search_results + graph_context + provenance
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective

Unified search combining content retrieval with graph expansion. Maps `graph_hops` to `TraversalQuery.max_hops` (CP16). Assembles provenance metadata linking results to sources.

## Context

- Protocol: `serve/knowledge/src/owlbear_knowledge/protocols/query.py`
- Design decisions: CP16 (graph_hops = facade hint), D53 (scope = Content filter only, graph global)
- Depends on: ContentStore search (#1872), GraphStore traversal (#1874)
- Target file: `serve/knowledge/src/owlbear_knowledge/query_facade.py`

## Implementation Notes

- QueryFacade receives ContentStore + GraphStore via constructor injection
- search flow: Content.search(text, scopes, source_ids) → extract entity mentions → Graph.traverse(entity_id, max_hops=graph_hops) → assemble QueryResult
- Provenance: for each search hit, resolve chunk → document → source chain; populate exact_text from chunk.text (not a separate column, R44)
- entity_types and relation_types on QueryRequest filter the graph expansion, not the content search
- Graph expansion strategy (seed selection from search results) is implementation-defined