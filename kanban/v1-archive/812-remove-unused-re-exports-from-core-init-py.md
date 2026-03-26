---
id: 812
title: Remove unused re-exports from core __init__.py
status: archived
priority: nice-to-have
created: 2026-03-14T21:07:50.8288534+01:00
updated: 2026-03-15T12:14:26.2539934+01:00
started: 2026-03-15T12:14:08.4075658+01:00
completed: 2026-03-15T12:14:08.4075658+01:00
tags:
    - audit
    - architecture
    - scope:core
class: standard
---

owlbear.core.__init__.py exports 6 symbols with __all__, but 0/58 consumers use short paths  100% import from submodules (e.g. from owlbear.core.agent import OwlBearAgent). Remove re-exports and __all__, keep docstring and from __future__ import annotations. See docs/research/init-reexports.md section 3.2.

[[2026-03-15]] Sun 09:11

## Research

Doc: docs/research/core-init-reexport-removal.md

Key findings:

- 0/64 production consumers use short-path imports from owlbear.core
- 100% use deep paths (from owlbear.core.agent import OwlBearAgent)
- Conflicting research resolved: init-reexports.md evidence-based (.85 remove) vs init-re-exports.md assumption-based (.90 add)
- 3 tests in TestFromAC_CoreReExport verify the re-export itself (must be deleted with re-exports)
- Recommendation: remove all re-exports + __all__ (.90 confidence)

Follow-up tasks created:

- #822 Implement core __init__.py re-export removal
- #823 Close #813 as won't-do per re-export research

[[2026-03-15]] Sun 10:06

## Test-Writer Notes

- Test file: tests/test_core_init_clean.py
- Classes: TestFromAC_CoreInitNoReExports
- Tests per category: happy 1 (no __all__), edge 16 (parametrized: each of 16 previously exported symbols absent), error 0, boundary 0
- Total: 17 tests, all FAIL (AssertionError)
- ruff: clean
- AC coverage:
  - Remove __all__: test_no_all_attribute (FAIL)
  - Remove re-exports: test_symbol_not_in_namespace x16 (FAIL)
  - Keep docstring/annotations: existing behavior, no RED test needed
- Note: Builder must also delete TestFromAC_CoreReExport (3 tests) in tests/test_exception_hierarchy.py since those verify the removed feature

[[2026-03-15]] Sun 10:21

## Builder Notes

- Files changed: src/owlbear/core/__init__.py (removed re-exports + __all__), tests/test_exception_hierarchy.py (deleted TestFromAC_CoreReExport class)
- Tests: 34 passed (17 test_core_init_clean + 17 test_exception_hierarchy), 0 failed
- Coverage: core/__init__.py is trivial (docstring + annotation only)
- Lint: ruff clean
- Evidence: 0 production consumers used short-path imports. grep confirmed.

[[2026-03-15]] Sun 11:19

## Review Evidence

### Test Results

- pytest: 34 passed, 0 failed (test_core_init_clean.py + test_exception_hierarchy.py)

### Lint Results

- ruff: All checks passed

### Pass 1 - CRITICAL

#### Security Review

No security issues. Change only removes imports and __all__ from __init__.py.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_CoreInitNoReExports::test_no_all_attribute | No change | PRESERVED |
| TestFromAC_CoreInitNoReExports::test_symbol_not_in_namespace x16 | No change | PRESERVED |
| TestFromAC_CoreReExport (3 tests, task #791) | Deleted per test-writer instruction - verified removed feature | REMOVED (authorized) |

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | hasattr with specific symbols + failure messages |
| Negative/error paths | ADEQUATE | Tests are inherently negative (absent symbols) |
| Mutation reasoning | STRONG | Re-adding any re-export caught by parametrized test |
| Test independence | STRONG | No shared mutable state |
| Descriptive names | STRONG | test_no_all_attribute, test_symbol_not_in_namespace |

#### Data Safety

No data safety issues.

### Pass 2 - INFORMATIONAL

No informational findings.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Remove __all__ | __init__.py has no __all__; dir() confirms | test_no_all_attribute | PASS |
| Remove re-exports (16 symbols) | __init__.py is 3 lines; all 16 absent | test_symbol_not_in_namespace x16 | PASS |
| Keep docstring | Line 1: docstring present | N/A (trivial) | PASS |
| Keep annotations import | Line 3: present | N/A (trivial) | PASS |
| Delete TestFromAC_CoreReExport | Diff confirms removal; remaining 34 tests pass | N/A (feature removed) | PASS |

### Verdict: PASS

Confidence: .95

### Action Taken

kanban edit 812 --status docs --release

[[2026-03-15]] Sun 11:42

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Internal cleanup: removed re-exports, no behavior/API/convention change |
| 2 | Docstrings complete | Yes | Pass | core/__init__.py has docstring; only other change was test deletion |
| 3 | sources/overview.md | Yes | Pass | Already has 2 entries under Core Re-export Removal Research Task #812 |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/core-init-reexport-removal.md exists, linked in task body |
| 6 | No impact | -- | -- | Items 2,3,5 apply |

### Files Updated

- None

### Scratch Files Cleaned

- None (no 812-* files found)

[[2026-03-15]] Sun 12:14

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Remove __all__ | core/__init__.py has no __all__ (3 lines total) | PASS |
| Remove re-exports (16 symbols) | No imports in file; test_symbol_not_in_namespace x16 pass | PASS |
| Keep docstring | L1: docstring present | PASS |
| Keep annotations import | L3: from __future__ import annotations | PASS |
| Delete TestFromAC_CoreReExport | grep confirms absent from test_exception_hierarchy.py | PASS |

### Test Results

- pytest (scoped): 34 passed, 0 failed (test_core_init_clean.py + test_exception_hierarchy.py)
- pytest (full): 3470 passed, 51 failed (all pre-existing: AgentRegistry sig, IngestPipeline sig, _chat_loop import, role policies), 5 collection errors (regex/trafilatura)
- ruff: All checks passed

### Quality Notes

- Upstream gap: test-writer and builder did not commit deliverables. Auditor committed as leftovers.
- Follow-up tasks #822 and #823 created at ideation. Note: #822 is redundant since #812 already implemented the removal.

### Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 0444ded | refactor | core/__init__.py, test_core_init_clean.py, test_exception_hierarchy.py, core-init-reexport-removal.md | #812 |

### Confidence: .97

### Action: archive
