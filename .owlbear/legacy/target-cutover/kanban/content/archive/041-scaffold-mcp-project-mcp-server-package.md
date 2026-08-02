---
id: 41
title: Scaffold mcp-project MCP server package
status: archived
priority: medium
created: 2026-03-26 18:50:07.713415+01:00
updated: 2026-03-27 22:15:35.597279+01:00
started: 2026-03-27 22:15:35.597279+01:00
completed: 2026-03-27 22:15:35.597279+01:00
tags:
- phase-1
- scope:mcp
- scope:build
depends_on:
- 7
- 67
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Create packages/mcp-project/ with FastMCP server for project metadata. Minimal scaffold with stub tools and a working resource.

## Acceptance Criteria
- [ ] Package uses src-layout: packages/mcp-project/pyproject.toml, packages/mcp-project/src/mcp_project/__init__.py, __main__.py, server.py
- [ ] pyproject.toml declares uv_build backend (>=0.11.1,<0.12), requires-python >=3.12, runtime dep on mcp (>=1.26,<2), and project.scripts entry mcp-project pointing to mcp_project entry point
- [ ] server.py exports a FastMCP('owlbear-project', lifespan=app_lifespan) instance
- [ ] app_lifespan is an @asynccontextmanager yielding a frozen @dataclass AppContext with stub fields (project_store: Any = None); no real storage connections (deferred to #17)
- [ ] set_active_project(project_name: str) registered via @mcp.tool(), returns static string 'Not yet implemented' (real impl deferred to #17)
- [ ] list_projects() registered via @mcp.tool(), returns static string 'Not yet implemented' (real impl deferred to #17)
- [ ] project://definition registered via @mcp.resource(), reads owlbear-project.json from CWD, returns file contents on success or JSON string '{"error": "No owlbear-project.json found"}' when file absent
- [ ] __main__.py calls mcp.run() (stdio entry point)
- [ ] .vscode/mcp.json adds owlbear-project server entry (type=stdio, command=uv, args referencing the package)
- [ ] All tests from preceding test task #67 pass GREEN

## Context
See docs/research/scaffold-mcp-project-server.md for full analysis.
See docs/research/mcp-python-sdk.md for SDK patterns.
v1 prior art: v1/src/owlbear/projects/ (ProjectStore, ProjectToolset patterns).
Depends on #7 (monorepo skeleton) for packages/ directory and uv workspace config.
Schema specification in #53 (not a blocker; scaffold uses preliminary fields).
Full feature expansion in #17 (depends on this scaffold).

[[2026-03-26]] Thu 19:12
## Research
Doc: docs/research/scaffold-mcp-project-server.md

Key findings:
- Flat package layout (server.py + __main__.py) recommended (.90)
- owlbear-project.json schema: name, type, owlbear_path, created_at
- FastMCP v1 with stdio transport, @mcp.resource for project definition
- Task #17 now depends on #41 (scaffold before full build)
- Created #53 for owlbear-project.json schema specification

Follow-up tasks created:
- #53 Define owlbear-project.json schema specification (ideation)
- #17 updated with depends_on: [41]

[[2026-03-26]] Thu 20:06
## Architecture Review
**Verdict:** REFINE

### AC Assessment

AC1 (package structure): Missing src-layout detail and file paths. Rewritten with full src/mcp_project/ layout matching siblings #39 and #40.
AC2 (pyproject.toml): Missing build backend, dep version, scripts. Rewritten with uv_build, mcp>=1.26, entry point.
AC3 (FastMCP instance): Vague. Rewritten with instance name 'owlbear-project' and lifespan param.
AC4 (lifespan): Was missing entirely. Added with stub AppContext pattern (matching #40).
AC5-6 (tools): Vague 'set_active_project, list_projects'. Rewritten as explicit stubs returning 'Not yet implemented' (real impl deferred to #17). Storage location question is deferred.
AC7 (resource): Vague. Rewritten with project://definition URI, CWD read, and error JSON behavior.
AC8 (__main__.py): Implicit. Made explicit.
AC9 (mcp.json): Kept, clarified format.
AC10 (tests): 'Tests for tool functions' moved to TDD test task #67. Replaced with 'all tests from #67 pass GREEN'.

### Architecture Notes
Research is thorough (.85 confidence). Flat package layout is correct for 2 stub tools + 1 resource (YAGNI). Follows FastMCP v1 quickstart pattern and matches sibling scaffolds #39 (mcp-kanban) and #40 (mcp-knowledge). Tools are stubs matching #40 pattern; real ProjectStore integration deferred to #17. Resource reads owlbear-project.json from CWD (safe file I/O, workspace-confined by VS Code server spawn). No security surface concerns for stubs.

Critical gap: packages/ directory does not exist yet. Task #7 (Create monorepo skeleton) is still in ideation. Added as dependency.

Single domain: scope:mcp scaffold. No cross-domain concerns.

### Changes Made
- Rewrote AC: 6 vague items refined to 10 precise testable items
- Added depends_on: #7 (monorepo skeleton, packages/ dir)
- Added depends_on: #67 (TDD RED test task)
- Created #67: Test task with 6 test scenarios at backlog
- Removed 'Tests for tool functions' from impl AC (moved to #67)
- Made tools return stub strings (matching #40 scaffold pattern)

### Dependencies
- Added: #7 (Create monorepo skeleton) required for packages/ dir
- Added: #67 (Test: Scaffold mcp-project) TDD RED phase must run first
- Verified: #53 (schema spec) at ideation, not a blocker for scaffold
- Verified: #17 (full build) correctly depends on #41
