---
id: 255
title: 'Research: Intra-document graph builder'
status: archived
priority: needed
created: 2026-02-28T12:40:38.679783+01:00
updated: 2026-03-01T00:02:50.5416637+01:00
started: 2026-02-28T22:56:15.8192633+01:00
completed: 2026-03-01T00:02:50.5416637+01:00
tags:
    - phase-9
    - knowledge-graph
    - research
    - agent
class: standard
---

## Context
Currently entity extraction happens per-chunk — each chunk is processed in isolation. This misses relationships between entities in different chunks of the SAME document. An intra-document graph builder would:

1. After all chunks are extracted, collect all entities from all chunks of that document
2. Ask the LLM: 'given these entities from different parts of the document, what relationships exist?'
3. Create edges between entities that come from different chunks but the same document
4. Result: richer per-document knowledge graph with cross-chunk connections

This is a background enrichment job — runs after ingestion, low priority, non-blocking.

## Research Checklist
- [ ] Theoretical validity: Does post-hoc graph enrichment improve retrieval quality? By how much?
- [ ] Prior art: LlamaIndex KnowledgeGraphIndex, Neo4j GraphRAG, Microsoft GraphRAG, LangChain graph extractors
- [ ] Technical feasibility: LLM cost per document (how many entities to cross-reference?), token limits
- [ ] Architecture fit: New module or extend EntityExtractor? Background job scheduling?
- [ ] Implementation approach: Pairwise entity comparison vs document-summary-based extraction

## Key Design Questions
- How many entities per document on average? 10? 50? 200? What's the LLM cost of cross-referencing all pairs?
- Should we use entity descriptions as context or go back to chunk text?
- Batching strategy: all entities at once (fits in context?) or sliding window?
- Quality: how to avoid hallucinated edges? Confidence scoring?
- When to run: immediately after ingestion? Scheduled? On-demand?
- Incremental: when new chunks are added to existing document, only relate new entities?

## What This Enables
- Better intra-document navigation: 'this concept mentioned on page 3 is implemented by the pattern on page 12'
- Foundation for inter-document graph builder: richer per-document graphs mean more connection points
- Graph-augmented retrieval (#234) becomes more powerful with denser graphs

## Acceptance Criteria
- [ ] Research doc in docs/
- [ ] Follow-up implementation tasks created
- [ ] LLM cost analysis (tokens per document of various sizes)
- [ ] Quality assessment approach proposed
- [ ] Comparison with alternative approaches (embedding-based edge detection, etc.)
