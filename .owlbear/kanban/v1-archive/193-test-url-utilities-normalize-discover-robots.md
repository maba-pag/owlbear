---
id: 193
title: Test URL utilities — normalize, discover, robots
status: archived
priority: important
created: 2026-02-27T22:18:27.5643935+01:00
updated: 2026-02-28T23:53:42.9837835+01:00
started: 2026-02-27T23:47:27.1105931+01:00
completed: 2026-02-28T23:53:42.9837835+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
    - test
class: standard
---

Write tests in tests/test_url_utils.py for src/owlbear/tools/browser/url_utils.py. Test: (1) normalize_url lowercases scheme+host, strips trailing slash, strips fragment, sorts query params (2) normalize_url handles edge cases: empty string, relative URLs, non-HTTP schemes (3) discover_links extracts href from <a> tags and resolves relative URLs (4) discover_links filters by same_domain, allow_patterns, deny_patterns from CrawlConfig (5) discover_links returns normalized URLs (6) RobotsTxtChecker.can_fetch returns True/False per robots.txt rules (7) RobotsTxtChecker.crawl_delay returns delay value or None (8) RobotsTxtChecker handles missing/unreachable robots.txt gracefully (default allow)
