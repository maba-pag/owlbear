---
id: 411
title: Add source_pipeline filter to GraphStore.list_entities/list_edges
status: archived
priority: nice-to-have
created: 2026-03-01T20:19:36.5834638+01:00
updated: 2026-03-03T16:40:08.9368197+01:00
started: 2026-03-01T20:24:00.401048+01:00
completed: 2026-03-03T16:40:08.9368197+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

## Context
From #275 provenance-tracking-research.md S3.4.
See docs/provenance-tracking-research.md.

## Acceptance Criteria
- [ ] GraphStore.list_entities() accepts optional source_pipeline: str | None = None parameter
- [ ] When source_pipeline is not None, adds WHERE clause: json_extract(metadata, '$.source_pipeline') = ?
- [ ] list_entities(source_pipeline='ingest') returns only entities whose metadata contains source_pipeline='ingest'
- [ ] list_entities(source_pipeline=None) returns all entities (no filter applied) — backward compatible
- [ ] GraphStore.list_edges() accepts optional source_pipeline: str | None = None parameter with identical json_extract filter logic
- [ ] Tests: insert 2 entities (one with source_pipeline='ingest' in metadata, one without) and verify list_entities(source_pipeline='ingest') returns only the first; same pattern for edges

## Implementation Notes
- Follow existing clauses/params pattern in list_entities() and list_edges()
- Uses SQLite json_extract() from JSON1 extension (ships with Python 3.12+)
- ~15 LOC across list_entities + list_edges
- Depends on #410 (entities must have provenance in metadata to be filterable)
