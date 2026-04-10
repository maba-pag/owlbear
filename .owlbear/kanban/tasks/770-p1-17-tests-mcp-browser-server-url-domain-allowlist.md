---
id: 770
title: 'P1-17: Tests — MCP browser server + URL domain allowlist'
status: research
priority: needed
created: '2026-04-10T10:56:34.316989+00:00'
updated: '2026-04-10T10:56:34.316989+00:00'
tags:
- phase-1
- type:test
- scope:mcp-browser
parent: 751
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
RED phase. Tests for MCP browser server:
1. FastMCP server registers tools: navigate, click, type, select, read_text, snapshot
2. URL domain allowlist enforcement at tool level — tools reject URLs outside allowed domains
3. Allowlist read from env var
4. Tool annotations set correctly
5. BROWSER_TOOLS_EXCLUDE env var removes tools

Mock-based. All tests fail (RED).

Parent: #751
