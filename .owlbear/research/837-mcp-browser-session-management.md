# MCP Browser Session Management — Implementation Research

> **Owning task:** #837 — Implement browser session management in mcp-browser AppContext
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

Task #837 replaces stub tool bodies in mcp-browser with live Playwright-backed implementations. The `owlbear_browser` package already provides `CDPConnectionManager`, `EdgeCDPLauncher`, `BrowserContentFetcher`, and `extract_content`. The question: how should `AppContext` + `app_lifespan` wire these into the MCP server, and what page lifecycle model should tools use?

**Prerequisite:** Task #836 (add `ctx: Context` to all 6 tools) is still at `todo`. Tools cannot access `AppContext` fields until #836 is complete. This research assumes #836 is done.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | mcp-browser server.py | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | 1.0 |
| 2 | CDPConnectionManager | `serve/browser/src/owlbear_browser/cdp.py` | .95 |
| 3 | EdgeCDPLauncher | `serve/browser/src/owlbear_browser/edge_launcher.py` | .90 |
| 4 | BrowserContentFetcher | `serve/browser/src/owlbear_browser/fetcher.py` | .90 |
| 5 | extract_content | `serve/browser/src/owlbear_browser/extractor.py` | .85 |
| 6 | mcp-knowledge lifespan (ref) | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` | .85 |
| 7 | mcp-memory lifespan (ref) | `serve/mcp-memory/src/owlbear_mcp_memory/server.py` | .85 |
| 8 | Prior research #771 §3f | `.owlbear/research/771-mcp-browser-server.md` | .95 |
| 9 | Prior research #836 | `.owlbear/research/836-mcp-browser-ctx-refactor.md` | .90 |
| 10 | Playwright Page API | playwright.dev/python/docs/api/class-page | .80 |
| 11 | Existing CDP tests | `tests/test_edge_launcher_cdp_755.py` | .80 |
| 12 | BrowserContentFetcher tests | `tests/test_contentfetcher_impl_830.py` | .85 |

## 3. Analysis

### 3a. Connection Strategy

| Criterion | A: Attach to running Edge | B: Launch Edge subprocess | C: Attach-or-skip |
|-----------|---------------------------|---------------------------|---------------------|
| SSO cookies available | Yes — user's session | No — fresh profile | Yes (if Edge running) |
| Server startup cost | Low (CDP connect) | High (subprocess + connect) | Low |
| Graceful degradation | Fails if no Edge | Always works | Tools return ToolError |
| KISS alignment | High | Medium | Highest |
| Subprocess cleanup | None needed | Must terminate on exit | None needed |
| Existing pattern | CDPConnectionManager | EdgeCDPLauncher | CDPConnectionManager |

**Recommendation: Option C** (confidence: .85). Lifespan attempts CDP connection; if no Edge is running, `AppContext.cdp = None`. Tools check and raise `ToolError("No browser session — start Edge with CDP enabled")`. This matches the "fail gracefully" AC and avoids subprocess management in the MCP server.

### 3b. Page Lifecycle Model

| Criterion | Shared page | Page-per-call |
|-----------|-------------|---------------|
| Interactive workflow | Natural — navigate, then click/type | Awkward — each call loses state |
| State isolation | State persists across calls | Clean state each call |
| Memory | 1 page | N pages (closed after each) |
| AC alignment | Matches "navigate() uses Page.goto()" | Doesn't match click/type/select flow |
| read_text/snapshot | Read from navigated page | Must re-navigate |

**Recommendation: Shared page** (confidence: .90). The AC describes a sequential workflow: navigate → click → type → read_text. A shared page obtained from `context.new_page()` in the lifespan, stored in `AppContext.page`, supports this naturally. If the page crashes or closes, tools raise ToolError.

### 3c. AppContext Changes

```python
@dataclass
class AppContext:
    allowlist: DomainAllowlist
    cdp: CDPConnectionManager | None = None
    page: Any = None  # Playwright Page (optional dep)
