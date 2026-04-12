# Wire check_sso_redirect() into Browser URL-Fetch Pipeline — Research

> **Owning task:** #838 — Wire check_sso_redirect() into browser URL-fetch pipeline
> **Date:** 2026-04-12  **Status:** Complete

## 1. Context and Question

Task #838 (child of #751) requires wiring `CDPConnectionManager.check_sso_redirect(page)` into the browser fetch→extract pipeline so that SSO redirects are detected before extraction, with `AuthenticationRequired` propagating to callers including MCP tools.

Key question: Is #838 already covered by sibling task #830 and its subtasks, or does it represent unique scope?

## 2. Sources Studied

| Source | Location | Relevance |
|--------|----------|-----------|
| check_sso_redirect impl | `serve/browser/…/cdp.py:116-128` | .95 |
| AuthenticationRequired | `serve/browser/…/_errors.py:14-15` | .90 |
| ContentFetcher protocol | `serve/knowledge/…/protocol.py:97-106` | .90 |
| BrowserContentFetcher tests (#830) | `tests/test_contentfetcher_impl_830.py` | .95 |
| #830 research doc | `.owlbear/research/830-concrete-contentfetcher-implementations.md` | .95 |
| SSO detection unit tests | `tests/test_edge_launcher_cdp_755.py:244-303` | .85 |
| MCP browser server | `serve/mcp-browser/…/server.py` (full file) | .90 |
| #830 task body (planning notes) | kanban board | .90 |
| #842 task (GREEN impl) | kanban board, status=in-progress | .85 |
| extractor.py | `serve/browser/…/extractor.py` | .80 |

## 3. Analysis

### 3a. AC-by-AC Overlap Assessment

| #838 AC | Requirement | Covered by #830? | Evidence |
|---------|-------------|-------------------|----------|
| AC1 | Call `check_sso_redirect(page)` before `extract()` | **Yes** | #830 research §3a step 3; test `test_fetch_calls_check_sso_redirect_with_page` |
| AC2 | `AuthenticationRequired` aborts extraction | **Yes** | test `test_sso_redirect_raises_authentication_required` + `page_closed_even_when_error_is_raised` |
| AC3 | MCP `navigate`/`read_text` surface the error | **No** | MCP server is stubs; no task covers wiring BrowserContentFetcher into MCP tools |
| AC4 | Integration test with stubbed IdP URL | **Yes** | tests in `test_contentfetcher_impl_830.py:194-243` cover exact scenario |

### 3b. MCP Server Gap Analysis

The MCP browser server (`server.py`, ~100 LOC) has 6 tool stubs. None delegates to `BrowserContentFetcher` or any CDP code. Wiring requires:

1. Injecting a `BrowserContentFetcher` instance into `AppContext` (via lifespan)
2. `navigate()` calling `fetcher.fetch(url)` and catching `AuthenticationRequired` → `ToolError`
3. `read_text()` returning the last fetched content

This is distinct scope from #830 (which builds the fetcher class itself) and should be a separate task.

### 3c. Dependency Chain

```
#788 (extractor) ─┐
#796 (protocol)  ─┼─► #842 (GREEN: BrowserContentFetcher impl) ─► [NEW: MCP wiring]
#841 (RED tests) ─┘
```

The MCP wiring task depends on #842 completing first — it needs a `BrowserContentFetcher` to inject.

### 3d. Recommendation

| Option | Description | Confidence |
|--------|-------------|------------|
| A: Close #838 as superseded, create MCP wiring follow-up | 3/4 ACs are duplicate with #830. Create focused task for AC3. | **.85** |
| B: Keep #838, narrow to AC3 only | Rewrite body to only cover MCP layer wiring. | .70 |
| C: Keep #838 as-is | Risks duplicate implementation effort when #842 completes. | .30 |

**Recommendation: Option A.** Close #838 as superseded by #830/#842 for AC1/AC2/AC4. Create a new follow-up task for the MCP server wiring (AC3) that depends on #842. This avoids duplicate work and matches the actual dependency chain.

Challenge: FALLBACK — challenger subagent unavailable. Self-challenge: "Should we keep #838 and just narrow it?" No — #838's parent is #751 and its AC was written before #830 existed. The overlap is ~75%. A narrow MCP wiring task with clean AC is more actionable than retrofitting #838.

## 4. Follow-up Tasks

1. **MCP browser server: wire BrowserContentFetcher into navigate/read_text tools** — depends on #842. Scope: inject fetcher into AppContext, implement navigate() → fetcher.fetch(), catch AuthenticationRequired → ToolError, implement read_text() with last-fetched content. Integration test at MCP layer.

## 5. Tier Classification

- **T1 — Autonomous**: Closing #838 as superseded and creating the MCP wiring follow-up task are housekeeping/feature decomposition. No architecture change, no security impact, no user-facing behavior change.
