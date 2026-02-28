---
id: 183
title: WebCrawler class — async crawl orchestrator using BrowserManager
status: archived
priority: important
created: 2026-02-27T22:10:55.9705792+01:00
updated: 2026-02-28T23:53:31.044612+01:00
started: 2026-02-27T22:12:10.5348598+01:00
completed: 2026-02-28T23:53:31.044612+01:00
tags:
    - phase-9
    - knowledge-graph
    - browser
depends_on:
    - 180
    - 181
    - 182
    - 195
class: standard
---

Module: src/owlbear/tools/browser/crawler.py | Test: tests/test_web_crawler.py | See docs/web-crawling-research.md S3.1, S3.6.

AC:
- WebCrawler class accepting a BrowserManager instance
- async crawl(config: CrawlConfig) -> CrawlResult method
- CrawlResult frozen Pydantic model: pages: list[CrawlPage], total_pages: int, errors: list[str]
- CrawlPage frozen Pydantic model: url: str, content: str, title: str | None, metadata: dict[str, Any]
- URL queue via asyncio.Queue, visited set (set[str] of normalized URLs) for dedup
- Respects CrawlConfig.max_depth: tracks depth per URL, does not follow links beyond max_depth
- Respects CrawlConfig.max_pages: stops crawling after limit reached
- same_domain_only: filters discovered links to seed URL domains only
- Checks robots.txt before each fetch via RobotsTxtChecker (when config.respect_robots=True)
- Content extraction via extract_content() from content_extractor.py
- Link discovery via discover_links() from url_utils.py
- Rate limiting via asyncio.sleep(config.delay_seconds) between page fetches
- Navigation via BrowserManager.page.goto() + page.content() for rendered HTML
- Errors on individual pages logged and added to CrawlResult.errors (crawl continues)
- ruff clean, all tests in tests/test_web_crawler.py pass
