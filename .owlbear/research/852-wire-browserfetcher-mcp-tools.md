# Wire BrowserContentFetcher into MCP Browser Server Tools

> **Owning task:** #852 — Wire BrowserContentFetcher into MCP browser server tools
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

The MCP browser server (`serve/mcp-browser/src/owlbear_mcp_browser/server.py`) has 6 stub tools. `navigate()` returns the raw URL; `read_text()` returns `""`. Task #852 wires `BrowserContentFetcher` (delivered by #842) into these tools so they perform real browser operations.

**Key design questions:**

1. How should `BrowserContentFetcher` be initialized — eager in lifespan, lazy on first call, or optional with fallback?
2. How does `read_text()` access the result of the most recent `navigate()` call?
3. What is the dependency chain — does #852 require #850 (ctx: Context refactor)?

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | MCP browser server | `serve/mcp-browser/…/server.py` (full) | .95 |
| 2 | BrowserContentFetcher | `serve/browser/…/fetcher.py` (full) | .95 |
| 3 | AuthenticationRequired | `serve/browser/…/_errors.py:14-15` | .90 |
| 4 | CDPConnectionManager | `serve/browser/…/cdp.py:43-90` (constructor + connect) | .90 |
| 5 | mcp-knowledge server | `serve/mcp-knowledge/…/server.py:260-285` (ctx pattern) | .85 |
| 6 | Prior research #838 | `.owlbear/research/838-wire-check-sso-redirect.md` | .90 |
| 7 | Task #850 body | kanban (ctx: Context refactor plan) | .85 |
| 8 | Task #849 body | kanban (RED tests for ctx refactor) | .80 |
| 9 | mcp-browser pyproject.toml | `serve/mcp-browser/pyproject.toml` — already depends on owlbear-browser | .80 |
| 10 | Fetcher test patterns | `tests/test_contentfetcher_impl_830.py:40-75` (mock helpers) | .85 |
| 11 | MCP browser test patterns | `tests/test_mcp_browser_775.py` (ctx mock style) | .85 |

## 3. Analysis

### 3a. Initialization Strategy

`BrowserContentFetcher.__init__(cdp)` only stores a reference — no I/O. `CDPConnectionManager.connect()` is async and requires a running Edge instance. Three options:

| Criterion | A: Eager + Optional | B: Lazy factory | C: Eager required |
|-----------|---------------------|-----------------|-------------------|
| Complexity | Low | Medium | Low |
| KISS alignment | .90 | .60 | .75 |
| Startup resilience | Graceful (None → ToolError) | Graceful (deferred) | Fails if no browser |
| Testability | Easy (inject mock/None) | Harder (factory mock) | Easy but brittle |
| Pattern match | mcp-knowledge `Optional` fields | No precedent | No precedent |
| Error clarity | Explicit "browser not available" | Hidden in first call | Startup crash |

**Recommendation: Option A** — `AppContext.fetcher: BrowserContentFetcher | None = None`. Lifespan attempts creation; if CDPConnectionManager is unavailable, fetcher stays `None`. `navigate()` returns `ToolError("Browser not available")`.

### 3b. State Management for read_text()

AC4 requires `read_text()` to return the most recent `navigate()` result. Options:

| Approach | Pros | Cons |
|----------|------|------|
| `AppContext.last_content: str` field | Simple, co-located with ctx | Mutable shared state |
| Store on fetcher instance | Encapsulated | Couples fetcher to MCP lifecycle |
| Module-level variable | No ctx needed | Anti-pattern, untestable |

**Recommendation:** `AppContext.last_content: str = ""`. `navigate()` updates it; `read_text()` reads it. Simplest, testable via mock ctx.

### 3c. Dependency Chain Analysis

Current `navigate()` reads `os.environ` directly — no `ctx` parameter. #850 adds `ctx: Context` to all 6 tools. #852 needs `ctx` to access AppContext.fetcher.

| Task | Status | Role | Required by #852? |
|------|--------|------|--------------------|
| #842 | review | BrowserContentFetcher impl | Yes (declared) |
| #849 | todo | RED: update tests for ctx | Yes (transitive) |
| #850 | todo | GREEN: add ctx: Context to tools | **Yes (missing dep)** |

**Finding:** #852 `depends_on` must include #850. Without `ctx: Context` in tool signatures, tools cannot access `AppContext.fetcher`. Current deps list only [842].

### 3d. Error Handling Pattern

The existing PermissionError → ToolError pattern in `navigate()` is the exact model:

```python
# Existing pattern (server.py L73-76)
try:
    allowlist.check(url)
except PermissionError as exc:
    raise ToolError(str(exc)) from exc
```

AuthenticationRequired follows identically:

```python
try:
    content = await fetcher.fetch(url)
except AuthenticationRequired as exc:
    raise ToolError(str(exc)) from exc
```

Both `ToolError` and `AuthenticationRequired` are already importable (source #1, #3).

### 3e. Testing Approach

Established mock pattern from mcp-knowledge/kanban tests:

1. `_make_app_ctx(...)` → `AppContext(allowlist=..., fetcher=mock_fetcher, last_content="")`
2. `_make_mcp_ctx(app_ctx)` → `MagicMock(request_context=MagicMock(lifespan_context=app_ctx))`
3. Call tool functions directly: `await navigate(ctx, url="...")`
4. Assert: `mock_fetcher.fetch.assert_awaited_once_with(url)`
5. Assert: `ctx.request_context.lifespan_context.last_content == expected`

Test cases needed: success path, AuthenticationRequired path, fetcher-is-None path, read_text after navigate, read_text without navigate.

## 4. Recommendation

**Approach (confidence: .85):**

1. Add `fetcher: BrowserContentFetcher | None = None` and `last_content: str = ""` to `AppContext`
2. In `app_lifespan()`, create CDPConnectionManager + BrowserContentFetcher (guarded by try/except)
3. `navigate(ctx, url)`: allowlist check → `fetcher.fetch(url)` → store in `last_content` → return content
4. `read_text(ctx)`: return `ctx.request_context.lifespan_context.last_content`
5. Catch `AuthenticationRequired` → `ToolError` in `navigate()`
6. Add `depends_on: [842, 850]` to task #852

Challenge: FALLBACK — no challenger agent available. Self-challenge: "Should fetcher creation be the MCP server's responsibility?" Yes — the server owns the lifespan, and existing servers (mcp-knowledge) create their service objects in lifespan. No alternative owner exists in the architecture.

## 5. Follow-up Tasks

1. **RED: Tests for BrowserContentFetcher wiring in MCP browser tools** — test navigate() delegation, AuthenticationRequired → ToolError, read_text() state, fetcher-None guard. Depends on [849, 850].
2. **GREEN: Wire BrowserContentFetcher into MCP browser server** — implement AC1-AC4. Depends on RED task above + [842, 850].
3. **Dependency correction: Add #850 to #852 depends_on** — #852 cannot proceed without ctx: Context in tool signatures.
