---
id: 262
title: 'Research: Adopt existing knowledge pipeline vs build custom'
status: archived
priority: critical
created: 2026-02-28T12:56:29.620611+01:00
updated: 2026-02-28T23:54:28.8804513+01:00
started: 2026-02-28T13:57:46.8176301+01:00
completed: 2026-02-28T23:54:28.8804513+01:00
tags:
    - phase-9
    - knowledge-graph
    - research
class: standard
---

## Context
Before executing 14 implementation tasks (#247-#259, #261), we must evaluate whether an existing open-source knowledge pipeline framework can replace our custom-built one. Our principles: 'Nothing we build is new or unique. Research before implementation, always.'

Our current pipeline reimplements what mature OSS projects have solved: chunking, embedding, vector search, entity extraction, graph building, document management, ingestion orchestration, reranking.

## Candidates (research all equally, no bias)

| Project | Focus | License |
|---|---|---|
| LlamaIndex | Full RAG pipeline, document management, multiple index types | MIT |
| Cognee | Knowledge graphs + vectors + LLM extraction, purpose-built | Apache 2.0 |
| Microsoft GraphRAG | Graph enrichment, community detection, hierarchical summaries | MIT |
| txtai | Lightweight embeddings DB with graph, hybrid search | Apache 2.0 |
| Haystack (deepset) | Production pipelines, document stores, retrievers | Apache 2.0 |
| R2R (SciPhi) | Production RAG with document management, knowledge graphs | MIT |
| Unstructured.io | Document processing (intake layer only) | Apache 2.0 |

## Research Checklist
- [ ] Theoretical validity: Can an existing framework replace our custom pipeline without losing functionality?
- [ ] Prior art: Clone top 3-4 repos to docs/research/, analyze architecture, API surface, extension points
- [ ] Technical feasibility: Compatibility with our stack (Python 3.12, PydanticAI, Qdrant, bge-m3, CPU-only)
- [ ] Architecture fit: Can it integrate with OwlBear's agent layer, scope system, channels?
- [ ] Implementation approach: Full adoption vs partial adoption (use their pipeline, keep our agents)?

## Evaluation Criteria

1. **Qdrant + bge-m3 support** — Can it use Qdrant as vector store AND bge-m3 for hybrid (dense+sparse+ColBERT)?
2. **Knowledge graph** — Does it extract entities/relationships? Build intra/inter-document graphs?
3. **Document management** — Content hashing, delta re-ingest, source registry, update detection?
4. **Extensibility** — Can we plug in our PydanticAI agents, custom extractors, scope filtering?
5. **Weight** — Dependency footprint, RAM, CPU requirements for laptop-resident daemon?
6. **API quality** — Clean Python API? Typed? Pydantic models? Or stringly-typed mess?
7. **Community health** — Contributors, release cadence, bus factor, issue response time?
8. **What we'd lose** — What custom features would we have to rebuild or sacrifice?
9. **What we'd gain** — What features do they have that we haven't built and would take weeks to add?

## Decision Framework

Three possible outcomes:
- **Full adopt**: Replace owlbear.memory.knowledge with framework X. Keep SQLite for our relational data, delegate vector/graph/ingestion to the framework.
- **Partial adopt**: Use framework X for specific layers (e.g., use their document management + ingestion, keep our own graph store). Cherry-pick.
- **Learn and build**: No framework fits. Document what they do well, apply patterns to our custom code.

## Acceptance Criteria
- [ ] Top 4 frameworks cloned to docs/research/ and analyzed
- [ ] Comparison matrix across all 9 evaluation criteria
- [ ] Proof-of-concept: ingest a document, search it, show entity graph — using the top candidate
- [ ] Honest assessment: what we gain, what we lose, what it costs
- [ ] Decision with confidence score and rationale
- [ ] Follow-up tasks: either adoption plan OR 'proceed with custom build' confirmation
- [ ] Impact assessment on existing tasks #247-#259: which survive, which become redundant?
