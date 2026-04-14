---
id: 864
title: 'P3-03: Wire InterDocGraphBuilder into refresh pipeline'
status: backlog
priority: nice-to-have
created: '2026-04-13T19:16:55.201306+00:00'
updated: '2026-04-14T14:26:11.140521+00:00'
tags:
- phase-3
- scope:knowledge
- deferred
parent: 772
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

InterDocGraphBuilder is a standalone class — neither refresh.py nor ingest.py calls it. For cross-source linking to work, the builder must be triggered after intra-doc graph building completes for a newly ingested document.

See: .owlbear/research/772-interdocgraphbuilder-corporate-types.md (Gap G6)

## Acceptance Criteria

- [ ] After document ingestion + intra-doc build, trigger inter-doc build for new doc's entities
- [ ] Inter-doc build is async (non-blocking to ingestion flow)
- [ ] Skip inter-doc build if fewer than 2 documents exist in scope
- [ ] Config toggle to enable/disable inter-doc building (default: disabled until Phase 3 launch)
- [ ] Integration test: ingest 2 docs from different sources, verify cross-doc edges created

## Affected Files

- `serve/knowledge/src/owlbear_knowledge/refresh.py` or `ingest.py`

## Dependency

Depends on P3-01 (prompt fix) and P3-02 (source-aware filtering).

[[2026-04-14]]
## Research
- Research doc: .owlbear/research/864-wire-interdocgraphbuilder-pipeline.md
- Sources: 7 studied (all codebase-internal), 5 high-relevance
- Recommendation: Wire at RefreshOrchestrator level — 2 new optional DI params (inter_doc_builder, graph_store), 1 new private async method, asyncio.create_task for non-blocking, DI-based config toggle (builder=None = disabled). Confidence: .78
- Follow-up tasks created: #874 (P3-05: StructuredExtractor replacement — research status, important priority)
- Decision requests: none (T1 — structural wiring)

Key findings:
1. **Dependency blocker:** #862 (P3-01) is BLOCKED — LLMExtractor removed, no StructuredExtractor impl exists. #864 depends_on field should be [862, 863] per #772 review.
2. **Wiring point:** RefreshOrchestrator (not IngestPipeline) — orchestrator is the natural coordination layer, preserves IngestPipeline SRP.
3. **Edge storage gap:** InterDocGraphBuilder.build() returns edges but does NOT persist — caller must call graph_store.insert_edge() per edge.
4. **Scoped doc count:** AC3 requires scoped check; get_counts() is global. Use list_documents(scopes=[scope]) for correctness.