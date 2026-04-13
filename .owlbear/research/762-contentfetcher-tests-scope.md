# ContentFetcher Protocol Tests — Scope Analysis

> **Owning task:** #762 — P1-09: Tests — ContentFetcher protocol + pipeline injection
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #762 specifies RED-phase tests for four items: (1) ContentFetcher Protocol definition, (2) BrowserContentFetcher delegation, (3) HttpxContentFetcher for unauthenticated sources, (4) pipeline injection. This research validates which items require new tests vs. which are already covered.

Key question: How much of #762's scope is already tested, and what is the genuine novel RED-phase work?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `serve/knowledge/src/owlbear_knowledge/protocol.py` L97-106 | Internal — ContentFetcher impl | .95 |
| `tests/test_authenticated_content_pipeline_751.py` AC4 class | Internal — 5 existing protocol tests | .95 |
| `tests/test_authenticated_content_pipeline_775.py` SC3/SC4 class | Internal — 8 existing injection tests | .95 |
| `serve/knowledge/src/owlbear_knowledge/refresh.py` L56-68, L218-268 | Internal — pipeline injection + handler | .90 |
| `serve/browser/src/owlbear_browser/` (cdp.py, edge_launcher.py) | Internal — browser building blocks | .85 |
| `serve/knowledge/src/owlbear_knowledge/intake.py` L60-85 (read_url) | Internal — httpx-based URL fetch | .85 |
| Task #792 (AUTHENTICATED_WEB + ContentFetcher tests, parent #775) | Internal — parallel task | .90 |

## 3. Analysis

### 3a. Overlap Matrix — #762 Scope Items vs Existing Tests

| #762 Scope Item | Existing Coverage | Tests/Location | Novel? |
|----------------|-------------------|----------------|--------|
| 1. ContentFetcher Protocol definition | 5 tests (import, runtime_checkable, fetch method, url param, isinstance) | `test_*_751.py` `TestFromAC_AuthenticatedContentProtocol` | NO |
| 2. BrowserContentFetcher delegates to CDP + extractor | 0 tests. No class exists. | N/A | **YES** |
| 3. HttpxContentFetcher for unauthenticated sources | 0 tests. No class exists. `intake.read_url()` uses httpx but isn't ContentFetcher-shaped. | N/A | **YES** |
| 4. Pipeline accepts ContentFetcher via injection | 8 tests (kwarg, storage, dispatch, call delegation, RefreshResult, empty URLs, error handling) | `test_*_775.py` `TestFromAC_AuthWebRefreshHandler` | NO |

**Result:** 2 of 4 items (50%) are already tested. Items 1 and 4 would produce GREEN-on-RED tests.

### 3b. Parallel Task Overlap — #762 vs #792

| Dimension | #762 (P1-09) | #792 |
|-----------|-------------|------|
| Parent | #751 | #775 |
| Status | research | todo |
| Scope | Protocol + BrowserContentFetcher + HttpxContentFetcher + injection | SourceType.AUTHENTICATED_WEB + ContentFetcher protocol + _handle_authenticated_web dispatch |
| Novel parts | BrowserContentFetcher, HttpxContentFetcher | None (all already implemented + tested per architect review) |
| Risk | Duplicate tests for items 1,4 | Entire scope already tested in #751/#775 |

### 3c. BrowserContentFetcher — Expected Interface

Based on browser package contents (`CDPConnectionManager`, `EdgeCDPLauncher`) and ContentFetcher protocol:

- **Location:** `serve/browser/src/owlbear_browser/` (new module, e.g. `fetcher.py`)
- **Satisfies:** `ContentFetcher` protocol (`async fetch(url: str) -> str`)
- **Delegates to:** `CDPConnectionManager` for page navigation, content extraction (trafilatura or similar) for HTML→text
- **Test pattern:** Mock CDPConnectionManager + mock extractor, verify delegation chain

### 3d. HttpxContentFetcher — Expected Interface

Based on existing `intake.read_url()` and ContentFetcher protocol:

- **Location:** `serve/knowledge/src/owlbear_knowledge/` (new module, e.g. `fetcher.py`)
- **Satisfies:** `ContentFetcher` protocol (`async fetch(url: str) -> str`)
- **Uses:** httpx `AsyncClient.get()` — same pattern as `intake.read_url()`
- **Test pattern:** Mock httpx, verify URL fetching returns text content

## 4. Recommendation

**Narrow #762 scope to items 2 and 3 only.** Confidence: .85.

The test-writer should create `tests/test_contentfetcher_protocol_762.py` with:
- `TestFromAC_BrowserContentFetcher` — isinstance check, delegation to CDPConnectionManager, delegation to extractor, error handling
- `TestFromAC_HttpxContentFetcher` — isinstance check, httpx delegation, error on non-2xx
- Skip items 1 and 4 — already covered by #751 and #775 test files

Task #792 should also be flagged as potentially redundant — its entire scope is pre-existing.

**Tier:** T1 — scope clarification for a test task. No new capabilities or architecture.

Challenge: FALLBACK — challenger subagent not available in agent roster. Self-challenge: Could items 1+4 still warrant tests in #762's file for co-location? No — DRY principle applies to tests. The existing coverage in #751/#775 is comprehensive (13 tests total) and mutation-resistant per the #751 review evidence.

## 5. Follow-up Tasks

- Narrow #762 AC to BrowserContentFetcher + HttpxContentFetcher only (flagged in task body)
- Flag #792 as potentially redundant (all scope already tested)
