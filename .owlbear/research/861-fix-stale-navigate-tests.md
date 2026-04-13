# Fix Stale Navigate Tests in #775/#850 — Research

> **Owning task:** #861 — Fix stale navigate tests in #775/#850 to supply mock fetcher
> **Date:** 2026-04-13  **Status:** Complete

## 1. Context and Question

Task #861 requires updating 2 stale tests that construct `AppContext` without a `fetcher` and call `navigate()`. After #852 wired `BrowserContentFetcher`, `navigate()` needs a fetcher to succeed. The tests test allowlist behavior — their intent is valid, they just need the fetcher prerequisite.

**Key question:** What is the current state of both tests, and what remains to be done?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Prior research | `.owlbear/research/856-red-browserfetcher-wiring-tests.md` §3b-3c | .95 |
| 2 | Test file (775) | `tests/test_mcp_browser_775.py` L198-211 | .95 |
| 3 | Test file (850) | `tests/test_mcp_browser_ctx_850.py` L127-134 | .95 |
| 4 | Server impl | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` L75-77 | .90 |
| 5 | Builder reject notes | #852 task body → Builder Notes + Test-Writer Notes | .85 |
| 6 | GREEN task | #857 AC5: fetcher=None → ToolError | .80 |

## 3. Analysis

### Current State (verified by running tests)

| AC | Test | Current Result | Reason |
|----|------|---------------|--------|
| AC1 | `test_mcp_browser_775.py::test_navigate_does_not_raise_for_allowlisted_domain` | **PASS — ALREADY FIXED** | mock_fetcher added during #852 reject cycle |
| AC2 | `test_mcp_browser_ctx_850.py::test_navigate_permits_url_when_ctx_allows_even_if_env_var_is_empty` | PASS (accidentally) | server.py returns `""` for fetcher=None; will break when #857 changes to `raise ToolError` |

### Server.py State

`navigate()` at L76: `if app_ctx.fetcher is None: return ""` — the builder reverted the `raise ToolError` after reject. #857 (GREEN, backlog) will re-implement the ToolError raise. When that happens, AC2's test will fail unless fixed first.

### #852 Test Regression

2 of 17 tests in `test_mcp_browser_fetcher_852.py` currently fail (`test_navigate_fetcher_none_raises_tool_error`, `test_navigate_fetcher_none_tool_error_describes_unavailability`) because server.py has `return ""` not `raise ToolError`. These are expected to pass after #857.

### Fix Approach for AC2

Identical pattern to the already-applied AC1 fix:
1. Add `AsyncMock` to imports in `test_mcp_browser_ctx_850.py`
2. Create `mock_fetcher = MagicMock(); mock_fetcher.fetch = AsyncMock(return_value="# Page")`
3. Pass `fetcher=mock_fetcher` to `AppContext` constructor (bypass `_make_app_ctx` helper — only 1 test needs it)

## 4. Recommendation

**Scope reduction:** AC1 is complete — only AC2 needs implementation. Estimated ≤10 LOC change in one file. (confidence: .95)

**Tier:** T1 — trivial test fix, no architectural decisions, proven pattern.

Challenge: skipped — trivial research, no recommendation to challenge.

## 5. Follow-up Tasks

None needed. #857 (GREEN, backlog) already covers the server.py `return ""` → `raise ToolError` change. Task #861 itself IS the follow-up from #856 research.
