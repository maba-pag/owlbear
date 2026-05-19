---
id: 883
title: Preserve dir() parity for owlbear.tools lazy exports
status: archived
priority: nice-to-have
created: 2026-03-20T16:49:05.1644711+01:00
updated: 2026-03-21T18:06:32.4505201+01:00
started: 2026-03-21T18:06:27.4440838+01:00
completed: 2026-03-21T18:06:27.4440838+01:00
tags:
    - architecture
    - scope:tools
    - type:build
parent: 859
depends_on:
    - 879
    - 888
class: standard
---

This is the GREEN implementation task for #888. Keep it scoped to dir() parity in src/owlbear/tools/__init__.py.

## AC

- [ ] Update src/owlbear/tools/__init__.py only for the runtime change; keep scope limited to the tools package root and do not modify tool submodules or other package roots.
- [ ] Add a module-level __dir__ in src/owlbear/tools/__init__.py that returns the curated public export surface from __all__ without importing lazy target modules.
- [ ] After bare import owlbear.tools, dir(owlbear.tools) exposes exactly AskUserToolset, FileToolset, GitLocalToolset, GitHubToolset, HookedToolset, KanbanToolset, MCPServerRegistry, TerminalToolset, find_toolset, and unwrap.
- [ ] Calling dir(owlbear.tools) after bare import still leaves owlbear.tools.github_api and owlbear.core.retry absent from sys.modules.
- [ ] The existing 10-name __all__ contract remains unchanged and no public names beyond that contract are added.
- [ ] Keep this as a targeted owlbear.tools exception; do not add __dir__ to src/owlbear/memory/knowledge/__init__.py, introduce repo-wide lazy-export helpers, or add a new runtime dependency.
- [ ] GREEN verification target for this task is uv run pytest tests/test_tools_lazy_exports.py -q --tb=short passing after the implementation change.

## Research

- Doc: docs/research/tools-root-lazy-exports-dir-parity.md
- Key findings:
  - Clean runtime probe: bare import owlbear.tools keeps owlbear.tools.github_api and owlbear.core.retry out of sys.modules, but dir(owlbear.tools) exposes none of the 10 supported names from __all__.
  - Python data model + PEP 562 make module-level __dir__ the supported fix for dynamic module attributes.
  - Scientific Python SPEC 1 and lazy-loader prior art both pair __dir__ with lazy __getattr__ to preserve interactive exploration without eager imports.
  - src/owlbear/memory/knowledge/__init__.py remains the repo precedent for leaving __dir__ out by default, so this should stay a targeted owlbear.tools exception.
- Recommendation (.92):
  - Add a minimal module-level __dir__ in src/owlbear/tools/__init__.py that returns list(__all__).
  - Keep lazy_loader out of scope and keep this exception limited to owlbear.tools.
  - Replace the current tests/test_tools_lazy_exports.py no-custom-__dir__ assertion with positive parity checks.
- Follow-up task handling:
  - Created #888: Add RED coverage for owlbear.tools dir() parity.
- Attribution:
  - Added task #883 source rows to docs/sources/overview.md.

[[2026-03-21]] Sat 06:14

## Architecture Review

__Verdict:__ REFINE

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| dir(owlbear.tools) includes the 10 supported names after bare import | Correct goal, but it must be anchored to the exact __all__ contract rather than a loose inclusion check | Rewrote into an explicit GREEN AC tied to the existing 10-name surface |
| bare import still leaves owlbear.tools.github_api and owlbear.core.retry absent from sys.modules | Correct constraint, but it must remain true after calling dir() rather than only after import | Kept and tightened to a post-dir() subprocess assertion |
| no public names beyond the existing __all__ contract are added | Architecturally correct and mechanically verifiable | Kept and tied to unchanged __all__ plus a metadata-only __dir__ |
| scoped tests pass | Too vague for execution and missing a RED predecessor | Created RED task #888 and pinned the GREEN verification target to tests/test_tools_lazy_exports.py |

### Architecture Notes

- Verified src/owlbear/tools/__init__.py already mirrors src/owlbear/memory/knowledge/__init__.py via a cached _LAZY_IMPORTS plus module-level __getattr__ pattern; __dir__ is the only missing seam for interactive discovery parity.
- Verified tests/test_tools_lazy_exports.py is the dedicated post-#879 coverage file and currently encodes the opposite __dir__ expectation, so the RED update belongs there rather than in tests/test_tools_init_reexports.py.
- Single-domain check passes: the runtime change stays inside scope:tools, and the test work is isolated in the new RED predecessor.
- Layering check passes: a metadata-only module __dir__ does not introduce new upward imports or new cross-layer dependencies.

### Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| owlbear.tools.__dir__() | Returns names beyond __all__ or diverges from the supported contract | None | Prevented by binding the contract to the existing 10-name __all__ surface | dir(owlbear.tools) misrepresents the supported API |
| owlbear.tools.__dir__() | Triggers lazy imports while collecting names | Import side effects visible in sys.modules | Prevented by requiring a metadata-only implementation and subprocess coverage | Bare import regresses #879's import-cost fix |

### Changes Made

- Created #888 as the RED test predecessor for dir() parity.
- Rewrote #883 into a discrete GREEN-phase contract scoped to src/owlbear/tools/__init__.py.
- Added depends_on #888 so the build task cannot advance ahead of its RED pair.
- Kept #883 in backlog because the new RED task still needs its own architect gate before either task should move forward.

### Dependencies

- Added/Removed/Verified: verified #879 is archived and remains the runtime prerequisite; added #888 as the RED predecessor; verified parent #859 still owns the optional __dir__ follow-up track.

[[2026-03-21]] Sat 14:00

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Update src/owlbear/tools/__init__.py only for the runtime change; keep scope limited to the tools package root and do not modify tool submodules or other package roots. | Precise single-file GREEN scope aligned with the existing lazy-export package root. | Kept as written. |
| Add a module-level __dir__ in src/owlbear/tools/__init__.py that returns the curated public export surface from __all__ without importing lazy target modules. | Matches the PEP 562 module hook and the current __getattr__ plus _LAZY_IMPORTS pattern in src/owlbear/tools/__init__.py; the metadata-only requirement prevents eager imports. | Kept as written. |
| After bare import owlbear.tools, dir(owlbear.tools) exposes exactly AskUserToolset, FileToolset, GitLocalToolset, GitHubToolset, HookedToolset, KanbanToolset, MCPServerRegistry, TerminalToolset, find_toolset, and unwrap. | Exact public-surface contract is tied to the existing 10-name __all__ and aligns with the RED subprocess contract in tests/test_tools_lazy_exports.py. | Kept as written. |
| Calling dir(owlbear.tools) after bare import still leaves owlbear.tools.github_api and owlbear.core.retry absent from sys.modules. | Preserves #879's lazy-import invariant on the new dir() codepath. | Kept as written. |
| The existing 10-name __all__ contract remains unchanged and no public names beyond that contract are added. | Keeps __all__ as the single source of truth and prevents API widening. | Kept as written. |
| Keep this as a targeted owlbear.tools exception; do not add __dir__ to src/owlbear/memory/knowledge/__init__.py, introduce repo-wide lazy-export helpers, or add a new runtime dependency. | Confines the change to scope:tools and respects the absence of any other module-level __dir__ precedent in src/. | Kept as written. |
| GREEN verification target for this task is uv run pytest tests/test_tools_lazy_exports.py -q --tb=short passing after the implementation change. | Now valid because RED predecessor #888 is complete and the scoped test file is the executable contract for this GREEN task. | Kept as written. |

### Architecture Notes

- Verified src/owlbear/tools/__init__.py currently mirrors the cached _LAZY_IMPORTS plus __getattr__ pattern in src/owlbear/memory/knowledge/__init__.py, with module-level __dir__ as the only missing parity seam.
- Verified tests/test_tools_lazy_exports.py now contains the RED subprocess coverage for dir() parity and lazy-import preservation, so #883 no longer relies on prose alone for its executable contract.
- Verified there is still no other module-level __dir__ precedent in src/, so this remains a targeted tools-package exception rather than a repo-wide lazy-export policy change.
- Single-domain check passes: the task is a scope:tools runtime metadata change only, with the RED test work isolated in #888.
- Layering and security checks pass: metadata-only __dir__ adds no new imports, no new dependency, and no new system boundary.
- The earlier reason to keep #883 in backlog is resolved because #888 now exists, is complete, and remains encoded in depends_on alongside #879.

### Changes Made

- Claimed #883 for architect review.
- Re-validated docs/research/tools-root-lazy-exports-dir-parity.md against the current src/owlbear/tools/__init__.py, src/owlbear/memory/knowledge/__init__.py, and tests/test_tools_lazy_exports.py.
- Verified #888 is complete and still linked as the RED predecessor in depends_on.
- Advanced #883 from backlog to todo.

### Dependencies

- Added/Removed/Verified: verified #879 archived prerequisite; verified #888 done as the RED predecessor; no split or additional dependency edits needed.

[[2026-03-21]] Sat 14:54

## Test-Writer Notes

