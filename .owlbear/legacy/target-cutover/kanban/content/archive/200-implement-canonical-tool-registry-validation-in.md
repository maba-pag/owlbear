---
id: 200
title: Implement canonical tool registry validation in validate_agents.py
status: archived
priority: medium
created: 2026-03-30 03:21:21.863649+02:00
updated: 2026-03-30 06:28:19.709333+02:00
started: 2026-03-30 06:28:19.709333+02:00
completed: 2026-03-30 06:28:19.709333+02:00
tags:
- phase-1
- tooling
- agent
- config
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add full tool name validation to validate_agents.py.

## AC
- [ ] Define TOOL_SETS and BUILT_IN_TOOLS frozensets with all 37 known tools + 7 sets
- [ ] New validate function: classify each tools: entry as tool-set, built-in, MCP pattern, or unknown
- [ ] MCP pattern: any name matching */* (glob-style server reference)
- [ ] Flag unknown tool names with actionable error messages
- [ ] Keep existing todo/resolveMemoryFileUri checks
- [ ] Add source URL and date comment for maintenance
- [ ] All 11 current agent files pass validation
- [ ] ruff clean

See docs/research/canonical-tool-registry-validation.md
