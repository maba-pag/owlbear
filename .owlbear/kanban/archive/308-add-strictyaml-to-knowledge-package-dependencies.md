---
id: 308
title: Add strictyaml to knowledge package dependencies
status: archived
priority: medium
created: 2026-03-30 20:30:35.143878+02:00
updated: 2026-03-31 04:34:46.045266+02:00
started: 2026-03-31 04:34:45.514238+02:00
completed: 2026-03-31 04:34:45.514238+02:00
tags:
- phase-2
- scope:knowledge
- type:build
class: standard
archival_reason: completed
archival_refs: []
---

## Objective
Add strictyaml to packages/knowledge pyproject.toml dependencies so the loader module can import it.

## Acceptance Criteria
- [ ] strictyaml>=1.7 added to [project.dependencies] in packages/knowledge/pyproject.toml
- [ ] uv lock updated
- [ ] Import works: python -c 'from owlbear_knowledge import loader'

[[2026-03-30]] Mon 21:19
## Research
N/A - trivial dep addition. strictyaml 1.7.3 (latest, 2023-03-10) is pure Python, ~124KB wheel, zero native deps. Already a root dev dep, needs adding to knowledge package for loader (#176).

AC refinements (architect):
- AC 3 import check depends on #176 creating loader.py; refine to: import strictyaml, or defer AC 3 to #176
- #176 should add depends_on: [32, 308] so builder has the dep available

Checklist: 1-sound concept, 2-already root dep, 3-PyPI 1.7.3, 4-pure Python 3.12 compat. All trivial.

[[2026-03-30]] Mon 21:30
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| strictyaml>=1.7 in [project.dependencies] | Clear, verifiable, correct version spec | Keep |
| uv lock resolves | Mechanical check, verifiable | Keep |
| Import from owlbear_knowledge import loader | Depends on #176 (loader.py not created yet) | Refined to: import strictyaml in package context |

### Architecture Notes
- Trivial dep addition following existing pattern (pydantic already in [project.dependencies])
- strictyaml 1.7.3: pure Python, zero native deps, 124KB wheel, Python 3.12 compatible
- Already present as root dev dep; adding as knowledge package runtime dep
- No new security surface, no code changes, no failure modes
- #176 should update depends_on to include 308

### Changes Made
- Refined AC 3: changed import check from loader (not yet created) to strictyaml directly
- Added architecture notes about pattern and dependency relationship

### Dependencies
- Verified: no depends_on needed (standalone dep addition)
- Note: #176 should add depends_on: [32, 308] (not edited here per one-task rule)

[[2026-03-30]] Mon 22:47
## Test-Writer Notes
- Test file: tests/test_knowledge_strictyaml_dep_308.py
- Classes: TestFromAC_StrictYAMLDependency
- Tests per category: happy 5, edge 1, boundary 2
- Total: 8 tests, all FAIL
- ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| strictyaml>=1.7 in project.dependencies | test_pyproject_has_strictyaml_in_project_dependencies, test_pyproject_strictyaml_version_spec_gte_1_7 | happy |
| version uses >= not == | test_pyproject_strictyaml_uses_gte_operator_not_exact_pin | boundary |
| uv lock updated - deps list | test_lock_owlbear_knowledge_runtime_deps_include_strictyaml | happy |
| uv lock updated - metadata requires-dist | test_lock_owlbear_knowledge_metadata_requires_dist_includes_strictyaml | happy |
| uv lock metadata version spec | test_lock_owlbear_knowledge_metadata_strictyaml_version_spec | boundary |
| import strictyaml in package context | test_installed_package_metadata_declares_strictyaml_runtime_dep | happy |
| metadata version constraint | test_installed_package_metadata_strictyaml_version_constraint | edge |

[[2026-03-30]] Mon 23:47
## Builder Notes
- Files changed: packages/knowledge/pyproject.toml, uv.lock
- Tests: 8 passed, ruff clean
- Evidence: 8 passed in 0.50s
- Fixes applied: None

[[2026-03-31]] Tue 03:42
## Review Evidence
**Reviewer:** reviewer | **Date:** 2026-03-31

### Test Results
- pytest: 8 passed, 0 failed (tests/test_knowledge_strictyaml_dep_308.py)
- Evidence: 8 passed in 0.55s

### Lint Results
- ruff: All checks passed!

### Coverage
- No source code changed; config-only task. Coverage N/A.

### Test-Writer Coverage Table
All 7 test slots cover AC lines with STRONG specificity.

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|----------------|---------------------------|---------|
| strictyaml>=1.7 in [project.dependencies] | test_pyproject_has_strictyaml_in_project_dependencies, test_pyproject_strictyaml_version_spec_gte_1_7 | Yes - reads deps list directly and asserts >=1.7 present | COVERED |
| version uses >= not == | test_pyproject_strictyaml_uses_gte_operator_not_exact_pin | Yes - asserts '==' absent AND '>=' present | COVERED |
| uv lock runtime deps list | test_lock_owlbear_knowledge_runtime_deps_include_strictyaml | Yes - checks lock package.dependencies names | COVERED |
| uv lock metadata requires-dist | test_lock_owlbear_knowledge_metadata_requires_dist_includes_strictyaml | Yes - checks metadata.requires-dist without marker | COVERED |
| uv lock metadata version spec | test_lock_owlbear_knowledge_metadata_strictyaml_version_spec | Yes - asserts specifier == '>=1.7' exactly | COVERED |
| import strictyaml in package context | test_installed_package_metadata_declares_strictyaml_runtime_dep | Yes - uses importlib.metadata.requires at runtime | COVERED |
| metadata version constraint >=1.7 | test_installed_package_metadata_strictyaml_version_constraint | Yes - checks '>=1.7' in live metadata requirement | COVERED |

### TestFromAC Integrity
Builder did not modify any TestFromAC tests (only pyproject.toml and uv.lock changed). All 8 tests preserved intact.

### AC Compliance Table
| AC Line | Evidence | Status |
|---------|----------|--------|
| strictyaml>=1.7 in [project.dependencies] | packages/knowledge/pyproject.toml line 8: strictyaml>=1.7 | PASS |
| uv lock updated - runtime deps | uv.lock:2068: { name = strictyaml } in owlbear-knowledge dependencies | PASS |
| uv lock updated - metadata requires-dist | uv.lock:2096: { name = strictyaml, specifier = >=1.7 } (no marker) | PASS |
| import strictyaml in package context | importlib.metadata test passes; test_installed_package_metadata_declares_strictyaml_runtime_dep confirms live metadata | PASS |

### Security
No code changes. strictyaml 1.7.3 is pure Python, zero native deps, already present as a root dev dep. No new attack surface.

### Necessity (6.6)
strictyaml was a root-level dev dep only, not declared as a runtime dep of owlbear-knowledge. Task #176 (loader.py) depends on it. Confirmed current requirement, no overlap.

### Test Quality
- Assertion specificity: STRONG - all tests assert exact values/structures
- Negative/error coverage: STRONG - boundary tests verify == is rejected, >=1.7 floor enforced
- Independence: STRONG - each test loads fresh data from disk/metadata
- Naming: STRONG - all names are descriptive

### Verdict: PASS
**Confidence: 0.97**

[[2026-03-31]] Tue 04:10
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | Config-only; no behavior, API, or convention change |
| 2 | Docstrings complete | No | N/A | Only pyproject.toml and uv.lock changed; no Python modules modified |
| 3 | sources/overview.md | No | N/A | No external patterns; strictyaml already a root dev dep |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | Research N/A per task body; trivial dep addition |

No docs impact. Config-only task (pyproject.toml + uv.lock).

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-31]] Tue 04:34
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| strictyaml>=1.7 in [project.dependencies] | packages/knowledge/pyproject.toml L8: strictyaml>=1.7 | PASS |
| uv lock updated | Committed at 67c6193; 4 lock tests pass | PASS |
| Import strictyaml in package context | 2 metadata tests pass (importlib.metadata) | PASS |

### Test Results
- pytest (task-scoped): 8 passed, 0 failed (0.41s)
- pytest (full suite): 1892 passed, 154 failed (pre-existing), 1 error. No new failures from #308.
- ruff: All checks passed

### Cross-Task Note
test_knowledge_foundation::test_pydantic_is_sole_runtime_dependency now fails (expects pydantic as sole dep). Stale assertion from #15, not a #308 defect. Needs independent update.

### Architect Quality
- AC specificity: clear and verifiable
- Edge cases: N/A (config-only)
- Design direction: architect refined AC3 correctly (loader not yet created)
- AC quality score: 4/5

### Upstream Commits
- c430890: test: add failing tests for strictyaml knowledge dep (#308, test-writer)
- 67c6193: feat: add strictyaml>=1.7 to owlbear-knowledge dependencies (#308, builder)

### Deduction breakdown: no deductions apply from rubric
### Confidence: .98
### Action: archive
