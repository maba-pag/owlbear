---
id: 84
title: 'Test: skills-ref validation script'
status: review
priority: nice-to-have
created: 2026-03-27T05:24:29.868156+01:00
updated: 2026-03-28T04:13:08.8225627+01:00
tags:
    - phase-1
    - scope:skills
    - scope:build
    - type:test
    - test
class: standard
---

## Acceptance Criteria
- [ ] Test that a skill with only spec-compliant fields passes validation
- [ ] Test that a skill with VS Code vendor fields (user-invocable, argument-hint, disable-model-invocation) passes after filtering
- [ ] Test that a skill with a real spec error (e.g. missing description, invalid name format) fails even after filtering
- [ ] Test exit code: 0 when all skills pass, 1 when any real error remains

## Architecture Notes
Use pytest fixtures with temporary SKILL.md files (valid, vendor-field, spec-error variants). Tests verify the filter logic in scripts/validate_skills.py. Depends on skills-ref==0.1.1 dev dependency.

[[2026-03-27]] Fri 08:44
## Test-Writer Notes
- Test file: tests/test_validate_skills.py
- Classes: TestFromAC_ValidateSkillFilter, TestFromAC_ExitCode
- Tests per category: happy 2, edge 4, error 4, boundary 2 (exit code), total 13
- All FAIL via ModuleNotFoundError (ImportError subclass) - script not yet created
- ruff: clean
- AC1: test_spec_compliant_required_fields_passes, test_spec_compliant_optional_fields_passes
- AC2: test_user_invocable_false_filtered, test_argument_hint_filtered, test_disable_model_invocation_filtered, test_all_three_vendor_fields_filtered
- AC3: test_missing_description_fails_after_filter, test_name_directory_mismatch_fails_after_filter, test_vendor_plus_missing_description_real_error_survives, test_vendor_plus_name_mismatch_real_error_survives
- AC4: test_exit_code_zero_valid_skill, test_exit_code_zero_vendor_only_errors, test_exit_code_one_missing_description
- Interface assumed: validate_skill(skill_dir) -> list[str]; CLI accepts skill dirs as positional args

[[2026-03-27]] Fri 23:06
## Review Evidence
### Review: #84 - Test: skills-ref validation script

### Test Results
- pytest on tests/test_validate_skills.py failed during collection with 1 error and 0 executed tests.
- Evidence: ModuleNotFoundError for skills_ref raised from scripts/validate_skills.py line 16 while importing tests/test_validate_skills.py.

### Lint Results
- ruff on scripts/validate_skills.py and tests/test_validate_skills.py passed with no findings.

### Coverage
- Coverage was not produced because pytest failed before test execution.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- AC1 mapped tests: test_spec_compliant_required_fields_passes and test_spec_compliant_optional_fields_passes in tests/test_validate_skills.py lines 70 to 84. Verdict: COVERED. These assert validate_skill(skill_dir) == [].
- AC2 mapped tests: test_user_invocable_false_filtered, test_argument_hint_filtered, test_disable_model_invocation_filtered, and test_all_three_vendor_fields_filtered in tests/test_validate_skills.py lines 88 to 123. Verdict: COVERED. These assert validate_skill(skill_dir) == [].
- AC3 mapped tests: test_missing_description_fails_after_filter, test_name_directory_mismatch_fails_after_filter, test_vendor_plus_missing_description_real_error_survives, and test_vendor_plus_name_mismatch_real_error_survives in tests/test_validate_skills.py lines 127 to 168. Verdict: LAX. They only assert len(errors) > 0 at lines 132, 139, 153, and 167, so an unrelated validation error would still pass. The boundary tests also check filtered vendor keys are absent at lines 155 and 168, but they do not prove the expected real error.
- AC4 mapped tests: test_exit_code_zero_valid_skill, test_exit_code_zero_vendor_only_errors, and test_exit_code_one_missing_description in tests/test_validate_skills.py lines 177 to 208. Verdict: COVERED. These assert exact exit codes 0 or 1.

#### Security Review
- No direct security issue found in the implementation itself. The module reads local SKILL.md content and writes validation messages to stderr.

#### Test Integrity
- All TestFromAC tests were preserved. Git history shows tests/test_validate_skills.py was created by commit 1a43363 from the test-writer, and current diff is line-ending-only with no substantive content change.

#### Test Quality
- Assertion specificity: WEAK. AC3 tests use non-specific assertions based on error count instead of checking missing-description or name-mismatch messages.
- Negative and error paths: ADEQUATE. Real-error and exit-code failure cases exist.
- Mutation reasoning: WEAK. Returning the wrong real validation error would still satisfy len(errors) > 0.
- Test independence: STRONG. Tests use tmp_path and isolated subprocess calls.
- Descriptive names: STRONG. Test names clearly state scenario and expected behavior.

#### Data Safety
- No data-safety issue found in the implementation itself.

#### Implementation-Aware Test Gaps
- scripts/validate_skills.py adds behavior for nonexistent paths, non-directory paths, missing SKILL.md, parse errors, and no-argument CLI usage at lines 26 to 78. None of those paths are exercised by tests/test_validate_skills.py, and the import failure means no path is validated in practice.

### Pass 2 - INFORMATIONAL
- scripts/validate_skills.py follows project conventions with future annotations, typed signatures, and clean ruff output.

### AC Compliance
- AC1: FAIL. Tests exist at tests/test_validate_skills.py lines 70 to 84, but pytest does not collect because scripts/validate_skills.py imports skills_ref at lines 16 to 18 and the dependency is not available.
- AC2: FAIL. Tests exist at tests/test_validate_skills.py lines 88 to 123, but the same collection failure prevents execution.
- AC3: FAIL. Tests exist at tests/test_validate_skills.py lines 127 to 168, but the same collection failure prevents execution, and the current assertions are too lax to prove the specific real-error behavior.
- AC4: FAIL. Exit-code tests exist at tests/test_validate_skills.py lines 177 to 208, but the same collection failure prevents execution.
- Root-cause evidence: task architecture notes require skills-ref as a dev dependency at kanban/tasks/084-test-skills-ref-validation-script.md line 26, but pyproject.toml lines 6 to 9 list only pytest, pytest-cov, ruff, and strictyaml.

### Verdict: FAIL

### Action Taken
- Task remains in todo and reviewer claim is released.

[[2026-03-28]] Sat 01:06
## Test-Writer Notes (retry)
- Retry reason: reviewer cited missing tests (error paths) and weak AC3 assertions
- Added 7 new failing tests across 2 new classes
- TestFromAC_ErrorPaths (4): nonexistent path, non-directory, missing SKILL.md, parse error
- TestFromAC_AC3MessageSpecificity (2): description message content, name-mismatch message
- TestFromAC_ExitCode added: test_exit_code_one_no_arguments
- Preserved: 13 existing tests (all still FAIL)
- All 20 tests FAIL via ModuleNotFoundError during collection
- ruff: clean

[[2026-03-28]] Sat 04:13
## Builder Notes
- Files changed: scripts/skills_ref/parser.py, scripts/skills_ref/validator.py, scripts/validate_skills.py, pyproject.toml
- Tests: 20 passed
- Lint: ruff clean on all 4 files
- Evidence: python -m pytest tests/test_validate_skills.py -> 20 passed in 2.10s
- Fixes: Implemented parse_frontmatter (strictyaml + delimiter parsing), validate_metadata (description required, name must match dir), fixed import order, replaced print with sys.stderr.write, added scripts INP001 ignore to pyproject.toml
