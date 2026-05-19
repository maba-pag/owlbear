---
id: 776
title: Add graph community detection (Leiden algorithm) to knowledge graph
status: archived
priority: nice-to-have
created: 2026-03-13T11:19:56.4549618+01:00
updated: 2026-03-22T19:17:51.819598+01:00
started: 2026-03-13T12:28:38.7808263+01:00
completed: 2026-03-22T19:17:51.819598+01:00
tags:
    - knowledge-graph
    - agent
    - enrichment
blocked: true
block_reason: 'Duplicate/YAGNI: archived #274 and docs/research/community-detection.md already reject Leiden community detection on scale, GPL-license, and query-fit grounds; current graph retrieval already uses BFS expansion.'
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

[[2026-03-21]] Sat 04:15

## Architecture Review

**Verdict:** BLOCK

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Implement community detection on GraphStore entities using python-igraph or leidenalg | Reject. Duplicate of archived #274; docs/research/community-detection.md records scale mismatch and GPL-license blockers for the named libraries. pyproject.toml is MIT-licensed and currently carries no graph-clustering dependency footprint. | Block |
| Generate per-community summaries via PydanticAI agent | Reject. Adds a new LLM summarization pipeline for global sensemaking, but current knowledge queries already favor targeted graph expansion over global summaries. | Block |
| Expose communities as retrieval context for RAG queries | Reject. src/owlbear/memory/knowledge/retrieval.py already uses GraphStore.get_neighbors() from src/owlbear/memory/knowledge/graph.py for low-complexity BFS expansion, and tests cover that path. | Block |
| Tests for detection + summary generation with mocked LLM | Incomplete TDD contract. No preceding RED test task exists on the board, and the underlying feature is rejected on architecture grounds. | Block |

### Architecture Notes

- Task body already marks #776 as a duplicate of archived #274 and recommends archiving it as YAGNI; advancing it would ignore the task's own research.
- Current graph architecture is intentionally lightweight:
  - GraphStore is a thin SQLite data-access layer in src/owlbear/memory/knowledge/graph.py.
  - GraphAugmentedRetriever in src/owlbear/memory/knowledge/retrieval.py expands seed entities through BFS neighbors instead of clustering.
  - GraphEnricher in src/owlbear/memory/knowledge/enrichment.py schedules background graph jobs without adding heavyweight graph-analysis dependencies.
- Existing tests already reinforce the lighter retrieval path: tests/test_graph_store_neighbors.py, tests/test_graph_augmented_retrieval.py, and tests/test_knowledge_query_service_expansion.py.
- The proposal also bundles three responsibilities into one card: clustering algorithm, LLM summarization, and retrieval-surface changes. Even if reopened later, it would require split RED/GREEN tasks rather than a single implementation card.
- TDD compliance fails: board search found no RED predecessor for community detection.
- Dependency fit fails: archived #258 already led to the graph-augmented retrieval path for the specific cross-reference use case this task is trying to address.

### Changes Made

- Claimed #776 as architect.
- Appended this architecture review.
- Blocking the task and moving it back to ideation to prevent duplicate builder dispatch.

### Dependencies

- Verified: #274 is archived and carries the original community-detection scope.
- Verified: docs/research/community-detection.md recommends do not build at current scale.
- Verified: #258 is archived and its follow-up retrieval work established the lower-complexity query path.
- Missing by design: no RED test task exists because this should not enter implementation flow.
