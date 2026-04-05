---
id: 542
title: Add TypedDict return types for outputSchema specificity on mcp-project
status: in-progress
priority: important
created: 2026-04-02T06:16:23.9009603+02:00
updated: 2026-04-04T23:18:58.3294273+02:00
tags:
    - scope:mcp
    - type:build
    - phase-2
depends_on:
    - 543
class: standard
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
