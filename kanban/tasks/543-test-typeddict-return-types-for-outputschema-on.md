---
id: 543
title: 'Test: TypedDict return types for outputSchema on mcp-project'
status: todo
priority: important
created: 2026-04-02T07:53:54.8951737+02:00
updated: 2026-04-02T17:00:16.1633676+02:00
started: 2026-04-02T07:54:11.3863978+02:00
tags:
    - scope:mcp
    - ' type:test'
    - ' test'
    - ' phase-2'
blocked: true
block_reason: 'AC4 structurally unsatisfiable: implementation committed (df21f2f) before RED-phase review cleared. Two consecutive FAIL cycles -- infinite loop. Architect must update AC4 (remove or reframe as retrospective pipeline-violation note) before task can advance.'
class: standard
---

## Acceptance Criteria

- [ ] Schema-pinning test: `fn_metadata.output_schema` for `project_info` has top-level `properties` with keys: name, type, project_path, owlbear_path, created_at (all `type: string`)
- [ ] Schema-pinning test: `fn_metadata.output_schema` for `project_list` items schema contains `name` and `path` properties (inside FastMCP `result` wrapper)
- [ ] ToolError test: `project_info` raises `ToolError` (from `mcp.server.fastmcp.exceptions`) when `project_file is None`
- [ ] All new tests fail (RED phase — TypedDicts and ToolError not yet implemented)

## Design Notes

- Access `fn_metadata.output_schema` via `mcp._tool_manager._tools` (same pattern as mcp-kanban schema overrides)
- `project_info` returns TypedDict directly: fields at top-level `properties`
- `project_list` returns `list[TypedDict]`: fields inside FastMCP `{result: {items: ...}}` wrapper
- Test file: `packages/mcp-project/tests/test_typeddict_outputschema_542.py`

[[2026-04-02]] Thu 10:45
## Test-Writer Notes
- Test file: packages/mcp-project/tests/test_typeddict_outputschema_542.py
- Classes: TestFromAC_ProjectInfoOutputSchema, TestFromAC_ProjectListOutputSchema, TestFromAC_ProjectInfoToolError
- Tests per category: happy 0, edge 0, error 3, boundary 12
- Total: 15 tests, all FAIL
- ruff: clean
- AC coverage:
  AC1 (project_info schema): test_project_info_output_schema_has_properties_key, _has_name_property, _has_type_property, _has_project_path_property, _has_owlbear_path_property, _has_created_at_property, _all_required_fields_present (7 tests)
  AC2 (project_list schema): test_project_list_output_schema_has_items, _items_schema_has_name_property, _items_schema_has_path_property, _items_schema_name_is_string_type, _items_schema_path_is_string_type (5 tests)
  AC3 (ToolError): test_project_info_raises_tool_error_when_no_project_file, _does_not_return_string_when_no_project_file, _tool_error_message_describes_missing_config (3 tests)

[[2026-04-02]] Thu 12:15
## Review Evidence
See docs/scratch/543-reviewer.md for full evidence.

[[2026-04-02]] Thu 12:15
## Review Evidence
See docs/scratch/543-reviewer.md for full evidence.

[[2026-04-02]] Thu 12:15
## Review Evidence
See docs/scratch/543-reviewer.md for full evidence.

[[2026-04-02]] Thu 12:15
## Review Evidence
See docs/scratch/543-reviewer.md for full evidence.

[[2026-04-02]] Thu 15:31
## Test-Writer Notes (retry)
- Retry reason: reviewer FAIL was about AC4 (RED phase pipeline violation), not missing tests.
- Builder committed TypedDict implementation (commit 9156065) before reviewer verified RED phase.
- All 15 existing tests: STRONG quality (per reviewer evidence). All PASS against completed implementation.
- AC1 (project_info schema): 7 tests present, all assertions specific and correct.
- AC2 (project_list schema): 5 tests present, items navigation handles both wrapped and unwrapped forms.
- AC3 (ToolError): 3 tests present, pytest.raises(ToolError) with direct async invocation.
- Existing tests preserved unchanged. Builder should close as implementation is complete.

[[2026-04-02]] Thu 16:25
## Builder Notes
- Files changed: packages/mcp-project/tests/test_typeddict_outputschema_542.py (encoding fix only)
- Tests: 15 passed (AC1: 7, AC2: 5, AC3: 3)
- Lint: ruff clean
- Evidence: 15 passed in 0.62s
- Fixes applied: Encoding correction em dash mojibake in committed test file

[[2026-04-02]] Thu 17:00
## Review Evidence (Cycle 2)

**Reviewer:** reviewer-v2 | **Date:** 2026-04-02

### Test Results
- pytest packages/mcp-project/tests/test_typeddict_outputschema_542.py: **15 passed, 0 failed**

### Lint Results
- ruff check packages/mcp-project/: All checks passed!

### TestFromAC Comparison
| Test Class | Change Made | Assessment |
|------------|-------------|------------|
| TestFromAC_ProjectInfoOutputSchema (7 tests) | Encoding fix only (mojibake to em dash); logic unchanged | PRESERVED |
| TestFromAC_ProjectListOutputSchema (5 tests) | Encoding fix only | PRESERVED |
| TestFromAC_ProjectInfoToolError (3 tests) | Encoding fix only | PRESERVED |

### Test Quality
| Dimension | Rating | Notes |
|-----------|--------|-------|
| Assertion specificity | STRONG | Specific field names, types, schema structure |
| Error-path coverage | STRONG | 3 ToolError tests with pytest.raises and message check |
| Mutation resistance | STRONG | Would catch generic-dict regression |
| Test independence | STRONG | No shared mutable state |
| Descriptive names | STRONG | All names describe scenario and outcome |

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: project_info schema has 5 named fields (type:string) | 7 tests, all pass, assertions specific | PASS |
| AC2: project_list items schema has name+path | 5 tests, all pass, items navigation handles both wrapped/unwrapped | PASS |
| AC3: project_info raises ToolError when project_file is None | 3 tests, pytest.raises(ToolError), message check | PASS |
| AC4: All new tests fail (RED phase) | 15 PASSED, 0 FAILED -- implementation committed in df21f2f (cycle 1) | FAIL |

### Verdict: FAIL (Cycle 2) -- confidence .97

AC4 violated for the second consecutive cycle.
Root cause: pipeline ordering violation (implementation committed before RED-phase review).
Resolution: AC4 is structurally unsatisfiable -- implementation is committed and tests correctly pass.
Sending back to todo creates an infinite loop.
BLOCKED for architect resolution: AC4 must be removed or updated to reflect post-implementation reality.
