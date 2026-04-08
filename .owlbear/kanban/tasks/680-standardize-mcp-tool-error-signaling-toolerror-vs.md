---
id: 680
title: Standardize MCP tool error signaling (ToolError vs error strings)
status: research
priority: nice-to-have
created: 2026-04-08T18:40:23.4451397+02:00
updated: 2026-04-08T18:40:23.4451397+02:00
tags:
    - scope:mcp
    - ' type:refactor'
    - ' source:analysis'
class: standard
---

## Context

Analysis synthesis identified inconsistent error signaling across MCP servers. Within the same server, some tools raise `ToolError` (MCP `isError: true`) while others return `error: ...` strings.

Examples:
- **Memory server:** `set_approval_state` raises `ToolError` for missing entries but returns `error: ...` for invalid transitions. `record_learning` always returns error strings.
- **Knowledge server:** Most tools return error strings; some raise `ToolError`.
- **Project server:** `project_info` raises `ToolError`; other tools return error strings.

Agents must handle both patterns for every tool call.

## Acceptance Criteria

- [ ] AC1: Audit all 26 MCP tools across 4 servers for error signaling pattern
- [ ] AC2: Define a convention: when to use `ToolError` vs `error: ...` strings (recommendation: `ToolError` for "cannot proceed" errors, error strings for "partial/degraded result")
- [ ] AC3: Apply the convention consistently across all tools
- [ ] AC4: Update SKILL.md documentation to reflect the standardized behavior
- [ ] AC5: Verify no agent breakage — test all tool error paths

**Risk:** This is a breaking change for agents adapted to current patterns. Needs careful staging.
