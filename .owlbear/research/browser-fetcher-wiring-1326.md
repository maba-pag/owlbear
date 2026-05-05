# Browser Fetcher Wiring + RefreshOrchestrator Fix — Implementation Research

> **Owning task:** #1326 — P1-10: Browser fetcher wiring + RefreshOrchestrator fix
> **Date:** 2026-05-05 **Status:** Complete

## 1. Context and Question

Task #1326 requires wiring `ContentFetcher` and `GraphStore` into `RefreshOrchestrator`, adding `select_content_fetcher()` for fetch-method routing, and ensuring `_BrowserContentFetcher` doesn't leak URLs in errors. The question: what remains to implement?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L101–106, L335–341, L766 | 1.0 |
| 2 | `serve/knowledge/src/owlbear_knowledge/refresh.py` L52–90 | 1.0 |
| 3 | `tests/test_browser_fetcher_wiring_1325.py` — 13 tests, all GREEN | 1.0 |

## 3. Analysis

### Current State vs ACs

| AC | Implementation Location | Status |
|----|------------------------|--------|
| ContentFetcher injected into RefreshOrchestrator | `server.py:339` `content_fetcher=select_content_fetcher("http")` | ✅ |
| GraphStore injected for entity/edge cleanup | `server.py:341` `graph_store=gs` | ✅ |
| inter_doc_builder skipped (enrichment by agent workers) | Passed but safe-returns when `None`; design aligns with D7 | ✅ |
| refresh_source uses saved fetch_method from source manifest | `server.py:766` `select_content_fetcher(source.fetch_method)` | ✅ |
| Browser fetcher selected when fetch_method='browser' | `server.py:103-106` returns `_BrowserContentFetcher()` | ✅ |
| All #1325 tests pass green | 13/13 pass (verified 2026-05-05) | ✅ |

### Implementation Already Complete

All six ACs are satisfied by the current codebase. The builder work was completed during a prior session (likely alongside #1325's test-writing or immediately after). The `select_content_fetcher()` function, the lifespan wiring, and the URL-sanitized `_BrowserContentFetcher` placeholder are all in place.

## 4. Recommendation

**No implementation work required.** Advance task directly through pipeline.

Confidence: 0.95 — all tests green, code directly satisfies each AC.

Challenge: SKIPPED — no alternatives to evaluate; implementation is already complete.

## 5. Follow-up Tasks

None needed — implementation is complete and all tests pass.
