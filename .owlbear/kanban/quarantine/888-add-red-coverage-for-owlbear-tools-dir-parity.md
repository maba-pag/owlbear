---
id: 888
title: Add RED coverage for owlbear.tools dir() parity
status: archived
priority: nice-to-have
created: 2026-03-21T06:13:43.3428661+01:00
updated: 2026-03-21T14:06:53.431194+01:00
started: 2026-03-21T14:06:48.9865697+01:00
completed: 2026-03-21T14:06:48.9865697+01:00
tags:
    - test
    - architecture
    - scope:tools
    - type:test
parent: 859
depends_on:
    - 879
class: standard
---

This is the RED test predecessor for #883. Keep it scoped to dir() parity coverage in tests/test_tools_lazy_exports.py.

## AC

- [ ] Update tests/test_tools_lazy_exports.py only; do not change src/owlbear/tools/__init__.py in this task.
- [ ] Replace the current no-custom-__dir__ assertion with positive dir() parity coverage for the targeted owlbear.tools exception while preserving the existing no-lazy_loader guard.
- [ ] Add a clean-subprocess assertion using the existing subprocess.run([sys.executable, -c, ...], capture_output=True, text=True, check=False) pattern already used in this file.
- [ ] The new subprocess assertion imports owlbear.tools, calls dir(owlbear.tools), and verifies the returned names expose exactly AskUserToolset, FileToolset, GitLocalToolset, GitHubToolset, HookedToolset, KanbanToolset, MCPServerRegistry, TerminalToolset, find_toolset, and unwrap.
- [ ] The same subprocess assertion verifies calling dir(owlbear.tools) does not load owlbear.tools.github_api or owlbear.core.retry into sys.modules.
- [ ] Preserve the existing #879 lazy-export coverage in tests/test_tools_lazy_exports.py for module-level __getattr__, globals caching, unsupported-name AttributeError, and the no-lazy_loader constraint.
- [ ] On the current tree, uv run pytest tests/test_tools_lazy_exports.py -q --tb=short fails because dir(owlbear.tools) does not yet expose the curated public names, not because prior #879 lazy-export assertions were weakened or removed.
- [ ] uv run ruff check tests/test_tools_lazy_exports.py passes.

See docs/research/tools-root-lazy-exports-dir-parity.md.

[[2026-03-21]] Sat 06:29

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Update tests/test_tools_lazy_exports.py only; do not change src/owlbear/tools/__init__.py in this task. | Precise single-file RED scope that keeps the test task isolated from the runtime implementation in #883. | Kept as written. |
| Replace the current no-custom-__dir__ assertion with positive dir() parity coverage for the targeted owlbear.tools exception while preserving the existing no-lazy_loader guard. | Matches the current test shape: AC 8 in tests/test_tools_lazy_exports.py currently forbids __dir__, and the no-lazy_loader guard should survive the replacement. | Kept as written. |
| Add a clean-subprocess assertion using the existing subprocess.run([sys.executable, -c, ...], capture_output=True, text=True, check=False) pattern already used in this file. | Mechanically verifiable and consistent with the existing subprocess-based lazy-import checks in the same file. | Kept as written. |
| The new subprocess assertion imports owlbear.tools, calls dir(owlbear.tools), and verifies the returned names expose exactly AskUserToolset, FileToolset, GitLocalToolset, GitHubToolset, HookedToolset, KanbanToolset, MCPServerRegistry, TerminalToolset, find_toolset, and unwrap. | Exact-name contract is precise and aligned with the existing 10-name public __all__ surface. | Kept as written. |
| The same subprocess assertion verifies calling dir(owlbear.tools) does not load owlbear.tools.github_api or owlbear.core.retry into sys.modules. | Correctly protects #879's lazy-import invariant while scoping the check to the dir() codepath this task introduces. | Kept as written. |
| Preserve the existing #879 lazy-export coverage in tests/test_tools_lazy_exports.py for module-level __getattr__, globals caching, unsupported-name AttributeError, and the no-lazy_loader constraint. | Important regression boundary: the RED task tightens one assertion without weakening the earlier lazy-export contract. | Kept as written. |
| On the current tree, uv run pytest tests/test_tools_lazy_exports.py -q --tb=short fails because dir(owlbear.tools) does not yet expose the curated public names, not because prior #879 lazy-export assertions were weakened or removed. | Valid RED requirement. Verified current runtime probe returns none of the curated names from dir(owlbear.tools) while leaving owlbear.tools.github_api and owlbear.core.retry absent from sys.modules. | Kept as written. |
| uv run ruff check tests/test_tools_lazy_exports.py passes. | Scoped, verifiable lint gate with no unrelated baseline debt in the target file. | Kept as written. |

