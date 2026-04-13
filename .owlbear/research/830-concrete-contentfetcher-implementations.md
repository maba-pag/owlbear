# Concrete ContentFetcher Implementations — Research

> **Owning task:** #830 — Concrete ContentFetcher implementations (BrowserContentFetcher + HttpxContentFetcher)
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

Task #830 is residual scope from superseded #762/#763 (P1-09/P1-10). The ContentFetcher protocol and pipeline injection are already shipped (#751 builder, #796 AC). Two concrete implementations remain unbuilt: BrowserContentFetcher (authenticated fetch via CDP) and HttpxContentFetcher (unauthenticated fetch). Both must satisfy `isinstance(obj, ContentFetcher)` and the `async fetch(url: str) -> str` contract.

Key questions: (1) Where should HttpxContentFetcher live? (2) What is BrowserContentFetcher's delegation chain? (3) Are dependencies ready?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| ContentFetcher protocol | `serve/knowledge/…/protocol.py:97-106` | .95 |
| RefreshOrchestrator._handle_authenticated_web | `serve/knowledge/…/refresh.py:219-270` | .95 |
| CDPConnectionManager | `serve/browser/…/cdp.py` (connect/disconnect/check_sso_redirect) | .90 |
| extract_content() | `serve/browser/…/extractor.py:46-73` | .90 |
| intake.read_url() | `serve/knowledge/…/intake.py:58-81` | .85 |
| browser package exports | `serve/browser/…/__init__.py` | .80 |
| knowledge pyproject.toml | httpx as optional dep under `[intake]` | .80 |
| browser pyproject.toml | No httpx dependency | .75 |
| #763 research doc | `.owlbear/research/763-contentfetcher-pipeline-injection.md` | .90 |
| #762 research doc | `.owlbear/research/762-contentfetcher-tests-scope.md` | .85 |
| #788 task body | status=review (blocked), extractor.py + cleaner.py exist | .85 |
| #796 task body | status=backlog, ContentFetcher protocol already shipped | .80 |

## 3. Analysis

### 3a. BrowserContentFetcher — Delegation Chain

CDPConnectionManager holds a Playwright `_browser` (private). BrowserContentFetcher wraps:

1. `cdp._browser.contexts[0].new_page()` — open tab
2. `page.goto(url)` — navigate
3. `cdp.check_sso_redirect(page)` — detect SSO/login redirects → raise `AuthenticationRequired`
4. `page.content()` — get HTML
5. `extract_content(html, url)` — trafilatura + cleaner fallback → markdown
6. `page.close()` — cleanup in `finally`

Same-package access to `_browser` is standard Python convention. No public API change to CDPConnectionManager needed.

Estimated: ~20 LOC.

### 3b. HttpxContentFetcher — Design

Wraps `httpx.AsyncClient.get()` → returns `response.text`. Mirrors `intake.read_url()` but shaped as ContentFetcher protocol.

Estimated: ~15 LOC.

### 3c. HttpxContentFetcher Location

| Option | Package | Pros | Cons |
|--------|---------|------|------|
| A: knowledge | `serve/knowledge/…/fetcher.py` | httpx already optional dep; near protocol.py; semantic fit (unauthenticated=knowledge concern) | Different package from BrowserContentFetcher |
| B: browser | `serve/browser/…/fetcher.py` | Co-located with BrowserContentFetcher | Adds httpx dep to browser; semantic mismatch (browser pkg = authenticated) |

**Recommendation: Option A.** HttpxContentFetcher in knowledge package. Confidence: .85.

### 3d. Dependency Readiness

| Dep | Status | Impact |
|-----|--------|--------|
| #788 (extractor/cleaner) | review (blocked on pytest-xdist) | Code exists and works. BrowserContentFetcher can import `extract_content` now |
| #796 (protocol + AUTHENTICATED_WEB) | backlog | Protocol already exists in code. Formal task completion shouldn't block |

Both building blocks exist in code. The task dependencies are for kanban sequencing; no code is actually missing.

### 3e. Test Strategy

| Class | Test pattern | Mock surface |
|-------|-------------|--------------|
| BrowserContentFetcher | isinstance check; delegation to CDP; SSO detection; extract_content call; page cleanup | CDPConnectionManager._browser (mock contexts/page), extract_content |
| HttpxContentFetcher | isinstance check; httpx delegation; non-2xx error; response.text return | httpx.AsyncClient |

Estimated: ~8-10 tests per class, ~16-20 total.

## 4. Recommendation

**Decompose into RED/GREEN TDD pair with HttpxContentFetcher in knowledge package.**

Confidence: .85.

- BrowserContentFetcher → `serve/browser/src/owlbear_browser/fetcher.py`
- HttpxContentFetcher → `serve/knowledge/src/owlbear_knowledge/fetcher.py`
- Both satisfy `ContentFetcher` protocol (`async fetch(url: str) -> str`)
- Page lifecycle managed per-fetch (open → navigate → extract → close)
- SSO detection integrated via `check_sso_redirect(page)`

Challenge: FALLBACK — challenger subagent not available. Self-challenge: Could both classes live in one package? Yes, but that either forces httpx into browser (unnecessary dep) or moves browser-specific CDP logic into knowledge (wrong domain). Separation matches existing package boundaries.

## 5. Follow-up Tasks

See task body for created task IDs.
