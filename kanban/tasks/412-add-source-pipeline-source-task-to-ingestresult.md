---
id: 412
title: Add source_pipeline/source_task to IngestResult model
status: archived
priority: nice-to-have
created: 2026-03-01T20:19:51.3501642+01:00
updated: 2026-03-03T16:40:09.5058265+01:00
started: 2026-03-01T20:24:01.725242+01:00
completed: 2026-03-03T16:40:09.5058265+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

## Context
From #275 provenance-tracking-research.md S4.

## Acceptance Criteria
- [ ] IngestResult model gains source_pipeline: str = 'ingest' field (default matches IngestPipeline default)
- [ ] IngestResult model gains source_task: str = 'full_pipeline' field (represents the overall pipeline run)
- [ ] IngestPipeline.ingest() and ingest_text() populate source_pipeline from self._pipeline_name in the returned IngestResult
- [ ] Skipped results (status='skipped') still include source_pipeline/source_task
- [ ] Failed results (status='failed') still include source_pipeline/source_task
- [ ] Tests: verify IngestResult from ingest() has source_pipeline='ingest' and source_task='full_pipeline'; verify custom pipeline_name propagates

## Implementation Notes
- Add 2 fields to IngestResult Pydantic model (~2 LOC)
- Update return statements in ingest(), ingest_text(), _ingest_from_intake() (~3 LOC per method)
- Depends on #410 (pipeline_name constructor param must exist first)
