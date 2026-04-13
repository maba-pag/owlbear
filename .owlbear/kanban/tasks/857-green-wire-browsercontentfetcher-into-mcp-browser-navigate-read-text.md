---
id: 857
title: 'GREEN: Wire BrowserContentFetcher into MCP browser navigate/read_text'
status: research
priority: important
created: '2026-04-12T15:15:50.852819+00:00'
updated: '2026-04-12T15:15:50.852819+00:00'
tags:
- phase-1
- scope:mcp-browser
- tdd-green
parent: 852
depends_on:
- 856
- 842
- 850
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

Implement wiring of BrowserContentFetcher into MCP browser server tools. RED partner: #856.

See `.owlbear/research/852-wire-browserfetcher-mcp-tools.md` for full analysis.

## Acceptance Criteria

1. `AppContext` has `fetcher: BrowserContentFetcher | None = None` and `last_content: str = ""` fields.
2. `app_lifespan()` creates CDPConnectionManager + BrowserContentFetcher (guarded, fallback to None on failure).
3. `navigate(ctx, url)` calls `fetcher.fetch(url)`, stores result in `ctx.request_context.lifespan_context.last_content`, returns the markdown content.
4. `navigate()` catches `AuthenticationRequired` → `ToolError` with descriptive message.
5. `navigate()` returns `ToolError` if fetcher is None.
6. `read_text(ctx)` returns `ctx.request_context.lifespan_context.last_content`.
7. All #856 RED tests pass.
8. ruff clean.

## Notes

- Depends on #856 (RED tests), #842 (BrowserContentFetcher impl), #850 (ctx: Context in tools).
- `import` from `owlbear_browser` for `BrowserContentFetcher` and `AuthenticationRequired`.
- owlbear-mcp-browser pyproject.toml already depends on owlbear-browser (workspace dep).

**Affected files:** `serve/mcp-browser/src/owlbear_mcp_browser/server.py`