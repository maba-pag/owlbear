---
id: 410
title: Stamp provenance metadata in IngestPipeline
status: backlog
priority: nice-to-have
created: 2026-03-01T20:19:22.8294167+01:00
updated: 2026-03-01T20:23:58.0236007+01:00
started: 2026-03-01T20:23:58.0236007+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

From #275 provenance-tracking-research.md. Add pipeline_name: str = 'ingest' constructor param to IngestPipeline. Stamp source_pipeline + source_task into entity/edge metadata dict via model_copy in _store_extractions() (source_task='entity_extraction') and _enrich_graph() (source_task='graph_enrichment'). ~20 LOC. AC: New entities/edges have metadata.source_pipeline and metadata.source_task populated; existing entities without provenance unaffected. Depends on #275.
