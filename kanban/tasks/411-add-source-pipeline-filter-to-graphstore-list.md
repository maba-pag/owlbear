---
id: 411
title: Add source_pipeline filter to GraphStore.list_entities/list_edges
status: backlog
priority: nice-to-have
created: 2026-03-01T20:19:36.5834638+01:00
updated: 2026-03-01T20:24:00.401048+01:00
started: 2026-03-01T20:24:00.401048+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

From #275 provenance-tracking-research.md. Add optional source_pipeline: str | None parameter to list_entities() and list_edges(). Uses json_extract(metadata, '$.source_pipeline') = ? clause. ~15 LOC. AC: list_entities(source_pipeline='ingest') returns only entities from that pipeline; list_edges same; None means no filter. Depends on #275, #410.
