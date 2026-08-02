---
id: 512
title: Add ToolAnnotations to mcp-project server tools
status: archived
priority: medium
created: 2026-04-01 00:39:23.993893+02:00
updated: 2026-04-04 07:10:00.102859+02:00
started: 2026-04-04 07:09:34.477616+02:00
completed: 2026-04-04 07:09:34.477616+02:00
tags:
- scope:mcp
- ' type:build'
- ' phase-2'
class: standard
archival_reason: completed
archival_refs: []
---

## AC
- [ ] Add ToolAnnotations (readOnlyHint, idempotentHint, destructiveHint) to all 4 mcp-project tools: project_info, project_list, project_readme, project_structure
- [ ] All 4 tools are read-only: readOnlyHint=true, destructiveHint=false
- [ ] Follow mcp-kanban server.py annotation pattern as reference
- [ ] Update tests if applicable

## Context
Gap identified during #508 architecture review. mcp-kanban has ToolAnnotations on all tools; mcp-project has none. See docs/research/mcp-server-error-return-standardization.md section 3d (annotation audit not covered by #506).
