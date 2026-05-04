---
id: 1349
title: Add MCP KANBAN_DIR board binding validation
status: backlog
priority: critical
created: 2026-05-04T18:17:29.608220+00:00
updated: 2026-05-04T18:17:29+00:00
tags:
- sync-blocker
- mcp-kanban
- config
- dev-experience
parent:
depends_on:
- 1337
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

The MCP kanban server binds to `Path(".owlbear/kanban")` relative to the process working directory. That likely works when VS Code starts the server from a single project root, but it is implicit, hard to diagnose when wrong, and unlike Cockpit's explicit `KANBAN_DIR` override. It also makes dev-code smoke tests and multi-root/project layouts more brittle than they need to be.

Audit decision: add explicit `KANBAN_DIR` support and startup validation to MCP.

## Acceptance Criteria

1. MCP app startup reads `KANBAN_DIR` when set; otherwise it preserves the current default of `.owlbear/kanban` relative to the process working directory.
2. Relative `KANBAN_DIR` values are resolved predictably relative to the process working directory and stored in `AppContext.kanban_dir` consistently.
3. Startup validates that the selected board directory exists and contains the expected kanban structure, at minimum `config.yml` and the configured task/archive paths after config load.
4. Startup failure messages name the resolved kanban directory and explain how to set/fix `KANBAN_DIR`.
5. `engine.sweep()` runs only after the intended board is selected and validated.
6. Tests prove default cwd binding, environment override binding, relative override behavior, and invalid path failure.
7. Docs and seed/config guidance mention the optional MCP `KANBAN_DIR` override without changing the default consumer setup.
8. `#1347` can use the override or a documented temp-cwd strategy to prove dev-code MCP runtime against an isolated test board.

## Key Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/README.md`
- `share/skills/h-mcp-kanban/SKILL.md`
- `seed/.vscode/mcp.json`
- `.vscode/mcp.json`
- `serve/mcp-kanban/tests/`

## Audit Evidence

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` defines `_DEFAULT_KANBAN_DIR = Path(".owlbear/kanban")` and does not read `KANBAN_DIR`.
- Cockpit already supports `KANBAN_DIR`, so MCP and Cockpit have inconsistent board-selection behavior.
- A wrong process cwd can silently bind MCP tools to the wrong board or fail without an actionable configuration path.

## Source

Deployment audit finding group 6, 2026-05-04.
