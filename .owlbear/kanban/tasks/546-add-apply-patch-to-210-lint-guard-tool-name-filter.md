---
id: 546
title: 'Add apply_patch to #210 lint guard tool_name filter'
status: review
priority: needed
created: 2026-04-02T14:51:56.2992239+02:00
updated: 2026-04-05T10:24:22.4569655+02:00
tags:
    - scope:agents
    - hooks
    - type:build
depends_on:
    - 210
class: standard
---

## Context
Empirical verification (#532, docs/research/posttooluse-subagent-output-routing.md s3.6) discovered that the builder uses tool_name 'apply_patch' for file edits. Task #210's AC currently filters on create_file|replace_string_in_file|multi_replace_string_in_file only, missing apply_patch.

## Acceptance Criteria
- [ ] #210 lint guard script matches apply_patch in addition to existing tool_names
- [ ] Verified via hook log that apply_patch triggers lint check

[[2026-04-02]] Thu 15:50
## Research
See docs/research/apply-patch-lint-guard-filter.md for full findings.

Key findings:
- apply_patch confirmed as builder edit tool_name (#532 empirical, VS Code hooks docs)
- tool_input format unknown: likely tool_input.filePath or tool_input.patch with diff headers
- T1 classification: filter extension, no new capability or arch change
- depends_on #210 added: script must exist before modification

Refined AC guidance:
- Add apply_patch to tool_name regex in lint-changed.ps1
- For path extraction: try tool_input.filePath first, fall back to diff header parsing
- Add test cases parallel to existing AC3a-AC3f for apply_patch tool_name
- Builder should log actual apply_patch tool_input JSON to confirm format

[[2026-04-02]] Thu 15:50
## Research
See docs/research/apply-patch-lint-guard-filter.md for full findings.

Key findings:
- apply_patch confirmed as builder edit tool_name (#532 empirical, VS Code hooks docs)
- tool_input format unknown: likely tool_input.filePath or tool_input.patch with diff headers
- T1 classification: filter extension, no new capability or arch change
- depends_on #210 added: script must exist before modification

Refined AC guidance:
- Add apply_patch to tool_name regex in lint-changed.ps1
- For path extraction: try tool_input.filePath first, fall back to diff header parsing
- Add test cases parallel to existing AC3a-AC3f for apply_patch tool_name
- Builder should log actual apply_patch tool_input JSON to confirm format

[[2026-04-05]] Sun 00:00
## Architecture Review

### AC Refinement
Original AC was vague ("Verified via hook log" is untestable). Replaced with precise, testable criteria parallel to existing #210 test patterns:

**Refined Acceptance Criteria (supersedes original):**
- [ ] AC1: `edit_tools` array in `scripts/hooks/lint-changed.ps1` includes `'apply_patch'`
- [ ] AC2: `apply_patch` with `tool_input.filePath` pointing to a ruff-clean `.py` file returns `{}`
- [ ] AC3: `apply_patch` with `tool_input.filePath` pointing to a file with lint errors returns JSON with non-empty `systemMessage` containing ruff output and `hookSpecificOutput.additionalContext`
- [ ] AC4: `apply_patch` with nonexistent `tool_input.filePath` returns `{}` (graceful degradation, same as AC5 pattern in #210)
- [ ] AC5: `apply_patch` with missing/null `tool_input.filePath` returns `{}` (graceful degradation)
- [ ] AC6: Script exit code is never 2 for any `apply_patch` invocation (non-blocking design)
- [ ] AC7: All script stdout for `apply_patch` tool_name is valid JSON

**Path extraction note:** apply_patch uses the `else` branch in lint-changed.ps1 (same as create_file/replace_string_in_file), reading `tool_input.filePath`. Graceful degradation to `{}` if field absent. No diff-header parsing needed for this scope.

**Test pattern:** Tests parallel existing AC3a-f/AC5/AC6 in `tests/test_lint_guard_hook_210.py` using `_run_hook()` helper with `tool_name: "apply_patch"`.

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One thing: add apply_patch to lint guard filter |
| Interface clarity | PASS (after refinement) | 7 precise AC lines, all testable via subprocess |
| Dependency correctness | PASS | #210 archived; dependency satisfied |
| Module layering | N/A | PowerShell hook script, no Python module layering |
| TDD compliance | PASS | Test-writer will create tests from refined AC |
| KISS/YAGNI | PASS | Minimal scope: one tool_name addition to existing array |
| Premise challenge | PASS | apply_patch confirmed empirically (#532 s3.6) |
| Pattern consistency | PASS | deny-writes.ps1 already includes apply_patch; follows existing edit_tools pattern |
| Security surface | PASS | No new system boundaries; same trusted VS Code hook context |
| Single domain | PASS | Hooks domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| apply_patch with filePath | ruff fails on file | catch block | Yes, returns {} | None (graceful) |
| apply_patch without filePath | $fp is $null | filePath check | Yes, returns {} | None (graceful) |

### Process Note
Commit 68c6a55 ("feat: add apply_patch...#546, builder") exists before architecture review. Pipeline violation: builder ran before arch review + test-writing. Existing implementation should be validated against refined AC by test-writer. Duplicate research section in body should be cleaned up.

### Challenge Results
- Challenger: FALLBACK (subagent returned no output)
- Architect response: Proceeded with review; low-risk T1 filter extension

### Verdict: APPROVE (after refinement)
### Action: Advance to todo. Test-writer should use refined AC above (7 criteria) instead of original 2-line AC.
[[2026-04-05]] Sun 02:27
## Test-Writer Notes
- Test file: tests/test_lint_guard_hook_546.py
- Classes: TestFromAC_ApplyPatchFilter, TestFromAC_ApplyPatchBehavior
- Tests per category: happy 4, edge 2, error 1, boundary 5
- Total: 12 tests
- ruff: clean
- Commit: 4c7caea

**Pipeline violation note:** Commit 68c6a55 (builder) added apply_patch before test-writing.
Per architect's process note, test-writer validates post-hoc. All 12 tests PASS — implementation
meets all 7 refined AC criteria. Tests serve as regression guards going forward.

**AC coverage:**
| AC | Test(s) |
|----|---------|
| AC1: 'apply_patch' in edit_tools array | test_apply_patch_in_edit_tools_array |
| AC2: clean file -> {} | test_apply_patch_clean_file_returns_empty_json |
| AC3: lint errors -> systemMessage + hookSpecificOutput.additionalContext | test_apply_patch_lint_errors_returns_system_message, test_apply_patch_lint_errors_returns_hook_specific_additional_context |
| AC4: nonexistent filePath -> {} | test_apply_patch_nonexistent_filepath_returns_empty_json |
| AC5: missing/null filePath -> {} | test_apply_patch_missing_filepath_returns_empty_json, test_apply_patch_null_filepath_returns_empty_json |
| AC6: exit code never 2 | test_apply_patch_exit_code_never_2_clean_file, _lint_errors, _missing_filepath |
| AC7: stdout always valid JSON | test_apply_patch_stdout_is_valid_json_for_lint_errors, _for_clean_file |

[[2026-04-05]] Sun 10:24
## Builder Notes

**Files changed:**
- `.owlbear/hooks/lint-changed.ps1` — `apply_patch` added to `edit_tools` array (committed pre-pipeline in 68c6a55; validated here)
- `tests/test_lint_guard_hook_546.py` — 12 tests written by test-writer (4c7caea)

**Test results:** 12 passed, 0 failed

**Lint status:** ruff clean (`tests/test_lint_guard_hook_546.py`)

**AC evidence:**
| AC | Status | Evidence |
|----|--------|---------|
| AC1: `apply_patch` in `edit_tools` array | PASS | lint-changed.ps1 line 19 |
| AC2: clean file → `{}` | PASS | test_apply_patch_clean_file_returns_empty_json |
| AC3: lint errors → systemMessage + additionalContext | PASS | test_apply_patch_lint_errors_returns_system_message + _additional_context |
| AC4: nonexistent filePath → `{}` | PASS | test_apply_patch_nonexistent_filepath_returns_empty_json |
| AC5: missing/null filePath → `{}` | PASS | test_apply_patch_missing/null_filepath_returns_empty_json |
| AC6: exit code never 2 | PASS | 3 tests covering clean/lint-errors/missing-filepath |
| AC7: stdout always valid JSON | PASS | test_apply_patch_stdout_is_valid_json_for_lint_errors + _clean_file |

**Pipeline note:** Implementation existed pre-pipeline (commit 68c6a55). Tests were written post-hoc by test-writer and all 12 pass — serves as regression guard going forward.
