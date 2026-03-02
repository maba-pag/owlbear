---
id: 256
title: 'Research: Inter-document graph builder'
status: archived
priority: important
created: 2026-02-28T12:41:01.1162616+01:00
updated: 2026-03-02T09:14:14.6570268+01:00
started: 2026-03-01T19:55:10.4616375+01:00
completed: 2026-03-02T09:14:14.6570268+01:00
tags:
    - phase-9
    - knowledge-graph
    - research
    - agent
depends_on:
    - 255
class: standard
---

## Context
After intra-document graphs are solid, build cross-document connections. Takes entities from document A and document B, asks the LLM 'how are these related?', creates edges.
Depends on #255 (intra-document graph builder).

## Research Checklist
- [x] Theoretical validity: Does cross-document graph enrichment improve retrieval? Microsoft GraphRAG evidence?
- [x] Prior art: Microsoft GraphRAG community detection, LlamaIndex cross-doc linking, knowledge graph completion
- [x] Technical feasibility: N^2 entity pair explosion across documents -- how to prune?
- [x] Architecture fit: Separate module? Extension of intra-document builder? Background job?
- [x] Implementation approach: Entity clustering? Embedding similarity pre-filter? Community detection?

## Acceptance Criteria
- [x] Research doc in docs/ -- docs/inter-document-graph-builder-research.md (139 lines)
- [x] Follow-up implementation tasks created -- #388-390 (all done)
- [x] Scaling analysis -- O(N^2*M^2) pair explosion quantified with N=50/200/500 scenarios
- [x] Pre-filtering strategy -- embedding cosine similarity threshold (0.70) + cross-doc filter
- [x] Comparison with alternative approaches -- embedding-only vs rule-based vs community detection evaluated
