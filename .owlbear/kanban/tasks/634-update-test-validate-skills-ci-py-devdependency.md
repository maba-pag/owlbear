---
id: 634
title: Update test_validate_skills_ci.py DevDependency tests for validation group
status: in-progress
priority: needed
created: 2026-04-05T14:28:59.7832139+02:00
updated: 2026-04-05T17:40:59.6667605+02:00
tags:
    - scope:infra
    - type:test
    - phase-2
class: standard
---

## Summary

Task #614 moved `skills-ref==0.1.1` from the `dev` dependency group to the `validation` group in pyproject.toml. The existing tests in `tests/test_validate_skills_ci.py::TestFromAC_DevDependency` (from task #44) still assert that `skills-ref` is in `[dependency-groups.dev]`, causing 2 regressions.

## Acceptance Criteria

- [ ] AC1: `TestFromAC_DevDependency::test_skills_ref_present_in_dev_group` updated to check the `validation` group instead of `dev`
- [ ] AC2: `TestFromAC_DevDependency::test_skills_ref_pinned_to_exact_version_0_1_1` updated to check the `validation` group
- [ ] AC3: Class name (`TestFromAC_DevDependency` to `TestFromAC_ValidationDependency`), helper method (`_dev_deps` to `_validation_deps`), test method names, docstrings, and error messages updated to reference `validation` instead of `dev`
- [ ] AC4: Module-level docstring (lines 1-12) updated: AC1 description references `dependency-groups.validation`
- [ ] AC5: Both updated tests pass (`uv run pytest tests/test_validate_skills_ci.py::TestFromAC_ValidationDependency -v`)
- [ ] AC6: Full test suite shows no new regressions (`uv run pytest tests/ -m "not api" -q`)

## Affected Files

- `tests/test_validate_skills_ci.py`

## Context

- Created during audit of #614: builder moved the dep but did not update downstream tests, reviewer marked "no pytest run required" for config change
- `test_ci_integration.py` line 14 has a stale comment referencing `dev deps`: cosmetic, not gated here

[[2026-04-05]] Sun 15:36
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One file, one concern: align test assertions with actual dep group |
| Interface clarity | PASS | AC names exact methods, classes, groups, and verification commands |
| Dependency correctness | PASS | No deps needed; #614 (the move) is already done |
| Module layering | N/A | Test file only, no module interactions |
| TDD compliance | PASS | Task IS a test update; type:test tag present |
| KISS/YAGNI | PASS | Mechanical rename + group swap, minimal scope |
| Premise challenge | PASS | Tests genuinely fail on current HEAD; fix is necessary |
| Pattern consistency | PASS | Follows existing test file structure |
| Security surface | N/A | Test file only |
| Single domain | PASS | scope:infra only |

### Challenge Results

- Challenger: proceed (confidence 0.85)
- Raised: stale class/method/helper names, docstrings, and error messages would make tests actively misleading
- Architect response: accepted; added AC3 (rename identifiers) and AC4 (update module docstring) to address

### Verdict: APPROVE (after AC refinement)

### Action Taken

Refined AC from 4 to 6 lines: added AC3 (rename class/method/helper/docstrings/error messages from dev to validation), AC4 (update module docstring), renumbered pass/regression checks to AC5-AC6. Advancing to todo.

[[2026-04-05]] Sun 17:40
## Test-Writer Notes
- Non-implementation task (tagged type:test) — no tests applicable.
- Passing through to builder.
- Task is a mechanical rename of an existing test class: `TestFromAC_DevDependency` → `TestFromAC_ValidationDependency`, helper `_dev_deps` → `_validation_deps`, group lookup `dev` → `validation`, plus docstring/error-message updates.
- No new testable interfaces introduced; all AC lines address the test file itself.
- Builder should update `tests/test_validate_skills_ci.py` and verify AC5 (`pytest tests/test_validate_skills_ci.py::TestFromAC_ValidationDependency -v` passes) and AC6 (no regressions).
