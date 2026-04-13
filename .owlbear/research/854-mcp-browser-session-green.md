# GREEN: MCP Browser Session Management — Implementation Research

> **Owning task:** #854 — GREEN: Implement mcp-browser session management
> **Date:** 2026-04-12  **Status:** Complete (validation pass)

## 1. Context and Question

Task #854 implements browser session management to make RED tests (from #853) pass. The parent task (#837) research doc covers the full implementation approach. This is a validation pass confirming the approach remains accurate against current codebase state.

## 2. Sources Studied

| # | Source | Location | Relevance |
|---|--------|----------|-----------|
| 1 | Parent research doc | `.owlbear/research/837-mcp-browser-session-management.md` | 1.0 |
| 2 | mcp-browser server.py | `serve/mcp-browser/src/owlbear_mcp_browser/server.py` | 1.0 |
| 3 | CDPConnectionManager | `serve/browser/src/owlbear_browser/cdp.py` L43-120 | .95 |
| 4 | extract_content | `serve/browser/src/owlbear_browser/extractor.py` L48-74 | .90 |
| 5 | mcp-knowledge lifespan (ref) | `serve/mcp-knowledge/src/owlbear_mcp_knowledge/server.py` L183-230 | .85 |
| 6 | Architect review on #837 | Task #837 body | .90 |

## 3. Validation Against Current Codebase

| Research claim | Current state | Valid? |
|---------------|--------------|--------|
| AppContext has only `allowlist` field | server.py L22-25: `AppContext(allowlist: DomainAllowlist)` | Yes |
| Tools are stubs returning placeholders | server.py L80-108: click returns selector, read_text returns "" | Yes |
| CDPConnectionManager has connect/disconnect | cdp.py L99-120: `connect()`, `disconnect()`, `_browser` attribute | Yes |
| `_browser.contexts[0].new_page()` for shared page | cdp.py L67: `_browser: Any = None`; Playwright Browser API confirmed | Yes |
| `extract_content(html, url)` signature | extractor.py L48: `def extract_content(html: str, url: str \| None = None)` | Yes |
| Lifespan yields AppContext with try/finally | server.py L51-58: current lifespan pattern, no cleanup needed yet | Yes |
| Tools lack `ctx: Context` param | server.py L65-108: no ctx on any tool | Yes — #850 prerequisite |

## 4. Implementation Approach (from parent research §3c-§3e)

**AppContext extension:** Add `cdp: CDPConnectionManager | None = None` and `page: Any = None`.

**Lifespan:** Read `BROWSER_CDP_PORT` (default 9222), create CDPConnectionManager, attempt `connect()` + `new_page()`. On failure: degrade to `cdp=None, page=None`. Cleanup: close page, disconnect CDP in finally block.

**Tool bodies:** Each tool extracts `page` from `ctx.request_context.lifespan_context.page`, raises `ToolError("No browser session")` if None. Specific mappings:
- navigate → allowlist.check(url) then page.goto(url)
- click → page.locator(selector).click()
- type → page.locator(selector).fill(text)
- select → page.locator(selector).select_option(value)
- read_text → extract_content(await page.content(), page.url)
- snapshot → page.aria_snapshot()

Confidence: .88 (validated against codebase, straightforward implementation).

Challenge: FALLBACK — implementation approach dictated by parent research + architect approval. No controversial recommendation.

## 5. Dependency Chain and Blockers

| Dependency | Status | Blocker? |
|-----------|--------|----------|
| #850 (ctx refactor GREEN) | `todo` | Yes — tools need ctx: Context before session fields are usable |
| #853 (RED tests) | `research` | Yes — GREEN requires RED tests to validate against |
| #855 (playwright bump) | `research` | Soft — snapshot() needs >=1.59.0 for aria_snapshot |

**No new follow-up tasks needed** — #853, #855 already cover remaining work items.

**Tier: T1 — Autonomous.** Implementation within approved Phase 2 architecture.
