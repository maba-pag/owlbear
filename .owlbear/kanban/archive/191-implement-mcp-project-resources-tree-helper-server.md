---
id: 191
title: Implement mcp-project resources + tree helper (server.py part 2)
status: archived
priority: medium
created: 2026-03-29 22:44:09.026693+02:00
updated: 2026-03-30 21:08:55.797075+02:00
started: 2026-03-29 22:44:30.318217+02:00
completed: 2026-03-30 21:08:23.651872+02:00
tags:
- phase-1
- scope:mcp
- test
depends_on:
- 190
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Builder GREEN phase: implement tree.py helper and the two resource handlers (project://readme, project://structure) in server.py to pass the corresponding failing tests from #99.

Parent task: #99 (umbrella). This is subtask 2 of 2.

## Scope

### build_tree helper (tree.py)
Implement in `packages/mcp-project/src/owlbear_mcp_project/tree.py`:
- [ ] build_tree(root, max_depth, exclude) returns indented text tree
- [ ] build_tree respects max_depth parameter (content at max_depth+1 excluded)
- [ ] build_tree respects custom exclude set (named entries hidden)
- [ ] build_tree signature: (root: Path, max_depth: int = 3, exclude: set[str] | None = None)

### project://readme resource
Add to `packages/mcp-project/src/owlbear_mcp_project/server.py`:
- [ ] project://readme returns README.md content (UTF-8) when present
- [ ] project://readme returns exact fallback string when README.md missing

### project://structure resource
Add to `packages/mcp-project/src/owlbear_mcp_project/server.py`:
- [ ] project://structure returns indented tree string with max depth 3
- [ ] project://structure excludes .git, __pycache__, node_modules, .venv, .mypy_cache

## Dependencies
Depends on #190 (server infrastructure must exist before resources can be added to it).

## Test files
- packages/mcp-project/tests/test_server.py — classes: TestFromAC_ReadmeResource, TestFromAC_StructureResource
- packages/mcp-project/tests/test_tree.py — class: TestFromAC_BuildTree

## Exit criteria
All tests in the listed test classes pass. ruff clean.

[[2026-03-30]] Mon 14:21
## Triage Note (2026-03-30)
- Task reached in-progress without test-writer processing. Moved back to todo so the test-writer can create failing tests before the builder implements.
- Test files already listed in body (test_server.py, test_tree.py) -- TW should verify they exist and contain RED tests.

[[2026-03-30]] Mon 15:19
## Test-Writer Notes
- Test file (tree): packages/mcp-project/tests/test_tree.py
- Test file (server): packages/mcp-project/tests/test_server.py
- Classes: TestFromAC_BuildTree, TestFromAC_ReadmeResource (+1 RED), TestFromAC_StructureResource (+1 RED)
- RED tests: 13 total FAIL (11 ImportError tree.py missing + 2 AssertionError resource URIs not registered)
- Existing PASS tests: 11 tests for already-implemented tool behavior (kept, do not break)
- ruff: clean
- AC coverage: all lines covered
  - build_tree(root,max_depth,exclude) -> 11 tests (tree.py ImportError)
  - project://readme content + fallback -> 3 tests (PASS, existing tool impl)
  - project://readme as MCP resource URI -> 1 test FAIL (not registered as resource)
  - project://structure tree+excludes -> 8 tests (PASS, existing tool impl)
  - project://structure as MCP resource URI -> 1 test FAIL (not registered as resource)

[[2026-03-30]] Mon 20:25
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | mcp-project already listed; resource URIs are internal impl detail, no behavior change to document |
| 2 | Docstrings | Yes | Pass | tree.py: module docstring + build_tree docstring complete; server.py: project_readme_resource and project_structure_resource both have accurate docstrings |
| 3 | sources/overview.md | No | N/A | FastMCP @mcp.resource pattern already logged in task #17 (line 481); tree.py uses stdlib pathlib only |
| 4 | README.md | No | N/A | No CLI commands added |
| 5 | Research doc | No | N/A | Builder task, no research phase |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/191-* files present)

[[2026-03-30]] Mon 21:08
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 694cf9f | chore | kanban/tasks/191-*.md | #191 |
