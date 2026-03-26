# Browser Automation Alternatives — Keep Custom vs Adopt OSS

> **Owning task:** #264 — Research: Browser automation alternatives
> **Date:** 2026-02-28
> **Status:** Complete

## 1. Context and Question

The project audit identified our browser module (12 files, ~1200 LOC) as a potential
OSS replacement candidate. The user's hypothesis: we likely need to keep custom due
to corporate IT constraints (no admin, Edge policy-locked, no extensions).

**Key litmus test:** Does any library support `playwright.chromium.connect_over_cdp()`
to attach to a user's existing corporate-locked Edge browser?

**Environmental constraints (non-negotiable):**

- No admin access on Windows corporate laptop
- Edge browser policy-locked by IT (no extension sideloading)
- No additional browser addons allowed
- Playwright already a dependency (`owlbear[browser]` extra)
- CDP attach mode essential — connect to running Edge, not launch a new browser

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| browser-use (v0.12.0) | github.com/browser-use/browser-use | .85 | AI browser agent framework, CDP support, Playwright-based |
| browser-use docs | docs.browser-use.com/customize/browser | .90 | Full parameter reference, CDP/remote browser docs |
| crawl4ai (v0.8.0) | github.com/unclecode/crawl4ai | .75 | LLM-friendly web crawler, CDP modes, deep crawl strategies |
| crawl4ai BrowserConfig | crawl4ai/async_configs.py (GitHub) | .85 | `cdp_url`, `browser_mode`, `channel` parameter analysis |
| Stagehand (v3.6.1) | github.com/browserbase/stagehand | .50 | AI browser automation, TypeScript-first |
| stagehand-python (v3.6.0) | github.com/browserbase/stagehand-python | .55 | Python SDK — API client for Browserbase cloud service |
| readabilipy (v0.3.0) | pypi.org/project/readabilipy | .40 | Mozilla Readability.js Python wrapper |
| trafilatura | github.com/adbar/trafilatura | .60 | Currently used; baseline for content extraction comparison |

## 3. Analysis

### 3.1 CDP Attach Support (Litmus Test)

| Criterion | OwlBear Custom | browser-use | crawl4ai | Stagehand |
|-----------|---------------|-------------|----------|-----------|
| CDP connect_over_cdp | Yes (`BrowserManager._enter_cdp`) | Yes (`cdp_url` param) | Yes (`cdp_url` + `browser_mode="cdp"`) | Cloud-only CDP |
| Edge channel support | Yes (custom `launcher.py`) | Yes (`channel: 'msedge'`) | Yes (`channel: 'msedge'`) | N/A |
| Find/launch Edge with CDP | Yes (~100 LOC launcher) | No — assumes CDP already running | No — assumes CDP already running | No |
| Probe CDP readiness | Yes (`is_cdp_available()`) | No | No | No |
| No-extension mode | Yes (no extensions used) | Must set `enable_default_extensions=False` | No extensions by default | N/A |
| No-admin install | Yes (Playwright only) | Yes (Playwright only) | Yes (Playwright only) | Requires cloud account |

**Finding:** browser-use and crawl4ai both support CDP connect, but neither handles the full
Edge CDP lifecycle (find → probe → launch → connect) that our launcher provides. Our
~100 LOC Edge launcher is irreplaceable custom logic.

### 3.2 Feature Comparison — Interactive Browser Automation

| Feature | OwlBear BrowserToolset | browser-use | crawl4ai | Stagehand |
|---------|----------------------|-------------|----------|-----------|
| Navigate | `browser_navigate` | `agent.run(task)` | `crawler.arun(url)` | `sessions.navigate()` |
| Click | `browser_click(selector)` | AI-selected | JS injection only | `sessions.act()` |
| Type | `browser_type(selector, text)` | AI-selected | JS injection only | `sessions.act()` |
| Select dropdown | `browser_select(selector, value)` | AI-selected | N/A | N/A |
| Read text | `browser_read_text(selector)` | AI extract | Markdown/HTML output | `sessions.extract()` |
| Screenshot | `browser_screenshot()` | Built-in | `screenshot=True` config | N/A |
| URL safety guard | `URLSafetyGuard` (regex blocklist/allowlist) | `allowed_domains`/`prohibited_domains` (glob) | N/A | N/A |
| PydanticAI FunctionToolset | Native integration | No — brings own agent loop | No — standalone crawler | No — API client |
| Hook system integration | `PRE_TOOL_USE` via `URLSafetyGuard.register()` | No | No | No |
| Language | Python | Python | Python | TypeScript (Python SDK = API client) |
| LOC | ~1200 | ~15,000+ | ~20,000+ | N/A (cloud service) |
| License | Internal | MIT | Apache 2.0 | MIT |

### 3.3 Feature Comparison — Web Crawling