### Architecture Notes

- Verified tests/test_tools_lazy_exports.py is the dedicated lazy-export coverage file and currently contains the opposite __dir__ expectation, so this task belongs there and remains test-only.
- Verified src/owlbear/tools/__init__.py exposes __all__ plus cached __getattr__ but no __dir__, and a clean probe currently returns no curated names from dir(owlbear.tools) while owlbear.tools.github_api and owlbear.core.retry stay absent from sys.modules.
- Verified #883 already depends_on #888 and #879, so the RED to GREEN sequence is encoded mechanically rather than only described in prose.
- Single-domain check passes: this task is purely scope:tools and type:test, with no spillover into the runtime change or repo-wide lazy-export policy.
- Layering and security checks pass: the task reuses an existing subprocess assertion pattern in the test file and introduces no new dependency or system boundary.

### Changes Made

- Claimed #888 for architect review.
- Verified docs/research/tools-root-lazy-exports-dir-parity.md against the current test file and tools package root.
- Verified the current runtime gap with a clean probe and confirmed the target file's scoped ruff check passes.
- Advanced #888 from backlog to todo.

### Dependencies

- Added/Removed/Verified: verified #879 remains the archived prerequisite; verified #883 depends_on #888 and #879; no split or additional dependency edits needed.

[[2026-03-21]] Sat 06:53

## Test-Writer Notes

- Test file: tests/test_tools_lazy_exports.py
- Classes: TestFromAC_NoNewDependencies (1 replaced), TestFromAC_DirParity (new)
- 2 new tests, all FAIL; 14 prior pass
- ruff: clean

[[2026-03-21]] Sat 12:30

## Builder Notes

- Non-implementation pass-through — AC explicitly forbids changes to src/owlbear/tools/__init__.py in this task.
- Files changed: none (RED test task only)
- RED state verified: 14 passed, 2 failed
  - TestFromAC_NoNewDependencies::test_tools_module_has_custom_dir_for_parity FAILED (AssertionError: owlbear.tools does not define a custom __dir__)
  - TestFromAC_DirParity::test_dir_exposes_all_curated_names_subprocess FAILED (dir(owlbear.tools) missing all 10 curated names)
- Prior #879 assertions: all 14 pass — no regressions, no weakened assertions
- Failure reason matches AC: __dir__ absent, not because prior tests were changed
- Lint: ruff check tests/test_tools_lazy_exports.py — All checks passed

[[2026-03-21]] Sat 12:59

## Review Evidence

## Review: #888 - Add RED coverage for owlbear.tools dir() parity

### Test Results

- Command: uv run pytest tests/test_tools_lazy_exports.py -q --tb=short
- Result: 14 passed, 2 failed, 2 warnings
- Failing tests:
  - TestFromAC_NoNewDependencies::test_tools_module_has_custom_dir_for_parity
  - TestFromAC_DirParity::test_dir_exposes_all_curated_names_subprocess
- Failure cause matches RED target: owlbear.tools has no custom __dir__, so dir(owlbear.tools) does not expose the curated names yet.

### Lint Results

- Command: uv run ruff check tests/test_tools_lazy_exports.py
- Result: All checks passed

### Coverage

- Command: uv run pytest tests/test_tools_lazy_exports.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short
- Result: 14 passed, 2 failed (same RED failures)
- Module coverage evidence:
  - src/owlbear/tools/__init__.py: 100% (13 statements, 0 missed)

### Pass 1 - CRITICAL

#### Security Review

- No hardcoded secrets introduced in task scope.
- No SQL/shell/template injection sink introduced by this task.
- No path-traversal or unsafe deserialization added.
- No eval/exec use added.
- No new dependency introduced.
- No secret leakage in logs/errors introduced.
- Verdict: No security issues found.

#### Test Integrity (TestFromAC comparison)

| Original Test | Change Made | Assessment |
|---|---|---|
| TestFromAC_NoNewDependencies::test_tools_module_has_custom_dir_for_parity | Present in tests/test_tools_lazy_exports.py and failing for expected RED reason | PRESERVED |
| TestFromAC_DirParity::test_dir_exposes_all_curated_names_subprocess | Present in tests/test_tools_lazy_exports.py and failing for expected RED reason | PRESERVED |

