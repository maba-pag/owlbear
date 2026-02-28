---
id: 256
title: 'Research: Inter-document graph builder'
status: ideation
priority: important
created: 2026-02-28T12:41:01.1162616+01:00
updated: 2026-02-28T14:54:40.2333949+01:00
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
After intra-document graphs are solid, build cross-document connections. Takes entities from document A and document B, asks the LLM 'how are these related?', creates edges. This is where Confluence security policy connects to PydanticAI docs connects to ISO standards.

Depends on #255 (intra-document graph builder) — better internal connections make external ones more useful.

## Research Checklist
- [ ] Theoretical validity: Does cross-document graph enrichment improve retrieval? Microsoft GraphRAG evidence?
- [ ] Prior art: Microsoft GraphRAG community detection, LlamaIndex cross-doc linking, knowledge graph completion
- [ ] Technical feasibility: N^2 entity pair explosion across documents — how to prune?
- [ ] Architecture fit: Separate module? Extension of intra-document builder? Background job?
- [ ] Implementation approach: Entity clustering? Embedding similarity pre-filter? Community detection?

## Key Design Questions
- Entity pair explosion: 1000 entities across 50 docs = 500K pairs. How to prune efficiently?
- Pre-filter with embedding similarity: only compare entities with cosine > threshold?
- Community detection (Louvain, Leiden) to find entity clusters first, then enrich within clusters?
- Scope-aware: only connect entities within same scope, or cross-scope?
- When to run: nightly? After each new document? On-demand per document pair?
- Quality: how to validate cross-document edges aren't hallucinated?

## What This Enables
- 'How does our security documentation requirement relate to PydanticAI structured output?' -> explicit graph path
- Discovery: 'show me all concepts that bridge our security domain and our technical stack'
- Graph-augmented retrieval finds related chunks across domains via graph traversal, not just vector similarity

## Acceptance Criteria
- [ ] Research doc in docs/
- [ ] Follow-up implementation tasks created
- [ ] Scaling analysis (how many LLM calls for N documents with M entities each)
- [ ] Pre-filtering strategy to avoid N^2 explosion
- [ ] Comparison with alternative approaches (embedding-only, rule-based, community detection)
