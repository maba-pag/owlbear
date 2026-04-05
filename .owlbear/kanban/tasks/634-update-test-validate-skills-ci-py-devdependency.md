---
id: 634
title: Update test_validate_skills_ci.py DevDependency tests for validation group
status: backlog
priority: needed
created: 2026-04-05T14:28:59.7832139+02:00
updated: 2026-04-05T14:28:59.7832139+02:00
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
- [ ] AC3: Both tests pass after update
- [ ] AC4: Full test suite shows no new regressions from the change

## Affected Files

- `tests/test_validate_skills_ci.py`

## Context

- Created during audit of #614 — builder moved the dep but didn't update downstream tests, reviewer marked "no pytest run required" for config change
