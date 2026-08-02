---
id: 872
title: 'RED: Tests for BrowserContentFetcher accepting Playwright BrowserContext'
status: archived
priority: medium
created: '2026-04-14T01:51:21.630834+00:00'
updated: '2026-04-14T17:07:22.106919+00:00'
tags:
- pivot
- phase-1
- scope:browser
- type:test
- tdd-red
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

Extracted from #869 AC4 during architecture review. The fetcher interface change (CDP → Playwright BrowserContext) is a separate concern from the launcher implementation (#868/#869) with a different test surface and breaking-change impact.

Current `BrowserContentFetcher.__init__` accepts a CDP manager object. Refactored fetcher accepts a Playwright `BrowserContext` directly. SSO redirect detection (`check_sso_redirect`) is removed — the SSO extension handles auth transparently in a persistent context.

Supersedes `test_contentfetcher_impl_830.py` AC-B3 (CDP delegation chain) and AC-B4 (SSO redirect detection). AC-B1, B2, B5, B6 behavior is preserved and re-verified with the new interface.

## Acceptance Criteria

1. Test file `tests/test_fetcher_playwright_{this_task_id}.py`
2. Tests for `BrowserContentFetcher.__init__(context)`:
   - Constructor accepts a mock `BrowserContext` object (mock provides `new_page` as `AsyncMock`)
3. Tests for `fetch(url)` happy path:
   - Opens new page via `context.new_page()`
   - Navigates with `page.goto(url, wait_until="domcontentloaded")`
   - Calls `page.content()` to get HTML
   - Passes `(html, url)` to `extract_content()`
   - Returns the string from `extract_content()`
4. Tests for `fetch(url)` — no SSO redirect check:
   - Verify `check_sso_redirect` is NOT called during `fetch()` — SSO extension handles auth transparently in persistent context
5. Tests for page lifecycle:
   - `page.close()` awaited after successful fetch
   - `page.close()` awaited even when an exception occurs during fetch
6. Tests for `ContentFetcher` protocol compliance:
   - `isinstance(BrowserContentFetcher(mock_context), ContentFetcher)` is True (imports from `owlbear_knowledge.protocol`)
   - `BrowserContentFetcher.fetch` is an async coroutine function
7. All tests FAIL at RED phase — current `BrowserContentFetcher.__init__` expects CDP object, not `BrowserContext`; `fetch()` calls `cdp._browser.contexts[0].new_page()` and `check_sso_redirect(page)`, which won't match the new mock setup
8. ruff clean

## Notes

- Mock `BrowserContext` shape: `context.new_page = AsyncMock(return_value=mock_page)` where `mock_page` has `goto`, `content`, `close` as `AsyncMock`s
- Existing `test_contentfetcher_impl_830.py` is NOT modified — old tests continue testing the old interface until the GREEN task updates them
- See `serve/browser/src/owlbear_browser/fetcher.py` for current implementation
- See `serve/knowledge/src/owlbear_knowledge/protocol.py` for `ContentFetcher` protocol definition
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | RED tests only for fetcher interface change (CDP → Playwright BrowserContext) |
| Interface clarity | PASS | AC specifies exact mock shapes, method calls (`context.new_page()`, `page.goto(url, wait_until="domcontentloaded")`), and assertion targets |
| Dependency correctness | PASS | No dependencies needed — RED tests run against existing `BrowserContentFetcher` with new mock shape; confirms #873 (GREEN) correctly depends on this |
| Module layering | PASS | Tests import from `owlbear_browser.fetcher` and `owlbear_knowledge.protocol` — standard cross-package test imports |
| TDD compliance | PASS | This IS the RED phase task; corresponding GREEN task #873 exists in backlog |
| KISS/YAGNI | PASS | Minimal scope — 8 AC items map directly to testable assertions, no speculative coverage |
| Premise challenge | PASS | Pivot from CDP to Playwright BrowserContext is a legitimate architectural change; tests must exist before GREEN |
| Pattern consistency | PASS | Follows `test_{feature}_{task_id}.py` naming; mock patterns consistent with `test_contentfetcher_impl_830.py`; `patch("owlbear_browser.fetcher.extract_content", ...)` pattern established |
| Security surface | PASS | Test file only — no new system boundaries |
| Single domain | PASS | Entirely `scope:browser` |

