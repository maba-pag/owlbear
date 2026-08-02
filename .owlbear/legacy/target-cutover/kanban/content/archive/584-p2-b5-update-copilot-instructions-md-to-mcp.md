---
id: 584
title: 'P2-B5: Update copilot-instructions.md to MCP-primary'
status: archived
priority: medium
created: 2026-04-03 16:42:56.807306+02:00
updated: 2026-04-04 23:06:22.358029+02:00
started: 2026-04-04 23:03:31.448088+02:00
completed: 2026-04-04 23:06:22.358029+02:00
tags:
- scope:mcp
- ' phase-2'
- ' type:build'
parent: 484
depends_on:
- 484
class: standard
archival_reason: completed
archival_refs: []
---

**Source:** docs/research/phase-b-mcp-only-kanban-migration.md §3d\n\nUpdate .github/copilot-instructions.md kanban-md section to be MCP-primary. This file is loaded into every agent context, so agents seeing CLI commands undermines the MCP migration.\n\nConvert agent-facing CLI examples to MCP syntax. Keep the section as project documentation with CLI available for human terminal use.\n\n**Specific refs:**\n- L143: kanban-md edit/list blocked task guidance\n- L149: kanban-md flags for dependency tracking\n- L165: kanban-md list filter examples\n- L169: kanban-md create in research lifecycle\n\n**AC:**\n- [ ] kanban-md section uses MCP tool syntax as primary path\n- [ ] CLI usage noted as available for human terminal use\n- [ ] Agent-facing workflow descriptions use MCP tool names\n- [ ] kanban-md binary/setup info retained for installation docs

[[2026-04-04]] Sat
Cancelled by orchestrator: zero remaining scope, target lines dont exist. Parent #484 archived with all scope captured.

[[2026-04-04]] Sat 23:06
Cancelled: stale subtask, target lines nonexistent, scope captured by archived parent #484.
