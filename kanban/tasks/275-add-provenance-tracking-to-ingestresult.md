---
id: 275
title: Add provenance tracking to IngestResult
status: archived
priority: nice-to-have
created: 2026-02-28T14:21:44.8669303+01:00
updated: 2026-03-03T16:40:07.7784779+01:00
started: 2026-03-01T18:51:11.0977368+01:00
completed: 2026-03-03T16:40:07.7784779+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

## TRACKING EPIC — Do not implement directly

This task is tracked by its three child tasks:
- #410 — Stamp provenance metadata in IngestPipeline
- #411 — Add source_pipeline filter to GraphStore.list_entities/list_edges
- #412 — Add source_pipeline/source_task to IngestResult model

All three children must reach done before this epic can be closed.

## Context
Apply Cognee's provenance tracking pattern: stamp each entity and edge with source_pipeline and source_task metadata.
See docs/provenance-tracking-research.md S4.

## Original Acceptance Criteria (delegated to children)
- [ ] Add source_pipeline and source_task fields to Entity/Edge metadata - #410
- [ ] IngestPipeline stamps provenance on all extracted entities - #410
- [ ] Provenance queryable via GraphStore.list_entities filter - #411
- [ ] IngestResult exposes provenance fields - #412
