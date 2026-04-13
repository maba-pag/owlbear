---
id: 855
title: Bump playwright dependency to >=1.59.0 for aria_snapshot support
status: research
priority: important
created: '2026-04-12T14:03:37.182864+00:00'
updated: '2026-04-12T14:03:37.182864+00:00'
tags:
- phase-2
- scope:mcp-browser
parent: 837
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
Update serve/browser/pyproject.toml playwright dependency from >=1.40.0 to >=1.59.0.

**Source:** .owlbear/research/837-mcp-browser-session-management.md §3f

**Why:** page.aria_snapshot() was added in Playwright v1.59. The snapshot() MCP tool requires this API.

**AC:**
- [ ] serve/browser/pyproject.toml: playwright>=1.59.0
- [ ] uv lock succeeds
- [ ] Existing browser tests still pass