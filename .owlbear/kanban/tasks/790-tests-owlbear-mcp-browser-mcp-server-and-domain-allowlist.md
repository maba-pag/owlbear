---
id: 790
title: Tests — owlbear_mcp_browser MCP server and domain allowlist
status: backlog
priority: needed
created: '2026-04-10T12:31:33.683712+00:00'
updated: '2026-04-10T12:31:33.683712+00:00'
tags:
- phase-1
- scope:mcp-browser
- type:test
parent: 775
depends_on:
- 787
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify 6 MCP tools registered: `navigate`, `click`, `type`, `select`, `read_text`, `snapshot`
- Tests verify domain allowlist configuration via `BROWSER_ALLOWED_DOMAINS` env var
- Tests verify requests to non-allowlisted domains are rejected with `ToolError`
- Tests verify `BROWSER_TOOLS_EXCLUDE` env var removes tools from registration
- File: `tests/test_mcp_browser_775.py`

## Context
- WS-C: Browser Packages
- Scope item 2 from #775
