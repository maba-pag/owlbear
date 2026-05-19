---
id: 889
title: Test planning package root exports and docstring (RED)
status: archived
priority: someday
created: 2026-03-21T06:35:54.7967511+01:00
updated: 2026-03-21T14:56:42.0604662+01:00
started: 2026-03-21T14:56:37.8891674+01:00
completed: 2026-03-21T14:56:37.8891674+01:00
tags:
    - planning
    - type:test
    - audit
class: standard
---

## Context

Task #572 defines the package-root API for owlbear.planning. src/owlbear/planning/__init__.py is currently empty, so there is no automated coverage for the package-root docstring or explicit export surface.

## Acceptance Criteria

- [ ] Create tests/test_planning_package_exports.py.
- [ ] Add a test that import owlbear.planning as planning succeeds and that planning.__doc__ is a str whose .strip() value is non-empty.
- [ ] Add a test that from owlbear.planning import ProjectDefinition, ProjectDefinitionExtractor, Requirement, project_definition_to_markdown succeeds.
- [ ] Add identity assertions showing each package-root symbol is the same object as its canonical definition from owlbear.planning.models, owlbear.planning.extractor, or owlbear.planning.markdown.
- [ ] Add a test that owlbear.planning.__all__ is exactly the four-name string list ProjectDefinition, ProjectDefinitionExtractor, Requirement, and project_definition_to_markdown, in that order.
- [ ] Add a negative export-surface test that EXTRACTION_PROMPT is not present in owlbear.planning.__all__; the exact __all__ assertion is the guard against any additional package-root exports.
- [ ] Run the new test file on the current tree and verify it fails until task #572 is implemented.

[[2026-03-21]] Sat 07:00

## Architecture Review

__Verdict:__ Approved

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Create tests/test_planning_package_exports.py | Precise and scoped to a single RED deliverable | Kept |
| import owlbear.planning succeeds and __doc__ is non-empty | Needed a stricter docstring contract so whitespace-only content cannot pass | Rewrote |
| package-root imports succeed | Correct contract for the public API exposed by #572 | Kept |
| imported symbols are identical to canonical definitions | Correct identity check for eager re-export pattern | Kept |
| __all__ equals [ProjectDefinition, ProjectDefinitionExtractor, Requirement, project_definition_to_markdown] | Ambiguous: Python package __all__ contains string names, not the imported objects | Rewrote |
| internal helpers are not part of the export surface; at minimum EXTRACTION_PROMPT excluded | Needed an exact negative check tied to the explicit export list | Rewrote |
| tests fail until #572 is implemented | Good RED-phase requirement, but needed the execution scope stated explicitly | Rewrote |

### Architecture Notes

- Existing package-root pattern is eager re-export plus explicit string-based __all__, as used by src/owlbear/memory/__init__.py and src/owlbear/channels/__init__.py.
- src/owlbear/planning/extractor.py defines both ProjectDefinitionExtractor and the internal EXTRACTION_PROMPT; the RED task must lock in that only the public class is exported.
- src/owlbear/planning/markdown.py keeps helper functions private. The exact __all__ assertion is the no-extra-exports guard, so this task stays narrow and mechanically verifiable.
- Single domain verified: planning package public API tests only. No new security boundary or failure-mode map is needed for this test-only task.

### Changes Made

- Claimed #889 for architecture review.
- Rewrote the acceptance criteria to use the codebase's string-based __all__ contract and a stricter docstring check.
- Prepared the task for backlog -> todo handoff.

### Dependencies

- Verified: #572 is the paired build task and already requires all tests added by #889 to pass.
- Verified: src/owlbear/planning/models.py, src/owlbear/planning/extractor.py, and src/owlbear/planning/markdown.py already contain the canonical symbols referenced by this RED task.

[[2026-03-21]] Sat 12:37

## Test-Writer Notes\n- Test file: tests/test_planning_package_exports.py\n- Classes: TestFromAC_PlanningDocstring, TestFromAC_PlanningImports, TestFromAC_PlanningSymbolIdentity, TestFromAC_PlanningAll\n- Total: 13 tests, all FAIL\n- ruff: clean

[[2026-03-21]] Sat 13:03

## Builder Notes

- Files changed: src/owlbear/planning/__init__.py (20 lines added, was empty)
- Tests: 13 passed, coverage 100% on planning/__init__.py and planning/models.py
- Lint: ruff check + format --check both clean
- Evidence: 13 tests FAILED pre-impl, 13 passed post-impl; ruff 'All checks passed!'
- Fixes applied: None — pure GREEN phase, no TestFromAC modifications

[[2026-03-21]] Sat 13:37

## Review Evidence

## Review: #889 - Test planning package root exports and docstring (RED)

### Test Results

- Command: uv run pytest tests/test_planning_package_exports.py -q --tb=short
- Result: 13 passed, 0 failed, 2 warnings (optional qdrant dependency skips from tests/conftest.py).

### Lint Results

- Command: uv run ruff check src/ tests/
- Result: 461 errors in unrelated, pre-existing files outside #889 scope.
- Command: uv run ruff check src/owlbear/planning/__init__.py tests/test_planning_package_exports.py
- Result: All checks passed.

### Coverage

- Command: uv run pytest tests/test_planning_package_exports.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- First attempt: transient KeyboardInterrupt during pytest plugin startup.
- Second attempt: completed successfully with 13 passed.
- Relevant module coverage from report:
  - src/owlbear/planning/__init__.py: 100%
  - src/owlbear/planning/models.py: 100%
