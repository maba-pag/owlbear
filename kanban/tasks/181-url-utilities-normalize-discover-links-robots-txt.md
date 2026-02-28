---
id: 181
title: URL utilities — normalize, discover links, robots.txt
status: archived
priority: important
created: 2026-02-27T22:10:42.7028995+01:00
updated: 2026-02-28T23:53:29.5862296+01:00
started: 2026-02-27T22:12:09.5352305+01:00
completed: 2026-02-28T23:53:29.5862296+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
depends_on:
    - 193
class: standard
---

Module: src/owlbear/tools/browser/url_utils.py | Test: tests/test_url_utils.py | See docs/web-crawling-research.md S3.3-3.5.

AC:
- normalize_url(url: str) -> str — lowercase scheme+host, strip trailing slash, strip fragment (#...), sort query params
- discover_links(html: str, base_url: str, config: CrawlConfig) -> list[str] — extract href from <a> tags, resolve relative URLs via urllib.parse.urljoin, filter by same_domain/allow/deny patterns, return normalized URLs
- RobotsTxtChecker class wrapping urllib.robotparser.RobotFileParser:
  - async load(url: str) -> None — fetch robots.txt for the URL's domain (httpx)
  - can_fetch(url: str) -> bool — check if URL is allowed for our user_agent
  - crawl_delay() -> float | None — return Crawl-delay directive value or None
- RobotsTxtChecker handles missing/unreachable robots.txt gracefully (defaults to allow-all)
- HTML parsing via stdlib html.parser or re (no new deps — KISS)
- ruff clean, all tests in tests/test_url_utils.py pass