### Codebase Evidence

- Current `BrowserContentFetcher` at `serve/browser/src/owlbear_browser/fetcher.py` (21 lines): `__init__(self, cdp: object)`, fetch uses `self._cdp._browser.contexts[0].new_page()` and `self._cdp.check_sso_redirect(page)`
- `ContentFetcher` protocol at `serve/knowledge/src/owlbear_knowledge/protocol.py`: `@runtime_checkable`, requires `async def fetch(self, url: str) -> str`
- `extract_content` at `serve/browser/src/owlbear_browser/extractor.py`: `extract_content(html: str, url: str | None = None) -> str`
- Existing `test_contentfetcher_impl_830.py` tests CDP interface — no overlap with Playwright BrowserContext tests
- No other test files reference BrowserContext — zero duplicate coverage

### RED Failure Mechanism Verified

AC7 correctly identifies why tests fail at RED: constructor accepts any `object`, but `fetch()` calls `self._cdp._browser.contexts[0].new_page()` — when `_cdp` is a mock BrowserContext (with `new_page` directly on it), the CDP path fails. AC3's `wait_until="domcontentloaded"` assertion also fails since current code uses `page.goto(url)` without `wait_until`.

### Challenge Results

- Challenger: FALLBACK — challenger agent not available; codebase exploration confirmed zero duplicate coverage and no conflicting changes
- Architect response: accepted — no issues found

### Non-impl Tags

`type:test` and `tdd-red` already present — pass-through tags verified.

### Verdict: APPROVE

### Action Taken: Advanced #872 backlog → todo. AC is precise, architecturally sound, and codebase-verified. Ready for test-writer

[[2026-04-14]]

## Test-Writer Notes

**Test file:** `tests/test_fetcher_playwright_872.py`
**Class:** `TestFromAC_BrowserContentFetcherPlaywright`
**Commit:** `4871878f`

### Test counts by category

| Category | Count |
|----------|-------|
| Happy path (AC3) | 5 |
| Error path (AC5 exception) | 1 |
| Boundary / no-op (AC4 SSO absent) | 1 |
| Constructor / signature (AC2) | 1 |
| Page lifecycle — success (AC5) | 1 |
| Protocol compliance (AC6) | 2 |
| **Total** | **11** |

### Failure confirmation

`pytest tests/test_fetcher_playwright_872.py` → **11 FAILED, 0 PASSED**

| Failure mechanism | Tests affected |
|-------------------|---------------|
| `AttributeError: 'BrowserContentFetcher' object has no attribute '_context'` | 1 (AC2 constructor) |
| `TypeError: object MagicMock can't be used in 'await' expression` (cdp._browser.contexts[0].new_page() path) | 8 (AC3/AC4/AC5 async) |
| `AssertionError: assert 'context' in mappingproxy({'self': ..., 'cdp': ...})` | 2 (AC6 signature) |

### AC coverage table

| AC item | Test(s) |
|---------|---------|
| AC2 — constructor accepts BrowserContext | `test_constructor_stores_context_not_cdp` |
| AC3 — context.new_page() | `test_fetch_opens_new_page_via_context` |
| AC3 — goto(url, wait_until="domcontentloaded") | `test_fetch_navigates_with_domcontentloaded` |
| AC3 — page.content() | `test_fetch_calls_page_content` |
| AC3 — extract_content(html, url) | `test_fetch_passes_html_and_url_to_extract_content` |
| AC3 — returns extract_content result | `test_fetch_returns_extract_content_result` |
| AC4 — check_sso_redirect NOT called | `test_fetch_does_not_call_check_sso_redirect` |
| AC5 — page.close() on success | `test_fetch_closes_page_after_successful_fetch` |
| AC5 — page.close() on exception | `test_fetch_closes_page_on_exception` |
| AC6 — ContentFetcher protocol | `test_satisfies_contentfetcher_protocol` |
| AC6 — async coroutine | `test_fetch_is_async_coroutine_function` |