Integrity notes:

- Builder notes report non-implementation pass-through for this RED task.
- Current scoped status confirms no runtime file change in src/owlbear/tools/__init__.py during this task review.

#### Test Quality

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | ADEQUATE | Uses concrete failure checks (missing curated names list, explicit __dir__ presence assertion) with clear diagnostics. |
| Negative/error paths | STRONG | Covers unsupported-name AttributeError and lazy-load side-effect guards in subprocess assertions. |
| Mutation reasoning | STRONG | Reintroducing eager-load side effects or omitting __dir__ parity breaks the targeted tests. |
| Test independence | STRONG | Subprocess-based checks isolate interpreter/module state and avoid inter-test contamination. |
| Descriptive names | STRONG | Test names state exact behavior and expected outcome. |

#### Data Safety

- No data-safety concerns found in task scope (tests-only RED task; no persistence or concurrency path changes).

### Pass 2 - INFORMATIONAL

- Process hygiene note: tests/test_tools_lazy_exports.py is currently untracked in git status. This does not change AC behavior evidence for this review, but should be handled in commit hygiene before archival.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---|---|---|---|
| Update tests/test_tools_lazy_exports.py only; do not change src/owlbear/tools/__init__.py | git status scoped to these files shows tests/test_tools_lazy_exports.py present while src/owlbear/tools/__init__.py has no new task-local modification and still lacks __dir__ | Scope constraint | PASS |
| Replace no-custom-__dir__ assertion with positive dir() parity coverage while preserving no-lazy_loader guard | tests/test_tools_lazy_exports.py:332 and tests/test_tools_lazy_exports.py:347 and tests/test_tools_lazy_exports.py:369 | test_tools_module_has_custom_dir_for_parity; test_lazy_loader_package_not_imported_by_tools; TestFromAC_DirParity::* | PASS |
| Add clean-subprocess assertion using subprocess.run(..., capture_output=True, text=True, check=False) | tests/test_tools_lazy_exports.py:413 and tests/test_tools_lazy_exports.py:417 | test_dir_exposes_all_curated_names_subprocess | PASS |
| Subprocess assertion checks dir(owlbear.tools) exposes curated public names | tests/test_tools_lazy_exports.py:386 and tests/test_tools_lazy_exports.py:405 | test_dir_exposes_all_curated_names_subprocess | PASS |
| Same assertion checks dir() does not load owlbear.tools.github_api or owlbear.core.retry | tests/test_tools_lazy_exports.py:408 and tests/test_tools_lazy_exports.py:410 | test_dir_exposes_all_curated_names_subprocess | PASS |
| Preserve #879 lazy-export coverage (__getattr__, caching, unsupported-name AttributeError, no-lazy_loader) | tests/test_tools_lazy_exports.py:55 and tests/test_tools_lazy_exports.py:99 and tests/test_tools_lazy_exports.py:282 and tests/test_tools_lazy_exports.py:347; pytest result shows 14 pass | Existing TestFromAC classes outside the 2 new RED failures | PASS |
| On current tree, pytest fails because dir() parity is missing, not prior regressions | pytest output: only 2 failures are the new dir parity checks; 14 prior tests pass | test_tools_module_has_custom_dir_for_parity; test_dir_exposes_all_curated_names_subprocess | PASS |
| uv run ruff check tests/test_tools_lazy_exports.py passes | ruff scoped command output: All checks passed | Lint gate | PASS |

### Verdict: PASS

- Confidence: .94

### Action Taken

- review -> docs

[[2026-03-21]] Sat 13:29

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | RED test-only task; no behavior, API, or convention change |
| 2 | Docstrings complete | No | N/A | Only tests/test_tools_lazy_exports.py modified; no public Python API added or changed |
| 3 | sources/overview.md | No | N/A | Reused existing subprocess pattern within same test file; no external inspiration |
| 4 | README.md | No | N/A | No CLI commands added or modified |
| 5 | Research doc produced | Yes | Pass | docs/research/tools-root-lazy-exports-dir-parity.md exists and linked in task body; follow-up #883 depends on this RED contract |

### Files Updated

- None

### Scratch Files Cleaned

- None (no docs/scratch/888-* files found)
