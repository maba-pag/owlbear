---
id: 190
title: Implement mcp-project server infrastructure + tools (server.py part 1)
status: archived
priority: medium
created: 2026-03-29 22:43:56.360255+02:00
updated: 2026-03-30 07:12:41.833386+02:00
started: 2026-03-29 22:44:26.874600+02:00
completed: 2026-03-30 07:12:21.406519+02:00
tags:
- phase-1
- scope:mcp
- test
depends_on:
- 68
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Builder GREEN phase: implement server.py infrastructure (AppContext, app_lifespan, server structure) and the two tool handlers (project_info, project_list) to pass the corresponding failing tests from #99.

Parent task: #99 (umbrella). This is subtask 1 of 2.

## Scope
Implement in `packages/mcp-project/src/owlbear_mcp_project/server.py`:

### ServerStructure
- [ ] FastMCP app named "owlbear-project" exists and is importable as `mcp`

### AppContext
- [ ] AppContext has exactly 3 fields: project_file (OwlbearProjectFile | None), project_root (Path), owlbear_root (Path)
- [ ] AppContext.project_file is None when owlbear-project.json missing or invalid

### app_lifespan
- [ ] app_lifespan resolves owlbear_root from OWLBEAR_ROOT env var
- [ ] app_lifespan falls back to Path('..') when OWLBEAR_ROOT not set

### project_info tool
- [ ] project_info returns dict with keys (name, type, project_path, owlbear_path, created_at) when owlbear-project.json exists
- [ ] project_info returns descriptive error string (non-empty str) when owlbear-project.json missing
- [ ] project_path value is str(CWD)