- Note: bare --cov reports project-wide totals; unrelated modules show 0% in this scoped run.

### Pass 1 - CRITICAL

#### Security Review

- No hardcoded secrets found in the reviewed scope.
- No injection/path traversal/deserialization/eval risks introduced.
- No new dependency added.
- No secret leakage/logging risks introduced.

#### Test Integrity (TestFromAC comparison)

- Builder commit scope check (git show --name-only fc17a4c) reports only src/owlbear/planning/__init__.py changed; no task test-file modifications were included in that commit.

| Original Test Group | Change Made | Assessment |
|--------------------|-------------|------------|
| TestFromAC_PlanningDocstring | No weakening/removal observed | PRESERVED |
| TestFromAC_PlanningImports | No weakening/removal observed | PRESERVED |
| TestFromAC_PlanningSymbolIdentity | No weakening/removal observed | PRESERVED |
| TestFromAC_PlanningAll | No weakening/removal observed | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact identity assertions and exact ordered __all__ list assertion; explicit non-empty docstring checks. |
| Negative/error paths | ADEQUATE | Explicit negative export-surface check for EXTRACTION_PROMPT exclusion. |
| Mutation reasoning | STRONG | Reordering/removing exports, changing canonical symbol binding, or exposing internal symbol would fail targeted tests. |
| Test independence | STRONG | Independent import-based checks with no shared mutable state. |
| Descriptive names | STRONG | Test names map directly to behavior contracts. |

#### Data Safety

- No data integrity, atomicity, race, or unbounded-input risks introduced in the reviewed change.

### Pass 2 - INFORMATIONAL

- git status shows tests/test_planning_package_exports.py currently untracked in this workspace; behavior is verified, but commit hygiene should ensure test artifact persistence.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Create tests/test_planning_package_exports.py | File exists and executes in scoped pytest run | tests/test_planning_package_exports.py suite | PASS |
| import owlbear.planning succeeds and __doc__ is non-empty str | src/owlbear/planning/__init__.py line 1 docstring + scoped pytest pass | test_docstring_is_str; test_docstring_is_non_empty_after_strip | PASS |
| from owlbear.planning import ProjectDefinition, ProjectDefinitionExtractor, Requirement, project_definition_to_markdown succeeds | Re-export imports in src/owlbear/planning/__init__.py lines 11-13 + scoped pytest pass | test_import_project_definition; test_import_project_definition_extractor; test_import_requirement; test_import_project_definition_to_markdown | PASS |
| Package-root symbols are identical to canonical definitions | Canonical definitions in src/owlbear/planning/models.py (lines 18, 28), src/owlbear/planning/extractor.py line 45, src/owlbear/planning/markdown.py line 36 + identity tests pass | test_project_definition_identity; test_requirement_identity; test_project_definition_extractor_identity; test_project_definition_to_markdown_identity | PASS |
| __all__ is exact ordered four-name string list | src/owlbear/planning/__init__.py lines 15-20 defines exact four-name ordered list; scoped tests pass | test_all_is_exact_four_name_list_in_order | PASS |
| EXTRACTION_PROMPT excluded from package-root export surface | Internal helper exists at src/owlbear/planning/extractor.py line 17 and exclusion test passes | test_extraction_prompt_not_in_all | PASS |
| New file was RED before #572 implementation | Test-Writer Notes in task body record 13 tests all FAIL before implementation | Historical RED evidence from Test-Writer stage | PASS |

### Verdict: PASS

- Confidence: .93

### Action Taken

- Appended this review evidence and moved task from review to docs.

[[2026-03-21]] Sat 14:08

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | TDD test + package __init__ re-exports; no behavior change or tech stack update needed |
| 2 | Docstrings complete | Yes | Pass | src/owlbear/planning/__init__.py has accurate module-level docstring listing all 4 exported symbols |
| 3 | sources/overview.md | No | N/A | Pure re-export from internal modules; no external patterns used |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc linked | No | N/A | No research phase; task is TDD RED+GREEN only |
| 6 | No impact default | -- | Pass | All non-docstring items N/A; docstring already accurate |

### Files Updated

- None

### Scratch Files Cleaned

- None

[[2026-03-21]] Sat 14:56

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Create tests/test_planning_package_exports.py | File exists, 96 lines, 13 tests | PASS |
| import owlbear.planning + __doc__ non-empty str | TestFromAC_PlanningDocstring (2 tests), docstring at __init__.py L1-6 | PASS |
| from owlbear.planning import 4 symbols | TestFromAC_PlanningImports (4 tests), re-exports at __init__.py L11-13 | PASS |
| Identity assertions to canonical definitions | TestFromAC_PlanningSymbolIdentity (4 tests) | PASS |
| __all__ exact 4-name string list in order | test_all_is_exact_four_name_list_in_order, __init__.py L15-20 | PASS |
| EXTRACTION_PROMPT not in __all__ | test_extraction_prompt_not_in_all | PASS |
| Tests fail until #572 implemented | Test-Writer notes: 13 FAIL; Builder notes: 13 FAIL->PASS | PASS |

### Test Results

- pytest (scoped): 13 passed, 0 failed
- pytest (full suite): 3715 passed, 105 failed (pre-existing), 20 skipped
- ruff (scoped): All checks passed

### Quality Gap

- Test file was untracked (test-writer missed commit); committed as 9033cec by auditor.

### Confidence: .97

### Action: archive

[[2026-03-21]] Sat 14:56

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 9033cec | test | tests/test_planning_package_exports.py | #889 |
