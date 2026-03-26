---
id: 195
title: Test WebCrawler — async crawl with mocked browser
status: archived
priority: important
created: 2026-02-27T22:18:44.747991+01:00
updated: 2026-02-28T23:53:44.5852365+01:00
started: 2026-02-28T00:26:41.2313428+01:00
completed: 2026-02-28T23:53:44.5852365+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
    - test
class: standard
---

Write tests in tests/test_web_crawler.py for src/owlbear/tools/browser/crawler.py. Test: (1) WebCrawler accepts BrowserManager instance (2) crawl() returns CrawlResult with pages list, total_pages, errors (3) CrawlPage model has url, content, title, metadata (4) Respects max_depth — does not follow links beyond configured depth (5) Respects max_pages — stops after limit (6) same_domain_only filters cross-domain links (7) Checks robots.txt before each fetch (when respect_robots=True) (8) Rate limiting: pauses delay_seconds between requests (mock asyncio.sleep) (9) URL dedup: does not visit same normalized URL twice (10) All browser interactions mocked (BrowserManager, page.goto, page.content) (11) Uses pytest-asyncio for async tests