ruff: clean

[[2026-04-14]]

## Builder Notes

- `type:test` + `tdd-red` task — non-implementation pass-through, no code changes needed.
- Test file: `tests/test_fetcher_playwright_872.py` — already written by test-writer (commit `4871878f`).
- RED phase confirmed: **11 FAILED, 0 PASSED** against current `BrowserContentFetcher` (CDP interface).
- ruff: **clean** (verified by builder).
- GREEN implementation is in dependent task #873 (backlog).

### Failure summary (for review)

| Root cause | Tests affected |
|------------|---------------|
| Constructor param `cdp` not `context`; `_context` attribute missing | 2 (AC2/AC6 signature) |
| `fetch()` calls `self._cdp._browser.contexts[0].new_page()` → `TypeError: object MagicMock can't be used in 'await'` | 9 (AC3/AC4/AC5) |
[[2026-04-14]]

## Review Evidence

### Test Results

- pytest: 31 passed, 0 failed (11 `test_fetcher_playwright_872.py` + 20 `test_contentfetcher_impl_830.py`)
- Note: tests now pass because #873 GREEN was implemented while #872 was in review — this is the intended TDD outcome. AC7 RED failure (11/11) was verified by test-writer and builder at time of writing against the old CDP implementation.

### Lint: clean

### Coverage: owlbear_browser.fetcher: 100%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC2 — constructor accepts BrowserContext | `test_constructor_stores_context_not_cdp` | Yes — `assert fetcher._context is ctx` (identity check); fails if param named `cdp` | COVERED |
| AC3 — context.new_page() | `test_fetch_opens_new_page_via_context` | Yes — `assert_awaited_once()` fails if impl routes through CDP chain | COVERED |
| AC3 — goto(url, wait_until="domcontentloaded") | `test_fetch_navigates_with_domcontentloaded` | Yes — `assert_awaited_once_with(_TEST_URL, wait_until="domcontentloaded")` is argument-exact | COVERED |
| AC3 — page.content() | `test_fetch_calls_page_content` | Yes — `assert_awaited_once()` fails if not called | COVERED |
| AC3 — extract_content(html, url) | `test_fetch_passes_html_and_url_to_extract_content` | Yes — `assert_called_once_with(_SAMPLE_HTML, _TEST_URL)` is argument-exact | COVERED |
| AC3 — returns string | `test_fetch_returns_extract_content_result` | Yes — `assert result == _SAMPLE_MARKDOWN` | COVERED |
| AC4 — check_sso_redirect NOT called | `test_fetch_does_not_call_check_sso_redirect` | Yes — explicit AsyncMock setup + `assert_not_called()` catches any call | COVERED |
| AC5 — page.close() on success | `test_fetch_closes_page_after_successful_fetch` | Yes — `assert_awaited_once()` fails if never closed or not awaited | COVERED |
| AC5 — page.close() on exception | `test_fetch_closes_page_on_exception` | Yes — `side_effect=RuntimeError` + `pytest.raises` + `assert_awaited_once()` enforces try/finally pattern | COVERED |
| AC6 — ContentFetcher protocol | `test_satisfies_contentfetcher_protocol` | Yes — `isinstance(fetcher, ContentFetcher)` + "context" in params | COVERED |
| AC6 — async coroutine | `test_fetch_is_async_coroutine_function` | Yes — `inspect.iscoroutinefunction` + "context" in params | COVERED |
| AC7 — all tests FAIL at RED | Confirmed 11/11 failed by test-writer + builder before GREEN | Structurally sound: CDP chain `self._cdp._browser.contexts[0].new_page()` → TypeError on BrowserContext mock | COVERED |
| AC8 — ruff clean | ruff exit 0 | — | COVERED |

#### Security Review

- No issues. Test file only; no new system boundaries.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 11 `TestFromAC_BrowserContentFetcherPlaywright` tests | No changes — builder declared pass-through | PRESERVED |

#### Test Quality

