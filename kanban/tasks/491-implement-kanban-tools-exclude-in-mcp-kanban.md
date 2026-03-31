---
id: 491
title: Implement KANBAN_TOOLS_EXCLUDE in mcp-kanban server
status: ideation
priority: needed
created: 2026-03-31T06:22:24.6041271+02:00
updated: 2026-03-31T06:22:24.6041271+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
class: standard
---

## Acceptance Criteria

- [ ] Add _apply_tool_exclusions() helper that reads KANBAN_TOOLS_EXCLUDE env var
- [ ] Call mcp.remove_tool(name) for each excluded tool (comma-separated)
- [ ] Invalid tool names silently ignored (try/except)
- [ ] Default (no env var): all 7 tools registered (backwards-compatible)
- [ ] Tests: exclude one tool, exclude multiple, exclude none, invalid name
- [ ] Update mcp-kanban SKILL.md to document configuration
- [ ] Update setup-guide.md or mcp.json example

See docs/research/kanban-tools-exclude-config.md for design details.
