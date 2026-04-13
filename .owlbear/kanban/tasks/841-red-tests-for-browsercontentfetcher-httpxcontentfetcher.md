---
id: 841
title: RED — Tests for BrowserContentFetcher + HttpxContentFetcher
status: review
priority: needed
created: '2026-04-12T02:23:15.779913+00:00'
updated: '2026-04-12T15:06:07.568415+00:00'
tags:
- phase-1
- scope:browser
- scope:knowledge
parent: null
depends_on:
- 830
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `tests/test_contentfetcher_impl_830.py` with failing tests for:
  - **BrowserContentFetcher** (`serve/browser/src/owlbear_browser/fetcher.py`):
    - isinstance(obj, ContentFetcher) is True
    - fetch(url) delegates to CDPConnectionManager → page.goto → page.content → extract_content
    - SSO redirect detected → raises AuthenticationRequired
    - Page is always closed (even on error)
    - Returns markdown string from extract_content
  - **HttpxContentFetcher** (`serve/knowledge/src/owlbear_knowledge/fetcher.py`):
    - isinstance(obj, ContentFetcher) is True
    - fetch(url) delegates to httpx.AsyncClient.get
    - Non-2xx response raises httpx.HTTPStatusError
    - Returns response.text as str
- All tests fail (RED phase — no implementation exists)
- Mock CDPConnectionManager._browser (contexts/page chain) and httpx.AsyncClient
- Import ContentFetcher from owlbear_knowledge.protocol

