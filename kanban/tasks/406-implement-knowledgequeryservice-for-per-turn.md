---
id: 406
title: Implement KnowledgeQueryService for per-turn context injection
status: archived
priority: needed
created: 2026-03-01T20:18:42.6218969+01:00
updated: 2026-03-02T09:15:00.8137725+01:00
started: 2026-03-01T20:23:53.1416656+01:00
completed: 2026-03-02T09:15:00.8137725+01:00
tags:
    - phase-13
    - knowledge-graph
    - agent
    - memory
depends_on:
    - 423
class: standard
---

From #305 context-aware-knowledge-injection.md. New service at src/owlbear/memory/knowledge/query_service.py (~60 LOC). AC: - Class: KnowledgeQueryService.__init__(self, vector_store: VectorStoreProtocol, graph_store: GraphStore, embedding_provider: EmbeddingProvider, *, scopes: list[str] | None = None) - Method: query_for_context(self, prompt: str, *, max_tokens: int = 2000, top_k: int = 5) -> str | None - Embeds prompt via embedding_provider.embed_hybrid([prompt])[0] (fallback to .embed() + HybridEmbedding wrapper) - Calls vector_store.search_similar(embedding, top_k=top_k, embedding_type='document', scopes=self._scopes) - Filters results with similarity score < 0.3 - Resolves doc IDs via graph_store.get_document(doc_id) for each result above threshold - Formats as 'Relevant knowledge:\n\n- {title}: {content_snippet}...' - Truncates to max_tokens using len(text.split()) word count heuristic - Results sorted by similarity descending; lowest-scored dropped first when over budget - Returns None when no results above threshold or vector_store empty - All exceptions caught, logged at WARNING, return None (graceful degradation) - Export from owlbear.memory.knowledge.__init__ - Depends on test task #423
