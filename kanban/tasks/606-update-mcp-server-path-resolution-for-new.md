---
id: 606
title: Update MCP server path resolution for new structure
status: backlog
priority: needed
created: 2026-04-04T20:31:28.5105181+02:00
updated: 2026-04-04T20:31:28.5105181+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
depends_on:
    - 601
    - 602
    - 603
parent: 598
class: standard
---

## Summary

Update MCP server path resolution for the new folder structure. kanban server reads from .owlbear/kanban/, knowledge server reads from both store/knowledge/ (global) and .owlbear/knowledge/ (local), memory server reads from store/memory/.

## Acceptance Criteria

- [ ] AC1: mcp-kanban resolves KANBAN_BIN from .owlbear/kanban/kanban-md.exe
- [ ] AC2: mcp-kanban finds config.yml and tasks/ in .owlbear/kanban/
- [ ] AC3: mcp-knowledge reads global KB from store/knowledge/
- [ ] AC4: mcp-knowledge reads project-local KB from .owlbear/knowledge/ (if present)
- [ ] AC5: mcp-memory reads from store/memory/
- [ ] AC6: mcp-project reads owlbear-project.json from project root (unchanged)
- [ ] AC7: .vscode/mcp.json server entries updated if needed (env vars, args)
- [ ] AC8: All MCP server unit tests pass
- [ ] AC9: MCP servers start successfully in VS Code

## Notes

Environment variables and config resolution in each MCP server package need auditing for hardcoded paths.
