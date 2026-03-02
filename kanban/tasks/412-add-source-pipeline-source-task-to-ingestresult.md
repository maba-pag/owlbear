---
id: 412
title: Add source_pipeline/source_task to IngestResult model
status: backlog
priority: nice-to-have
created: 2026-03-01T20:19:51.3501642+01:00
updated: 2026-03-01T20:24:01.725242+01:00
started: 2026-03-01T20:24:01.725242+01:00
tags:
    - phase-9
    - knowledge-graph
class: standard
---

From #275 provenance-tracking-research.md. Expose provenance on IngestResult model for callers. ~5 LOC. AC: IngestResult includes source_pipeline and source_task fields; callers can inspect provenance of ingestion results. Depends on #275, #410.
