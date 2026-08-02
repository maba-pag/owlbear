---
id: 56
title: Expand mcp-kanban to full kanban-md tool set
status: archived
priority: medium
created: 2026-03-26 19:20:05.696176+01:00
updated: 2026-03-28 03:46:08.974369+01:00
started: 2026-03-28 03:46:08.974369+01:00
completed: 2026-03-28 03:46:08.974369+01:00
tags:
- phase-3
- mcp
- tooling
depends_on:
- 39
- 89
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Implement the full mcp-kanban MCP server: FastMCP setup, lifespan, subprocess helper, 7 kanban-md tools, and stdio entry point. Covers scope originally split between #39 (scaffold, archived but undelivered) and #56 (expansion).

## Acceptance Criteria

### Package setup
- [ ] pyproject.toml adds mcp>=1.26 to [project.dependencies] and declares [project.scripts] entry point for mcp-kanban
- [ ] .vscode/mcp.json adds mcp-kanban server entry (type: stdio, command: uv, args referencing owlbear-mcp-kanban package)

### Server infrastructure (server.py)
- [ ] server.py exports mcp = FastMCP("mcp-kanban", lifespan=app_lifespan)
- [ ] AppContext dataclass with kanban_bin: Path and kanban_dir: Path fields
- [ ] app_lifespan async context manager yields AppContext; binary resolution: KANBAN_BIN env var first, then kanban/kanban-md.exe relative to cwd; raises FileNotFoundError with descriptive message if binary absent
- [ ] _run_kanban async helper: runs kanban-md via asyncio.create_subprocess_exec with --no-color --dir {kanban_dir} appended; returns (stdout, stderr, returncode)

### Tools (7 total, each registered via @mcp.tool())
- [ ] list_tasks(*, status: str|None, tag: str|None, priority: str|None, block_filter: str|None, search: str|None, sort: str|None, unclaimed: bool=False) wraps kanban-md list --compact
- [ ] show_task(task_id: str) wraps kanban-md show {id} --json
- [ ] create_task(title: str, *, priority: str|None, tags: str|None, body: str|None, depends_on: str|None, claim: str|None) wraps kanban-md create
- [ ] move_task(task_id: str, status: str) wraps kanban-md move
- [ ] edit_task(task_id: str, *, body: str|None, block: str|None, unblock: bool=False, tags: str|None, priority: str|None, append_body: str|None, claim: str|None, release: bool=False, status: str|None, timestamp: bool=False) wraps kanban-md edit
- [ ] pick_task(*, status: str|None, claim: str|None, move: str|None, tags: str|None) wraps kanban-md pick
- [ ] board_context() wraps kanban-md context (no params)

### Error handling
- [ ] All tools return stdout on rc==0; return "error: {stderr.strip()}" string on non-zero rc (v1 KanbanToolset pattern, no exceptions)

### Entry point
- [ ] __main__.py calls mcp.run() for stdio transport

## References
- v1 prior art: v1/src/owlbear/tools/kanban.py (KanbanToolset._run_kanban, 7 tool signatures)
- Research: docs/research/expand-mcp-kanban-tools.md (Option B recommended)
- Scaffold research: docs/research/scaffold-mcp-kanban.md (lifespan pattern, binary resolution)

## Architecture Review
See below.

[[2026-03-27]] Fri 22:47
## Architecture Review
**Verdict:** REFINE (AC rewritten)

### AC Assessment (original AC)
| AC Line | Assessment | Action |
|---------|------------|--------|
| All 7 kanban-md commands exposed as MCP tools | Vague: doesn't enumerate tools or params | Rewrite with full signatures |
| Tool signatures match v1 KanbanToolset patterns | Contradicts research: Option B adds agent-essential params beyond v1 | Rewrite to specify v1 + new params |
| Each tool has unit test with mock subprocess | Vague: no scenario count, no paths specified | Moved to test task #89 with 17 scenarios |
| Error handling for binary failures | Vague: what behavior? | Rewrite to specify error string pattern |

### Architecture Notes
- #39 (scaffold) is archived but its deliverables (server.py, __main__.py, list_tasks, mcp dep) are absent from the codebase. Expanded #56 scope to cover full build.
- Module: packages/mcp-kanban/src/owlbear_mcp_kanban/ (single domain: tools/mcp)
- Pattern: matches scaffold-mcp-kanban research (FastMCP + lifespan + subprocess helper)
- v1 tool signatures validated against v1/src/owlbear/tools/kanban.py
- Agent-essential param additions per research: edit(claim, release, status, timestamp), create(claim), list(search, sort, unclaimed), pick(tags)
- asyncio.create_subprocess_exec (no shell=True): safe against command injection
- No module layering concerns: MCP server is a standalone package wrapping external binary

### Changes Made
- Rewrote AC body: 14 precise testable items replacing 4 vague items
- Created #89 (Test: mcp-kanban full tool set): TDD RED task with 17 test scenarios, depends_on: [7]
- Added depends_on: [89] to #56 (test-first sequencing)
- Kept depends_on: [39] (already set, archived)

### Dependencies
- Verified: #39 (scaffold) archived (deliverables missing, scope absorbed into #56)
- Verified: #7 (monorepo skeleton) at review (required for packages/ and uv workspace)
- Created: #89 (TDD RED test task, depends_on: [7])
- Added: #56 depends_on: [89] (builder cannot start until tests exist)
