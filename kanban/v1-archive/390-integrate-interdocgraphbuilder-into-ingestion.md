---
id: 390
title: Integrate InterDocGraphBuilder into ingestion pipeline
status: archived
priority: important
created: 2026-03-01T20:16:09.2973662+01:00
updated: 2026-03-02T09:14:58.9912354+01:00
started: 2026-03-01T20:23:11.6435606+01:00
completed: 2026-03-02T09:14:58.9912354+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

## Context
From #256 inter-document-graph-builder.md.
Hook InterDocGraphBuilder into IngestPipeline after intra-doc graph enrichment.
Follows _schedule_graph_enrichment pattern in ingest.py.

## Acceptance Criteria
- [ ] IngestPipeline.__init__() accepts optional inter_doc_builder: InterDocGraphBuilder | None = None (following graph_builder param pattern)
- [ ] New method _schedule_inter_doc_enrichment(document_id, extract_results, scope) mirrors _schedule_graph_enrichment() pattern
- [ ] Called in ingest() after _schedule_graph_enrichment() (step 9b), guarded by inter_doc_builder is not None
- [ ] _schedule_inter_doc_enrichment creates asyncio.Task, adds to _background_tasks set with done_callback
- [ ] Skip if fewer than 2 documents exist in scope (query document_status table for scope count)
- [ ] Config: add inter_doc_graph_building: bool = False to OwlBearSettings (default off, expensive operation)
- [ ] Bootstrap: _build_knowledge_toolset() instantiates InterDocGraphBuilder when settings.inter_doc_graph_building is True, passes to IngestPipeline
- [ ] Inter-doc edges inserted via graph_store.insert_edge() in background task (same as _enrich_graph pattern)
- [ ] Integration test: ingest 2 docs with related entities under same scope, verify inter-doc edges appear in GraphStore with metadata source=inter_doc_inference

## Dependencies
Depends on #388 (InterDocGraphBuilder core class).
