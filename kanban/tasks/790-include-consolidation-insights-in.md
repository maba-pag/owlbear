---
id: 790
title: Include consolidation insights in KnowledgeQueryService context injection
status: backlog
priority: nice-to-have
created: 2026-03-13T20:17:27.3782043+01:00
updated: 2026-03-13T20:17:27.3782043+01:00
tags:
    - scope:core
    - memory
    - knowledge
class: standard
---

## Goal
Extend KnowledgeQueryService.query_for_context() to include recent consolidation insights in the injected context.

## AC
- [ ] query_for_context() queries consolidations table (ORDER BY created_at DESC) for recent insights
- [ ] Insight text appended after RAG results within max_tokens budget
- [ ] When no insights exist, behavior is unchanged (no regression)
- [ ] When consolidation_enabled is False, skip insight query (zero cost path)
- [ ] Tests verify insights appear in formatted context output
- [ ] Tests verify token budget is respected when including insights

## Pattern references
- src/owlbear/memory/knowledge/query_service.py (existing query pipeline)
- docs/research/always-on-memory-integration.md section 5d

## Dependencies
- ConsolidationService (#723)
