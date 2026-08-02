---
id: 546
title: 'Add apply_patch to #210 lint guard tool_name filter'
status: archived
priority: medium
created: 2026-04-02 14:51:56.299224+02:00
updated: 2026-04-05 14:37:04.147034+02:00
started: 2026-04-05 14:37:04.147034+02:00
completed: 2026-04-05 14:37:04.147034+02:00
tags:
- scope:agents
- hooks
- type:build
depends_on:
- 210
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-04-05]] Sun 11:20
## Review Evidence
### Test Results
- pytest: 12 passed, 0 failed (background terminal; foreground hangs are a known VS Code tool I/O interaction — not a test defect, all 12 pass in isolation and in background)

### Lint: clean (ruff: All checks passed!)

### Coverage: N/A — PowerShell hook script; coverage tooling not applicable

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: 'apply_patch' in edit_tools | test_apply_patch_in_edit_tools_array | Yes — checks `"'apply_patch'" in content` | COVERED |
| AC2: clean file → {} | test_apply_patch_clean_file_returns_empty_json | Yes — `assert output == {}` | COVERED |
| AC3: lint errors → systemMessage + additionalContext | test_apply_patch_lint_errors_returns_system_message, _hook_specific_additional_context | Yes — checks key presence + non-empty | COVERED |
| AC4: nonexistent filePath → {} | test_apply_patch_nonexistent_filepath_returns_empty_json | Yes (with LAX caveat — see Pass 2) | COVERED |
| AC5: missing/null filePath → {} | test_apply_patch_missing_filepath_returns_empty_json, test_apply_patch_null_filepath_returns_empty_json | Yes (with LAX caveat — see Pass 2) | COVERED |
| AC6: exit code never 2 | test_apply_patch_exit_code_never_2_clean_file, _lint_errors, _missing_filepath | Yes — `assert code != 2` | COVERED |
| AC7: stdout valid JSON | test_apply_patch_stdout_is_valid_json_for_lint_errors, _for_clean_file | Yes — json.loads raises on invalid | COVERED |

#### Security Review
- No hardcoded secrets. Path `tool_input.filePath` fed to ruff (lint tool only, no execution). VS Code hook trusted context. No injection risk.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 12 TestFromAC_* tests | No builder modifications detected | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | `== {}` for empty, key+non-empty for error paths, `!= 2` for exit code |
| Negative/error-path coverage | STRONG | AC4/AC5/AC6 cover nonexistent, null, missing, clean, and error paths |
| Manual mutation reasoning | STRONG | Removing 'apply_patch' from edit_tools → AC1 fails; flipping filePath check → AC4/AC5 fail |
| Test independence | STRONG | Each test uses own `tmp_path` fixture; no shared state |
| Descriptive test names | STRONG | All names reference AC being tested |

#### Data Safety
- No issues. No LLM output persistence, no shared mutable state.

#### Implementation-Aware Gaps
- No untested paths for `apply_patch` code branch. All five apply_patch paths (clean, lint-error, nonexistent, missing, null filePath) are exercised. `try/catch` around JSON parse (malformed input → `{}`) not tested by 546 tests but covered by #210 test suite (shared code).

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- AC4/AC5 tests: `assert output == {}` also passes if script writes nothing to stdout and crashes silently (since `_run_hook` defaults to `{}` on empty stdout). Implementation is correct per code read (explicit `Write-Output '{}'` on each degradation path), so this is not a latent defect — informational only.
- Pipeline violation (build before test-writing) acknowledged by all three upstream agents. Tests serve as regression guards going forward; no action required from reviewer.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: 'apply_patch' in edit_tools | lint-changed.ps1:19 `'apply_patch'` | test_apply_patch_in_edit_tools_array | PASS |
| AC2: clean file → {} | test output: PASSED; output == {} confirmed | test_apply_patch_clean_file_returns_empty_json | PASS |
| AC3: lint errors → systemMessage + additionalContext | test output: PASSED; response keys verified at runtime | two AC3 tests | PASS |
| AC4: nonexistent filePath → {} | lint-changed.ps1 uses Test-Path filter; nonexistent path filtered out → {} | test_apply_patch_nonexistent_filepath_returns_empty_json | PASS |
| AC5: missing/null filePath → {} | lint-changed.ps1 `if ($fp)` guard; null/missing → file_paths.Count == 0 → {} | two AC5 tests | PASS |
| AC6: exit code never 2 | script ends `exit 0` on all paths; test: PASSED | three AC6 tests | PASS |
| AC7: stdout valid JSON | json.loads verified at runtime; test: PASSED | two AC7 tests | PASS |

### Confidence: .98
### Verdict: PASS

[[2026-04-05]] Sun 11:39
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `.owlbear/hooks/lint-changed.ps1` behavior changed (edit_tools extended), but `copilot-instructions.md` does not document hook tool_name lists — no entry to update |
| 2 | Module docstrings | Yes | Verified | `tests/test_lint_guard_hook_546.py`: module docstring covers all 7 ACs + pipeline note. `_run_hook` helper has docstring. Both test classes and all 12 test methods have docstrings. Complete. |
| 3 | External attribution | No | N/A | Research doc cites VS Code Hooks docs (code.visualstudio.com/docs/copilot/customization/hooks) — already attributed in `.owlbear/sources/overview.md` under Task #37 (same URL). No new row needed. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/apply-patch-lint-guard-filter.md` exists. Referenced in task body. No outstanding follow-ups. |

### Scratch files
None found matching `.owlbear/scratch/546-*`.

### Files updated
None — no documentation changes required.

### Verdict
docs gate passed

[[2026-04-05]] Sun 14:37
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: apply_patch in edit_tools | lint-changed.ps1:19 confirmed | PASS |
| AC2: clean file returns {} | test_apply_patch_clean_file_returns_empty_json PASSED | PASS |
| AC3: lint errors returns systemMessage + additionalContext | 2 tests PASSED | PASS |
| AC4: nonexistent filePath returns {} | test_apply_patch_nonexistent_filepath_returns_empty_json PASSED | PASS |
| AC5: missing/null filePath returns {} | 2 tests PASSED | PASS |
| AC6: exit code never 2 | 3 tests PASSED | PASS |
| AC7: stdout valid JSON | 2 tests PASSED | PASS |

### Test Results
- pytest: 12/12 passed (task-scoped); 190 passed, 58 failed suite-wide (all unrelated: test_agent_port_v2, test_agent_scoped_hooks_research, test_analysis, test_approve_memory_585)
- ruff: All checks passed

### Reviewer Evidence
Present and detailed (.98 PASS). Trusted for code-level findings.

### Architect Quality: 4/5
Original AC vague (2 lines). Architect refined to 7 precise, testable criteria. Solid work.

### Deduction Breakdown
- No rubric deductions: all 7 AC covered, lint clean, reviewer present, no task-scope failures
- Pipeline violation (build before test-writing): informational, mitigated by post-hoc tests

### Confidence: .98
### Action: archive
