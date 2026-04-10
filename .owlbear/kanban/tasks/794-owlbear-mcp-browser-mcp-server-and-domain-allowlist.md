---
id: 794
title: owlbear_mcp_browser MCP server and domain allowlist
status: backlog
priority: important
created: '2026-04-10T12:31:51.889527+00:00'
updated: '2026-04-10T12:31:51.889527+00:00'
tags:
- phase-1
- scope:mcp-browser
parent: 775
depends_on:
- 790
- 788
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `serve/mcp-browser/` package created: `pyproject.toml`, `src/owlbear_mcp_browser/__init__.py`, `server.py`
- 6 MCP tools registered: `navigate`, `click`, `type`, `select`, `read_text`, `snapshot` — each with `ToolAnnotations` (readOnlyHint, idempotentHint, destructiveHint)
- AppContext + lifespan pattern per architecture standards
- Domain allowlist enforcement: `BROWSER_ALLOWED_DOMAINS` comma-separated env var; requests to non-allowlisted domains rejected with `ToolError`
- `BROWSER_TOOLS_EXCLUDE` env var removes specified tools from registration
- `ALLOWED_IMPORTS` updated: `owlbear_mcp_browser: {"owlbear_browser"}`
- All #790 tests pass
- Files: `serve/mcp-browser/`, `tests/test_package_boundary.py`

## Context
- WS-C: Browser Packages
- Scope item 2 from #775
