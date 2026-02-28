---
id: 137
title: 'Research: MCP servers — inventory, evaluation, integration path'
status: archived
priority: important
created: 2026-02-27T14:57:50.444795+01:00
updated: 2026-02-28T23:53:02.0632976+01:00
started: 2026-02-27T20:20:10.4463278+01:00
completed: 2026-02-28T23:53:02.0632976+01:00
tags:
    - phase-10
    - research
    - mcp
class: standard
---

PydanticAI has native MCP client support (MCPServerStdio, MCPServerHTTP). Survey available MCP servers and evaluate which fill gaps vs our native tools.

Research doc: docs/mcp-servers-research.md

## AC (research task)

- [x] Research doc complete: docs/mcp-servers-research.md
- [x] Research checklist: theoretical validity, prior art, technical feasibility, architecture fit, implementation approach — all addressed
- [x] Server evaluation matrix: GitHub (.90 Adopt), Git (.80 Consider), Fetch (.75 Consider), Brave (.70 Defer), Filesystem/Memory/Playwright (.15–.30 Skip)
- [x] Recommendation: hybrid model — keep native toolsets, add MCP for new capabilities
- [ ] Create follow-up kanban tasks in ideation (phase-10, mcp):
  1. MCP client infrastructure — MCPServerRegistry + tool_resolver `mcp:` prefix extension + settings
  2. GitHub MCP server integration — configure @modelcontextprotocol/server-github via MCPServerStdio
  3. Git MCP server integration — @modelcontextprotocol/server-git
  4. Fetch MCP server integration — @modelcontextprotocol/server-fetch
  5. MCP server lifecycle management — async context manager cleanup, health checks

## Architecture notes

- Note overlap: GitHub MCP server vs #166 GitHubToolset (httpx). Phase-8 proceeds with httpx (YAGNI — build what's needed now). Phase-10 evaluates whether MCP replaces or complements.
- PydanticAI MCPServer extends AbstractToolset — integrates with HookedToolset, FilteredToolset, RolePolicy with zero adapter code.
- Do NOT replace native FileToolset, BrowserToolset, or knowledge graph with MCP equivalents — our implementations are sandboxed, safer, and better integrated.
