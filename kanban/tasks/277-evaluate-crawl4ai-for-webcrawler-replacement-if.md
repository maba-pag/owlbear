---
id: 277
title: Evaluate crawl4ai for WebCrawler replacement if crawling demand grows
status: archived
priority: nice-to-have
created: 2026-02-28T14:22:06.7778096+01:00
updated: 2026-03-02T09:14:23.5632046+01:00
started: 2026-03-01T19:58:26.0120766+01:00
completed: 2026-03-02T09:14:23.5632046+01:00
tags:
    - browser
    - research
    - phase-6
class: standard
---

## Context
Research #264 identified crawl4ai's crawler as significantly more mature than our ~180 LOC WebCrawler:
- Crash recovery (resume_state)
- Prefetch mode (5-10x faster URL discovery)
- Concurrent crawling (semaphore_count)
- BFS/DFS/Best-First strategies

## Acceptance Criteria
- [ ] Only pursue if crawling becomes a primary OwlBear use case
- [ ] Evaluate crawl4ai's crawler component ONLY (not full browser automation)
- [ ] Must work with our existing BrowserManager CDP connection
- [ ] Must integrate with crawl_and_ingest pipeline

See docs/research/browser-automation.md Section 3.3
