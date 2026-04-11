# ContentFetcher Protocol + Pipeline Injection — Research

> **Owning task:** #763 — P1-10: Impl — ContentFetcher protocol + pipeline injection
> **Date:** 2026-04-11  **Status:** Complete

## 1. Context and Question

Task #763 is a GREEN-phase implementation task (pair of #762 RED) under parent #751. It specifies four deliverables: (1) ContentFetcher protocol in knowledge package, (2) BrowserContentFetcher in browser package, (3) HttpxContentFetcher preserved, (4) Pipeline constructor accepts ContentFetcher.

Key question: What remains unimplemented, given that the #751 builder already shipped some of this scope, and how does #763 relate to the #775 decomposition tree?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| ContentFetcher protocol | `serve/knowledge/src/owlbear_knowledge/protocol.py:98-106` | .95 |
| IngestPipeline constructor | `serve/knowledge/src/owlbear_knowledge/ingest.py:43-63` | .90 |
| RefreshOrchestrator constructor | `serve/knowledge/src/owlbear_knowledge/refresh.py:56-68` | .95 |
| `_handle_authenticated_web` | `serve/knowledge/src/owlbear_knowledge/refresh.py:219-270` | .90 |
| #751 builder notes | Task #751 body — Builder Notes section | .95 |
| #788 refined AC | Task #788 body — Architecture Review | .90 |
| #796 AC | Task #796 body | .85 |
| #759 architect review | Task #759 body — supersession evidence | .85 |
| #761 researcher notes | Task #761 body — supersession evidence | .85 |
| Browser package exports | `serve/browser/src/owlbear_browser/__init__.py` | .80 |
| CDPConnectionManager | `serve/browser/src/owlbear_browser/cdp.py` | .85 |

## 3. Analysis

### 3a. Scope vs Implementation State

| #763 Deliverable | Already Implemented? | By Whom | Evidence |
|------------------|---------------------|---------|----------|
| ContentFetcher protocol | YES | #751 builder (commit `2dfae28b`) | `protocol.py:98-106` — `@runtime_checkable`, `async fetch(url)->str` |
| Pipeline injection | YES | #751 builder (commit `2dfae28b`) | `refresh.py:65` — `content_fetcher: object \| None = None` |
| BrowserContentFetcher | NO | — | Not in codebase. No class wrapping CDP+extractor as ContentFetcher |
| HttpxContentFetcher | NO | — | Not in codebase. `intake.read_url()` uses httpx but not via protocol |

**Result: 2 of 4 deliverables already shipped. 2 remain.**

### 3b. Overlap with #775 Decomposition

| #763 Deliverable | #775 Subtask Coverage | Gap? |
|------------------|-----------------------|------|
| ContentFetcher protocol | #796 AC: "protocol.py defines ContentFetcher" — also done | None |
| Pipeline injection | #796 AC: "RefreshOrchestrator accepts content_fetcher" — also done | None |
| BrowserContentFetcher | #788 builds extractor.py + cleaner.py (building blocks), but NO fetcher class | **YES** |
| HttpxContentFetcher | Not in any #775 subtask | **YES** |

### 3c. Supersession Pattern

Tasks #756–#761 (P1-05 through P1-08, siblings of #762/#763) have all been confirmed superseded by the #775 decomposition, per architect and researcher reviews:

| Old task | Superseded by | Confirming review |
|----------|---------------|-------------------|
| #756 (P1-05 HTML cleaner tests) | #783 | #756 researcher |
| #759 (P1-06 HTML cleaner impl) | #788 + #829 | #759 architect |
| #760 (P1-07 extractor tests) | #783 | #760 researcher |
| #761 (P1-08 extractor impl) | #788 | #761 researcher |

#762/#763 (P1-09/P1-10) follow the same pattern: superseded for delivered scope, with residual scope needing a new task.

### 3d. Concrete Fetcher Implementations — What's Needed

**BrowserContentFetcher** (~30-50 LOC in `serve/browser/src/owlbear_browser/fetcher.py`):
- Wraps CDPConnectionManager + content extractor from #788
- Navigates to URL, gets page HTML, extracts content via `extract_content()`
- Returns cleaned markdown string
- Depends on: #788 (extractor/cleaner must exist first)

**HttpxContentFetcher** (~15-25 LOC in knowledge package):
- Wraps `httpx.AsyncClient.get()` in ContentFetcher protocol
- Replaces direct `intake.read_url()` for protocol-based fetching
- No new dependencies — httpx already optional dep

### 3e. Dependency Gaps in #763

| Gap | Issue |
|-----|-------|
| Missing `depends_on: [762]` | GREEN task has no dependency on its RED partner |
| Missing dep on #788 | BrowserContentFetcher needs extractor.py which #788 creates |
| RED partner #762 still in research | No test file exists for P1-09 tests |

### 3f. Protocol Return Type Discrepancy

#762 body says "ContentFetcher Protocol definition (async fetch → cleaned text + metadata)" but the implemented protocol returns `str` only (no metadata). The `str` return is correct per the implemented protocol and #796 architect-corrected AC. #762 description is stale.

## 4. Recommendation

**Close #763 (and #762) as superseded. Create one new task for concrete fetcher implementations.** Confidence: .88.

Rationale:
1. 2 of 4 deliverables already shipped under #751 builder
2. Sibling tasks #756–#761 all confirmed superseded by #775 subtree
3. RED partner #762 has no test file and is still in research — GREEN cannot proceed
4. Remaining unique scope (BrowserContentFetcher, HttpxContentFetcher) is better placed as a #775 subtask with correct dependencies on #788 and #796

The existing #775 tree has proper dependency chains, architect-approved AC, and TDD pairing. Bolting new work onto #762/#763 (which lack deps and have stale descriptions) would fight the established decomposition.

Challenge: FALLBACK — challenger subagent not available. Self-challenge: could #763 be narrowed and kept? Yes, but it would require rewriting AC, adding dependencies, and correcting #762's stale protocol description — equivalent effort to a new task, without the clean lineage.

## 5. Follow-up Tasks

- New task needed: "Concrete ContentFetcher implementations (BrowserContentFetcher + HttpxContentFetcher)" under #775, depends on #788 + #796, at `research` status
- #762 should also be closed as superseded (same reasoning)
