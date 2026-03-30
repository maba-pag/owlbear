---
id: 99
title: 'Test: mcp-project server tools and resources'
status: in-progress
priority: needed
created: 2026-03-28T04:04:45.3489882+01:00
updated: 2026-03-29T22:45:20.5796602+02:00
tags:
    - phase-1
    - scope:mcp
    - test
depends_on:
    - 190
    - 191
class: standard
---

## Objective
**Umbrella task.** This task has no own acceptance criteria. It is complete when both child tasks have been successfully implemented, reviewed, and archived:

- **#190** — Implement mcp-project server infrastructure + tools (server.py part 1): AppContext, app_lifespan, server structure, project_info tool, project_list tool
- **#191** — Implement mcp-project resources + tree helper (server.py part 2): build_tree, project://readme resource, project://structure resource

## Why split
The original #99 scope (18 AC items across 7 components) exceeded LLM context limits when dispatched as a single builder task, crashing twice. Split into two subtasks with ~11 and ~8 AC items respectively.

## Original context
Tests already written under #17's test-writer phase (49 tests in test_server.py + test_tree.py, all following TestFromAC_ convention). Both subtasks reference these existing test files.
Test files: packages/mcp-project/tests/test_server.py, packages/mcp-project/tests/test_tree.py
Depends on #68 (model, archived). Pattern: #89 TestFromAC_ convention.

[[2026-03-29]] Sun 19:26
## Architecture Review
**Verdict:** APPROVED (AC refined)

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| project_info expected dict | Vague: keys unspecified | Refined: 5 keys listed |
| project_info error string | Adequate | Refined: non-empty str |
| project_list returns list | Vague: entry shape unspecified | Refined: {name, path} dicts, registry path |
| project_list empty list | Clear | Kept |
| project://readme content | Adequate | Added UTF-8 note |
| project://readme fallback | Vague: message unspecified | Refined: exact fallback string |
| project://structure tree | Clear | Kept |
| AppContext populated | Vague: 'correctly' undefined | Refined: 3 typed fields, None on missing/invalid |
| app_lifespan env var | Clear | Split into 2 scenarios |
| build_tree scenarios | Adequate | Added signature spec |
| (missing) Non-.json filter | Not in original AC | Added |
| (missing) project_path value | Implicit | Added: str(CWD) |

### Architecture Notes
- Single domain: scope:mcp (packages/mcp-project/tests/ only)
- Pattern: follows #89 TestFromAC_ convention
- Tests ALREADY EXIST: #17 test-writer wrote 49 tests (test_server.py: 46, test_tree.py: 11) covering all 18 scenarios
- Existing classes: TestFromAC_ServerStructure, TestFromAC_AppContext, TestFromAC_Lifespan, TestFromAC_ProjectInfoTool, TestFromAC_ProjectListTool, TestFromAC_ReadmeResource, TestFromAC_StructureResource, TestFromAC_BuildTree
- Import target: owlbear_mcp_project.server (ModuleNotFoundError in RED)
- server.py/tree.py not in src/ yet (only models.py); builder #17 in-progress
- No security surface: test files only

### Changes Made
- Refined 14 original scenarios into 18 precise testable AC items grouped by component
- Added 3 missing scenarios: project_path str(CWD), non-.json filter, build_tree signature
- Added NOTE: tests exist from #17 pipeline; test-writer verifies
- Added exact fallback string for project://readme from #17 AC

### Dependencies
- Verified: #68 (OwlbearProjectFile model) archived
- Related: #17 (impl task) depends on #99, in-progress (builder)
- Pattern ref: #89 (mcp-kanban test task) at review

[[2026-03-29]] Sun 19:57
## Test-Writer Notes
- Test files: packages/mcp-project/tests/test_server.py, packages/mcp-project/tests/test_tree.py
- Classes: TestFromAC_ServerStructure, TestFromAC_AppContext, TestFromAC_Lifespan, TestFromAC_ProjectInfoTool, TestFromAC_ProjectListTool, TestFromAC_ReadmeResource, TestFromAC_StructureResource, TestFromAC_BuildTree
- Tests per category: happy 15, edge 6, error 7, boundary 21
- Total: 49 tests, all FAIL with ModuleNotFoundError (owlbear_mcp_project.server + .tree)
- ruff: clean
- Commit: 23f2d7b
- AC coverage: all 18 scenarios covered across 8 TestFromAC_ classes
- Note: tests verified as pre-existing from #17 pipeline; line-ending normalization commit only

## Split into subtasks (2026-03-29)\nUmbrella task — no own AC. Blocked until #190 and #191 are both archived.\n- #190: server infrastructure + tools (in-progress)\n- #191: resources + tree helper (in-progress, depends on #190)
