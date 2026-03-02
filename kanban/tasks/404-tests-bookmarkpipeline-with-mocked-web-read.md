---
id: 404
title: 'Tests: BookmarkPipeline with mocked web_read, evaluator, ingest'
status: backlog
priority: important
created: 2026-03-01T20:18:20.1669989+01:00
updated: 2026-03-01T20:23:50.5295296+01:00
started: 2026-03-01T20:23:50.5295296+01:00
tags:
    - phase-13
    - test
    - knowledge-graph
class: standard
---

From #304 source-discovery-bookmarking-research.md. TDD with mocked web_read, SourceEvaluator, IngestPipeline. Test full pipeline flow, dedup behavior, ingest threshold logic. AC: Full pipeline tested with mocks; dedup tested (duplicate URL skipped); ingest threshold tested (low score skips ingest, high score triggers ingest). Depends on #304.
