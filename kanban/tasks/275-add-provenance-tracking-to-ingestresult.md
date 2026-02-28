---
id: 275
title: Add provenance tracking to IngestResult
status: ideation
priority: nice-to-have
created: 2026-02-28T14:21:44.8669303+01:00
updated: 2026-02-28T14:21:44.8669303+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

## Context
Apply Cognee's provenance tracking pattern: stamp each entity and edge with source_pipeline and source_task metadata.
See docs/knowledge-pipeline-research.md S4.

## Acceptance Criteria
- [ ] Add source_pipeline and source_task fields to Entity/Edge metadata
- [ ] IngestPipeline stamps provenance on all extracted entities
- [ ] Provenance queryable via GraphStore.list_entities filter
