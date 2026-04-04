---
id: 584
title: 'P2-B5: Update copilot-instructions.md to MCP-primary'
status: ideation
priority: important
created: 2026-04-03T16:42:56.8073061+02:00
updated: 2026-04-03T16:42:56.8073061+02:00
tags:
    - scope:mcp
    - ' phase-2'
    - ' type:build'
parent: 484
depends_on:
    - 484
class: standard
---

**Source:** docs/research/phase-b-mcp-only-kanban-migration.md §3d\n\nUpdate .github/copilot-instructions.md kanban-md section to be MCP-primary. This file is loaded into every agent context, so agents seeing CLI commands undermines the MCP migration.\n\nConvert agent-facing CLI examples to MCP syntax. Keep the section as project documentation with CLI available for human terminal use.\n\n**Specific refs:**\n- L143: kanban-md edit/list blocked task guidance\n- L149: kanban-md flags for dependency tracking\n- L165: kanban-md list filter examples\n- L169: kanban-md create in research lifecycle\n\n**AC:**\n- [ ] kanban-md section uses MCP tool syntax as primary path\n- [ ] CLI usage noted as available for human terminal use\n- [ ] Agent-facing workflow descriptions use MCP tool names\n- [ ] kanban-md binary/setup info retained for installation docs
