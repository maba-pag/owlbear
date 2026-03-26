---
id: 196
title: Test pipeline integration — crawl to ingest flow
status: archived
priority: important
created: 2026-02-27T22:18:53.0925009+01:00
updated: 2026-02-28T23:53:45.3866801+01:00
started: 2026-02-28T00:36:32.9263039+01:00
completed: 2026-02-28T23:53:45.3866801+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
    - test
class: standard
---

Write tests in tests/test_crawl_integration.py for src/owlbear/tools/browser/integration.py. Test: (1) crawl_and_ingest() accepts WebCrawler, IngestPipeline, CrawlConfig (2) Each CrawlPage feeds into IngestPipeline.ingest() as text with URL metadata (3) Returns list[IngestResult] — one per crawled page (4) Errors in individual pages logged but do not halt batch (5) Empty crawl result returns empty list (6) All deps mocked (WebCrawler.crawl, IngestPipeline.ingest) (7) Uses pytest-asyncio for async tests
