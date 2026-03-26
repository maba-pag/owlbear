---
id: 759
title: Implement raw-HTML cache layer for WebCrawler
status: archived
priority: someday
created: 2026-03-12T12:45:14.7512822+01:00
updated: 2026-03-22T19:20:10.0631324+01:00
started: 2026-03-22T19:20:10.0631324+01:00
completed: 2026-03-22T19:20:10.0631324+01:00
tags:
    - browser
    - phase-4
blocked: true
block_reason: Already implemented in source, tests, and git history; stale tracker, do not route to builder
class: standard
---

Pattern: cache raw HTML by URL hash, separate from extracted content. Enables re-extraction without re-crawling. Inspired by botasaurus two-layer cache (see docs/research/botasaurus.md S4.4). AC:
- [ ] Cache raw HTML to disk keyed by normalized URL hash
- [ ] WebCrawler checks cache before fetching
- [ ] Cache TTL configurable via CrawlConfig
- [ ] Existing crawl_and_ingest pipeline unchanged

[[2026-03-21]] Sat 06:40
## Architecture Review
**Verdict:** Block

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Cache raw HTML to disk keyed by normalized URL hash | Already implemented in src/owlbear/tools/browser/html_cache.py via HtmlCache with SHA-256 of normalized URL and .html filenames; original AC is no longer an actionable implementation contract. | Do not route to builder again; treat as stale tracker. |
| WebCrawler checks cache before fetching | Already implemented in src/owlbear/tools/browser/crawler.py with injected HtmlCache and cache-hit short-circuit before navigation. | Do not route to builder again; treat as stale tracker. |
| Cache TTL configurable via CrawlConfig | Already implemented in src/owlbear/tools/browser/crawl_config.py as cache_ttl_seconds with non-negative validation and default 86400. | Do not route to builder again; treat as stale tracker. |
| Existing crawl_and_ingest pipeline unchanged | Existing integration boundary remains in src/owlbear/tools/browser/integration.py; current repo state already preserves the non-regression requirement. | Do not route to builder again; treat as stale tracker. |

### Architecture Notes
- Codebase check shows the feature already exists in the browser domain: src/owlbear/tools/browser/html_cache.py, src/owlbear/tools/browser/crawl_config.py, src/owlbear/tools/browser/crawler.py, and tests/test_html_cache.py.
- Git history already contains the #759 pipeline commits: 3494359 (tests), b861495 (builder), c4a5f9c (writer), and 2dfda2e (cleanup/chore).
- Routing this task to builder would duplicate shipped browser-layer behavior and violates KISS/YAGNI.
- TDD coverage already exists via task #834 and tests/test_html_cache.py; the board state is stale, not the architecture.
- If future work is needed here, it must be framed as incremental cleanup or regression verification against the existing HtmlCache / WebCrawler / CrawlConfig contract, not as a new implementation task.

### Changes Made
- Claimed #759 for architecture review.
- Appended this architecture review with codebase and git-history evidence.
- Moved #759 to ideation and blocked it as a stale task so it does not re-enter builder flow.

### Dependencies
- Verified: #834 exists as the preceding RED task for #759.
- Verified: implementation and tests already exist for the original AC surface.
