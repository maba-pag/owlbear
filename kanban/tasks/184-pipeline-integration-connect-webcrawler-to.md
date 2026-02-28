---
id: 184
title: Pipeline integration — connect WebCrawler to ingestion intake
status: archived
priority: important
created: 2026-02-27T22:11:02.6607169+01:00
updated: 2026-02-28T23:53:31.8431751+01:00
started: 2026-02-27T22:12:11.0826341+01:00
completed: 2026-02-28T23:53:31.8431751+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
depends_on:
    - 176
    - 183
    - 196
class: standard
---

Module: src/owlbear/tools/browser/integration.py | Test: tests/test_crawl_integration.py | See docs/web-crawling-research.md S3.6.

AC:
- async crawl_and_ingest(crawler: WebCrawler, pipeline: IngestPipeline, config: CrawlConfig) -> list[IngestResult] function
- Each CrawlPage from WebCrawler.crawl() fed to IngestPipeline.ingest() as text content with URL metadata
- URL and page title passed in IntakeResult metadata for source tracking
- Returns list[IngestResult] — one per successfully ingested page
- Errors in individual page ingestion logged at WARNING but do not halt the batch
- Empty CrawlResult (no pages) returns empty list
- Function is the bridge between browser/crawler.py and memory/knowledge/ingest.py
- ruff clean, all tests in tests/test_crawl_integration.py pass
