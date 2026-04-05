# Web Crawling into Knowledge Graph via Playwright

> **Owning task:** #134 — Web crawling into knowledge graph via Playwright
> **Date:** 2026-02-27
> **Status:** Complete

## 1. Context and Question

OwlBear needs to crawl web pages (API docs, blog posts, GitHub READMEs, intranet articles) and feed extracted content into the knowledge ingestion pipeline (#133). The existing `src/owlbear/tools/browser/` package provides `BrowserManager` (Playwright lifecycle), `BrowserToolset` (6 actions including `browser_read_text`), and `BrowserConfig` (URL safety, CDP config). The question is: **build on the existing browser toolset, or adopt a dedicated crawling framework?** And: **what content extraction approach yields the cleanest text for knowledge ingestion?**

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Crawlee-python (Apify) | github.com/apify/crawlee-python | .80 | Full crawling framework: PlaywrightCrawler, request queue, retries, proxy rotation, `enqueue_links()`, `max_requests_per_crawl`. 8.1k stars |
| trafilatura | github.com/adbar/trafilatura | .90 | Best-in-class HTML→text extraction: readability + jusText hybrid, native Markdown/JSON output, metadata (title, author, date), URL deduplication. 5.4k stars, used by HuggingFace/IBM/Microsoft |
| readability-lxml | github.com/buriy/python-readability | .70 | Readability.js Python port: article body extraction from HTML. 2.9k stars. Simpler but less accurate than trafilatura |
| urllib.robotparser (stdlib) | docs.python.org/3/library/urllib.robotparser.html | .85 | Python stdlib robots.txt parser: `can_fetch()`, `crawl_delay()`, `site_maps()`. Zero dependencies |
| Crawlee anti-blocking guide | crawlee.dev/python/docs/guides/avoid-blocking | .50 | Fingerprint rotation, Camoufox integration. Relevant context but overkill for our use case |
| Knowledge ingestion research (#133) | docs/research/knowledge-ingestion.md | .95 | Pipeline architecture: intake → chunk → embed → extract → store. Defines the interface crawled content must feed into |

## 3. Analysis

### 3.1 Approach — Crawling Framework vs Custom on Existing Toolset

| Criterion | Crawlee PlaywrightCrawler (.55) | Custom on existing BrowserToolset (.85) | trafilatura standalone (.60) |
|-----------|--------------------------------|----------------------------------------|------------------------------|
| JS rendering | Yes (own Playwright) | Yes (existing Playwright) | No (httpx only) |
| Content extraction | DIY | DIY + extraction library | Built-in best-in-class |
| Dependency count | ~50+ packages, own browser pool | 0 new for navigation | ~15 packages |
| Conflicts with existing code | **Yes** — parallel BrowserPool/Manager | **None** — reuses BrowserManager | N/A — no browser |
| Queue management | Built-in AutoscaledPool | Custom (asyncio.Queue — ~20 LOC) | Built-in URL queue |
| Rate limiting | Built-in | Custom (asyncio.sleep — ~5 LOC) | Built-in |
| robots.txt | Not built-in | urllib.robotparser (stdlib) | Not focused |
| KISS score | **Low** (full framework) | **High** (thin layer) | Medium |
| YAGNI risk | High — proxy rotation, fingerprints, dataset storage we don't need | Low — build only what we need | Medium — CLI/spider features unused |

**Key insight:** Crawlee introduces a parallel browser management system (`BrowserPool`, its own Playwright launcher) that **conflicts with our existing `BrowserManager`/`BrowserConfig`**. We'd have two independent browser lifecycles — one for agent tools, one for crawling. That violates DRY and adds complexity for no benefit.

**Recommendation (.85):** Build a thin `WebCrawler` class on the existing `BrowserManager`. Use trafilatura for content extraction from Playwright-rendered HTML. This gives us JS rendering (existing) + best-in-class extraction (trafilatura) with minimal new code.

### 3.2 Content Extraction — How to Get Clean Text

| Criterion | `browser_read_text` (existing) (.40) | readability-lxml (.65) | trafilatura (.85) |
|-----------|--------------------------------------|------------------------|-------------------|
| Article isolation | No — returns ALL text (nav, footer, ads) | Yes — Readability algorithm | Yes — hybrid readability + jusText |
| Metadata extraction | None | Title only | Title, author, date, site name, categories |
| Markdown output | No | No | **Yes — native** |
| Benchmark accuracy | N/A | Good | **Best** (proven #1 in 3+ benchmarks) |
| Dependencies | 0 | lxml, cssselect (~5 MB) | ~6 packages (~10 MB) |
| Handles edge cases | Poor (truncation only) | Decent | Excellent (CJK, tables, code blocks) |

**Critical flow:** Playwright renders the page (handles SPAs, JS-generated content) → `page.content()` gets the full rendered HTML → trafilatura extracts clean article text + metadata. This combines the strengths of both tools.

**Recommendation (.85):** trafilatura for extraction. It natively outputs Markdown — ideal for the ingestion pipeline's recursive separator-based chunker (#133 recommends splitting on `\n##`, `\n###`, `\n\n`). readability-lxml outputs HTML which would need an extra html-to-text conversion step.

### 3.3 Crawl Depth and Scope Control

Prior art patterns from Crawlee and trafilatura:

- Crawlee: `max_requests_per_crawl=10`, `enqueue_links(include=[GlobPattern])` for URL filtering
- trafilatura: domain-specific crawling, sitemap discovery, URL deduplication by normalized URL

| Setting | Default | Rationale |
|---------|---------|-----------|
| `max_depth` | 1 (target page only) | Conservative default; most use cases are single-page doc ingestion |
| `max_pages` | 50 | Safety limit; prevents runaway crawls |
| `same_domain_only` | True | Prevents scope creep to external sites |
| `allow_patterns` | `[]` (all allowed) | Regex list — reuses BrowserConfig pattern |
| `deny_patterns` | `[]` (none denied) | Regex list — block login pages, PDFs, etc. |

### 3.4 Rate Limiting and Politeness

| Mechanism | Implementation | Source |
|-----------|---------------|--------|
| robots.txt | `urllib.robotparser.RobotFileParser` (stdlib) | Python docs — `can_fetch()`, `crawl_delay()` |
| Default delay | 1.5s between requests | Industry standard; Crawlee defaults to 0, but we prefer politeness |
| Respect `Crawl-delay` | Use `robotparser.crawl_delay()`, fall back to default | robots.txt spec |
| User-Agent | `"OwlBear/1.0 (research crawler)"` | Transparent identification |
| Configurable override | `CrawlConfig.delay_seconds` | User can increase/decrease |

### 3.5 Deduplication

| Level | Method | When |
|-------|--------|------|
| URL normalization | Strip fragments, sort query params, lowercase scheme+host | Before queueing |
| Visited set | In-memory `set[str]` of normalized URLs per crawl session | During crawl |
| Content hash | SHA-256 of extracted text body | Before ingestion — skip re-processing identical content |
| Document store | Check `documents` table by source URL metadata | Cross-session — skip if already in knowledge graph |

### 3.6 Pipeline Integration

The ingestion pipeline (#133) defines Stage 1 as "Intake" — readers for file, URL, raw text. Web crawling is a **multi-URL intake source** that navigates, renders, extracts, and feeds content to the pipeline:

```
WebCrawler.crawl(seed_urls, config)
  for each URL in queue:
    1. Check robots.txt              → urllib.robotparser
    2. Navigate via BrowserManager   → page.goto(url)
    3. Get rendered HTML             → page.content()
    4. Extract with trafilatura      → clean text + metadata
    5. Discover links                → page links within scope
    6. Feed to ingestion pipeline    → IngestPipeline.ingest(text, metadata)
    7. Rate-limit delay              → asyncio.sleep(delay)
```

**Architecture — new modules:**

| Module | Location | Purpose |
|--------|----------|---------|
| `crawler.py` | `src/owlbear/tools/browser/crawler.py` | `WebCrawler` class — orchestrates crawl loop using existing `BrowserManager` |
| `crawl_config.py` | `src/owlbear/tools/browser/crawl_config.py` | `CrawlConfig` Pydantic model — scope, depth, rate limiting settings |
| `extractor.py` | `src/owlbear/tools/browser/extractor.py` | Thin wrapper around trafilatura — HTML→text+metadata from rendered pages |
| `url_utils.py` | `src/owlbear/tools/browser/url_utils.py` | URL normalization, link discovery, robots.txt helper |

## 4. Recommendation (.85 confidence)

**Build on existing `BrowserManager` + trafilatura.** Do not adopt Crawlee — it conflicts with the existing browser lifecycle and brings 50+ dependencies we don't need. The implementation is ~300-400 LOC across 4 modules:

1. **`CrawlConfig`** — Pydantic model with scope/depth/rate settings
2. **`WebCrawler`** — async crawl loop: URL queue → navigate → extract → ingest → discover links
3. **Content extractor** — `page.content()` → `trafilatura.extract(html, output_format='markdown')`
4. **URL utils** — normalization, robots.txt, link filtering

**New dependency:** `trafilatura` (~10 MB). Apache-2.0 license. Already used by HuggingFace, IBM, Microsoft Research. Proven #1 in multiple extraction benchmarks.

**Risk:** trafilatura duplicates some crawling features (its own downloader, URL queue). We only use its extraction function `trafilatura.extract()` — the rest is ignored. This is fine from a dependency perspective but means ~10 MB of code we don't call. Mitigation: acceptable trade-off for proven extraction quality.

## 5. Follow-up Tasks

1. **CrawlConfig model** — Pydantic frozen model with seed_urls, max_depth, max_pages, same_domain_only, allow/deny patterns, delay_seconds, respect_robots, user_agent
2. **URL utilities** — normalize_url(), discover_links(page, config), RobotsTxtChecker wrapper around urllib.robotparser
3. **Content extractor** — extract_content(html) using trafilatura with Markdown output + metadata
4. **WebCrawler class** — Async crawl orchestrator using BrowserManager, URL queue, dedup, rate limiting
5. **Pipeline integration** — Connect WebCrawler output to ingestion pipeline intake (#133)
6. **Tests** — Unit tests for each module (URL normalization, robots.txt, extraction, crawl loop with mocked browser)
