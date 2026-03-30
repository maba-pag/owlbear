---
id: 17
title: Build mcp-project server
status: in-progress
priority: important
created: 2026-03-26T17:21:36.1413972+01:00
updated: 2026-03-29T19:21:46.2844237+02:00
tags:
    - phase-1
    - scope:mcp
    - type:build
depends_on:
    - 2
    - 7
    - 68
    - 99
claimed_by: builder
claimed_at: 2026-03-29T19:21:46.2828834+02:00
class: standard
---

## Objective
Build an MCP server that provides project metadata and context to agents.

## Acceptance Criteria

### Server structure (follow mcp-kanban server.py pattern)
- [ ] FastMCP instance named "owlbear-project" in packages/mcp-project/src/owlbear_mcp_project/server.py
- [ ] AppContext dataclass (slots=True) with fields: project_file (OwlbearProjectFile | None), project_root (Path), owlbear_root (Path)
- [ ] app_lifespan async context manager that: (1) resolves owlbear_root from OWLBEAR_ROOT env var, fallback to Path(".."); (2) reads owlbear-project.json from CWD via OwlbearProjectFile.model_validate_json; (3) sets project_file to None when file missing or invalid (does NOT raise); (4) yields AppContext
- [ ] __main__.py entry point: from owlbear_mcp_project.server import mcp; mcp.run()
- [ ] stdio transport (mcp.run() default)

### Tools
- [ ] project_info tool: returns dict with keys name, type, project_path (str(CWD)), owlbear_path, created_at when project_file is not None; returns descriptive error string when project_file is None
- [ ] project_list tool: scans {owlbear_root}/data/projects/ directory for .json files (each containing project pointer with path key); returns list of {name, path} dicts; returns empty list when directory is missing or empty

### Resources
- [ ] project://readme resource: returns content of README.md from CWD (utf-8); returns "No README.md found in project root." when file is missing
- [ ] project://structure resource: returns indented directory tree from CWD using build_tree helper; max depth 3; excludes .git, __pycache__, node_modules, .venv, .mypy_cache

### Helpers
- [ ] build_tree(root: Path, max_depth: int = 3, exclude: set[str] | None = None) function in tree.py module; returns indented text tree; pathlib-based, no external deps

