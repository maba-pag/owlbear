---
id: 493
title: Add TOOLS_EXCLUDE config to knowledge and project MCP servers
status: ideation
priority: nice-to-have
created: 2026-03-31T06:37:25.2412013+02:00
updated: 2026-03-31T06:37:25.2412013+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
depends_on:
    - 473
class: standard
---

## Objective\n\nAdd per-server TOOLS_EXCLUDE env var support to mcp-knowledge and mcp-project servers, matching the pattern from mcp-kanban (#473).\n\n## Acceptance Criteria\n\n- [ ] mcp-knowledge reads `KNOWLEDGE_TOOLS_EXCLUDE` env var (comma-separated tool names)\n- [ ] mcp-project reads `PROJECT_TOOLS_EXCLUDE` env var (comma-separated tool names)\n- [ ] Tools listed in exclude are not registered with FastMCP\n- [ ] Default (no env var): all tools registered (backward-compatible)\n- [ ] Invalid names silently ignored\n- [ ] Tests cover: exclude one tool, exclude multiple, exclude none, invalid name — for both servers\n- [ ] Update knowledge-ops SKILL.md and any project docs to describe the config\n\n## Design Notes\n\n- Same pattern as #473 (KANBAN_TOOLS_EXCLUDE) applied to the other two servers\n- Implementation is ~10 lines per server (env parse + conditional registration)\n- Not a shared library — each server implements the same simple pattern independently\n\n## Dependencies\n\n- Depends on #473 (implement pattern in kanban first, then replicate)
