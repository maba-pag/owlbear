---
id: 259
title: 'Research: Knowledge pipeline as reusable module'
status: ideation
priority: important
created: 2026-02-28T12:41:54.4410414+01:00
updated: 2026-02-28T14:54:41.6951402+01:00
tags:
    - phase-9
    - knowledge-graph
    - research
class: standard
---

## Context
The knowledge pipeline (chunk -> embed -> extract -> graph -> store -> search) is fairly generic. User wants to evaluate whether this should be a standalone Python package reusable beyond OwlBear.

## Research Checklist
- [ ] Theoretical validity: Is the pipeline generic enough? What's OwlBear-specific vs reusable?
- [ ] Prior art: LlamaIndex, LangChain, Haystack, Unstructured.io — what do they do that we don't?
- [ ] Technical feasibility: Can we extract the module without breaking OwlBear?
- [ ] Architecture fit: Package boundaries — what stays in owlbear.memory.knowledge vs new package?
- [ ] Implementation approach: Monorepo with shared package? Separate repo? Plugin architecture?

## Components to Evaluate for Extraction
- TextChunker (separator-based, overlap) — generic
- EmbeddingProvider protocol + BgeM3Provider — generic
- VectorStoreProtocol + QdrantVectorStore — generic
- EntityExtractor (PydanticAI-based) — semi-generic (depends on LLM provider)
- GraphStore (SQLite CRUD) — generic
- IngestPipeline (orchestrator) — generic
- Intra/inter-document graph builders — generic
- Content hashing + delta re-ingest — generic
- Source registry — generic

## Key Questions
- Is there market/community value? Or is this an OwlBear-only thing?
- What's the minimum viable standalone package?
- Naming: owlbear-knowledge? knowledge-graph-pipeline? Something else?
- Licensing: MIT? Apache 2.0?
- Do we extract now (before all components exist) or later (after everything is built)?

## Acceptance Criteria
- [ ] Research doc in docs/
- [ ] Decision: extract or keep in-tree (with rationale)
- [ ] If extract: package boundary diagram, migration plan, timeline
- [ ] If keep: architectural notes on keeping it extractable later
