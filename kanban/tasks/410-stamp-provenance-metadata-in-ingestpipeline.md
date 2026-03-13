---
id: 410
title: Stamp provenance metadata in IngestPipeline
status: archived
priority: nice-to-have
created: 2026-03-01T20:19:22.8294167+01:00
updated: 2026-03-03T16:40:08.3811358+01:00
started: 2026-03-01T20:23:58.0236007+01:00
completed: 2026-03-03T16:40:08.3811358+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

## Context
From #275 provenance-tracking.md Option A (metadata dict approach).
See docs/research/provenance-tracking.md S3–S4.

## Acceptance Criteria
- [ ] IngestPipeline.__init__ accepts pipeline_name: str = 'ingest' parameter and stores as self._pipeline_name
- [ ] _store_extractions() merges {'source_pipeline': self._pipeline_name, 'source_task': 'entity_extraction'} into each entity's metadata dict via model_copy(update=...) — extending the existing updates dict
- [ ] _store_extractions() merges same provenance keys into each edge's metadata dict via model_copy(update=...) — note: currently edges only get scope stamped, provenance adds {'source_pipeline': ..., 'source_task': 'entity_extraction'} to the edge's metadata
- [ ] _enrich_graph() stamps edges from graph builder with {'source_pipeline': self._pipeline_name, 'source_task': 'graph_enrichment'} in metadata before insert_edge()
- [ ] Existing entities/edges without provenance metadata remain unaffected (backward compatible)
- [ ] Tests: unit test with mock graph_store verifying metadata dict contains source_pipeline and source_task after _store_extractions(); separate test for _enrich_graph() provenance

## Implementation Notes
- Pattern: follow existing model_copy(update={...}) in _store_extractions() L747+
- Entity metadata merge: extend the existing 'updates' dict or use nested model_copy for metadata
- Edge metadata merge: entity.model_copy(update={'metadata': {**entity.metadata, 'source_pipeline': ..., 'source_task': ...}})
- ~20 LOC across IngestPipeline constructor + _store_extractions + _enrich_graph