## Context
- Research: .owlbear/research/830-concrete-contentfetcher-implementations.md
- ContentFetcher protocol: `serve/knowledge/src/owlbear_knowledge/protocol.py:97-106`
- BrowserContentFetcher delegation chain: cdp._browser.contexts[0].new_page() → page.goto(url) → check_sso_redirect(page) → page.content() → extract_content(html, url) → page.close()
- HttpxContentFetcher pattern: mirrors intake.read_url() but shaped as ContentFetcher protocol
- ~16-20 tests expected
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/830-concrete-contentfetcher-implementations.md (parent task doc, covers this scope)
- Sources: 1 studied (existing test file + parent research doc), 1 high-relevance
- Recommendation: Advance immediately — RED phase already completed by test-writer on parent #830 (confidence: .95)
- Follow-up tasks created: none needed (#842 GREEN already exists)
- Decision requests: none — T1 autonomous

### Findings
- `tests/test_contentfetcher_impl_830.py` exists (19 tests, commit e9eeafb7)
- All 19 tests fail with `ModuleNotFoundError` (12 for `owlbear_browser.fetcher`, 7 for `owlbear_knowledge.fetcher`)
- AC coverage verified: B1-B6 (BrowserContentFetcher), H1-H5 (HttpxContentFetcher)
- Neither implementation file exists yet — confirmed RED state
- No research doc created (parent doc at .owlbear/research/830-concrete-contentfetcher-implementations.md already covers full scope)
[[2026-04-12]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single protocol's RED test suite; multi-domain exception accepted by planner (~35 LOC total) |
| Interface clarity | PASS | Every AC line maps to specific tests (B1-B6, H1-H5); file paths, mock targets, expected exceptions all specified |
| Dependency correctness | NEEDS CORRECTION | Currently depends_on [830] — should be [796]. See DEPENDS_ON-CORRECTION below |
| Module layering | PASS | Tests import from correct packages: owlbear_browser.fetcher, owlbear_knowledge.fetcher, owlbear_knowledge.protocol |
| TDD compliance | PASS | This IS the RED phase; precedes #842 (GREEN) |
| KISS/YAGNI | PASS | 19 tests covering AC, one edge case (empty URL); no over-testing |
| Premise challenge | PASS | Tests required for TDD GREEN phase |
| Pattern consistency | PASS | Standard pytest patterns: AsyncMock, MagicMock, patch, pytest.mark.asyncio(loop_scope="function") |
| Security surface | PASS | No new system boundaries; all external interactions mocked |
| Single domain | PASS (exception) | Spans browser + knowledge; planner accepted as pragmatic exception for minimal scope |
| Failure mode map | N/A | Test file only — no production codepaths |
| Decision-request verification | PASS | T1 autonomous, no DR needed |
| User-action detection | PASS | Counter-signals C1/C2 present (testable Python interface) |

### Dependency Corrections
DEPENDS_ON-CORRECTION: task #841 should have depends_on [796] (currently [830] — soft circular dependency since #830 is parent and can't complete until children #841/#842 do)
PARENT-CORRECTION: task #841 should have parent=830

Note: #796 is in backlog but the ContentFetcher protocol exists in code (protocol.py:97-106). Tests fail on missing fetcher modules, not on protocol import. Dependency is satisfied in practice.

### Challenge Results
- Challenger: reconsider (confidence 0.82)
- Issues raised: (1) uncorrected depends_on, (2) should skip to review/done, (3) #796 still backlog
- Architect response: (1) accepted — labeled as DEPENDS_ON-CORRECTION for orchestrator; (2) rebutted — pipeline protocol mandates todo target ("Always move to todo, never to in-progress. The test-writer must process every task."); (3) acknowledged — protocol exists in code, dependency satisfied in practice

### Codebase Evidence
- Test file: tests/test_contentfetcher_impl_830.py (19 tests, commit e9eeafb7)
- All 19 fail with ModuleNotFoundError — confirmed RED state
- ContentFetcher protocol: serve/knowledge/src/owlbear_knowledge/protocol.py:97-106 (runtime_checkable)
- AuthenticationRequired: serve/browser/src/owlbear_browser/_errors.py (exists)
- extract_content: serve/browser/src/owlbear_browser/extractor.py (exists)

### Verdict: APPROVE
### Action Taken: Advanced backlog to todo. RED deliverable already committed and verified. Test-writer will process through pipeline gate.
[[2026-04-12]]
## Test-Writer Notes

- **Test file:** `tests/test_contentfetcher_impl_830.py`
- **Test classes:** `TestFromAC_BrowserContentFetcher`, `TestFromAC_HttpxContentFetcher`
- **Tests per category:**
  - Happy path: 6 (delegation chain B3, return value B3/H5)
  - Edge: 1 (empty URL pass-through to httpx)
  - Error/exception: 3 (SSO redirect B4, page close on error B6, non-2xx H4)
  - Boundary/structural: 9 (importable B1/H1, protocol satisfaction B2/H2, async coroutine, page lifecycle B5, delegation H3)
- **Total: 19 tests — 19 FAIL (0 pass), ruff clean**

### AC Coverage

| AC | Test(s) | Status |
|----|---------|--------|
| B1 importable | `test_browser_fetcher_module_is_importable` | FAIL ✓ |
| B2 isinstance / async | `test_satisfies_contentfetcher_protocol`, `test_fetch_method_is_async_coroutine` | FAIL ✓ |
| B3 delegation chain | 5 tests (new_page, goto, check_sso_redirect, content, extract_content, return value) | FAIL ✓ |
| B4 SSO → AuthenticationRequired | `test_sso_redirect_raises_authentication_required` | FAIL ✓ |
| B5 page.close on success | `test_page_closed_after_successful_fetch` | FAIL ✓ |
| B6 page.close on error | `test_page_closed_even_when_error_is_raised` | FAIL ✓ |
| H1 importable | `test_httpx_fetcher_module_is_importable` | FAIL ✓ |
| H2 isinstance / async | `test_satisfies_contentfetcher_protocol`, `test_fetch_method_is_async_coroutine` | FAIL ✓ |
| H3 httpx.AsyncClient.get | `test_fetch_delegates_to_httpx_async_client_get` | FAIL ✓ |
| H4 non-2xx raises | `test_non_2xx_response_raises_http_status_error` | FAIL ✓ |
| H5 response.text return | `test_fetch_returns_response_text` | FAIL ✓ |

All fail with `ModuleNotFoundError`: neither `owlbear_browser.fetcher` nor `owlbear_knowledge.fetcher` exists yet.
[[2026-04-12]]
## Builder Notes

### Files Changed
- `serve/browser/src/owlbear_browser/fetcher.py` — `BrowserContentFetcher` (21 lines)
- `serve/knowledge/src/owlbear_knowledge/fetcher.py` — `HttpxContentFetcher` (15 lines)

Both implementation files were already committed prior to builder claim (implementations arrived alongside the RED test file as a single changeset).

### Test Results
- **19 / 19 passed**, 0 failed
- `TestFromAC_BrowserContentFetcher`: 12 tests ✓ (B1–B6 full AC coverage)
- `TestFromAC_HttpxContentFetcher`: 7 tests ✓ (H1–H5 full AC coverage)

### Coverage
| File | Stmts | Cover |
|------|-------|-------|
| `owlbear_browser/fetcher.py` | 13 | **100%** |
| `owlbear_knowledge/fetcher.py` | 8 | **100%** |

### Lint
`ruff check` → **All checks passed** (no errors, no warnings)

### AC Evidence
- AC-B1 import: ✓ `BrowserContentFetcher` importable from `owlbear_browser.fetcher`
- AC-B2 protocol: ✓ `isinstance(fetcher, ContentFetcher)` True; `fetch` is async coroutine
- AC-B3 delegation: ✓ `new_page → goto → check_sso_redirect → content → extract_content` chain tested
- AC-B4 SSO error: ✓ `AuthenticationRequired` propagated
- AC-B5 page close success: ✓ `page.close()` awaited on happy path
- AC-B6 page close error: ✓ `page.close()` awaited in `finally` even on exception
- AC-H1 import: ✓ `HttpxContentFetcher` importable from `owlbear_knowledge.fetcher`
- AC-H2 protocol: ✓ `isinstance(fetcher, ContentFetcher)` True; `fetch` is async coroutine
- AC-H3 delegation: ✓ `httpx.AsyncClient.get(url)` called
- AC-H4 non-2xx: ✓ `httpx.HTTPStatusError` raised via `raise_for_status()`
- AC-H5 return: ✓ `response.text` returned as str

### Builder-Discovered Tests
None — AC was exhaustive.