### Integration
- [ ] All tests from preceding test task #99 pass GREEN
- [ ] mcp[cli]>=1.26 present in pyproject.toml dependencies (verify #133 completed)

## Context
Depends on #2 (MCP SDK research), #7 (monorepo skeleton), #68 (OwlbearProjectFile model), #99 (TDD test task).
Follow packages/mcp-kanban/src/owlbear_mcp_kanban/server.py as the canonical MCP server pattern.
See docs/research/build-mcp-project-server.md for full research findings.
Registry mechanism for project_list: each project registers as {owlbear_root}/data/projects/{slug}.json during setup (v1 ProjectStore pattern, .85 confidence from research).

[[2026-03-29]] Sun 14:29
## Architecture Review
**Verdict:** REFINE

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| MCP server in packages/mcp-project/ | Vague: no file names, no pattern reference | Rewritten: FastMCP instance, AppContext, lifespan, __main__.py |
| project_info tool | Missing: data source, error behavior | Rewritten: owlbear-project.json source, None fallback |
| project_list tool | Missing: registry mechanism undefined | Rewritten: {owlbear_root}/data/projects/ scan per research |
| project://readme resource | Missing: fallback message | Rewritten: explicit fallback string |
| project://structure resource | Missing: depth limit, exclusion list | Rewritten: max_depth=3, 5 exclusions |
| Server reads .vscode/settings.json | WRONG: source is owlbear-project.json | Removed. Replaced by lifespan AC |
| owlbear-project.json schema line | Out of scope: #68 domain | Removed |
| Register in .vscode/mcp.json | Already done by setup.py (scripts/setup.py:63-82) | Removed (verify only) |
| SKILL.md | Docs-gate deliverable, not impl AC | Removed from impl AC |
| stdio transport | Clear | Kept |

### Architecture Notes
Follows mcp-kanban server.py exactly: FastMCP instance, app_lifespan, AppContext dataclass, __main__.py entry point. Research doc (docs/research/build-mcp-project-server.md) validated all AC items at .85+ confidence.

Key patterns to follow:
- mcp-kanban lifespan: binary discovery replaced by owlbear-project.json parsing
- AppContext via ctx.request_context.lifespan_context (MCP SDK pattern)
- project_file deliberately None (not raised) on missing config for graceful degradation
- project_list registry: v1 ProjectStore pattern, {owlbear_root}/data/projects/{slug}.json
- tree.py helper: pathlib.Path.iterdir() with recursive depth limit (~30 LOC)

Module structure: server.py + tree.py + __main__.py + models.py (existing). Single domain: scope:mcp.

No new security surface since tools are read-only (file reads from known paths, no user-controlled paths that could escape project root).

### Changes Made
- Rewrote all 10 AC lines into 13 precise, testable AC items grouped by category
- Removed wrong config source (.vscode/settings.json replaced by owlbear-project.json)
- Removed out-of-scope items (schema line from #68, SKILL.md for docs gate, mcp.json already done)
- Added build_tree helper AC (tested directly by #99)
- Added integration AC (tests GREEN, mcp[cli] dep)
- Added depends_on: #68 (model), #99 (test task) for TDD compliance

### Dependencies
- Verified: #2 (MCP SDK research) archived
- Verified: #7 (monorepo skeleton) archived
- Added: #68 (OwlbearProjectFile model) in-progress, direct import dependency
- Added: #99 (test task) in ideation, TDD RED phase must complete before builder GREEN
- Related: #133 (mcp[cli] dep) in-progress, builder should verify completion

[[2026-03-29]] Sun 15:34
## Architecture Review (cycle 2)
**Verdict:** APPROVE

### AC Assessment
| AC Line | Assessment | Status |
|---------|------------|--------|
| FastMCP instance owlbear-project in server.py | Matches mcp-kanban pattern exactly | OK |
| AppContext dataclass (slots=True) with 3 fields | Clear, testable fields and types | OK |
| app_lifespan: OWLBEAR_ROOT env var, parse json, None fallback, yields AppContext | 4 specific behaviors, all testable | OK |
| __main__.py entry point | Matches mcp-kanban pattern | OK |
| stdio transport via mcp.run() default | Clear | OK |
| project_info tool: dict with 5 keys, error on None | Return shape and error case specified | OK |
| project_list tool: scan data/projects/, empty list fallback | Registry mechanism clear from research | OK |
| project://readme resource: UTF-8, fallback message | Clear content and error path | OK |
| project://structure resource: build_tree, depth 3, 5 exclusions | Clear constraints | OK |
| build_tree in tree.py: pathlib, no external deps | Good module separation from server.py | OK |
| Tests from #99 pass GREEN | TDD compliance: #99 exists at ideation | OK |
| mcp[cli] in pyproject.toml | #133 done, already present in pyproject.toml | OK |

### Architecture Notes
AC was thoroughly refined in cycle 1. All 13 AC items are precise and testable. Pattern follows mcp-kanban server.py exactly (FastMCP, AppContext, app_lifespan, __main__.py). Single domain: scope:mcp.

Key verifications:
- OwlbearProjectFile model exists in models.py (archived #68), importable
- mcp[cli]>=1.26 already in pyproject.toml (#133 done)
- No security surface: read-only tools, no user-controlled paths, CWD-scoped
- build_tree helper in separate tree.py module: good separation of concerns
- project_file deliberately None on missing config: graceful degradation pattern

### Changes Made
- Approved as-is. AC from cycle 1 refinement is comprehensive.

### Dependencies
- Verified: #2 (MCP SDK research) archived
- Verified: #7 (monorepo skeleton) archived
- Verified: #68 (OwlbearProjectFile model) archived, models.py confirmed
- Verified: #99 (test task) at ideation, TDD dependency tracked in depends_on
- Verified: #133 (mcp[cli] dep) done, pyproject.toml confirmed

[[2026-03-29]] Sun 15:54
## Test-Writer Notes
- Test files: packages/mcp-project/tests/test_server.py, packages/mcp-project/tests/test_tree.py
- Classes: TestFromAC_ServerStructure, TestFromAC_AppContext, TestFromAC_Lifespan, TestFromAC_ProjectInfoTool, TestFromAC_ProjectListTool, TestFromAC_ReadmeResource, TestFromAC_StructureResource, TestFromAC_BuildTree
- Tests per category: happy 22, edge 12, error 6, boundary 9
- Total: 49 tests, all FAIL (ModuleNotFoundError for owlbear_mcp_project.server + .tree) ✓
- ruff: clean
- Every AC line covered by at least one test
