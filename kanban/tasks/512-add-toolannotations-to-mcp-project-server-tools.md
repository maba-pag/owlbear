---
id: 512
title: Add ToolAnnotations to mcp-project server tools
status: ideation
priority: important
created: 2026-04-01T00:39:23.993893+02:00
updated: 2026-04-01T03:05:43.2598919+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
blocked: true
block_reason: 'Capability already exists: all 4 mcp-project tools already have ToolAnnotations applied (server.py L82, L97, L114, L128). No work needed.'
class: standard
---

## AC
- [ ] Add ToolAnnotations (readOnlyHint, idempotentHint, destructiveHint) to all 4 mcp-project tools: project_info, project_list, project_readme, project_structure
- [ ] All 4 tools are read-only: readOnlyHint=true, destructiveHint=false
- [ ] Follow mcp-kanban server.py annotation pattern as reference
- [ ] Update tests if applicable

## Context
Gap identified during #508 architecture review. mcp-kanban has ToolAnnotations on all tools; mcp-project has none. See docs/research/mcp-server-error-return-standardization.md section 3d (annotation audit not covered by #506).