- Test file: tests/test_tools_lazy_exports.py
- Classes added: TestFromAC_DirExactBoundary (new, 1 test)
- Prior RED tests preserved: TestFromAC_NoNewDependencies::test_tools_module_has_custom_dir_for_parity (from #888), TestFromAC_DirParity::test_dir_exposes_all_curated_names_subprocess (from #888)
- Total: 3 failing, 14 passing; ruff: clean
- AC coverage:
| AC Line | Test(s) | Category |
|---------|---------|----------|
| Add __dir__ to owlbear.tools.__dict__ | test_tools_module_has_custom_dir_for_parity | happy |
| dir(owlbear.tools) includes all 10 curated names | test_dir_exposes_all_curated_names_subprocess | happy |
| dir() does not load github_api or core.retry | test_dir_exposes_all_curated_names_subprocess | edge |
| dir(owlbear.tools) exposes exactly those 10 names (no extras) | test_dir_exposes_no_public_names_beyond_all_contract_subprocess | boundary |

[[2026-03-21]] Sat 15:40

## Builder Notes\n- Files changed: src/owlbear/tools/__init__.py (+4 lines: __dir__ function)\n- Tests: 17 passed (tests/test_tools_lazy_exports.py)\n- Coverage: 93% on src/owlbear/tools/__init__.py (15 stmts, 1 miss: return inside __dir__, only hit by subprocess not tracked in-process)\n- Lint: ruff check clean, ruff format clean\n- Evidence: 17 passed, 0 failed, 2 warnings in 8.98s\n- Fixes applied: Added def __dir__() -> list[str]: return list(__all__) before __getattr__ in src/owlbear/tools/__init__.py

[[2026-03-21]] Sat 16:24

## Review Evidence

### Context Checked

- Reviewed AC and prior task body sections (Architecture Review, Test-Writer Notes, Builder Notes) via `kanban\kanban-md.exe show 883`.
- Verified builder commit `ac99be3` and RED baseline commit `e7bf6bc`.

### Independent Execution

- `uv run pytest tests/test_tools_lazy_exports.py -q --tb=short` => 17 passed, 2 warnings.
- `uv run pytest tests/test_tools_lazy_exports.py --cov --cov-report=term-missing --cov-fail-under=0 -q --tb=short` => 17 passed, 2 warnings.
- Coverage spot check: `src/owlbear/tools/__init__.py` => 93% (15 stmts, 1 miss).
- `uv run ruff check src/owlbear/tools/__init__.py tests/test_tools_lazy_exports.py` => All checks passed.
- IDE diagnostics (`get_errors`) on both in-scope files => no errors.

### Pass 1 Critical Checks

#### Security Review (OWASP-targeted)

- Hardcoded secrets: none found in in-scope source/test.
- Injection risks (SQL/shell/template): none; `__dir__` is metadata-only and does not process user input.
- Path traversal: none in in-scope change.
- Insecure deserialization/eval/exec: none in in-scope change.
- Input validation boundaries: not applicable to this change (no external/user input path added).
- Dependency risk: no dependency file touched; no new runtime dependency introduced.
- Secret leakage via logs/errors: none introduced.

#### TestFromAC Integrity (required comparison)

- Command: `git diff --name-only e7bf6bc..ac99be3 -- tests/test_tools_lazy_exports.py` produced no output.
- Interpretation: builder commit did not modify RED `TestFromAC_*` tests.

| Original Test | Change Made | Assessment |
|---|---|---|
| `TestFromAC_NoNewDependencies::test_tools_module_has_custom_dir_for_parity` | No change in builder commit | PRESERVED |
| `TestFromAC_DirParity::test_dir_exposes_all_curated_names_subprocess` | No change in builder commit | PRESERVED |
| `TestFromAC_DirExactBoundary::test_dir_exposes_no_public_names_beyond_all_contract_subprocess` | No change in builder commit | PRESERVED |

#### Test Quality Evaluation

| Dimension | Rating | Evidence |
|---|---|---|
| Assertion specificity | STRONG | Tests assert exact symbol sets and specific sys.modules invariants (not loose truthy checks). |
| Negative/error-path coverage | STRONG | Unknown attribute error-path tests in `TestFromAC_UnsupportedAttributeError`. |
| Manual mutation resistance | STRONG | If `__dir__` returns extra/fewer names or triggers imports, subprocess assertions fail. |
| Test independence | STRONG | Subprocess-based checks ensure clean import state per scenario. |
| Test naming clarity | STRONG | Descriptive method names communicate exact contract behavior. |

#### Data Safety

- Unvalidated LLM output persistence: none.
- Race-condition risk: none introduced.
- Missing atomicity risk: none introduced.
- Unbounded-input risk: none introduced.

### AC Compliance

| AC Line | Evidence | Status |
|---|---|---|
| Update `src/owlbear/tools/__init__.py` only for runtime change; no tool submodule/other package-root edits | `git show --name-only --stat --oneline ac99be3` lists only `src/owlbear/tools/__init__.py` | PASS |
| Add module-level `__dir__` returning curated surface from `__all__` without lazy imports | `src/owlbear/tools/__init__.py` line 40 defines `def __dir__() -> list[str]:` and line 41 returns `list(__all__)`; subprocess tests verify no eager imports | PASS |
| After bare import, `dir(owlbear.tools)` exposes exactly the 10 supported names | `tests/test_tools_lazy_exports.py` line 377 (`test_dir_exposes_all_curated_names_subprocess`) and line 439 (`test_dir_exposes_no_public_names_beyond_all_contract_subprocess`) both pass | PASS |
| Calling `dir(owlbear.tools)` after bare import keeps `owlbear.tools.github_api` and `owlbear.core.retry` out of `sys.modules` | Assertions at lines 408-411 in `tests/test_tools_lazy_exports.py` run in subprocess and pass in scoped pytest run | PASS |
| Existing 10-name `__all__` contract unchanged and no extra public names added | `src/owlbear/tools/__init__.py` line 11 defines 10-name `__all__`; commit diff adds only `__dir__`; boundary test at line 439 enforces exact public set | PASS |
| Keep this as targeted `owlbear.tools` exception; do not add `__dir__` to `src/owlbear/memory/knowledge/__init__.py`, add helper framework, or add dependency | `Select-String` found no `def __dir__` in `src/owlbear/memory/knowledge/__init__.py`; no helper/dependency files touched by builder commit | PASS |
| GREEN verification target `uv run pytest tests/test_tools_lazy_exports.py -q --tb=short` passes | Independent run result: 17 passed, 2 warnings | PASS |

### Informational (Pass 2)

- No blocking informational defects identified.

### Verdict

- PASS
- Confidence: .96

[[2026-03-21]] Sat 17:15

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Metadata-only dunder added; no behavior or convention change visible to agents/users |
| 2 | Docstrings complete | No | N/A | __dir__ is a 2-line module dunder; module docstring covers the lazy-export rationale; __getattr__ peer has no docstring either — consistent |
| 3 | docs/sources/overview.md | Yes | Pass | Section 'owlbear.tools dir() Parity Follow-up (Task #883)' present with 4 rows: Python data model docs, PEP 562, Scientific Python SPEC 1, lazy-loader |
| 4 | README.md | No | N/A | No CLI commands added |
| 5 | Research doc linked | Yes | Pass | docs/research/tools-root-lazy-exports-dir-parity.md exists; linked in task body; follow-up #888 created and archived |
| 6 | No impact | N/A | — | Items 3 and 5 applied |

### Files Updated

- None (sources/overview.md and research doc were already accurate)

### Scratch Files Cleaned

- None (no docs/scratch/883-* files exist)

[[2026-03-21]] Sat 18:06

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Update src/owlbear/tools/__init__.py only | Builder commit ac99be3 touches only that file (git show --name-only) | PASS |
| Add module-level __dir__ returning curated surface from __all__ | Lines 43-44: `def __dir__() -> list[str]: return list(__all__)` | PASS |
| dir(owlbear.tools) exposes exactly the 10 supported names after bare import | test_dir_exposes_all_curated_names_subprocess + test_dir_exposes_no_public_names_beyond_all_contract_subprocess both pass (17/17) | PASS |
| dir() after bare import keeps github_api and core.retry out of sys.modules | Subprocess assertions in test file pass; verified in scoped run | PASS |
| Existing 10-name __all__ contract unchanged, no extra public names | __all__ at line 11 has exactly 10 entries; boundary test enforces exact set | PASS |
| Targeted owlbear.tools exception only | No __dir__ in src/owlbear/memory/knowledge/__init__.py (grep confirmed); no helper framework or new dependency | PASS |
| GREEN verification: uv run pytest tests/test_tools_lazy_exports.py -q --tb=short passes | 17 passed, 2 warnings in 9.55s | PASS |

### Test Results

- pytest (scoped): 17 passed, 0 failed
- pytest (full suite): 3723 passed, 97 failed (all pre-existing: numpy compat, AgentRegistry signature, bootstrap unpacking â€” none related to #883)
- ruff: All checks passed

### Commits Verified

- ac99be3 feat: add __dir__ to tools/__init__.py for dir() parity (#883, builder)
- e7bf6bc test: add RED coverage for owlbear.tools dir() parity (#888, test-writer)

### Confidence: .97

### Action: archive
