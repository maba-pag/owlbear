---
id: 879
title: Implement cached lazy exports in owlbear.tools package root
status: archived
priority: important
created: 2026-03-20T16:03:40.7037836+01:00
updated: 2026-03-21T05:23:51.5368789+01:00
started: 2026-03-21T05:23:31.9937253+01:00
completed: 2026-03-21T05:23:31.9937253+01:00
tags:
    - architecture
    - bug
    - scope:tools
    - type:build
parent: 859
depends_on:
    - 878
class: standard
---

This is the GREEN implementation task for #878. Keep it scoped to lazy exports in src/owlbear/tools/__init__.py.

## AC

- [ ] Update src/owlbear/tools/__init__.py only for the runtime export change; keep scope limited to the package root and do not modify submodules such as src/owlbear/tools/github_api.py.
- [ ] Preserve the exact 10-name public surface from #814: __all__ still contains AskUserToolset, FileToolset, GitLocalToolset, GitHubToolset, HookedToolset, KanbanToolset, MCPServerRegistry, TerminalToolset, find_toolset, and unwrap.
- [ ] Replace the eager top-level re-export imports with a module-level lazy import map plus __getattr__ in the existing repo style used by src/owlbear/memory/knowledge/__init__.py.
- [ ] For supported export names, __getattr__ imports the target relative submodule with importlib.import_module, returns the requested attribute, and caches the resolved object in module globals so repeated lookups bypass the lazy path.
- [ ] For unsupported names, the package root continues to raise normal AttributeError rather than widening the public API or returning a sentinel.
- [ ] After a bare import owlbear.tools, owlbear.tools.github_api and owlbear.core.retry remain absent from sys.modules until a lazy export is actually accessed, satisfying the RED subprocess regression in #878.
- [ ] from owlbear.tools import GitHubToolset and the existing re-export identity coverage in tests/test_tools_init_reexports.py pass without weakening the current compatibility assertions.
- [ ] Do not add __dir__, lazy_loader, or any other new runtime dependency in this task.
- [ ] GREEN verification target for this task is uv run pytest tests/test_tools_init_reexports.py -q --tb=short passing after the implementation change.

[[2026-03-20]] Fri 16:45

## Research

- Doc: docs/research/tools-root-lazy-exports-implementation.md
- Key findings:
  - PEP 562 and the Python data model make module-level __getattr__ the right hook for package-root lazy exports.
  - OwlBear already has the cached importlib plus globals pattern in src/owlbear/memory/knowledge/__init__.py, and tests/test_tools_init_reexports.py plus tests/test_knowledge_exports.py already define the API and subprocess verification shape.
  - Scientific Python SPEC 1 allows direct module __getattr__ lazy loading and treats helper packages as optional; with no lazy-loader in pyproject.toml and #879 forbidding new deps, an inline map is the smallest fit.
- Recommendation (.93 confidence): keep the 10-name __all__ contract, add a _LAZY_IMPORTS map plus cached __getattr__ in src/owlbear/tools/__init__.py, and leave __dir__ plus helper dependencies out of scope.
- Follow-up tasks:
  - Existing execution path remains #878 (RED) -> #879 (GREEN).
  - Created #882: Document package-root lazy export pattern for OwlBear public APIs.
  - Create command: kanban\kanban-md.exe create 'Document package-root lazy export pattern for OwlBear public APIs' --priority nice-to-have --status ideation --tags docs,architecture,scope:tools,type:docs --parent 879 --body 'AC: add a short architecture note describing when package __init__.py may use cached module-level __getattr__ import maps; document why OwlBear keeps __all__ explicit and avoids adding lazy-loader for small public surfaces; cite src/owlbear/memory/knowledge/__init__.py and src/owlbear/tools/__init__.py as the current repo examples.'
- Attribution updates: added docs/sources/overview.md rows for the Python data model docs, PEP 562, Scientific Python SPEC 1, and the lazy-loader project docs.

[[2026-03-20]] Fri 18:10

## Architecture Review

__Verdict:__ APPROVED

### AC Assessment

| AC Line | Assessment | Action |
|---------|------------|--------|
| Original one-line AC bundled implementation shape, side-effect behavior, compatibility preservation, and dependency scope into one sentence | Directionally correct but not mechanically checkable by builder or reviewer as written | Rewrote into 9 discrete GREEN-phase AC lines |
| Replace eager package-root imports with cached lazy exports in src/owlbear/tools/__init__.py | Matches the existing repo precedent in src/owlbear/memory/knowledge/__init__.py and stays inside the tools layer | Kept and anchored to the local lazy-export pattern |
| Bare import owlbear.tools must not load owlbear.tools.github_api or owlbear.core.retry | This is the measurable side-effect regression already captured by the RED subprocess shape in tests/test_tools_init_reexports.py and tests/test_knowledge_exports.py | Kept and made it explicit that the absence holds until a lazy export is accessed |
| from owlbear.tools import GitHubToolset and re-export identity tests pass | This is the public compatibility contract established by #814 in tests/test_tools_init_reexports.py | Kept and pinned to existing compatibility assertions |
| No new dependency is added | Correct KISS/YAGNI constraint because pyproject.toml has no lazy-loader helper and the task already has a local inline pattern to copy | Kept and made helper dependencies plus __dir__ explicitly out of scope |

