---
id: 39
title: Scaffold mcp-kanban MCP server package
status: archived
priority: medium
created: 2026-03-26 18:49:54.134108+01:00
updated: 2026-03-27 22:15:34.929296+01:00
started: 2026-03-27 22:15:34.929296+01:00
completed: 2026-03-27 22:15:34.929296+01:00
tags:
- phase-1
- scope:mcp
- scope:build
depends_on:
- 7
- 65
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Create packages/mcp-kanban/ with FastMCP server wrapping kanban-md binary. Minimal one-tool scaffold.

## Acceptance Criteria
- [ ] Package uses src-layout: packages/mcp-kanban/pyproject.toml, packages/mcp-kanban/src/mcp_kanban/__init__.py, __main__.py, server.py
- [ ] pyproject.toml declares uv_build backend, mcp>=1.26 dependency, and project.scripts entry mcp-kanban pointing to mcp_kanban entry point
- [ ] server.py exports a FastMCP(mcp-kanban, lifespan=app_lifespan) instance
- [ ] Lifespan asynccontextmanager yields a context dataclass with resolved kanban binary Path; resolution: KANBAN_BIN env var first, then kanban/kanban-md.exe relative to cwd; raises FileNotFoundError with descriptive message if binary absent
- [ ] One tool list_tasks: calls kanban-md binary via asyncio.create_subprocess_exec with args list --no-color; returns stdout on rc=0, returns error: stderr on non-zero rc (matches v1 KanbanToolset._run_kanban pattern)
- [ ] __main__.py calls mcp.run() (stdio entry point)
- [ ] .vscode/mcp.json adds mcp-kanban server entry (type=stdio, command=uv, args referencing the package)
- [ ] Unit tests in packages/mcp-kanban/tests/test_server.py cover: (a) list_tasks returns subprocess stdout on success, (b) list_tasks returns error string on non-zero rc, (c) lifespan raises FileNotFoundError when binary missing

## Context
See docs/research/scaffold-mcp-kanban.md for full analysis.
See docs/research/mcp-python-sdk.md for SDK patterns.
v1 prior art: v1/src/owlbear/tools/kanban.py (_run_kanban helper, subprocess pattern).
Depends on #7 (monorepo skeleton) for packages/ directory and uv workspace config.

[[2026-03-26]] Thu 19:58
## Architecture Review
**Verdict:** APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Package src-layout | Precise: files and paths specified | Keep |
| pyproject.toml (uv_build, mcp dep, scripts) | Precise: backend, dep version, entry point | Keep |
| FastMCP instance with lifespan | Precise: constructor and param named | Keep |
| Lifespan binary resolution | Precise: env var fallback chain, error type | Keep |
| list_tasks tool (subprocess, rc handling) | Precise: args, success/error behavior, v1 pattern ref | Keep |
| __main__.py mcp.run() | Precise: entry point | Keep |
| .vscode/mcp.json registration | Precise: type/command/args | Keep |
| Unit tests (3 cases) | Precise: 3 named scenarios | Keep |

### Architecture Notes
- Follows v1 KanbanToolset subprocess pattern (asyncio.create_subprocess_exec)
- Lifespan pattern from FastMCP v1 docs, KANBAN_BIN env var + convention fallback
- src-layout aligns with sister task #40 and uv workspace conventions from #6
- Single domain: scope:mcp scaffold, no cross-domain concerns
- Security: subprocess calls our own binary with fixed args, no user-supplied path injection

### Changes Made
- Rewrote AC from 7 vague items to 8 precise testable items
- Removed untestable 'VS Code discovers the server' AC (covered by mcp.json registration + follow-up #57)
- Added depends_on: [7] (monorepo skeleton, packages/ dir)
- Created #65: Test task (TDD RED) with 6 test scenarios, depends_on: [7]
- Added depends_on: [65] to #39 (test-first sequencing)

### Dependencies
- Added: #7 (monorepo skeleton, must exist for packages/ dir)
- Added: #65 (TDD RED test task, must complete before builder)
- Verified: #56 (expand to full toolset) exists at backlog
- Verified: #57 (integration tests) exists at ideation
