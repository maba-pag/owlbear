---
id: 873
title: 'GREEN: Refactor BrowserContentFetcher to accept Playwright BrowserContext'
status: archived
priority: medium
created: '2026-04-14T01:51:43.508330+00:00'
updated: '2026-04-15T09:13:57.823876+00:00'
tags:
- pivot
- phase-1
- scope:browser
- tdd-green
parent: 751
depends_on:
- 872
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

Extracted from #869 AC4 during architecture review. Refactors `BrowserContentFetcher` to accept a Playwright `BrowserContext` instead of a CDP manager, completing the CDP → Playwright pivot for the fetcher layer.

## Acceptance Criteria

1. `serve/browser/src/owlbear_browser/fetcher.py` refactored:
   - `BrowserContentFetcher.__init__(self, context: BrowserContext)` — accepts Playwright `BrowserContext` (type annotation uses `playwright.async_api.BrowserContext`)
   - `fetch(url)` uses `context.new_page()` → `page.goto(url, wait_until="domcontentloaded")` → `page.content()` → `extract_content(html, url)` → returns markdown string; `page.close()` in `finally` block
   - No `check_sso_redirect` call — SSO extension handles auth transparently in persistent context
   - Still satisfies `owlbear_knowledge.protocol.ContentFetcher` protocol (`async fetch(url: str) -> str`)
2. `tests/test_contentfetcher_impl_830.py` updated:
   - Helpers `_make_mock_cdp` / `_make_mock_page` replaced with BrowserContext-based mocks
   - AC-B1 (import): unchanged
   - AC-B2 (protocol compliance): constructor updated to `BrowserContentFetcher(mock_context)`
   - AC-B3 (delegation chain): tests updated to verify `context.new_page()` → `page.goto(url, wait_until="domcontentloaded")` → `page.content()` → `extract_content(html, url)` (no CDP internals, no `check_sso_redirect`)
   - AC-B4 (SSO redirect): removed or replaced — `check_sso_redirect` no longer called by fetcher
   - AC-B5 (page close success): constructor updated for BrowserContext
   - AC-B6 (page close error): constructor updated for BrowserContext, error trigger changed (no longer `check_sso_redirect` side-effect — use e.g. `page.goto` raising)
3. All #872 RED tests pass
4. ruff clean

## Notes