### Architecture Notes

- Verified src/owlbear/tools/__init__.py currently performs 10 eager top-level imports, including GitHubToolset, so bare package import still loads owlbear.tools.github_api and pulls the retry path in early.
- Verified src/owlbear/memory/knowledge/__init__.py already uses the exact cached importlib.import_module plus globals()[name] module-level __getattr__ pattern this task should follow.
- Verified tests/test_tools_init_reexports.py is the compatibility contract for the 10 public exports, and tests/test_knowledge_exports.py is the in-repo subprocess pattern for import-side-effect assertions.
- Single-domain check passes: this task is a tools package-root runtime change only. Documentation is already split into #882, and optional dir() parity is already split into #883.
- Layering check passes: the change stays inside tools/ and depends only on stdlib importlib plus existing tool submodules; it does not introduce a new upward import.

### Failure Mode Map

| CODEPATH | FAILURE MODE | EXCEPTION | HANDLED? | USER IMPACT |
|----------|--------------|-----------|----------|-------------|
| owlbear.tools.__getattr__(name) | Unsupported export requested | AttributeError | Yes - should mirror normal missing-module-attribute behavior | Invalid attribute access fails fast without widening the API |
| owlbear.tools.__getattr__(name) | Lazy target import regresses in a submodule | Underlying import exception from target module | No custom handling required | The first access to that export fails, but bare package import remains clean |

### Changes Made

- Rewrote #879 from one bundled AC sentence into 9 discrete GREEN-phase acceptance criteria.
- Added depends_on #878 so the RED test task is enforced by the board, not just described in prose.
- Approved #879 to todo for implementation after architecture review.

### Dependencies

- Added/Removed/Verified: added dependency on #878; verified #882 remains the docs-only follow-up; verified #883 keeps optional __dir__ parity out of this task; verified parent #859 keeps this lazy-export cleanup separate from the earlier core/tools root-cause inversion work.

[[2026-03-21]] Sat 04:01

## Builder Notes

- Files changed: src/owlbear/tools/__init__.py, tests/test_tools_init_reexports.py
- Tests: 28 passed (26 TestFromAC + 2 TestBuilderDiscovered), coverage 100% on tools/__init__.py
- Lint: ruff clean
- Evidence: 1 TestFromAC test was RED (bare import side-effect), all 26 now GREEN; 2 builder-discovered tests cover unsupported-name AttributeError and cache hit paths
- Fixes applied: Replaced 9 eager top-level imports with _LAZY_IMPORTS map + __getattr__ + globals() cache, following src/owlbear/memory/knowledge/__init__.py pattern exactly

[[2026-03-21]] Sat 04:26

## Review Evidence

Reviewer pipeline executed.

[[2026-03-21]] Sat 04:27

### Detailed Evidence

### Test Results

Scoped pytest run on tests/test_tools_init_reexports.py passed all tests: 28 passed, 0 failed, with 2 optional dependency warnings.

### Lint Results

Repository-wide lint currently reports baseline debt outside this task scope. Task-scoped lint for src/owlbear/tools/__init__.py and tests/test_tools_init_reexports.py passed with no findings.

### Coverage

Coverage run reports src/owlbear/tools/__init__.py at 100 percent (13 statements, 0 missed).

### Pass 1 CRITICAL

#### Security Review

No hardcoded secrets, injection vectors, traversal paths, insecure deserialization, eval/exec, or dependency-manifest changes were introduced by this task. Unknown attribute requests are constrained by whitelist map lookup and rejected with AttributeError in src/owlbear/tools/__init__.py:41-48.

#### Test Integrity

Comparison source: git show a06e6f3 on tests/test_tools_init_reexports.py.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_ToolsReExports::test_import_ask_user_toolset | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_file_toolset | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_git_local_toolset | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_github_toolset | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_kanban_toolset | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_terminal_toolset | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_hooked_toolset | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_mcp_server_registry | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_find_toolset | No change | PRESERVED |
| TestFromAC_ToolsReExports::test_import_unwrap | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_ask_user_toolset_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_file_toolset_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_git_local_toolset_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_github_toolset_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_kanban_toolset_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_terminal_toolset_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_hooked_toolset_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_mcp_server_registry_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_find_toolset_identity | No change | PRESERVED |
| TestFromAC_ToolsReExportIdentity::test_unwrap_identity | No change | PRESERVED |
| TestFromAC_ToolsAllTuple::test_all_is_defined | No change | PRESERVED |
| TestFromAC_ToolsAllTuple::test_all_is_sequence | No change | PRESERVED |
| TestFromAC_ToolsAllTuple::test_all_contains_all_expected_names | No change | PRESERVED |
| TestFromAC_ToolsAllTuple::test_all_has_no_unexpected_names | No change | PRESERVED |
| TestFromAC_NoCircularImport::test_import_owlbear_tools_exposes_all_symbols | No change | PRESERVED |
| TestFromAC_ToolsImportSideEffect::test_bare_import_does_not_load_github_api_or_retry | No change | PRESERVED |

