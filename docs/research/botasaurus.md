# Botasaurus Feature Evaluation for OwlBear

> **Task:** #748 — Research omkarcloud/botasaurus for OwlBear
> **Date:** 2026-03-12
> **Status:** Complete

## 1. Context

OwlBear uses a custom Playwright-based browser module (~1200 LOC) with CDP attach to
corporate-locked Edge (#264 confirmed "keep custom" — see `browser-automation.md`).
This research evaluates which botasaurus *features and patterns* could improve OwlBear,
not whether to adopt botasaurus wholesale.

## 2. Sources

| Source | URL | License | Relevance |
|--------|-----|---------|-----------|
| omkarcloud/botasaurus (v4.0.97) | github.com/omkarcloud/botasaurus | MIT | Primary — 618-file monorepo, cloned and analyzed |
| botasaurus GitHub page | github.com/omkarcloud/botasaurus | MIT | 4.1k stars, 349 forks, 9 contributors, 243 dependents |
| botasaurus anti-detect-driver.md | (in-repo docs) | MIT | Anti-detection patterns: google_get, referral nav, bot check |
| OwlBear browser-automation-research | docs/research/browser-automation.md | Internal | Prior art — confirmed "keep custom" decision for browser stack |
| OwlBear crawl4ai-evaluation-research | docs/research/crawl4ai-evaluation.md | Internal | Prior art — crawl4ai can't reuse BrowserManager |

## 3. Architecture Overview

Botasaurus is a **Selenium-based web scraping framework** — fundamentally different from
OwlBear's purpose (AI development assistant with Playwright browser tools).

| Aspect | Botasaurus | OwlBear |
|--------|-----------|---------|
| Purpose | Web scraping framework | AI development assistant |
| Browser engine | Custom Selenium driver (botasaurus-driver) | Playwright (CDP attach to Edge) |
| Design | Synchronous, decorator-based (@browser/@request/@task) | Async, PydanticAI agent with FunctionToolset |
| Dependencies | 15+ packages (numpy, psutil, joblib, lxml, etc.) | Lean — Playwright + httpx + trafilatura |
| Server | Flask + SQLite/Postgres + React UI | Standalone daemon (asyncio) |

**Key finding:** Botasaurus cannot be adopted as a library. Its Selenium driver, sync
design, and heavy deps all conflict with OwlBear's stack. The value lies in
**extractable patterns**, not code reuse.

## 4. Feature-by-Feature Trade-off Analysis

### 4.1 Human-like Mouse Movement (botasaurus-humancursor)

Bezier-curve mouse trajectories using numpy + pytweening. Bypasses detection systems
that flag teleporting cursors.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Relevance to OwlBear | .30 | OwlBear browses for research, not to evade detection |
| Implementation effort | High | Requires numpy dep + Playwright CDP mouse dispatch |
| KISS/YAGNI | Fails both | OwlBear has no anti-detection requirement |
| Architecture fit | Low | Playwright's `page.mouse` API differs from Selenium's |

**Verdict: Skip.** OwlBear is not a scraper and doesn't need to evade bot detection.

### 4.2 Anti-Detection (google_get, referral navigation, fingerprint masking)

Navigation via Google referrer, randomized sleeps, user-agent hashing per profile,
Cloudflare/Datadome bypass.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Relevance to OwlBear | .25 | OwlBear accesses public pages and localhost; no WAF issues |
| Implementation effort | Medium | Referrer injection is trivial; full bypass is complex |
| KISS/YAGNI | Fails YAGNI | No user has reported detection issues |
| Architecture fit | Medium | Could add referrer to `browser_navigate` if ever needed |

**Verdict: Skip.** No evidence of need. Revisit only if users report access blocks.

### 4.3 Proxy Rotation & Management

Decorator-level proxy config, automatic rotation from proxy lists, authenticated proxy
with SSL via proxy-chain (Node.js dependency).

| Criterion | Score | Notes |
|-----------|-------|-------|
| Relevance to OwlBear | .20 | OwlBear operates on corporate LAN; proxies are irrelevant |
| Implementation effort | Medium | Playwright supports `proxy` in launch options natively |
| KISS/YAGNI | Fails both | Corporate environment already restricts proxy use |
| Architecture fit | Low | Would need `proxy-chain` (Node.js) for authenticated proxies |

**Verdict: Skip.** Corporate environment makes proxies both unnecessary and impractical.

### 4.4 Result Caching (MD5-hash file cache)

MD5-based file caching per scraping function — cache HTML separately from extracted
data, allowing re-extraction without re-scraping.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Relevance to OwlBear | .45 | Web research tool could benefit from page caching |
| Implementation effort | Low | ~50 LOC for hash-based file cache |
| KISS/YAGNI | Borderline | Knowledge store already caches ingested content |
| Architecture fit | Medium | Would layer above WebCrawler or content_extractor |

**Verdict: Maybe later.** The two-layer caching pattern (cache raw HTML + cache
extracted data) is a good practice for any web research tool. However, OwlBear's
knowledge store already ingests and indexes crawled content. A raw-HTML cache adds
value only if we need to re-extract from the same pages with different extractors.
File as nice-to-have.

### 4.5 Parallel Execution Model

Decorator parameter `parallel=N` launches N browser/request instances concurrently.
Async queue pattern for concurrent scroll + fetch.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Relevance to OwlBear | .35 | WebCrawler is sequential BFS; concurrency would help |
| Implementation effort | Low | asyncio.Semaphore already idiomatic in our stack |
| KISS/YAGNI | Passes KISS | crawl4ai already identified as superior crawler (#264) |
| Architecture fit | Good | asyncio native — straightforward to add |

**Verdict: Not from botasaurus.** If we need concurrent crawling, adopt crawl4ai's
semaphore pattern (already studied in prior research) rather than botasaurus's
thread-based parallelism which conflicts with our async design.

### 4.6 Browser Profiles (tiny_profile — cookie persistence)

Lightweight ~1KB profiles storing only cookies, vs full Chrome profiles (~100MB each).
Profile data stored in `profiles.json`.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Relevance to OwlBear | .40 | Could persist auth sessions across restarts |
| Implementation effort | Low | Cookie save/restore via Playwright's `context.cookies()` |
| KISS/YAGNI | Borderline | OwlBear uses single browser context currently |
| Architecture fit | Good | Playwright cookie API is clean |

**Verdict: Nice-to-have.** If OwlBear needs persistent browser sessions (e.g., staying
logged into services), a lightweight cookie-persistence layer is a good pattern.
Not needed now.

### 4.7 Decorator-Based Task Configuration

`@browser(headless=True, proxy=..., parallel=3, cache=True)` — all config as decorator
args with function-based dynamic resolution.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Relevance to OwlBear | .15 | OwlBear uses frozen Pydantic config + DI, not decorators |
| Implementation effort | N/A | Would require architectural rewrite |
| KISS/YAGNI | Fails | Our BrowserConfig + DI pattern is already clean |
| Architecture fit | Poor | Conflicts with PydanticAI's dependency injection model |

**Verdict: Skip.** Interesting DX for scraping scripts, but incompatible with OwlBear's
agent architecture.

### 4.8 Request-Based Scraping (botasaurus-requests)

HTTP requests with browser-like headers, correct cipher ordering, Google referrer
default. Based on hrequests library.

| Criterion | Score | Notes |
|-----------|-------|-------|
| Relevance to OwlBear | .30 | OwlBear uses httpx + trafilatura — already sufficient |
| Implementation effort | Low | httpx already supports custom headers |
| KISS/YAGNI | Fails YAGNI | No evidence httpx is insufficient |
| Architecture fit | Poor | Would add a parallel HTTP stack |

**Verdict: Skip.** httpx handles OwlBear's HTTP needs. No detection evasion required.

## 5. Summary Matrix

| Feature | Relevance | Effort | KISS/YAGNI | Fit | Verdict |
|---------|-----------|--------|------------|-----|---------|
| Human cursor | .30 | High | Fail | Low | **Skip** |
| Anti-detection | .25 | Medium | Fail | Med | **Skip** |
| Proxy rotation | .20 | Medium | Fail | Low | **Skip** |
| Result caching | .45 | Low | Border | Med | **Maybe** |
| Parallel exec | .35 | Low | Pass | Good | **Not from here** |
| Tiny profiles | .40 | Low | Border | Good | **Maybe** |
| Decorator config | .15 | N/A | Fail | Poor | **Skip** |
| Request scraping | .30 | Low | Fail | Poor | **Skip** |

## 6. Recommendation (.85 confidence)

**No features warrant immediate adoption.** Botasaurus is an impressive scraping
framework, but its feature set targets a fundamentally different use case (anti-detected
web scraping at scale) than OwlBear's (AI-assisted development with browser research).

Two patterns are worth filing for future reference:

1. **Two-layer caching** (raw HTML + extracted data) — useful if we ever need to
   re-process previously crawled pages with different extractors.
2. **Lightweight cookie profiles** — useful if OwlBear needs persistent auth sessions.

Both are low-effort (~50 LOC each) when/if the need arises. Neither is urgent.

## 7. Follow-up Tasks

No immediate implementation tasks warranted. Two backlog items for future reference:

```
kanban\kanban-md.exe create "Implement raw-HTML cache layer for WebCrawler" --priority someday --status backlog --tags "browser,phase-4" --body "Pattern: cache raw HTML by URL hash, separate from extracted content. Enables re-extraction without re-crawling. Inspired by botasaurus two-layer cache (see docs/research/botasaurus.md §4.4). AC:\n- [ ] Cache raw HTML to disk keyed by normalized URL hash\n- [ ] WebCrawler checks cache before fetching\n- [ ] Cache TTL configurable via CrawlConfig\n- [ ] Existing crawl_and_ingest pipeline unchanged"

kanban\kanban-md.exe create "Add cookie-persistence profiles to BrowserManager" --priority someday --status backlog --tags "browser,phase-4" --body "Pattern: save/restore cookies per named profile (~1KB each vs 100MB Chrome profiles). Inspired by botasaurus tiny_profile (see docs/research/botasaurus.md §4.6). AC:\n- [ ] BrowserConfig gains optional profile_name field\n- [ ] On context close, cookies saved to profiles/{name}.json\n- [ ] On context open, cookies restored if profile exists\n- [ ] Profile storage path configurable"
```
