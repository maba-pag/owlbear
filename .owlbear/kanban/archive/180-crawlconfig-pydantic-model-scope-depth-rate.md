---
id: 180
title: CrawlConfig Pydantic model — scope, depth, rate limiting
status: archived
priority: important
created: 2026-02-27T22:10:36.8102682+01:00
updated: 2026-02-28T23:53:28.6842779+01:00
started: 2026-02-27T22:12:09.0793793+01:00
completed: 2026-02-28T23:53:28.6842779+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
    - config
depends_on:
    - 192
class: standard
---

Module: src/owlbear/tools/browser/crawl_config.py | Test: tests/test_crawl_config.py | See docs/research/web-crawling.md S3.3.

AC:
- CrawlConfig frozen Pydantic model (frozen=True) with fields:
  - seed_urls: list[str] (required, non-empty)
  - max_depth: int = 1 (>= 0)
  - max_pages: int = 50 (>= 1)
  - same_domain_only: bool = True
  - allow_patterns: list[str] = [] (validated as compilable regex)
  - deny_patterns: list[str] = [] (validated as compilable regex)
  - delay_seconds: float = 1.5 (>= 0)
  - respect_robots: bool = True
  - user_agent: str = 'OwlBear/1.0 (research crawler)'
- Regex validation reuses pattern from BrowserConfig._validate_regex_patterns
- Field validators: max_depth >= 0, max_pages >= 1, delay_seconds >= 0.0, seed_urls non-empty
- ruff clean, all tests in tests/test_crawl_config.py pass
