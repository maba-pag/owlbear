---
id: 124
title: Document how to add project-specific MCP servers
status: archived
priority: medium
created: 2026-03-29 06:33:52.367210+02:00
updated: 2026-03-29 15:36:41.493360+02:00
started: 2026-03-29 15:36:41.493360+02:00
completed: 2026-03-29 15:36:41.493360+02:00
tags:
- phase-1
- scope:mcp
- type:docs
blocked: true
block_reason: 'Duplicate of #122 - identical AC and context'
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add brief documentation for users on how to add their own MCP servers to the generated mcp.json.

## Acceptance Criteria
- [ ] setup.py print output includes note about customizing mcp.json
- [ ] copilot-instructions.md or README includes section on adding MCP servers
- [ ] Section covers: adding a new server entry, stdio vs http types, env vars for secrets
- [ ] References VS Code MCP docs for full schema

## Context
See docs/research/mcp-server-registry.md section 3.6. AC item 9 of task 18.

[[2026-03-29]] Sun 07:07
## Research
Doc: docs/research/mcp-server-customization-docs.md
Follow-up: #128 (README section), #129 (setup.py hint)

[[2026-03-29]] Sun 07:08
## Research
Duplicate of task 122. Identical AC and context. Close this task.

[[2026-03-29]] Sun 15:36
## Architecture Review\n**Verdict:** Merge (delete duplicate)\n\n### Assessment\nConfirmed duplicate of #122 which is already archived (confidence .97, all 9 AC lines PASS). Identical objective, overlapping AC, same research context. Researcher flagged this in both the task body and via --block.\n\n### Changes Made\n- Verified #122 archived with full AC coverage\n- Deleting #124 as redundant
