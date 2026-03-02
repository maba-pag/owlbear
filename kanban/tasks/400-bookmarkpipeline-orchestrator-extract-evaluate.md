---
id: 400
title: 'BookmarkPipeline — orchestrator: extract, evaluate, ingest, store'
status: backlog
priority: needed
created: 2026-03-01T20:17:42.43629+01:00
updated: 2026-03-01T20:23:44.1431027+01:00
started: 2026-03-01T20:23:44.1431027+01:00
tags:
    - phase-13
    - knowledge-graph
class: standard
---

From #304 source-discovery-bookmarking-research.md. Orchestrates: web_read(url) -> extracted text -> dedup check (URL already bookmarked?) -> SourceEvaluator.evaluate() -> if score >= ingest_threshold (default 0.7): IngestPipeline.ingest() -> INSERT bookmark. AC: Full pipeline from URL to stored bookmark; high-score pages auto-ingested; dedup prevents duplicate bookmarks; returns summary to caller. Depends on #304, #398, #399.
