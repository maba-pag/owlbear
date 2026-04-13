---
id: 871
title: Pivot MCP browser server from CDPConnectionManager to PlaywrightLauncher
status: backlog
priority: critical
created: '2026-04-13T23:22:45.535455+00:00'
updated: '2026-04-13T23:22:45.535455+00:00'
tags:
- pivot
- phase-2
- scope:mcp-browser
parent: 751
depends_on:
- 869
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context

MCP browser server (`serve/mcp-browser/src/owlbear_mcp_browser/server.py`) directly imports and uses `CDPConnectionManager` from `owlbear_browser.cdp`. After the Playwright pivot (#869), this must be updated to use `PlaywrightLauncher` instead.

Current code (lines 19, 31, 66, 70):
```python
from owlbear_browser.cdp import CDPConnectionManager
# AppContext.cdp: CDPConnectionManager | None = None
# lifespan creates CDPConnectionManager(port=port)
```

## Acceptance Criteria

1. `server.py` imports `PlaywrightLauncher` from `owlbear_browser.playwright_launcher` instead of `CDPConnectionManager`
2. `AppContext` field changes from `cdp: CDPConnectionManager | None` to `launcher: PlaywrightLauncher | None` (or similar)
3. Lifespan creates `PlaywrightLauncher` instead of `CDPConnectionManager`
4. `BrowserContentFetcher` receives Playwright context (not CDP manager) in `navigate()` tool
5. No imports of `owlbear_browser.cdp` remain in `serve/mcp-browser/`
6. Existing MCP browser tests that mock CDP must be updated to mock Playwright launcher
7. All MCP browser tests pass
8. ruff clean

## Notes

- Depends on #869 (Playwright launcher implementation must exist first)
- This is the MCP integration layer — the Playwright launcher itself is built in #869
- `read_text()`, `snapshot()`, and other tools that use `page` will work through the launcher's context