| Feature | OwlBear WebCrawler | crawl4ai | browser-use |
|---------|-------------------|----------|-------------|
| BFS crawl | Yes (async, deque-based) | Yes (BFS/DFS/Best-First) | No — not a crawler |
| Depth limit | `max_depth` | `max_depth` + crash recovery | N/A |
| Page limit | `max_pages` | `max_pages` + prefetch mode | N/A |
| Robots.txt | `RobotsTxtChecker` (async httpx) | `check_robots_txt` flag | N/A |
| Rate limiting | `delay_seconds` | `mean_delay` + `max_range` jitter | N/A |
| Same-domain filter | `same_domain_only` | `exclude_external_links` | N/A |
| URL allow/deny | Regex patterns | Glob/function matchers | N/A |
| Deep crawl recovery | No | Yes (v0.8.0 — `resume_state`) | N/A |
| Prefetch mode | No | Yes (5-10x faster URL discovery) | N/A |
| Concurrent crawl | No (sequential BFS) | Yes (`semaphore_count`) | N/A |
| LOC | ~180 | ~5000+ | N/A |
| Maturity | Basic | Production-grade | N/A |

### 3.4 Content Extraction Comparison

| Feature | trafilatura (OwlBear) | crawl4ai built-in | readabilipy |
|---------|----------------------|-------------------|-------------|
| Output format | Markdown | Markdown/HTML/fit-markdown | JSON (HTML + plain text) |
| Metadata extraction | Title, author, date | Title, links, images, tables | Title, byline |
| Dependencies | Pure Python | Pure Python | Node.js (or Python fallback) |
| Maintenance | Active (adbar) | Active | Low activity |
| Table extraction | No | Yes (scored, configurable) | No |
| Image scoring | No | Yes (quality threshold) | No |
| LOC to integrate | ~110 (our wrapper) | N/A (built-in to crawler) | ~50 |

### 3.5 Architectural Fit

| Concern | OwlBear Custom | OSS Adoption (browser-use) | OSS Adoption (crawl4ai) |
|---------|---------------|---------------------------|------------------------|
| PydanticAI toolset | Native `FunctionToolset` subclass | Must wrap entire agent framework | Must wrap crawler as tool |
| Dependency injection | `page` + `config` injected per-tool | Brings own DI (Agent + Browser) | Brings own context manager |
| Hook system | `URLSafetyGuard` registered on `HookRegistry` | Must bridge to their event system | No hook support |
| Crawl → ingest pipeline | Direct `crawl_and_ingest()` bridge | Would need custom bridge | Would need custom bridge |
| Agent intelligence | PydanticAI agent decides actions | browser-use agent decides actions (conflict!) | No agent — crawl-only |
| Config model | Frozen `Pydantic BaseModel` | Mutable `BrowserProfile` class | Mutable `BrowserConfig` class |
| Test patterns | Comprehensive mock-based tests | Different test patterns | Different test patterns |

## 4. Recommendation (.90 confidence) — Keep Custom

**Decision: Keep the custom browser module.** No OSS library satisfies our constraints end-to-end.

### Why keep

1. **Edge CDP launcher is irreplaceable** (.95 confidence): No OSS library handles
   find-Edge → probe-CDP → launch-with-port → connect. This ~100 LOC is the core
   differentiator forced by our corporate IT constraints.

2. **Architectural integration** (.90): Our `BrowserToolset` is a `FunctionToolset`
   subclass that registers 6 tools directly consumable by PydanticAI agents. browser-use
   brings its own agent loop (conflict with our agent architecture). crawl4ai is a
   crawler, not an interactive automation toolkit.

3. **KISS** (.90): 1200 LOC doing exactly what we need vs 15,000-20,000 LOC libraries
   with features we'll never use (AI element selection, cloud browsers, proxy rotation,
   virtual scroll, stealth mode).

4. **YAGNI** (.85): browser-use's natural-language element selection and Stagehand's
   self-healing are impressive but unnecessary — our PydanticAI agents already handle the
   intelligence layer. Adding another AI-powered layer creates double inference cost.

5. **URL safety guard** (.80): Our regex-based `URLSafetyGuard` integrates with the
   `HookRegistry` (`PRE_TOOL_USE` event). browser-use's `allowed_domains` uses glob
   patterns — different API, different integration point.

6. **No extension dependency** (.95): browser-use defaults to loading extensions (uBlock,
   ClearURLs). This is forbidden by our IT policy. While `enable_default_extensions=False`
   disables them, this is a footgun — one upgrade could change default behavior.

### What we acknowledge

- **crawl4ai's crawler is significantly more mature**: Crash recovery, prefetch mode,
  concurrent crawling, and deep-crawl strategies exceed our ~180 LOC BFS crawler. If
  large-scale crawling becomes a primary use case, evaluate crawl4ai for the crawl
  component only (not the browser automation).

- **trafilatura remains the right content extractor**: No compelling alternative offers
  better Markdown output without adding Node.js or other heavy dependencies.

- **browser-use's `allowed_domains` pattern is worth studying**: Their O(1) optimized
  domain matching for large lists could improve our regex-based URLSafetyGuard if we
  need to scale the blocklist.

## 5. Follow-up Tasks

1. **Close #264 with "keep custom" decision** — document rationale in task body
2. **Architecture doc update** — strengthen the "why custom" note in architecture.md
   browser module section with constraint citations from this research
3. **WebCrawler maturity gap** — if crawling demand grows, evaluate crawl4ai as
   replacement for `crawler.py` only (not the whole browser module)
4. **URLSafetyGuard optimization** — study browser-use's set-based O(1) domain matching
   for potential improvement to our regex-based guard (currently fine for small lists)