### project_list tool
- [ ] project_list returns list of {name, path} dicts from {owlbear_root}/data/projects/*.json
- [ ] project_list returns empty list when registry dir missing
- [ ] project_list ignores non-.json files in registry dir

## Test files
- packages/mcp-project/tests/test_server.py — classes: TestFromAC_ServerStructure, TestFromAC_AppContext, TestFromAC_Lifespan, TestFromAC_ProjectInfoTool, TestFromAC_ProjectListTool

## Exit criteria
All tests in the listed test classes pass. ruff clean.

[[2026-03-30]] Mon 04:54
## Builder Notes
- Files changed: packages/mcp-project/src/owlbear_mcp_project/server.py (new), packages/mcp-project/src/owlbear_mcp_project/__main__.py (new)
- Tests: 39 passed, coverage 95% on server.py (100% models, 100% init)
- Lint: ruff clean
- Evidence: uv run pytest packages/mcp-project/tests/test_server.py -q => 39 passed
- Fixes applied: Removed unused noqa directives flagged by VS Code lint

[[2026-03-30]] Mon 05:20
## Review Evidence
See docs/scratch/190-reviewer.md for full evidence.

[[2026-03-30]] Mon 05:27
## Test-Writer Notes (retry)\n- Retry reason: reviewer FAIL cited untested project_list error path (L103-105: except JSONDecodeError/OSError)\n- Added 2 new tests to TestFromAC_ProjectListTool:\n  - test_silently_skips_malformed_json_no_exception: malformed-only dir returns []\n  - test_malformed_json_skipped_valid_entries_returned: mixed dir returns only valid entries\n- Preserved: 39 existing tests (all PASS)\n- New tests PASS against existing impl (behavior already coded, tests are regression guards)\n- ruff: clean\n- Total: 41 tests

[[2026-03-30]] Mon 06:05
## Builder Notes (retry)\n- Retry trigger: reviewer FAIL - untested project_list error path\n- Files changed: none (implementation was complete; test-writer added 2 regression guards)\n- Tests: 41 passed, coverage 97% overall (98% server.py, 100% models/init)\n- Lint: ruff clean\n- Evidence: uv run pytest packages/mcp-project/tests/test_server.py -q => 41 passed in 0.82s\n- Fixes applied: None - existing impl at L103-105 already catches JSONDecodeError/OSError

[[2026-03-30]] Mon 06:40
## Review Evidence (retry)
- pytest: 41 passed, 0 failed (was 39; +2 new tests)
- ruff: All checks passed
- coverage server.py: 98% (L129-130: _build_tree PermissionError/OSError â€” informational, extra-scope)

### Previous FAIL resolution
Prior FAIL: project_list L103-105 except path untested.
Fix: test-writer added 2 new tests to TestFromAC_ProjectListTool:
  - test_silently_skips_malformed_json_no_exception: creates broken.json, asserts result == []
  - test_malformed_json_skipped_valid_entries_returned: mixed dir, asserts only valid entry returned

Both tests STRONG: would fail if except were changed to raise.

### TestFromAC Comparison (retry)
Builder changed: no test file changes in retry. Test-writer added 2 methods to TestFromAC_ProjectListTool.
All prior TestFromAC methods: PRESERVED. New additions: STRENGTHENED.

### AC Compliance
| AC Line | Mapped Test(s) | Status |
|---------|----------------|--------|
| FastMCP named owlbear-project | test_mcp_instance_name_is_owlbear_project | PASS |
| AppContext 3 fields | test_app_context_has_exactly_three_fields | PASS |
| project_file None when json missing | test_lifespan_sets_project_file_none_when_json_missing | PASS |
| project_file None when json invalid | test_lifespan_sets_project_file_none_when_json_invalid | PASS |
| app_lifespan OWLBEAR_ROOT env var | test_lifespan_uses_owlbear_root_env_var | PASS |
| app_lifespan fallback Path(..) | test_lifespan_falls_back_to_dotdot_when_no_env_var | PASS |
| project_info 5-key dict | test_dict_contains_all_five_required_keys | PASS |
| project_info error string | test_returns_string_when_project_file_is_none | PASS |
| project_path is str(CWD) | test_project_path_is_string_of_project_root | PASS |
| project_list name+path entries | test_entries_have_name_and_path_keys + test_entry_name_is_stem + test_entry_path_comes_from_json | PASS |
| project_list empty when dir missing | test_returns_empty_list_when_projects_dir_missing | PASS |
| project_list ignores non-.json | test_ignores_non_json_files_in_projects_dir | PASS |
| [NEW] malformed json silently skipped | test_silently_skips_malformed_json_no_exception + test_malformed_json_skipped_valid_entries_returned | PASS |

### Security
No issues. No shell=True, no eval, no hardcoded secrets, no user-controlled path traversal.

### Verdict: PASS
Confidence: .93 (above .90 threshold)
All AC lines verified. Previously untested error path now covered by 2 strong tests.

[[2026-03-30]] Mon 06:49
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | mcp-project already in tech stack + directory table; no new behavior/conventions added |
| 2 | Docstrings | Yes | Pass | server.py: module, AppContext, app_lifespan, project_info, project_list, project_readme, _build_tree, project_structure all have accurate docstrings; __main__.py: module docstring present |
| 3 | docs/sources/overview.md | No | N/A | FastMCP lifespan+Context+tool-decorator patterns already attributed from tasks #17 and #41 |
| 4 | README.md | No | N/A | No new CLI commands; __main__.py entry point is MCP-internal |
| 5 | Research doc | No | N/A | No research phase for this builder task |

### Files Updated
- None

### Scratch Files Cleaned
- None (docs/scratch/190-reviewer.md referenced in body but not present on disk)

[[2026-03-30]] Mon 07:12
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| FastMCP named owlbear-project | server.py L77, test passes | PASS |
| AppContext 3 fields | server.py L40-44, test passes | PASS |
| project_file None when missing | server.py L63-67, test passes | PASS |
| project_file None when invalid | server.py L66 except clause, test passes | PASS |
| app_lifespan OWLBEAR_ROOT env var | server.py L56-57, test passes | PASS |
| app_lifespan fallback Path(..) | server.py L57, test passes | PASS |
| project_info 5-key dict | server.py L82-90, test passes | PASS |
| project_info error string | server.py L81-82, test passes | PASS |
| project_path is str(CWD) | server.py L88, test passes | PASS |
| project_list name+path dicts | server.py L100-108, tests pass | PASS |
| project_list empty when dir missing | server.py L98-99, test passes | PASS |
| project_list ignores non-.json | server.py L102, test passes | PASS |

### Test Results
- pytest (task-specific): 41 passed, 0 failed
- pytest (full suite): 5 collection errors (pre-existing RED-phase: planner, voice, mcp-project tree) - zero regressions from #190
- ruff: clean in scope (2 violations in #196 file, out of scope)

### Upstream Commits
- a2ee0de test: add malformed JSON contract tests (#190, test-writer)
- 399879b feat: implement mcp-project server infrastructure (#190, builder)

### AC Quality Score: 4/5
AC was specific and testable. Minor gap: malformed JSON error path discovered by reviewer (not in original AC), resolved via test-writer retry. Overall strong architect work.

### Deduction breakdown: none (all AC lines have evidence, lint clean in scope, AC quality 4, reviewer evidence present, no task-scope failures)
### Confidence: 1.00
### Action: archive

[[2026-03-30]] Mon 07:12
## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 1244cbd | chore | kanban/tasks/190-*.md | #190 |
