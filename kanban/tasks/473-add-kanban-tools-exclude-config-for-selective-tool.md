---
id: 473
title: Add KANBAN_TOOLS_EXCLUDE config for selective tool exposure
status: backlog
priority: needed
created: 2026-03-31T05:21:29.1281475+02:00
updated: 2026-03-31T06:55:31.2552535+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
class: standard
---

## Research (revised)
- Approach: lifespan-level removal using FastMCP's public remove_tool(name) API
- ~15 LOC helper _apply_tool_exclusions(), called in app_lifespan before yield
- Corrected from prior analysis: KANBAN_BIN is read in lifespan, not module level
- Option B (lifespan) scores .85 vs Option A (module-level) .65
- Invalid names silently ignored via try/except (ToolError)
- Backwards-compatible: no env var means all tools registered
- mcp.json env field used for deployment config
- Follow-up: #491 (implementation task at ideation)
- Doc: docs/research/kanban-tools-exclude-config.md (revised)
- Confidence: .85
