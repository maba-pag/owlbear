---
id: 423
title: Test KnowledgeQueryService
status: archived
priority: needed
created: 2026-03-01T22:19:06.4532396+01:00
updated: 2026-03-02T09:15:15.645744+01:00
started: 2026-03-01T22:19:11.5293388+01:00
completed: 2026-03-02T09:15:15.645744+01:00
tags:
    - phase-13
    - knowledge-graph
    - test
class: standard
---

TDD test task for #406. File: tests/test_knowledge_query_service.py. AC: - query_for_context(prompt) embeds prompt and returns formatted knowledge context string - Results filtered by similarity threshold 0.3 (below-threshold results excluded) - Token budget respected: output never exceeds max_tokens words (len(text.split()) heuristic) - Results sorted by similarity descending; lowest-scored dropped first when over budget - Returns None when vector_store has no results - Returns None when all results below similarity threshold - Scopes parameter passed through to search_similar - Resolves document content via graph_store.get_document for each result - Format: 'Relevant knowledge:\n\n- {title}: {snippet}...' - Graceful on exceptions: logs warning, returns None
