---
id: 776
title: Add graph community detection (Leiden algorithm) to knowledge graph
status: backlog
priority: nice-to-have
created: 2026-03-13T11:19:56.4549618+01:00
updated: 2026-03-13T12:30:47.1634104+01:00
started: 2026-03-13T12:28:38.7808263+01:00
tags:
    - knowledge-graph
    - agent
    - enrichment
claimed_by: researcher
claimed_at: 2026-03-13T12:30:47.1634104+01:00
class: standard
---

## Context

Research task #262 (knowledge-pipeline.md S4) recommended applying GraphRAG community detection to the entity graph. This was never created as a follow-up task.

## Acceptance Criteria

- [ ] Implement community detection on GraphStore entities using python-igraph or leidenalg
- [ ] Generate per-community summaries via PydanticAI agent
- [ ] Expose communities as retrieval context for RAG queries
- [ ] Tests for detection + summary generation with mocked LLM

## References

- docs/research/knowledge-pipeline.md S4
- GraphRAG paper (arxiv.org/abs/2404.16130)
- Existing enrichment.py pattern for background graph jobs

[[2026-03-13]] Fri 12:30

## Research

Duplicate of archived #274. Full research already exists at docs/research/community-detection.md (.85 confidence YAGNI).

**Key findings (from #274 research):**

- Scale mismatch: OwlBear's graph (500-2K entities) is 1-2 orders of magnitude below where community detection produces meaningful structure
- License blocker: leidenalg (GPL-3) and igraph (GPL-2) incompatible with MIT license
- Wrong query type: community summaries serve global sensemaking; OwlBear agents ask specific cross-reference queries
- 1-hop BFS (already implemented) covers 90%+ of retrieval use cases

**Recommendation:** Archive as YAGNI duplicate of #274. No follow-up tasks needed  the one lightweight alternative (entity-type clustering) was already created by the #274 research.
