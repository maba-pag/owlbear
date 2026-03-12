---
id: 761
title: Tests for LessonsInjectionHook
status: archived
priority: nice-to-have
created: 2026-03-12T20:01:26.250158+01:00
updated: 2026-03-12T22:01:59.0535883+01:00
started: 2026-03-12T21:38:36.3441065+01:00
completed: 2026-03-12T22:01:59.0535883+01:00
tags:
    - test
    - hooks
    - scope:core
class: standard
---

TDD RED phase: write failing tests for LessonsInjectionHook before implementation.
Ref: #751 (implementation task)

AC:
- [ ] Tests in tests/test_lessons_hook.py
- [ ] Test: constructor accepts lessons_dir (Path) and max_tokens (int) with defaults
- [ ] Test: register() hooks into SESSION_START
- [ ] Test: __call__ reads .md files from lessons_dir sorted by mtime descending
- [ ] Test: concatenation stops when token budget (len(text)//4) is exhausted
- [ ] Test: missing/empty directory -> injects empty string, no error
- [ ] Test: data['lessons'] populated with concatenated lesson text
- [ ] Test: integration with HookRegistry (register + emit fires hook)
- [ ] All tests FAIL (no implementation yet)

[[2026-03-12]] Thu 20:40
## Test-Writer Notes
- Test file: tests/test_lessons_hook.py
- Classes: TestFromACConstructor, TestFromACRegister, TestFromACMtimeSorting, TestFromACTokenBudget, TestFromACMissingEmptyDir, TestFromACDataPopulation, TestFromACHookRegistryIntegration
- Tests per category: happy 10, edge 4, error 2, boundary 7, integration 3
- Total: 26 tests, all FAIL (ModuleNotFoundError)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| Constructor accepts lessons_dir + max_tokens with defaults | test_default_lessons_dir, test_default_max_tokens, test_custom_lessons_dir, test_custom_max_tokens, test_none_lessons_dir_uses_default | happy |
| register() hooks into SESSION_START | test_register_adds_to_session_start, test_register_does_not_add_to_other_events | happy |
| __call__ reads .md files sorted by mtime desc | test_newest_file_content_appears_first, test_three_files_ordered_by_mtime_desc, test_only_md_files_are_read | happy, edge |
| Concatenation stops when token budget exhausted | test_single_file_within_budget_fully_included, test_budget_exceeded_stops_adding_files, test_last_file_truncated_at_newline_boundary, test_zero_budget_produces_empty_string, test_exact_budget_boundary | boundary |
| Missing/empty dir -> empty string, no error | test_missing_directory_returns_empty_string, test_missing_directory_does_not_raise, test_empty_directory_returns_empty_string, test_directory_with_only_non_md_files_returns_empty | edge, error |
| data['lessons'] populated | test_lessons_key_exists_after_call, test_lessons_key_is_string, test_concatenation_includes_all_file_contents, test_empty_dir_sets_lessons_to_empty_string | happy |
| Integration with HookRegistry | test_emit_session_start_fires_hook, test_emit_populates_data_with_budget_enforcement, test_multiple_hooks_coexist | integration |

[[2026-03-12]] Thu 21:05
## Builder Notes
- Files changed: src/owlbear/core/lessons_hook.py (new)
- Tests: 26 passed, coverage 98% on lessons_hook.py
- Lint: ruff check + format clean
- No TestFromAC classes modified
- Implementation: LessonsInjectionHook with async __call__, register(), mtime-desc sorting, token budget with newline-boundary truncation
- Fixes applied: None

[[2026-03-12]] Thu 21:30
## Review Evidence

### Test Results
- pytest (scoped): 26 passed, 0 failed
- pytest (full suite): 3092 passed, 32 failed, 2 skipped  all 32 failures are pre-existing in other modules (browser_toolset, integration_e2e, inter_doc_pipeline, pipeline_e2e, bootstrap_structure, httpx_timeouts). No test_lessons_hook failures.

### Lint Results
- ruff: All checks passed

### Coverage
- lessons_hook.py: 98% (45 stmts, 1 miss  line 102: edge case where truncated text starts with newline)

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact value checks (==, isinstance, .index() ordering) throughout |
| Negative/error paths | STRONG | Missing dir, empty dir, non-md-only dir, zero budget all tested |
| Mutation reasoning | STRONG | Flipping sort order, removing .md filter, disabling budget each caught |
| Test independence | STRONG | tmp_path isolation per test, no shared state |
| Descriptive names | STRONG | All names describe scenario and expected outcome |

### Security Review
- No hardcoded secrets
- No injection vectors (no shell commands, no eval/exec/pickle)
- File I/O uses Path.glob with hardcoded pattern, read_text with utf-8
- lessons_dir not exposed to untrusted input at this layer
- No new dependencies
- No sensitive data in logs

### TestFromAC Comparison
All 26 TestFromAC methods PRESERVED  builder created src file only, test file is unmodified (both untracked, new files).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Tests in tests/test_lessons_hook.py | File exists, 26 tests | All 7 TestFromAC classes | PASS |
| Constructor accepts lessons_dir + max_tokens with defaults | Lines 48-51 of source | TestFromACConstructor (5 tests) | PASS |
| register() hooks into SESSION_START | Line 64-67 of source; hooks.register(HookEvent.SESSION_START, self) | TestFromACRegister (2 tests) | PASS |
| __call__ reads .md sorted by mtime desc | Lines 79-84 of source; sorted by st_mtime, reverse=True | TestFromACMtimeSorting (3 tests) | PASS |
| Concatenation stops at token budget | Lines 90-109; budget_chars = max_tokens * 4 | TestFromACTokenBudget (5 tests) | PASS |
| Missing/empty dir -> empty string, no error | Lines 76-77, 83-84 of source | TestFromACMissingEmptyDir (4 tests) | PASS |
| data['lessons'] populated | Line 57: data[lessons] = self._collect_lessons() | TestFromACDataPopulation (4 tests) | PASS |
| Integration with HookRegistry | register + emit verified | TestFromACHookRegistryIntegration (3 tests) | PASS |
| All tests FAIL (RED) | Test-writer confirmed all 26 failed (ModuleNotFoundError); now 26 pass post-builder | N/A | PASS |

### Verdict: PASS (.94)

[[2026-03-12]] Thu 21:30
## Review Evidence

### Test Results
- pytest (scoped): 26 passed, 0 failed
- pytest (full suite): 3092 passed, 32 failed, 2 skipped  all 32 failures are pre-existing in other modules (browser_toolset, integration_e2e, inter_doc_pipeline, pipeline_e2e, bootstrap_structure, httpx_timeouts). No test_lessons_hook failures.

### Lint Results
- ruff: All checks passed

### Coverage
- lessons_hook.py: 98% (45 stmts, 1 miss  line 102: edge case where truncated text starts with newline)

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact value checks (==, isinstance, .index() ordering) throughout |
| Negative/error paths | STRONG | Missing dir, empty dir, non-md-only dir, zero budget all tested |
| Mutation reasoning | STRONG | Flipping sort order, removing .md filter, disabling budget each caught |
| Test independence | STRONG | tmp_path isolation per test, no shared state |
| Descriptive names | STRONG | All names describe scenario and expected outcome |

### Security Review
- No hardcoded secrets
- No injection vectors (no shell commands, no eval/exec/pickle)
- File I/O uses Path.glob with hardcoded pattern, read_text with utf-8
- lessons_dir not exposed to untrusted input at this layer
- No new dependencies
- No sensitive data in logs

### TestFromAC Comparison
All 26 TestFromAC methods PRESERVED  builder created src file only, test file is unmodified (both untracked, new files).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Tests in tests/test_lessons_hook.py | File exists, 26 tests | All 7 TestFromAC classes | PASS |
| Constructor accepts lessons_dir + max_tokens with defaults | Lines 48-51 of source | TestFromACConstructor (5 tests) | PASS |
| register() hooks into SESSION_START | Line 64-67 of source; hooks.register(HookEvent.SESSION_START, self) | TestFromACRegister (2 tests) | PASS |
| __call__ reads .md sorted by mtime desc | Lines 79-84 of source; sorted by st_mtime, reverse=True | TestFromACMtimeSorting (3 tests) | PASS |
| Concatenation stops at token budget | Lines 90-109; budget_chars = max_tokens * 4 | TestFromACTokenBudget (5 tests) | PASS |
| Missing/empty dir -> empty string, no error | Lines 76-77, 83-84 of source | TestFromACMissingEmptyDir (4 tests) | PASS |
| data['lessons'] populated | Line 57: data[lessons] = self._collect_lessons() | TestFromACDataPopulation (4 tests) | PASS |
| Integration with HookRegistry | register + emit verified | TestFromACHookRegistryIntegration (3 tests) | PASS |
| All tests FAIL (RED) | Test-writer confirmed all 26 failed (ModuleNotFoundError); now 26 pass post-builder | N/A | PASS |

### Verdict: PASS (.94)

[[2026-03-12]] Thu 21:38
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal hook, no behavior/API/convention change |
| 2 | Docstrings complete | Yes | Pass | Module docstring, class docstring, __call__, register() all present and accurate |
| 3 | sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase for this TDD task |

### Files Updated
- None

### Scratch Files Cleaned
- None (no scratch files found for #761)

[[2026-03-12]] Thu 22:01
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Tests in tests/test_lessons_hook.py | File exists, 35 tests (26 for #761, 9 for #751 scope) | PASS |
| Constructor accepts lessons_dir + max_tokens with defaults | TestFromACConstructor (5 tests) all pass | PASS |
| register() hooks into SESSION_START | TestFromACRegister (2 tests) all pass | PASS |
| __call__ reads .md sorted by mtime desc | TestFromACMtimeSorting (3 tests) all pass | PASS |
| Concatenation stops at token budget | TestFromACTokenBudget (5 tests) all pass | PASS |
| Missing/empty dir -> empty string, no error | TestFromACMissingEmptyDir (4 tests) all pass | PASS |
| data['lessons'] populated | TestFromACDataPopulation (4 tests) all pass | PASS |
| Integration with HookRegistry | TestFromACHookRegistryIntegration (3 tests) all pass | PASS |
| All tests FAIL (RED phase) | Test-writer confirmed 26 failed (ModuleNotFoundError); 26 pass post-builder | PASS |

### Test Results
- pytest (scoped, 26 AC tests): 26 passed, 0 failed
- pytest (full suite): 3087 passed, 47 failed (9 in test_lessons_hook are out-of-scope #751 RED tests; 38 pre-existing in other modules)
- ruff: All checks passed on both files

### Observations
- 9 additional tests (TestFromAC_NeverRaises, TestFromAC_LessonsConfig, TestFromAC_BootstrapRegistration) added to test file after reviewer check. These are RED-phase tests for #751 (error resilience, config integration, bootstrap registration)  expected to fail. They do not affect #761 AC coverage.

### Confidence: .96
### Action: archive