```

### 3d. Lifespan Pattern

```python
@asynccontextmanager
async def app_lifespan(server: FastMCP):
    _apply_tool_exclusions(server)
    # Allowlist (existing)
    allowlist = DomainAllowlist(...)
    # CDP connection (new)
    port = int(os.environ.get("BROWSER_CDP_PORT", "9222"))
    cdp = CDPConnectionManager(port=port)
    page = None
    try:
        await cdp.connect()
        page = await cdp._browser.contexts[0].new_page()
    except Exception:  # No Edge running — degrade gracefully
        cdp = None
    try:
        yield AppContext(allowlist=allowlist, cdp=cdp, page=page)
    finally:
        if page is not None:
            await page.close()
        if cdp is not None:
            await cdp.disconnect()
```

### 3e. Tool Implementation Mapping

| Tool | Playwright API | Error handling |
|------|---------------|----------------|
| navigate(url) | `page.goto(url)` | Allowlist check first, then ToolError on no page |
| click(selector) | `page.locator(selector).click()` | ToolError on no page |
| type(selector, text) | `page.locator(selector).fill(text)` | ToolError on no page |
| select(selector, value) | `page.locator(selector).select_option(value)` | ToolError on no page |
| read_text() | `extract_content(await page.content(), page.url)` | ToolError on no page |
| snapshot() | `page.locator("body").aria_snapshot()` | ToolError on no page; needs Playwright ≥1.49 |

Note: `click`, `type`, `select` use the locator-based API (recommended by Playwright over deprecated `page.click(selector)` etc.).

### 3f. Snapshot API

`locator.aria_snapshot()` (available since Playwright v1.49) returns a structured ARIA tree as a string. `page.aria_snapshot()` (v1.59 convenience alias) is equivalent to `page.locator('body').aria_snapshot()`. We use the locator form for compatibility with current Playwright releases. The `owlbear-browser` pyproject.toml has been bumped to `playwright>=1.49`.

### 3g. Test Strategy

Tests should mock at the CDP boundary (same pattern as `test_contentfetcher_impl_830.py`):
- Mock `CDPConnectionManager` with a mock `_browser.contexts[0].new_page()` chain
- Mock `Page` with async methods: `goto`, `content`, `aria_snapshot`, `locator().click()`, etc.
- Test graceful degradation: lifespan with failed CDP connection yields `cdp=None`
- Test each tool raises ToolError when `page is None`
- Test navigate checks allowlist before page.goto

### 3h. Dependency Chain

```
#836 (ctx refactor) ─┐
  #849 (RED)         ├── must complete before #837
  #850 (GREEN)       ┘
#837 (session mgmt) ── decomposes into:
  RED: tests for AppContext fields, lifespan with CDP, tool implementations
  GREEN: implement AppContext, lifespan, tool bodies
```

## 4. Recommendation (confidence: .85)

**Decompose #837 into atomic TDD tasks** with dependency on #836 completion. Use Option C (attach-or-skip) for connection strategy and shared-page model for tool interaction.

Key decisions:
1. `CDPConnectionManager` in AppContext, `Page` as shared state — matches AC and interactive workflow
2. Graceful degradation on missing Edge — tools raise ToolError, server still starts
3. `page.aria_snapshot()` for snapshot tool — bump playwright dep to ≥1.59
4. Locator-based API for click/type/select — Playwright best practice
5. `extract_content(html, url)` for read_text — reuses existing extractor

**Risk:** Shared page model means a crashed page breaks all subsequent tools until server restart. Mitigation: tool-level page health checks (check `page.is_closed()` before use).

Challenge: FALLBACK — no controversial recommendation. Architecture follows existing patterns.

**Tier: T1 — Autonomous.** Implementation within approved Phase 2 architecture. No new capabilities beyond what #751 already authorized.

## 5. Follow-up Tasks

1. RED: Write failing tests for AppContext CDP/Page fields, lifespan connection lifecycle, and all 6 tool implementations
2. GREEN: Implement AppContext changes, lifespan CDP wiring, and tool bodies
3. Bump playwright dep in serve/browser/pyproject.toml to >=1.59.0 for aria_snapshot support
