---
id: 409
title: Wire KnowledgeQueryService in bootstrap
status: archived
priority: important
created: 2026-03-01T20:19:10.9423785+01:00
updated: 2026-03-02T09:15:07.8441287+01:00
started: 2026-03-01T20:23:56.6802306+01:00
completed: 2026-03-02T09:15:07.8441287+01:00
tags:
    - phase-13
    - daemon
    - knowledge-graph
depends_on:
    - 407
    - 408
    - 426
class: standard
---

From #305 context-aware-knowledge-injection.md. Wire KnowledgeQueryService in src/owlbear/bootstrap.py (~15 LOC). AC: - In _build_knowledge_toolset(): after creating vector_store, graph_store, embedding_provider, also create KnowledgeQueryService(vector_store, graph_store, embedding_provider, scopes=...) - Change _build_knowledge_toolset return to include service: return tuple[AbstractToolset, KnowledgeQueryService] | None, or use a small dataclass - In build_toolsets() or bootstrap(): extract KnowledgeQueryService from the knowledge build result - Pass knowledge_service to OwlBearAgent constructor (new kwarg from #408) - Use settings.knowledge_context_tokens as the default max_tokens (pass to service or let caller use it) - When knowledge subsystem unavailable: knowledge_service=None passed to agent (existing graceful fallback) - project_scope flows to KnowledgeQueryService scopes same way it flows to KnowledgeToolset - Depends on #406, #407, #408, test task #426
