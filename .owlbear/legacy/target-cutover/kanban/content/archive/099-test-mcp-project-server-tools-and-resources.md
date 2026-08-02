---
id: 99
title: 'Test: mcp-project server tools and resources'
status: archived
priority: medium
created: 2026-03-28 04:04:45.348988+01:00
updated: 2026-03-31 06:40:22.635247+02:00
started: 2026-03-31 06:40:02.871761+02:00
completed: 2026-03-31 06:40:02.871761+02:00
tags:
- phase-1
- scope:mcp
- test
depends_on:
- 190
- 191
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-03-30]] Mon 18:39
## Builder Notes
- Umbrella task — no own implementation. Pass-through.
- Subtask #190: archived (server infrastructure + tools, 41 tests pass)
- Subtask #191: at review (resources + tree helper, 13 tests added GREEN)
- Full scope (53 tests): packages/mcp-project/tests/test_server.py + test_tree.py
- Test result: 53 passed, 0 failed
- Lint: ruff clean (packages/mcp-project/src/ + tests/)
- Files: tree.py (new), server.py (resource handlers added in part 2)
- No code changes by this builder — both subtasks already implemented

[[2026-03-30]] Mon 23:41
## Builder Notes (umbrella pass-through, 2026-03-30)
- Subtask #190: archived (server infrastructure + tools)
- Subtask #191: archived (resources + tree helper)
- Full suite: uv run pytest packages/mcp-project/tests/ -q => 91 passed, 0 failed
- No code changes by this builder -- both subtasks already implemented and archived
- Advancing to review as umbrella pass-through

[[2026-03-31]] Tue 04:41
## Test-Writer Notes (re-run pass-through, 2026-03-31)
- Non-implementation task (tagged test) — umbrella with no own AC.
- Tests from prior pipeline run remain valid: commit 23f2d7b, 91 tests (test_server.py + test_tree.py).
- Both subtasks #190 and #191 archived. Passing through to builder.

[[2026-03-31]] Tue 04:44
## Builder Notes (pass-through, 2026-03-31)
- Non-implementation task — umbrella with no own AC.
- Both subtasks #190 and #191 archived.
- Verified: uv run pytest packages/mcp-project/tests/ -q => 91 passed, 0 failed.
- No code changes. Advancing to review.

[[2026-03-31]] Tue 06:06
## Review Evidence
Umbrella task -- both subtasks archived. No own AC.

### Subtask Status
- #190 (server infrastructure + tools): **archived** (auditor confidence 1.00)
- #191 (resources + tree helper): **archived**

### Test Results
- uv run pytest packages/mcp-project/tests/ -q: **91 passed, 0 failed**

### Lint Results
- ruff check packages/mcp-project/: **All checks passed!**

### AC Compliance
| Criterion | Evidence | Status |
|-----------|----------|--------|
| #190 archived | kanban status: archived | PASS |
| #191 archived | kanban status: archived | PASS |
| Full test suite green | 91 passed, 0 failed | PASS |
| Lint clean | ruff all checks passed | PASS |

### Verdict: PASS
Confidence: .97

[[2026-03-31]] Tue 06:18
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Umbrella task; mcp-project already in tech stack table; both subtasks verified this independently |
| 2 | Docstrings | Yes | Pass | Read server.py and tree.py: module docstrings, AppContext, app_lifespan, project_info, project_list, project_readme, project_readme_resource, _build_tree, project_structure all have accurate docstrings; tree.py: build_tree, _iter_children, _append_leaf_files all documented |
| 3 | docs/sources/overview.md | No | N/A | FastMCP patterns already attributed from tasks #17 and #41 (confirmed by both subtask docs gates) |
| 4 | README.md | No | N/A | No CLI commands added |
| 5 | Research doc | No | N/A | No research phase; test umbrella task |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/99-* files present)

[[2026-03-31]] Tue 06:39
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| #190 archived | kanban status: archived (confidence 1.00) | PASS |
| #191 archived | kanban status: archived | PASS |
| 91 tests pass | uv run pytest packages/mcp-project/tests/: 91 passed | PASS |
| Lint clean | ruff check packages/mcp-project/: All checks passed | PASS |

### Test Results
- pytest (task scope): 91 passed, 0 failed
- pytest (full suite): 1926 passed, 157 failed (all pre-existing RED-phase, unrelated to #99)
- ruff: All checks passed

### Upstream Commits
- 23f2d7b test: add failing tests for mcp-project (#99, test-writer)
- 399879b feat: implement server infrastructure (#190, builder)
- a2ee0de test: add malformed JSON contract tests (#190, test-writer)
- 1a0e948 feat: implement tree.py and resource handlers (#191, builder)

### AC Quality Score: 4/5
Umbrella AC was clear. Original scope over-sized (crashed builder twice), architect adapted by splitting into two subtasks. Good recovery.

### Deduction breakdown: none
### Confidence: 1.00
### Action: archive

[[2026-03-31]] Tue 06:40
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 6733b12 | chore | kanban/tasks/099-*.md | #99 |
