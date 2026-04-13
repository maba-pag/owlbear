---
id: 856
title: 'RED: Tests for BrowserContentFetcher wiring in MCP browser navigate/read_text'
status: research
priority: important
created: '2026-04-12T15:15:37.708042+00:00'
updated: '2026-04-12T15:15:37.708042+00:00'
tags:
- phase-1
- scope:mcp-browser
- tdd-red
parent: 852
depends_on:
- 849
- 850
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

MCP browser server needs RED-phase tests for wiring BrowserContentFetcher into navigate() and read_text() tools. Tests must use the ctx: Context mock pattern (established by #849/#850).

See `.owlbear/research/852-wire-browserfetcher-mcp-tools.md` §3e for test patterns.

## Acceptance Criteria

1. Test file `tests/test_mcp_browser_fetcher_852.py` with `_make_app_ctx` and `_make_mcp_ctx` helpers.
2. Tests for `navigate(ctx, url)`:
   - Success: calls `fetcher.fetch(url)`, returns markdown content, updates `last_content` in AppContext.
   - AuthenticationRequired: caught and raised as `ToolError` with descriptive message.
   - Fetcher is None: raises `ToolError("Browser not available")` or similar.
3. Tests for `read_text(ctx)`:
   - Returns `last_content` from AppContext (set by prior navigate).
   - Returns empty string when no prior navigate.
4. Tests for `AppContext`:
   - Has `fetcher: BrowserContentFetcher | None` field (default None).
   - Has `last_content: str` field (default "").
5. All tests FAIL at RED phase (navigate/read_text still stubs).
6. ruff clean.

## Notes

- Depends on #849 (ctx mock helpers) and #850 (ctx: Context in tool signatures).
- Follow mock patterns from `tests/test_contentfetcher_impl_830.py` for BrowserContentFetcher mocks.
- `ToolError` imported from `mcp.server.fastmcp.exceptions`.