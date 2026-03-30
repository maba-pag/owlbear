---
id: 191
title: Implement mcp-project resources + tree helper (server.py part 2)
status: in-progress
priority: needed
created: 2026-03-29T22:44:09.0266926+02:00
updated: 2026-03-29T22:44:30.3182174+02:00
started: 2026-03-29T22:44:30.3182174+02:00
tags:
    - phase-1
    - scope:mcp
    - test
depends_on:
    - 190
class: standard
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
