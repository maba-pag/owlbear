---
id: 759
title: Implement raw-HTML cache layer for WebCrawler
status: backlog
priority: someday
created: 2026-03-12T12:45:14.7512822+01:00
updated: 2026-03-12T12:45:14.7512822+01:00
tags:
    - browser
    - phase-4
class: standard
---

Pattern: cache raw HTML by URL hash, separate from extracted content. Enables re-extraction without re-crawling. Inspired by botasaurus two-layer cache (see docs/research/botasaurus-research.md S4.4). AC:
- [ ] Cache raw HTML to disk keyed by normalized URL hash
- [ ] WebCrawler checks cache before fetching
- [ ] Cache TTL configurable via CrawlConfig
- [ ] Existing crawl_and_ingest pipeline unchanged