Builder additions are limited to pytest import plus TestBuilderDiscovered class. No TestFromAC assertions were weakened or removed.

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Identity checks and exact set checks are strict; importability checks are lighter but redundant with identity coverage. |
| Negative and error paths | STRONG | Unknown-name AttributeError and subprocess side-effect regression are both covered. |
| Mutation reasoning | STRONG | Reintroducing eager imports, breaking lazy map, or removing cache would fail existing tests. |
| Test independence | STRONG | No shared mutable fixture coupling; subprocess test isolates import state. |
| Descriptive names | STRONG | Method names clearly encode scenario and expectation. |

#### Data Safety

No persistence writes, transaction boundaries, unbounded input processing, or LLM-output ingestion are part of this change. Module global caching at src/owlbear/tools/__init__.py:45 is deterministic memoization for export resolution.

### Pass 2 INFORMATIONAL

Task files are lint-clean; repo-wide lint baseline remains noisy outside this scope.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Runtime export change is constrained to tools package root and no submodule edits | Builder commit changed src/owlbear/tools/__init__.py plus test file only, no tools submodule source edits | test_bare_import_does_not_load_github_api_or_retry | PASS |
| Exact ten-name public surface is preserved | src/owlbear/tools/__init__.py:11-22 defines ten names in __all__ | test_all_contains_all_expected_names, test_all_has_no_unexpected_names | PASS |
| Eager imports replaced by lazy map plus module __getattr__ in existing repo style | src/owlbear/tools/__init__.py:26-48 now implements _LAZY_IMPORTS and __getattr__; mirrors src/owlbear/memory/knowledge/__init__.py pattern | test_import_owlbear_tools_exposes_all_symbols, test_bare_import_does_not_load_github_api_or_retry | PASS |
| Supported names lazily import relative submodule, return attr, and cache in globals | src/owlbear/tools/__init__.py:43-46 uses importlib.import_module, getattr, globals cache | test_cached_lookup_returns_same_object and identity tests | PASS |
| Unsupported names raise AttributeError | src/owlbear/tools/__init__.py:47-48 | test_getattr_unsupported_name_raises_attribute_error | PASS |
| Bare import leaves github_api and core.retry absent from sys.modules until access | subprocess assertions in tests/test_tools_init_reexports.py:215-219 | test_bare_import_does_not_load_github_api_or_retry | PASS |
| GitHubToolset import and identity compatibility coverage pass without weakening | tests/test_tools_init_reexports.py:29-32 and 86-90 pass; TestFromAC diff shows preserved assertions | test_import_github_toolset, test_github_toolset_identity | PASS |
| No __dir__, no lazy loader helper dependency, no new runtime dependency | src/owlbear/tools/__init__.py contains no __dir__ and only stdlib importlib; commit scope shows no dependency file changes | code inspection plus commit scope check | PASS |
| Green verification target passes | Scoped pytest target completed with 28 passing tests | full target suite execution | PASS |

### Verdict

PASS with confidence .95

[[2026-03-21]] Sat 04:52

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | No behavior/API/convention change; public surface identical (same 10 names); no tools package entry in instructions |
| 2 | Docstrings complete | Yes | Pass | src/owlbear/tools/__init__.py has module docstring explaining lazy imports; __getattr__ is a dunder with no docstring per precedent in knowledge/__init__.py |
| 3 | docs/sources/overview.md | Yes | Updated | Added missing lazy-loader project docs row under new ## owlbear.tools Lazy-Export GREEN Implementation (Task #879) section |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/tools-root-lazy-exports-implementation.md exists and is linked from task body Research section |
| 6 | No impact default | N/A | N/A | Items 2, 3, 5 applied |

### Files Updated

- docs/sources/overview.md (added lazy-loader attribution row for #879)

### Scratch Files Cleaned

- None (no docs/scratch/879-* files existed)

[[2026-03-21]] Sat 05:23

## Commits

| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| a06e6f3 | feat | src/owlbear/tools/__init__.py, tests/test_tools_init_reexports.py | #879 |
| 02f8bca | docs | docs/sources/overview.md | #879 |
