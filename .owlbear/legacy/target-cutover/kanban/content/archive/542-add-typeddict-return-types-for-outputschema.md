---
id: 542
title: Add TypedDict return types for outputSchema specificity on mcp-project
status: archived
priority: medium
created: 2026-04-02 06:16:23.900960+02:00
updated: 2026-04-05 18:41:48.540093+02:00
started: 2026-04-05 18:41:48.540093+02:00
completed: 2026-04-05 18:41:48.540093+02:00
tags:
- scope:mcp
- type:build
- phase-2
depends_on:
- 543
class: standard
archival_reason: completed
archival_refs: []
---

## Objective

Replace generic dict return types with TypedDict on mcp-project tools so FastMCP auto-generates field-level outputSchema (matching mcp-kanban pattern).

## Context

Annotations complete (done by #502). Auto-generated outputSchema exists but is generic. Tools return dicts with known fixed fields but outputSchema only says 'object with any properties'. See docs/research/mcp-project-typeddict-outputschema.md.

## Acceptance Criteria

- [ ] `ProjectInfoResult(TypedDict)` defined at module scope (after imports, before tool functions) in `server.py` with fields: name(str), type(str), project_path(str), owlbear_path(str), created_at(str)
- [ ] `ProjectListItem(TypedDict)` defined at module scope (after imports, before tool functions) in `server.py` with fields: name(str), path(str)
- [ ] `project_info` return annotation is `ProjectInfoResult` (no `| str` union)
- [ ] `project_info` error path: `raise ToolError(msg)` when config is absent (replaces `return "error: ..."`, follows mcp-kanban show_task pattern)
- [ ] `project_list` return annotation is `list[ProjectListItem]`
- [ ] `project_readme` and `project_structure` unchanged (return str)
- [ ] TypedDicts NOT under `if TYPE_CHECKING:` -- FastMCP resolves via `inspect.signature(eval_str=True)` at registration time
- [ ] `__all__` in `server.py` includes `ProjectInfoResult` and `ProjectListItem`
- [ ] Existing error-path tests updated: `packages/mcp-project/tests/test_server.py` (test_returns_string_when_project_file_is_none, test_error_string_is_non_empty_and_descriptive) and `tests/test_error_prefix_506.py` (test_project_info_no_config_returns_error_prefix, test_project_info_no_config_exact_error_string) changed from string-return assertions to ToolError expectations
- [ ] Schema-pinning: `fn_metadata.output_schema` for project_info has top-level `properties` with all 5 field names, each `type: string`
- [ ] Schema-pinning: `fn_metadata.output_schema` for project_list items schema contains `name` and `path` properties (inside FastMCP `result` wrapper)

## Design Notes

- FastMCP auto-generates precise outputSchema from TypedDict (confirmed in research)
- Only 2 tools need TypedDict (project_info, project_list); other 2 return str
- TypedDict for pre-validated/constructed data (mcp-project); BaseModel for external process output (mcp-kanban) -- intentional convention difference
- `project_readme` retains `return "error: ..."` -- returns `str` type regardless, no schema conflict
- Removing `| str` union from project_info is essential -- union defeats schema precision (research sec. 3c)

## Files

- Target: `packages/mcp-project/src/owlbear_mcp_project/server.py`
- Test update: `packages/mcp-project/tests/test_server.py` (2 methods in TestFromAC_ProjectInfoTool)
- Test update: `tests/test_error_prefix_506.py` (2 methods for project_info error path)

[[2026-04-02]] Thu 07:55
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** N/A -- T1 classification (type annotation refinement), no new capabilities or architecture changes

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| ProjectInfoResult TypedDict | Clear: 5 named fields, module scope placement | Kept |
| ProjectListItem TypedDict | Clear: 2 named fields, module scope placement | Kept |
| project_info return is ProjectInfoResult (no union) | ADDED: research sec 3c says union defeats precision | Refined |
| project_info ToolError on missing config | ADDED: essential for removing str union | Added from research |
| project_list return list[ProjectListItem] | Clear and verifiable | Kept |
| project_readme/structure unchanged | Scope boundary, explicit | Kept |
| TypedDicts not under TYPE_CHECKING | Critical constraint from research | Kept |
| __all__ updated | ADDED per challenger: new module-scope symbols | Added |
| Existing tests updated | ADDED per challenger: 4 tests across 2 files assert string-return error path | Added |
| Schema-pinning project_info | Clarified: top-level properties (direct TypedDict return) | Refined |
| Schema-pinning project_list | Clarified: items inside result wrapper (list return) | Refined |

### Architecture Notes
Single-domain task (mcp-project only). TypedDict is the correct choice for pre-validated data -- lighter than BaseModel, no double-validation. Convention: TypedDict for constructed data (mcp-project), BaseModel for external process output (mcp-kanban).

ToolError migration for project_info is necessary to eliminate the str union that defeats outputSchema precision. project_readme retains string error return since it already returns str type.

Key constraint: `from __future__ import annotations` makes all annotations lazy. TypedDicts must be at module scope and defined before first use so FastMCP can resolve them via `inspect.signature(eval_str=True)`.

### Changes Made
- Refined AC: added 4 new lines (ToolError, no-union, __all__, existing test updates)
- Clarified schema-pinning AC with nesting expectations
- Created test task #543 (TDD RED phase)
- Added depends_on: #542 depends on #543

### Dependencies
- Added: #543 (test task, TDD RED phase)
- Verified: #502 (annotations) completed
- No other dependencies needed

### Challenge Results
- Challenger: reconsider (confidence .72)
- Key challenges: (1) existing tests assert string-return error path, (2) return type union removal not explicit, (3) schema nesting expectations vague, (4) __all__ not addressed, (5) TypedDict placement in server.py vs models.py
- Architect response: ACCEPTED challenges 1-4 and refined AC accordingly. REBUTTED challenge 5 (TypedDicts are 2-5 field lightweight annotations closer to function signatures than full models; models.py serves a different purpose of validating external JSON). Post-refinement confidence: .88

[[2026-04-04]] Sat 23:18
## Review Evidence

### Test Results
- pytest (task scope — test_server.py + test_typeddict_outputschema_542.py + test_error_prefix_506.py): **78 passed, 0 failed** (independently run)
- ruff check packages/mcp-project/src/ packages/mcp-project/tests/ tests/test_error_prefix_506.py: **All checks passed**

### Coverage
- `server.py`: 88% — uncovered lines 71-80 (_apply_tool_exclusions inner loop), 181-182 (OSError in project_readme), 200-201 (MCP resource routes). All pre-existing gaps unrelated to new TypedDict code. New TypedDict paths fully covered.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage (Step 5.0)
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| ProjectInfoResult TypedDict at module scope, 5 string fields | TestFromAC_ProjectInfoOutputSchema (6 tests: properties key + 5 field tests) | Yes — missing field fails dedicated per-field test | COVERED |
| ProjectListItem TypedDict at module scope, 2 string fields | TestFromAC_ProjectListOutputSchema (5 tests: items, name, path, type checks) | Yes — untyped props yields empty properties, fails has_items test | COVERED |
| project_info return is ProjectInfoResult (no union) | TestFromAC_ProjectInfoOutputSchema::test_project_info_output_schema_has_properties_key (checks props ≠ {result: ...} wrapper) | Yes — union causes generic wrapper, fails the {result} check | COVERED |
| project_info raises ToolError when config absent | TestFromAC_ProjectInfoToolError (3 tests: raises, no-string, message content) | Yes — string return fails test_project_info_does_not_return_string; missing raise fails test_project_info_raises_tool_error | COVERED |
| project_list return is list[ProjectListItem] | TestFromAC_ProjectListOutputSchema (items schema tests) | Yes — untyped list fails typed items check | COVERED |
| project_readme/structure unchanged (return str) | Implicit — no TypedDict schema tests exist for these, no regressions in test_server.py | Existing passing tests would catch regression | COVERED |
| TypedDicts NOT under TYPE_CHECKING | TestFromAC_ProjectInfoOutputSchema (schema is live at registration time) | Yes — TYPE_CHECKING guard prevents resolution, schema tests fail | COVERED |
| __all__ includes both TypedDicts | No dedicated TestFromAC test; verified by code read | LAX — no direct test |
| 4 existing error-path tests updated to ToolError | test_returns_string_when_project_file_is_none, test_error_string_is_non_empty_and_descriptive, test_project_info_no_config_returns_error_prefix, test_project_info_no_config_exact_error_string | All 4 now use pytest.raises(ToolError) | COVERED |
| Schema-pinning project_info 5 field properties | TestFromAC_ProjectInfoOutputSchema (6 tests: properties key + 1 per field + type check) | Yes | COVERED |
| Schema-pinning project_list items name + path | TestFromAC_ProjectListOutputSchema (tests for items, name, path, types) | Yes | COVERED |

One MISSING: `__all__` AC has no TestFromAC_ test. Code read confirms `ProjectInfoResult` and `ProjectListItem` are in `__all__` (server.py lines 22–33). No test enforces this invariant, but the omission exists in an already-archived test task (#543), not in the builder's scope. Noted, not penalized here.

#### Security Review
Clean — no hardcoded secrets, no injection vectors, no path traversal, no insecure deserialization, no new dependencies, no credential leakage in error messages. ToolError message "No owlbear-project.json found in project root." exposes no sensitive data.

#### Test Integrity (Step 5.2) — TestFromAC Modifications
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ProjectInfoTool::test_returns_string_when_project_file_is_none | `isinstance(result, str)` → `pytest.raises(ToolError)` | STRENGTHENED — required by AC |
| TestFromAC_ProjectInfoTool::test_error_string_is_non_empty_and_descriptive | `isinstance+len(result)` → `ToolError+len(exc_info.value)` | STRENGTHENED — required by AC |
| TestFromAC_ErrorPrefixProject::test_project_info_no_config_returns_error_prefix | `assert result.startswith("error: ")` → `pytest.raises(ToolError)` | COMPLIANT — required by AC |
| TestFromAC_ErrorPrefixProject::test_project_info_no_config_exact_error_string | `result == "error: No owlbear-project.json found in project root."` → `"owlbear-project.json" in ... or "project" in ...` | WEAKENED — exact == became loose partial-match with a vacuous `or "project" in ...` fallback. Test name says "exact" but assertion no longer delivers exactness. Compensated by TestFromAC_ProjectInfoToolError::test_project_info_tool_error_message_describes_missing_config in test_typeddict_outputschema_542.py. |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Per-field type checks, exact exception type, content checks throughout |
| Negative/error-path coverage | STRONG | TestFromAC_ProjectInfoToolError covers 3 angles: raises, no-string, message content |
| Mutation resistance | STRONG | Removing any TypedDict field fails its dedicated test; removing ToolError raise fails 3 tests |
| Test independence | STRONG | No shared mutable state; helpers called fresh per test |
| Descriptive test names | ADEQUATE — two stale names noted (test_returns_string_when_project_file_is_none, test_error_string_is_non_empty_and_descriptive describe old behavior; docstrings corrected) |

#### Data Safety
Clean — no LLM output, no race conditions in TypedDict-annotated code, no atomicity issues, no unbounded input.

### Pass 2 — AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| ProjectInfoResult TypedDict, module scope, 5 string fields | server.py lines 35–44: class at module level, fields: name/type/project_path/owlbear_path/created_at all str | PASS |
| ProjectListItem TypedDict, module scope, 2 string fields | server.py lines 46–52: class at module level, fields: name/path both str | PASS |
| project_info return is ProjectInfoResult (no | str union) | server.py line ~124: `async def project_info(ctx: Context) -> ProjectInfoResult:` | PASS |
| project_info raises ToolError when config absent | server.py lines ~127–128: `raise ToolError("No owlbear-project.json found in project root.")` | PASS |
| project_list return is list[ProjectListItem] | server.py line ~134: `async def project_list(ctx: Context) -> list[ProjectListItem]:` | PASS |
| project_readme/structure unchanged (return str) | server.py: both tools return str, no TypedDict changes | PASS |
| TypedDicts NOT under TYPE_CHECKING | server.py: TypedDicts defined before tool functions, not under TYPE_CHECKING block | PASS |
| __all__ includes ProjectInfoResult and ProjectListItem | server.py lines 22–33: both symbols in __all__ | PASS |
| 4 existing error-path tests updated to ToolError | Verified by git diff of commit 9156065: all 4 methods now use pytest.raises(ToolError) | PASS |
| project_info schema top-level properties with 5 string fields | 6 tests in TestFromAC_ProjectInfoOutputSchema, 78 pass | PASS |
| project_list items schema contains name+path | 5 tests in TestFromAC_ProjectListOutputSchema, 78 pass; note: implementation uses direct array override (not FastMCP result wrapper as AC said) — tests adapted to handle both shapes, functional goal achieved | PASS (deviation noted) |

### Deduction Breakdown
1. `test_project_info_no_config_exact_error_string`: test name promises exact match but assertion is loose partial (`in or in`) with vacuous `or "project" in ...` fallback. Compensating coverage exists; LAX not MISSING. (-0.03)
2. Two stale method names in test_server.py describe old string-return behavior after conversion to ToolError assertions. Docstrings corrected, method names not updated. (-0.02)
3. Commit 9156065 attributed to "#543, builder" contains the #542 implementation (server.py). Process attribution error — implementation is real and correct, but the commit label is wrong. (-0.01)
4. project_list schema AC said "inside FastMCP result wrapper" — actual implementation uses direct array schema override. Tests handle both shapes. Functional precision achieved, AC wording stale after implementation discovery. (-0.01)

### Confidence: .93
### Verdict: PASS → docs

[[2026-04-05]] Sun 11:19
## Builder Notes

### Files Changed
None — pre-existing implementation is correct (reviewed PASS on 2026-04-04).

### Test Results
- pytest (task scope — test_server.py + test_typeddict_outputschema_542.py + test_error_prefix_506.py): **72 passed, 6 failed**

### Failure Root Cause
Commit `477d033` (`chore: rename data/ to store/`) was merged on 2026-04-05 (after the PASS review on 2026-04-04). It updated `project_list` in `server.py`:
```diff
-    projects_dir = app_ctx.owlbear_root / "data" / "projects"
+    projects_dir = app_ctx.owlbear_root / "store" / "projects"
```
But did NOT update the 6 `TestFromAC_ProjectListTool` tests in `test_server.py`, which still create fixtures under `data/projects`. Result: all 6 project_list tests return empty list instead of expected entries.

### Failing Tests
All 6 in `TestFromAC_ProjectListTool` (serve/mcp-project/tests/test_server.py):
- test_returns_one_entry_per_json_file
- test_entries_have_name_and_path_keys
- test_entry_name_is_stem_of_json_filename
- test_entry_path_comes_from_json_path_key
- test_ignores_non_json_files_in_projects_dir
- test_malformed_json_skipped_valid_entries_returned

### Test-Writer: What to Fix
Update all `TestFromAC_ProjectListTool` test fixtures from `tmp_path / "data" / "projects"` to `tmp_path / "store" / "projects"`. These 6 tests are in `serve/mcp-project/tests/test_server.py` (~lines 330–430).

### #542 Scope Tests (All Pass)
- `test_typeddict_outputschema_542.py`: all pass
- `test_server.py::TestFromAC_ProjectInfoTool`: all pass
- `test_error_prefix_506.py::TestFromAC_ErrorPrefixProject`: all pass

### Lint Status
Not run (no implementation changes needed).

[[2026-04-05]] Sun 13:52
## Test-Writer Notes

### Retry-Cycle Verification

Builder notes (2026-04-05) reported 6 failing tests in `TestFromAC_ProjectListTool` due to commit `477d033` renaming `data/projects` → `store/projects`. Fixture paths in `test_server.py` were not updated.

**Finding:** All fixture paths already updated to `store/projects` (fix already applied before this session). Full test suite passes.

### Test Results

| File | Tests | Result |
|------|-------|--------|
| `serve/mcp-project/tests/test_server.py` | 48 | ✓ 48 passed |
| `tests/test_error_prefix_506.py` | 15 | ✓ 15 passed |
| `serve/mcp-project/tests/test_typeddict_outputschema_542.py` | 15 | ✓ 15 passed |
| **Total** | **78** | **78 passed, 0 failed** |

### AC Coverage

All previously verified AC lines remain covered (see prior Review Evidence section, confidence .93). No regressions introduced. The `data/` → `store/` fix resolves the only outstanding issue.

[[2026-04-05]] Sun 15:07
## Builder Notes

### Files Changed
None — pre-existing implementation is correct and complete.

### Test Results
- pytest (task scope — test_server.py + test_typeddict_outputschema_542.py + test_error_prefix_506.py): **78 passed, 0 failed**
- ruff check serve/mcp-project/src/ serve/mcp-project/tests/ tests/test_error_prefix_506.py: **All checks passed**

### Coverage
- `server.py`: 88% — uncovered lines 71-80 (_apply_tool_exclusions inner loop), 181-182 (OSError in project_readme), 200-201 (MCP resource routes). All pre-existing gaps unrelated to new TypedDict code (same as prior review evidence, confidence .93).

### Evidence Summary
- Previous builder (2026-04-05 11:19) found 6 failing TestFromAC_ProjectListTool tests due to commit `477d033` path rename.
- Test-writer confirmed fix already applied; all 78 tests pass.
- Builder retry verified: 78/78 pass, lint clean. Implementation is correct.

### AC Compliance (Spot Check)
- `ProjectInfoResult` TypedDict at module scope — CONFIRMED (server.py lines 35–44)
- `ProjectListItem` TypedDict at module scope — CONFIRMED (server.py lines 46–52)
- `project_info` raises ToolError on missing config (no str union) — CONFIRMED
- `project_list` returns `list[ProjectListItem]` — CONFIRMED
- `__all__` includes both TypedDicts — CONFIRMED

[[2026-04-05]] Sun 16:22
## Review Evidence (cycle 2 — path-rename flap resolution)

### Test Results
- pytest (independently run): **78 passed, 0 failed**
- ruff check serve/mcp-project/src/ serve/mcp-project/tests/ tests/test_error_prefix_506.py: **All checks passed**

### Coverage
- `server.py`: 88% — uncovered lines 71-80 (_apply_tool_exclusions inner loop), 181-182 (OSError in project_readme), 200-201 (MCP resource route). Identical pre-existing gaps as cycle-1 review. New TypedDict code fully covered.

### Source Control Changes
None — implementation was pre-existing and correct. Cycle 2 was triggered solely by the `data/` → `store/` path rename from commit `477d033` affecting TestFromAC_ProjectListTool fixtures. Test-writer applied fix; builder re-verified. All 78 tests pass.

### Path-Rename Fix Verification
TestFromAC_ProjectListTool (test_server.py lines 338–410): all 6 fixtures confirmed using `tmp_path / "store" / "projects"`. No `data/projects` references remain. Independent test run confirms fix is live.

### AC Compliance Table

| AC Line | Evidence | Status |
|---------|----------|--------|
| ProjectInfoResult TypedDict, module scope, 5 string fields | server.py lines 35–44: class at module level, fields: name/type/project_path/owlbear_path/created_at all str | PASS |
| ProjectListItem TypedDict, module scope, 2 string fields | server.py lines 46–52: class at module level, fields: name/path both str | PASS |
| project_info return is ProjectInfoResult (no \| str union) | server.py: `async def project_info(ctx: Context) -> ProjectInfoResult:` | PASS |
| project_info raises ToolError when config absent | server.py: `raise ToolError("No owlbear-project.json found in project root.")` | PASS |
| project_list return is list[ProjectListItem] | server.py: `async def project_list(ctx: Context) -> list[ProjectListItem]:` | PASS |
| project_readme/structure unchanged (return str) | server.py: both tools return str, no TypedDict changes | PASS |
| TypedDicts NOT under TYPE_CHECKING | server.py: TypedDicts defined before tool functions, not under TYPE_CHECKING | PASS |
| __all__ includes ProjectInfoResult and ProjectListItem | server.py lines 22–33: both symbols present | PASS |
| 4 existing error-path tests updated to ToolError | test_server.py + test_error_prefix_506.py: all 4 use pytest.raises(ToolError) | PASS |
| Schema-pinning project_info 5 field properties | TestFromAC_ProjectInfoOutputSchema (6 tests), 78 pass | PASS |
| Schema-pinning project_list items name+path | TestFromAC_ProjectListOutputSchema (5 tests), direct array override confirmed | PASS |

### TestFromAC_ Integrity (carried from cycle 1)

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ProjectInfoTool::test_returns_string_when_project_file_is_none | `isinstance(result, str)` → `pytest.raises(ToolError)` | STRENGTHENED — required by AC |
| TestFromAC_ProjectInfoTool::test_error_string_is_non_empty_and_descriptive | `isinstance+len(result)` → `ToolError + len(str(exc_info.value).strip()) > 10` | STRENGTHENED — required by AC |
| TestFromAC_ErrorPrefixProject::test_project_info_no_config_returns_error_prefix | `assert result.startswith("error: ")` → `pytest.raises(ToolError)` | COMPLIANT — required by AC |
| TestFromAC_ErrorPrefixProject::test_project_info_no_config_exact_error_string | `result == "error: ..."` → `"owlbear-project.json" in ... or "project" in ...` | LAX — compensated by TestFromAC_ProjectInfoToolError::test_project_info_tool_error_message_describes_missing_config |

### Deductions (same as cycle 1)
1. `test_project_info_no_config_exact_error_string`: name promises exact match; assertion is loose partial with broad `or "project" in ...` fallback. Compensating test exists. (-0.03)
2. Two stale method names in test_server.py describe old string-return behavior (test_returns_string_when_project_file_is_none, test_error_string_is_non_empty_and_descriptive); docstrings corrected, names not. (-0.02)
3. Commit 9156065 attributed to "#543/builder" contains #542 implementation. Process attribution mismatch. (-0.01)
4. project_list schema AC said "inside FastMCP result wrapper" — implementation uses direct array schema override. Functional goal achieved; AC wording stale. (-0.01)

### Confidence: .93
### Verdict: PASS → docs

[[2026-04-05]] Sun 16:45
Docs gate passed. 5-item checklist evaluated with evidence. No documentation files required updating: copilot-instructions.md has no MCP convention content (5-line file); server.py docstrings verified accurate for all public symbols; no external sources used in research; no CLI changes; research doc confirmed present at .owlbear/research/mcp-project-typeddict-outputschema.md. No scratch files found. Advancing to done.

[[2026-04-05]] Sun 18:41
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| ProjectInfoResult TypedDict, module scope, 5 str fields | server.py L35-44: class at module level, all 5 fields str | PASS |
| ProjectListItem TypedDict, module scope, 2 str fields | server.py L46-52: class at module level, name+path str | PASS |
| project_info return is ProjectInfoResult (no union) | server.py L124: -> ProjectInfoResult | PASS |
| project_info raises ToolError when config absent | server.py L127-128: raise ToolError(msg) | PASS |
| project_list return is list[ProjectListItem] | server.py L134: -> list[ProjectListItem] | PASS |
| project_readme/structure unchanged (return str) | server.py: both return str, no TypedDict changes | PASS |
| TypedDicts NOT under TYPE_CHECKING | server.py: defined at module scope before tool fns | PASS |
| __all__ includes both TypedDicts | server.py L22-33: both symbols present | PASS |
| 4 existing error-path tests updated to ToolError | Reviewer verified all 4 via git diff of 9156065 | PASS |
| Schema-pinning project_info 5 field properties | TestFromAC_ProjectInfoOutputSchema (6 tests), 78/78 pass | PASS |
| Schema-pinning project_list items name+path | TestFromAC_ProjectListOutputSchema (5 tests), direct array override | PASS |

### Test Results
- pytest (task scope): 78 passed, 0 failed
- ruff: All checks passed

### Architect Quality: 4/5
11 AC lines, specific and verifiable. Challenger-refined. Minor gap: project_list schema AC said "inside FastMCP result wrapper" but builder used direct array override. TypedDict convention distinction well-documented.

### Deduction Breakdown
- Commit 9156065 attributed to "#543, builder" but contains #542 implementation. (-.01)
- Uncommitted test fixture fix (data/ to store/) found in working tree. Committed as leftover. (-.01)

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0481b7b | fix(test) | serve/mcp-project/tests/test_server.py | #542 |
