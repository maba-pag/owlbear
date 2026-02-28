---
id: 192
title: Test CrawlConfig model — validation and defaults
status: archived
priority: important
created: 2026-02-27T22:18:17.5455072+01:00
updated: 2026-02-28T23:53:41.8393431+01:00
started: 2026-02-27T23:47:24.1606535+01:00
completed: 2026-02-28T23:53:41.8393431+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
    - config
    - test
class: standard
---

Write tests in tests/test_crawl_config.py for src/owlbear/tools/browser/crawl_config.py. Test: (1) CrawlConfig is frozen Pydantic model (2) Default values: max_depth=1, max_pages=50, same_domain_only=True, delay_seconds=1.5, respect_robots=True, user_agent='OwlBear/1.0 (research crawler)' (3) seed_urls is required and must be non-empty (4) Validates max_depth >= 0, max_pages >= 1, delay_seconds >= 0 (5) allow_patterns and deny_patterns validated as compilable regex (follow BrowserConfig pattern) (6) Invalid regex in patterns raises ValidationError (7) Model is immutable (frozen=True)
