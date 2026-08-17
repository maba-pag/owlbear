# RED: Tests for BrowserContentFetcher Wiring — Research

> **Owning task:** #856 — RED: Tests for BrowserContentFetcher wiring in MCP browser navigate/read_text
> **Date:** 2026-04-13  **Status:** Complete

## 1. Context and Question

Task #856 requests RED-phase tests for wiring `BrowserContentFetcher` into `navigate()` and `read_text()` tools. However, the TDD cycle was already executed on parent task #852 — test-writer wrote 17 tests in `tests/test_mcp_browser_fetcher_852.py`, and the builder implemented the code in `server.py`.

**Key question:** Is #856 redundant, and what remains to be done?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Existing test file | `tests/test_mcp_browser_fetcher_852.py` (17 tests, 330 lines) | .95 |
| 2 | Current server.py | `serve/mcp-browser/.../server.py` (fetcher wiring live) | .95 |
| 3 | Builder REJECT notes | #852 task body → Builder Notes | .90 |
| 4 | Failing #775 test | `tests/test_mcp_browser_775.py:195` | .90 |
| 5 | Failing #850 test | `tests/test_mcp_browser_ctx_850.py:126` | .90 |

## 3. Analysis

### 3a. Test File Already Exists

`tests/test_mcp_browser_fetcher_852.py` covers all 6 AC items of #856:

| AC | Tests | Status |
|----|-------|--------|
| AC1: `_make_app_ctx` / `_make_mcp_ctx` helpers | ✓ Both present, extended with `fetcher`/`last_content` params | GREEN |
| AC2: navigate success → calls fetch, returns markdown, updates last_content | ✓ 3 tests | GREEN |
| AC3: AuthenticationRequired → ToolError, fetcher=None → ToolError | ✓ 4 tests | GREEN |
| AC4: read_text returns last_content / empty string | ✓ 3 tests | GREEN |
| AC5: Tests FAIL at RED phase | ✗ All 17 PASS — implementation already shipped | N/A |
| AC6: ruff clean | ✓ Clean | GREEN |

### 3b. Cross-File Test Conflict

The builder on #852 was REJECTED because of contradictory test contracts across files:

| File | Test | Constructs AppContext | Expects |
|------|------|-----------------------|---------|
| `test_mcp_browser_775.py` | `test_navigate_does_not_raise_for_allowlisted_domain` | `AppContext(allowlist=...)` — no fetcher | No error |
| `test_mcp_browser_ctx_850.py` | `test_navigate_permits_url_when_ctx_allows_even_if_env_var_is_empty` | `_make_app_ctx(["domain"])` — no fetcher | No error |
| `test_mcp_browser_fetcher_852.py` | `test_navigate_fetcher_none_raises_tool_error` | `AppContext(fetcher=None)` | ToolError |

The #852 behavior is correct — `navigate()` SHOULD raise `ToolError` when fetcher is None. The two older tests assumed navigate() would succeed without a fetcher because they were written before the fetcher wiring existed. They need updating to supply a mock fetcher.

### 3c. Fix Pattern

Both stale tests need the same fix — add a mock fetcher to their AppContext construction:

```python
mock_fetcher = MagicMock()
mock_fetcher.fetch = AsyncMock(return_value="# Page")
ctx = _make_mcp_ctx(
    AppContext(
        allowlist=DomainAllowlist(domains=[...]),
        fetcher=mock_fetcher,
    )
)
```

Their intent (allowlist behavior) remains valid — they just need the fetcher prerequisite.

## 4. Recommendation

**Task #856 is effectively complete** — all test deliverables exist and cover the AC. The only remaining work is fixing 2 stale tests in sibling files that conflict with the new fetcher-None guard. (confidence: .90)

**Tier:** T1 — autonomous test fix, no architectural decisions needed.

Challenge: FALLBACK — trivial finding, no recommendation to challenge. Self-challenge: "Should the fetcher-None guard be removed to avoid breaking old tests?" No — the guard is correct behavior per #852 AC5 and prevents silent failures when CDP is unavailable.

## 5. Follow-up Tasks

1. **Fix stale navigate tests in #775 and #850 test files** — update 2 tests to supply mock fetcher so they test allowlist behavior (their intent) without hitting fetcher-None guard. Affected files: `tests/test_mcp_browser_775.py`, `tests/test_mcp_browser_ctx_850.py`.