- `test_mcp_browser_lifespan_857.py` also constructs `BrowserContentFetcher(cdp)` — NOT updated here. Lifespan wiring to use PlaywrightLauncher + BrowserContext is a separate task
- Old modules (`launcher.py`, `edge_launcher.py`, `cdp.py`) NOT modified — cleanup is separate
- Module docstring should be updated from "authenticated fetch via CDP" to "authenticated fetch via Playwright"
[[2026-04-14]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One class refactored (`BrowserContentFetcher`), associated tests in `test_contentfetcher_impl_830.py` updated — same logical change |
| Interface clarity | PASS | Constructor signature (`BrowserContext`), method chain (`new_page → goto → content → extract_content`), protocol compliance, and `finally` cleanup all precisely specified |
| Dependency correctness | PASS | Depends on #872 (RED tests). #872 is in backlog — correct ordering, no missing deps. `playwright>=1.40` already declared in `serve/browser/pyproject.toml` |
| Module layering | PASS | `fetcher.py` in `owlbear_browser` uses `playwright.async_api.BrowserContext` (declared dep) and `owlbear_browser.extractor.extract_content` (same package). No upward imports |
| TDD compliance | PASS | #872 is the RED counterpart creating `test_fetcher_playwright_872.py` |
| KISS/YAGNI | PASS | Minimal refactoring — swaps CDP private-attribute access (`cdp._browser.contexts[0]`) for clean BrowserContext injection, removes SSO redirect (pushed to extension layer), adds `wait_until="domcontentloaded"` |
| Premise challenge | PASS | Part of deliberate CDP → Playwright pivot (tagged `pivot`). Current pattern uses `cdp._browser.contexts[0]` which is fragile private-attribute access |
| Pattern consistency | PASS | Satisfies `ContentFetcher` protocol (`protocol.py:98-106`). Uses standard Playwright API patterns |
| Security surface | PASS | No new system boundaries. URL comes from existing callers, SSO handled by extension layer |
| Single domain | PASS | Entirely within `scope:browser` |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| `context.new_page()` | Playwright error | `playwright.Error` | Propagated (no page to close) | Fetch fails |
| `page.goto()` | Navigation error | `playwright.Error` | `page.close()` in `finally` | Fetch fails, page cleaned up |
| `page.content()` | Content retrieval error | `playwright.Error` | `page.close()` in `finally` | Fetch fails, page cleaned up |
| `extract_content()` | Extraction error | `Exception` | `page.close()` in `finally` | Fetch fails, page cleaned up |

### Codebase Evidence

- Current `fetcher.py`: 22 LOC, uses `cdp._browser.contexts[0].new_page()` + `cdp.check_sso_redirect(page)` — confirmed at `serve/browser/src/owlbear_browser/fetcher.py`
- `ContentFetcher` protocol: `async def fetch(self, url: str) -> str` at `serve/knowledge/src/owlbear_knowledge/protocol.py:98-106`
- `extract_content(html, url)` confirmed at `serve/browser/src/owlbear_browser/extractor.py:47`
- `test_mcp_browser_lifespan_857.py` uses `BrowserContentFetcher(cdp)` — correctly scoped OUT of this task per Notes
- No existing `BrowserContext` type annotation usage — this is the first module in the pivot to accept it directly

### Challenge Results

- Challenger: FALLBACK — challenger agent not available in agent list
- Architect response: self-challenge performed; no concerns found

### Verdict: APPROVE

### Action Taken: Advanced #873 to todo. AC is precise and verifiable, architecture sound, all failure modes handled by `finally` block, scope correctly bounded (excludes lifespan wiring and old module cleanup)

[[2026-04-14]]

## Test-Writer Notes

**Test file:** `tests/test_fetcher_playwright_872.py` (already present from #872 RED pass-through)

**Class:** `TestFromAC_BrowserContentFetcherPlaywright`

| Category | Tests | Count |
|----------|-------|-------|
| Happy path — delegation chain | `test_fetch_opens_new_page_via_context`, `test_fetch_navigates_with_domcontentloaded`, `test_fetch_calls_page_content`, `test_fetch_passes_html_and_url_to_extract_content`, `test_fetch_returns_extract_content_result` | 5 |
| Error path — no SSO redirect | `test_fetch_does_not_call_check_sso_redirect` | 1 |
| Boundary — page lifecycle | `test_fetch_closes_page_after_successful_fetch`, `test_fetch_closes_page_on_exception` | 2 |
| Constructor / protocol | `test_constructor_stores_context_not_cdp`, `test_satisfies_contentfetcher_protocol`, `test_fetch_is_async_coroutine_function` | 3 |
| **Total** | | **11** |

**Pytest result:** 0 passed, 11 failed — RED confirmed.

- `test_constructor_stores_context_not_cdp` → `AttributeError: 'BrowserContentFetcher' has no attribute '_context'`
- All async delegation tests → `TypeError: object MagicMock can't be used in 'await' expression` (current code calls `self._cdp._browser.contexts[0].new_page()`)
- Protocol tests → fail on `assert "context" in params` (param is named `cdp`)

**Ruff:** clean

**AC coverage:**

| AC line | Tests |
|---------|-------|
| AC1 `__init__(context: BrowserContext)` | `test_constructor_stores_context_not_cdp`, `test_satisfies_contentfetcher_protocol` |
| AC1 `context.new_page()` → `page.goto(url, wait_until="domcontentloaded")` | `test_fetch_opens_new_page_via_context`, `test_fetch_navigates_with_domcontentloaded` |
| AC1 `page.content()` → `extract_content(html, url)` → return str | `test_fetch_calls_page_content`, `test_fetch_passes_html_and_url_to_extract_content`, `test_fetch_returns_extract_content_result` |
| AC1 no `check_sso_redirect` | `test_fetch_does_not_call_check_sso_redirect` |
| AC1 `page.close()` in `finally` | `test_fetch_closes_page_after_successful_fetch`, `test_fetch_closes_page_on_exception` |
| AC2 `test_contentfetcher_impl_830.py` updates | Builder deliverable — no failing test required (test-of-test not applicable) |
| AC3 `#872 RED tests pass` | covered by all 11 above |

Note: `test_contentfetcher_impl_830.py` update (AC2) is a builder-only deliverable; the new interface is fully covered by the 11 tests above.

[[2026-04-14]]

## Builder Notes

### Files Changed

- `serve/browser/src/owlbear_browser/fetcher.py` — refactored: `__init__(context: BrowserContext)` stores `_context`; `fetch()` uses `context.new_page()` → `page.goto(url, wait_until="domcontentloaded")` → `page.content()` → `extract_content(html, url)`; removed `check_sso_redirect`; `BrowserContext` moved to `TYPE_CHECKING` block (TC002); docstring updated.
- `tests/test_contentfetcher_impl_830.py` — builder deliverable (AC2): replaced `_make_mock_cdp` with `_make_mock_context`; removed `_SSO_URL` constant; updated `TestFromAC_BrowserContentFetcher` — all 9 tests converted to BrowserContext mocks; `test_fetch_calls_check_sso_redirect_with_page` → `test_fetch_does_not_call_check_sso_redirect`; removed SSO redirect test (AC-B4); `test_page_closed_even_when_error_is_raised` now triggers via `page.goto` raising `RuntimeError`.

### RED Verification

`tests/test_fetcher_playwright_872.py`: **11 failed, 0 passed** before implementation — RED confirmed.

### Test Results

- `tests/test_fetcher_playwright_872.py`: **11 passed** (TestFromAC_BrowserContentFetcherPlaywright)
- `tests/test_contentfetcher_impl_830.py`: **20 passed** (TestFromAC_BrowserContentFetcher ×9, TestFromAC_HttpxContentFetcher ×9, TestBuilderDiscovered ×2)
- **Total: 31 passed, 0 failed**

### Lint Status

ruff: **clean** (0 violations)

### Coverage

Not measured (targeted GREEN phase — coverage deferred to full suite run)

### Evidence

All 11 TestFromAC_BrowserContentFetcherPlaywright tests green. test_contentfetcher_impl_830.py updated as builder deliverable per AC2 — kept HttpxContentFetcher and TestBuilderDiscovered tests intact. Surgical change: only 2 files touched, both within AC scope.
[[2026-04-14]]

## Review Evidence

### Test Results

- pytest: **31 passed, 0 failed** (11 × TestFromAC_BrowserContentFetcherPlaywright in `test_fetcher_playwright_872.py`; 20 × `test_contentfetcher_impl_830.py` — 9 BrowserContentFetcher, 9 HttpxContentFetcher, 2 TestBuilderDiscovered)

### Lint

- ruff: **clean** (0 violations)

### Coverage

- `owlbear_browser.fetcher`: **100%**

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: `__init__(context)` stores `_context` | `test_constructor_stores_context_not_cdp` | Yes — `assert fetcher._context is ctx` | COVERED |
| AC1: `context.new_page()` called | `test_fetch_opens_new_page_via_context` | Yes — `ctx.new_page.assert_awaited_once()` | COVERED |
| AC1: `page.goto(url, wait_until="domcontentloaded")` | `test_fetch_navigates_with_domcontentloaded` | Yes — `assert_awaited_once_with(_TEST_URL, wait_until="domcontentloaded")` | COVERED |
| AC1: `page.content()` called | `test_fetch_calls_page_content` | Yes — `page.content.assert_awaited_once()` | COVERED |
| AC1: `extract_content(html, url)` invoked with correct args | `test_fetch_passes_html_and_url_to_extract_content` | Yes — `mock_extract.assert_called_once_with(_SAMPLE_HTML, _TEST_URL)` | COVERED |
| AC1: returns extract_content result | `test_fetch_returns_extract_content_result` | Yes — `assert result == _SAMPLE_MARKDOWN` | COVERED |
| AC1: no `check_sso_redirect` | `test_fetch_does_not_call_check_sso_redirect` | Yes — `ctx.check_sso_redirect.assert_not_called()` | COVERED |
| AC1: `page.close()` in `finally` (success) | `test_fetch_closes_page_after_successful_fetch` | Yes — `page.close.assert_awaited_once()` | COVERED |
| AC1: `page.close()` in `finally` (exception) | `test_fetch_closes_page_on_exception` | Yes — raises, then `page.close.assert_awaited_once()` | COVERED |
| AC1: satisfies ContentFetcher protocol | `test_satisfies_contentfetcher_protocol` | Yes — `isinstance` + `"context" in params` | COVERED |
| AC1: fetch is async coroutine | `test_fetch_is_async_coroutine_function` | Yes — `inspect.iscoroutinefunction` | COVERED |
| AC2: `test_contentfetcher_impl_830.py` updated | builder deliverable (no RED counterpart) | N/A | COVERED |
| AC3: #872 RED tests pass | 11/11 green | all above | COVERED |
| AC4: ruff clean | ruff exit 0 | quality-runner | COVERED |

#### 5.1 Security Review

- No hardcoded secrets, tokens, or credentials
- No injection vectors (`url` forwarded directly to Playwright — same trust boundary as prior implementation)
- No path traversal, deserialization, or eval/exec usage
- `BrowserContext` import scoped under `TYPE_CHECKING` — correct pattern, no runtime exposure
- No secret leakage in error paths (exceptions propagated without augmentation)
- **No issues**

#### 5.2 Test Integrity — TestFromAC Comparison

`test_fetcher_playwright_872.py` — builder did not touch this file. All 11 original RED tests intact and passing.

`test_contentfetcher_impl_830.py` — builder-authorized AC2 migration. Changes assessed:

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `_make_mock_cdp` helper | Replaced with `_make_mock_context` (BrowserContext mock) | PRESERVED — interface migration per AC2 |
| `test_fetch_calls_check_sso_redirect_with_page` | Replaced with `test_fetch_does_not_call_check_sso_redirect` | PRESERVED — AC2 explicitly authorizes SSO direction inversion |
| `test_page_closed_even_when_error_is_raised` | Error trigger changed from `check_sso_redirect` side-effect to `page.goto` raising | PRESERVED — AC2 authorizes this; trigger is now cleaner and more direct |
| All other 7 AC-B tests | Constructor updated to use `BrowserContentFetcher(ctx)` | PRESERVED — same assertions, updated for new interface |

No WEAKENED or REMOVED findings.

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | `assert_awaited_once_with(url, wait_until=...)`, `assert_called_once_with(html, url)`, `assert result == _SAMPLE_MARKDOWN` — no lazy `assert result` patterns |
| Negative/error-path coverage | STRONG | `test_fetch_closes_page_on_exception` via `page.goto` raising; `test_fetch_does_not_call_check_sso_redirect` as negative assertion |
| Manual mutation reasoning | STRONG | Removing `wait_until="domcontentloaded"` fails `test_fetch_navigates_with_domcontentloaded`; removing `finally: page.close()` fails both close tests; renaming `_context` fails constructor test |
| Test independence | STRONG | Each test builds its own mock fixtures; no shared mutable state |
| Descriptive names | STRONG | All names are precise and map to AC lines |

#### 5.4 Data Safety

- No LLM output persistence in scope
- No shared mutable state (`page` is locally scoped per `fetch()` call; `_context` is injected at construction and read-only)
- `finally` block ensures page lifecycle atomicity
- **No issues**

#### 5.5 Implementation-Aware Test Gap Analysis

`fetcher.py` is 25 LOC with one method. All branches tested:

- `new_page()` → `goto()` → `content()` → `extract_content()` happy path: tested ✓
- `page.goto()` raises → `finally` closes page: tested ✓
- `page.content()` / `extract_content()` raising: not individually tested — but `finally` is unconditional; one error-path demonstration per `finally` is sufficient. Not flagged.
- `new_page()` raising: untested — page not yet created so `finally` can't close it; Playwright infrastructure failure class. Trivial defensive path. Not flagged.

**No untested paths of significance.**

#### 5.6 Necessity Check

Not applicable — refactor, no new dependencies introduced.

#### 5.7 Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL

- `BrowserContext` under `TYPE_CHECKING` with `from __future__ import annotations` is the idiomatic pattern for lazy Playwright imports. No flag.
- Module docstring updated from "CDP" to "Playwright" — correct per AC Notes.

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: `__init__(self, context: BrowserContext)` | `fetcher.py:16-17` | `test_constructor_stores_context_not_cdp` | PASS |
| AC1: `context.new_page()` → `goto(wait_until="domcontentloaded")` → `content()` → `extract_content()` | `fetcher.py:20-24` | 5 delegation-chain tests | PASS |
| AC1: No `check_sso_redirect` | absent from `fetcher.py` | `test_fetch_does_not_call_check_sso_redirect` | PASS |
| AC1: `page.close()` in `finally` | `fetcher.py:26` | `test_fetch_closes_page_after_successful_fetch`, `test_fetch_closes_page_on_exception` | PASS |
| AC1: Satisfies `ContentFetcher` protocol | `fetch(self, url: str) -> str` is async | `test_satisfies_contentfetcher_protocol` | PASS |
| AC2: `test_contentfetcher_impl_830.py` updated | file read — BrowserContext mocks, no CDP helpers, SSO inversion | builder deliverable | PASS |
| AC3: #872 RED tests pass | pytest: 11 passed | TestFromAC_BrowserContentFetcherPlaywright | PASS |
| AC4: ruff clean | ruff exit 0 | quality-runner | PASS |

### Confidence: .97

### Verdict: PASS

[[2026-04-14]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `copilot-instructions.md` has no CDP/fetcher references — no table entry needed |
| 2 | Module docstrings | Yes | Updated | `fetcher.py`: module docstring updated to "authenticated fetch via Playwright" (builder); class docstring accurate. `test_contentfetcher_impl_830.py`: stale "All 18 tests FAIL at RED phase" corrected to "All 20 tests pass: 11 BrowserContentFetcher, 7 HttpxContentFetcher, 2 TestBuilderDiscovered" |
| 3 | External attribution | No | N/A | Internal refactor — no external patterns used |
| 4 | CLI changes | No | N/A | No CLI surface touched |
| 5 | Research doc | No | N/A | No research doc for #873; extracted from #869 architecture review |

### Files Updated

- `tests/test_contentfetcher_impl_830.py` — stale RED-phase docstring updated (`addc694b`)
- `serve/browser/src/owlbear_browser/fetcher.py` — builder's uncommitted primary deliverable committed (`383c0822`); builder had never committed AC1 impl despite review passing

### Builder Commit Gap

Builder Notes listed both files as changed but only `test_contentfetcher_impl_830.py` was staged pending. `fetcher.py` was uncommitted in working tree. Doc-writer picked up both to preserve pipeline integrity. Implementation was fully reviewed (`.97` confidence, PASS verdict) before being committed here.

### Scratch Files

None found for `873-*`.
[[2026-04-15]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: `__init__(self, context: BrowserContext)` | `fetcher.py:16-17` — constructor stores `_context` | PASS |
| AC1: delegation chain `new_page→goto→content→extract_content` | `fetcher.py:20-25` — verified directly | PASS |
| AC1: No `check_sso_redirect` | absent from `fetcher.py` | PASS |
| AC1: `page.close()` in `finally` | `fetcher.py:26` | PASS |
| AC1: Satisfies `ContentFetcher` protocol | `fetch(self, url: str) -> str` async method | PASS |
| AC2: `test_contentfetcher_impl_830.py` updated | file verified — BrowserContext mocks, no CDP helpers, SSO inversion | PASS |
| AC3: #872 RED tests pass | 11/11 passed (not in failure list) | PASS |
| AC4: ruff clean | 3 violations all outside task scope | PASS |

### Test Results

- pytest: 4386 passed, 191 failed, 8 skipped — **0 failures in task scope** (failures are pre-existing in kanban/analysis/bookmark/lint-guard domains)
- ruff: 3 errors, all outside scope (engine.py E501, test_refresh_sharepoint_879.py RUF002/UP024)

### Reviewer Evidence

Present and thorough (.97 PASS). Security review, test integrity analysis, implementation-aware gap analysis, mutation reasoning. Trusted for code-level detail.

### Architect Quality: 5/5

AC was precise and complete: specific constructor signature with type annotation, detailed delegation chain with `wait_until` kwarg, explicit negative requirement (no SSO redirect), clear scope boundaries (lifespan wiring and old module cleanup excluded), per-test update requirements. No builder improvisation needed.

### Deduction Breakdown

- AC lines without evidence: 0 → -.00
- Lint in scope: clean → -.00
- AC quality ≤ 3: no (5/5) → -.00
- Missing reviewer section: no → -.00
- Full-suite failures in task scope: 0 → -.00

### Confidence: 1.00

### Action: archive

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 383c0822 | feat | fetcher.py | #873 |
| addc694b | docs | test_contentfetcher_impl_830.py | #873 |
| 43b976c2 | chore | kanban task 873 | #873 |