- **Assertion specificity: STRONG** — no lazy assertions found. All assertions use `assert_awaited_once_with(...)`, `assert_called_once_with(...)`, exact equality, or identity (`is`) checks.
- **Negative/error-path coverage: STRONG** — AC4 (no SSO) and AC5 exception path both covered with separate dedicated tests.
- **Mutation robustness: STRONG** — removing `wait_until="domcontentloaded"`, swapping `_context` for `_cdp`, or omitting `finally` each breaks a distinct test.
- **Test independence: SOUND** — fresh mocks per test via factory functions; no shared mutable state.
- **Test names: DESCRIPTIVE** — all 11 names signal intent, parameters, and scenario clearly.

#### Data Safety

- No data safety concerns. Test file only.

#### Builder Process Quality

- Single `## Builder Notes` section. No retries. CLEAN.

### Verdict

Confidence: .96 → PASS

Process note: #873 GREEN entered review while #872 was still in review (dependency ordering irregularity). This does not invalidate #872's deliverable — the RED artifacts are correct and complete. Flag for orchestrator awareness.
[[2026-04-14]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | TDD RED task — test file only; no application code modified |
| 2 | Module docstrings | No | N/A | Only `tests/test_fetcher_playwright_872.py` created; `fetcher.py` changes belong to #873 GREEN |
| 3 | External attribution | No | N/A | Standard `unittest.mock` / pytest patterns; no external repo inspiration |
| 4 | CLI changes | No | N/A | No CLI touched |
| 5 | Research doc | No | N/A | Task extracted from #869 arch review; no separate research doc produced |

### Files Updated

- None

### Scratch Files Cleaned

- None found (no `.owlbear/scratch/872-*` files)
[[2026-04-14]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 — test file exists | `tests/test_fetcher_playwright_872.py` (238 lines) | PASS |
| AC2 — constructor accepts BrowserContext | `test_constructor_stores_context_not_cdp` asserts `fetcher._context is ctx` | PASS |
| AC3 — happy path (5 tests) | `test_fetch_opens_new_page_via_context`, `test_fetch_navigates_with_domcontentloaded`, `test_fetch_calls_page_content`, `test_fetch_passes_html_and_url_to_extract_content`, `test_fetch_returns_extract_content_result` | PASS |
| AC4 — no SSO redirect | `test_fetch_does_not_call_check_sso_redirect` with `assert_not_called()` | PASS |
| AC5 — page lifecycle | `test_fetch_closes_page_after_successful_fetch`, `test_fetch_closes_page_on_exception` (RuntimeError side_effect + pytest.raises) | PASS |
| AC6 — protocol compliance | `test_satisfies_contentfetcher_protocol` (isinstance + param check), `test_fetch_is_async_coroutine_function` | PASS |
| AC7 — RED failure | Test-writer confirmed 11/11 FAILED; builder corroborated. Tests now pass due to #873 GREEN — intended TDD outcome | PASS |
| AC8 — ruff clean | ruff clean on task file; 1 E501 in `engine.py` is out of scope | PASS |

### Test Results

- pytest (task): 11 passed, 0 failed
- pytest (full suite): 4183 passed, 318 failed, 8 skipped — no failures in `test_fetcher_playwright_872.py`; 318 failures are pre-existing cross-task regressions (ImportError `owlbear_browser.cdp`, Pydantic schema changes, missing files, etc.)
- ruff: 1 violation in `serve/kanban/src/owlbear_kanban/engine.py:472` (E501) — out of task scope

### Architect Quality: 5/5

AC is exemplary — 8 items with exact method signatures (`context.new_page()`, `page.goto(url, wait_until="domcontentloaded")`), mock shapes specified, assertion targets explicit, RED failure mechanism documented in AC7. No builder improvisation needed.

### Deduction Breakdown

- All 8 AC lines have specific evidence: 0
- Lint violations in task scope: 0
- AC quality 5/5: 0
- Reviewer evidence present and detailed (.96 PASS): 0
- Full-suite failures in task scope: 0

### Confidence: 1.00

### Action: archive
