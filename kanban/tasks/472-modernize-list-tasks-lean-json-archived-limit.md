---
id: 472
title: 'Modernize list_tasks: lean JSON, archived, limit, blocked tri-state'
status: in-progress
priority: needed
created: 2026-03-31T05:21:21.4356377+02:00
updated: 2026-03-31T07:36:54.5457196+02:00
tags:
    - scope:mcp
    - ' type:build'
    - ' phase-2'
class: standard
---

## Acceptance Criteria\n\n- [ ] Add `archived: bool = False` parameter to `list_tasks` tool\n- [ ] When True, pass `--archived` flag to kanban-md list\n- [ ] Add `limit: int = 0` parameter (0 = no limit); when > 0, pass `--limit N`\n- [ ] Add `reverse: bool = False` parameter; when True, pass `--reverse`\n- [ ] Change `block_filter: str` to `blocked: bool | None = None`: None = no filter, True = `--blocked`, False = `--not-blocked`\n- [ ] Switch `list_tasks` output from `--compact` to `--json` + server-side stripping of `body`, `file`, `created`, `updated` fields (lean JSON)\n- [ ] Tests cover: archived flag, limit, reverse, blocked tri-state, lean JSON output (no body in result)\n- [ ] Update mcp-kanban SKILL.md to document changed and new parameters\n\n## Design Notes\n\n- `blocked` as `Optional[bool]` replaces the string enum pattern with a natural tri-state: None/True/False\n- Lean JSON: use `json.loads()` on kanban-md output, strip noisy fields, `json.dumps()` back\n- This is a breaking change for `block_filter` parameter name

[[2026-03-31]] Tue 06:28
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| Add archived: bool = False, pass --archived | Clear, testable, flag confirmed in kanban-md v0.33.0 | Keep |
| Add limit: int = 0, pass --limit N when >0 | Clear, testable, flag confirmed (-n/--limit) | Keep |
| Add reverse: bool = False, pass --reverse | Clear, testable, flag confirmed (-r/--reverse) | Keep |
| Change block_filter to blocked: bool or None tri-state | Well-designed, clear mapping (True/False/None) | Keep |
| Switch --compact to --json + strip body/file/created/updated | Clear, fields verified in JSON output schema | Keep |
| Tests cover all new params + lean JSON | Test-writer has clear guidance | Keep |
| Update mcp-kanban SKILL.md | Single-line table update, same domain | Keep |

### Architecture Notes
- All required CLI flags already exist in kanban-md v0.33.0 (verified via list --help)
- JSON output schema verified: fields id, title, status, priority, created, updated, tags, depends_on, class, body, file. Stripping body/file/created/updated leaves a clean listing set.
- blocked: bool or None is a clean tri-state that maps to JSON Schema anyOf[boolean, null]. FastMCP handles Optional[bool] correctly (.85 confidence per research doc).
- Breaking change (block_filter renamed to blocked) is acceptable per project principles (no backwards compat). All callers are internal OwlBear agents.
- Existing pattern: list_tasks builds args list from params, calls _run_kanban. New params follow same pattern. Lean JSON adds ~5 LOC of json.loads/dumps.
- Existing test_list_tasks_success_passes_args asserts --compact in args. Test-writer must update existing tests to assert --json instead when writing new test coverage.
- Note: Tasks #478 and #479 (ideation) duplicate this scope as separate TDD pair. They are redundant since the pipeline's test-writer/builder roles handle TDD naturally on #472. Recommend archiving #478/#479 as superseded.

### Changes Made
- Reviewed and approved AC as-is (no refinement needed)
- Moved to todo

### Dependencies
- No depends_on listed; none required (list_tasks is self-contained)
- Verified: no upstream tasks needed; kanban-md v0.33.0 already supports all flags

[[2026-03-31]] Tue 06:30
## Update: Add outputSchema\n\n- [ ] Define outputSchema for list_tasks (array of lean task objects: id, title, status, priority, tags, blocked, block_reason, claimed_by, depends_on)\n- [ ] Return structuredContent alongside text content

[[2026-03-31]] Tue 07:36
## Test-Writer Notes
- Test file: tests/test_mcp_kanban_list_tasks_472.py
- Classes: TestFromAC_ListTasksSignature, TestFromAC_ListTasksCliFlags, TestFromAC_ListTasksLeanJson, TestFromAC_ListTasksStructuredContent
- Tests per category: happy 8, edge 6, error 0, boundary 2
- Total: 21 tests, all FAIL ✓
- ruff: clean
- AC coverage:
  - archived param: test_has_archived_parameter_with_bool_default_false, test_archived_true_passes_archived_flag, test_archived_false_omits_archived_flag
  - limit param: test_has_limit_parameter_with_int_default_zero, test_limit_positive_passes_limit_flag_and_value, test_limit_zero_omits_limit_flag, test_limit_one_passes_limit_1
  - reverse param: test_has_reverse_parameter_with_bool_default_false, test_reverse_true_passes_reverse_flag, test_reverse_false_omits_reverse_flag
  - blocked tri-state: test_has_blocked_parameter_with_none_default, test_blocked_true_passes_blocked_flag, test_blocked_false_passes_not_blocked_flag, test_blocked_none_passes_no_block_filter_flags
  - block_filter removed: test_block_filter_param_no_longer_exists
  - --json not --compact: test_uses_json_flag_not_compact
  - lean JSON: test_stripped_fields_absent_from_result, test_all_tasks_in_list_have_fields_stripped
  - outputSchema: test_list_tasks_tool_has_output_schema, test_output_schema_is_array_type, test_result_is_lean_json_array_with_no_stripped_fields
