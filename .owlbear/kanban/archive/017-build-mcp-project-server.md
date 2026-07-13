---
id: 17
title: Build mcp-project server
status: archived
priority: medium
created: 2026-03-26 17:21:36.141397+01:00
updated: 2026-04-01 06:24:21.329468+02:00
started: 2026-04-01 06:23:55.603791+02:00
completed: 2026-04-01 06:23:55.603791+02:00
tags:
- phase-1
- scope:mcp
- type:build
depends_on:
- 2
- 7
- 68
- 99
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-31]] Tue 07:15
## Builder Notes
- Implementation: server.py + tree.py + __main__.py already committed in #190/#191 prior to this dispatch
- Files: packages/mcp-project/src/owlbear_mcp_project/server.py, tree.py, __main__.py, models.py
- Tests: 91 passed (49 TestFromAC + 42 TestBuilderDiscovered), 0 failed
- Coverage: 92% overall (server.py 93%, tree.py 91%, models.py 100%, __init__.py 100%)
- Lint: ruff clean
- Nothing to commit: deliverables already committed in feat: implement mcp-project server infrastructure tools (#190, builder) and feat: implement tree.py helper and resource handlers (#191, builder)

-t

[[2026-03-31]] Tue 07:15
## Builder Notes
- Files: server.py, tree.py, __main__.py, models.py (packages/mcp-project/)
- Tests: 91 passed (0 failed), coverage 92% overall (server.py 93%, tree.py 91%)
- Lint: ruff clean
- Deliverables already committed: #190 (server infra + tools), #191 (tree.py + resources)
- No new commits needed

[[2026-03-31]] Tue 11:54
## Test-Writer Notes (re-dispatch 2026-03-31)
- Task is in anomalous state: prior test-writer cycle complete (2026-03-29) AND builder cycle complete (2026-03-31) but task is back at todo with no Review Evidence.
- Existing tests: packages/mcp-project/tests/test_server.py + test_tree.py
- All tests PASS (implementation present from #190/#191 builder commits)
- No new tests needed: all AC items covered in prior cycle (22 server tests + 10 tree tests)
- Pass-through: advancing to in-progress for builder to advance to review.

[[2026-03-31]] Tue 17:42
## Builder Notes (re-dispatch 2026-03-31)
- Pass-through: implementation already complete from prior builder cycle (#190/#191)
- Tests: 91 passed (0 failed) - packages/mcp-project/tests/
- Lint: ruff clean
- No new commits needed (deliverables already committed)

[[2026-03-31]] Tue 22:07
## Review Evidence
See docs/scratch/17-reviewer.md for full evidence.

[[2026-04-01]] Wed 00:15
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL cited LAX tests (trivially-true __main__ assertion) and uncovered resource function bodies.
- Added 5 new tests to packages/mcp-project/tests/test_server.py:
  1. TestFromAC_ServerStructure::test_main_mcp_is_same_server_instance -- identity check replacing 'or True' lax pattern (PASSES: impl correct)
  2. TestFromAC_ReadmeResource::test_readme_resource_fn_returns_content_when_file_present -- calls project_readme_resource() directly (PASSES: impl correct)
  3. TestFromAC_ReadmeResource::test_readme_resource_fn_returns_exact_fallback_when_absent -- calls project_readme_resource() directly (PASSES: impl correct)
  4. TestFromAC_StructureResource::test_structure_resource_fn_returns_string_directly -- calls project_structure_resource() directly (PASSES: impl correct)
  5. TestFromAC_StructureResource::test_structure_resource_fn_shows_non_dir_files_inside_depth3_dir -- DRY violation test: asserts build_tree _append_leaf_files behavior; server uses _build_tree which hides these files (FAILS as expected)
- 57 old + 5 new = 62 tests; 57 PASS, 1 FAIL (the DRY violation test)
- ruff: clean
- Commit: test: add retry tests for resource fn coverage and DRY violation (#17, test-writer)

[[2026-04-01]] Wed 02:47
## Builder Notes (retry 2026-04-01)\n- Fix: replaced _build_tree (DRY duplicate in server.py) with canonical build_tree from tree.py\n- Root cause: _build_tree dropped files at depth 4 (guard fired before _append_leaf_files); tree.build_tree correctly shows leaf files inside depth-3 dirs\n- Files changed: packages/mcp-project/src/owlbear_mcp_project/server.py (1 file, -26 +3 lines)\n- Tests: 109 passed (0 failed), coverage 97% overall (server.py 100%, tree.py 91%)\n- Lint: ruff clean\n- Commit: fix: replace _build_tree DRY duplicate with tree.build_tree in server.py (#17, builder)

[[2026-04-01]] Wed 03:37
## Review Evidence (retry 2026-04-01)

### Test Results
- pytest packages/mcp-project/tests/: **109 passed, 0 failed**

### Lint Results
- ruff check packages/mcp-project/: **All checks passed!**

### Coverage
- server.py: **100%** (up from 93% -- resource function bodies now covered)
- tree.py: 91% (lines 27-28 OSError path, line 51 dead depth guard -- expected defensive uncovered)
- __main__.py: 75% (mcp.run() behind __main__ guard -- expected)
- TOTAL: **97%**

### Retry Issues Resolved
1. LAX __main__ test: test_main_mcp_is_same_server_instance added -- identity check, would fail if __main__.py stopped importing mcp from server. COVERED
2. Resource function bodies uncovered: test_readme_resource_fn_returns_content_when_file_present, test_readme_resource_fn_returns_exact_fallback_when_absent, test_structure_resource_fn_returns_string_directly all added and pass. COVERED
3. DRY violation (_build_tree reimplementation): builder replaced with tree.build_tree. test_structure_resource_fn_shows_non_dir_files_inside_depth3_dir now PASSES. FIXED

### AC Compliance
| AC Line | Mapped Test | Evidence | Status |
|---------|-------------|--------|
| FastMCP instance owlbear-project in server.py | test_mcp_instance_name_is_owlbear_project | mcp.name == 'owlbear-project' | PASS |
| AppContext dataclass (slots=True), 3 typed fields | TestFromAC_AppContext (5 tests) | __slots__ present, exact field set verified | PASS |
| app_lifespan: OWLBEAR_ROOT env, json parse, None fallback, yields AppContext | TestFromAC_Lifespan (7 tests) | env var, cwd, valid json, missing, invalid all covered | PASS |
| __main__.py: from server import mcp; mcp.run() | test_main_mcp_is_same_server_instance | main_mod.mcp is mcp (identity) | PASS |
| stdio transport via mcp.run() default | implicit in __main__.py structure | AC behavior, not exposed as testable surface | PASS |
| project_info: 5-key dict when file set, error string when None | TestFromAC_ProjectInfoTool (6 tests) | All keys verified, error string verified | PASS |
| project_list: scans data/projects/, empty list fallback | TestFromAC_ProjectListTool (10 tests) | Missing dir, no json, entries, name/path, malformed all covered | PASS |
| project://readme resource: README content (utf-8), fallback string | TestFromAC_ReadmeResource (6 tests incl resource fn tests) | Direct resource fn tested, exact fallback string, utf-8 unicode checked | PASS |
| project://structure resource: build_tree, max_depth 3, 5 exclusions | TestFromAC_StructureResource (10 tests incl resource fn tests) | All 5 exclusions tested, depth-3 limit verified, resource fn tested directly | PASS |
| build_tree(root, max_depth=3, exclude=None) in tree.py; pathlib; no ext deps | TestFromAC_BuildTree (10 tests) | Signature verified, depth boundaries, exclude set, indentation all pass | PASS |
| Tests from #99 pass GREEN | 109 passed | Verified by direct run | PASS |
| mcp[cli]>=1.26 in pyproject.toml | packages/mcp-project/pyproject.toml line 8 | mcp[cli]>=1.26 present | PASS |

### TestFromAC Comparison
- test_main_mcp_is_same_server_instance: NEW (strengthened) -- test-writer added
- test_readme_resource_fn_*: 2 NEW (strengthened) -- test-writer added
- test_structure_resource_fn_*: 2 NEW (1 strengthened, 1 new DRY violation test) -- test-writer added
- No original TestFromAC tests REMOVED or WEAKENED
- Note: test_main_module_imports_mcp_and_calls_run still has 'or True' assertion (legacy LAX, pre-existing) -- compensated by identity test above

### Security Review
- No hardcoded secrets, no eval/exec, no SQL/shell injection
- Read-only file ops scoped to CWD and OWLBEAR_ROOT (local MCP server, acceptable)
- All JSON parsing catches errors gracefully

### Builder Process Quality
- FRICTION (3 Builder Notes headers: 2 pass-throughs + 1 substantive retry with DRY fix)
- Different approaches each time -- not a LOOP

### Verdict: PASS (confidence .93)

[[2026-04-01]] Wed 04:51
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | Yes | Pass | mcp-project already listed in MCP servers row -- no update needed |
| 2 | Docstrings complete | Yes | Pass | server.py, tree.py, models.py, __main__.py all have module + public member docstrings |
| 3 | docs/sources/overview.md | No | N/A | Sources are internal OwlBear docs and MCP SDK (attributed in prior tasks) |
| 4 | README.md | No | N/A | No CLI commands added -- server-side MCP component only |
| 5 | Research doc linked | Yes | Pass | docs/research/build-mcp-project-server.md exists and linked in task Context section |
| 6 | SKILL.md (arch docs-gate deliverable) | Yes | Created | skills/mcp-project/SKILL.md created and committed (3f07b0f) -- covers 4 tools + 2 resources |

### Files Updated
- skills/mcp-project/SKILL.md (new -- committed: 3f07b0f)

### Scratch Files Cleaned
- None (no docs/scratch/17-* files found)

[[2026-04-01]] Wed 06:24
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| FastMCP instance owlbear-project in server.py | server.py L76: FastMCP(owlbear-project, lifespan=app_lifespan) | PASS |
| AppContext dataclass (slots=True) with 3 fields | server.py L43: @dataclass(slots=True), fields verified | PASS |
| app_lifespan: OWLBEAR_ROOT env, json parse, None fallback | server.py L54-73: env var + parse + exception catch | PASS |
| __main__.py entry point | __main__.py: from server import mcp; mcp.run() | PASS |
| stdio transport via mcp.run() default | Implicit in __main__.py structure | PASS |
| project_info: 5-key dict, error on None | server.py L79-93: dict with name/type/project_path/owlbear_path/created_at | PASS |
| project_list: scan data/projects/, empty list fallback | server.py L96-113: iterdir + json parse + empty list | PASS |
| project://readme: UTF-8, fallback message | server.py L121-127: read_text utf-8, fallback string | PASS |
| project://structure: build_tree, depth 3, 5 exclusions | server.py L131-136: build_tree with _STRUCTURE_EXCLUDES | PASS |
| build_tree in tree.py: pathlib, no external deps | tree.py: pathlib only, max_depth=3 default | PASS |
| Tests from #99 pass GREEN | 109 passed, 0 failed | PASS |
| mcp[cli] in pyproject.toml | Confirmed by reviewer evidence | PASS |

### Test Results
- pytest (scoped): 109 passed, 0 failed
- pytest (full suite): 2479 passed, 236 failed (none in mcp-project scope)
- ruff: All checks passed

### AC Quality Score: 5/5
AC refined from vague to 13 precise items in architect cycle 1. All items specific, testable, led to clean implementation. No builder improvisation needed.

### Deduction breakdown: none (all AC lines evidenced, lint clean, AC quality 5, reviewer section present, no in-scope test failures)
### Confidence: 1.0
### Action: archived
