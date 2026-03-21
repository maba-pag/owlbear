# Validate RED Coverage for `owlbear.tools` Package-Root Lazy Exports

> **Owning task:** #878 - Add RED coverage for owlbear.tools package-root lazy exports
> **Date:** 2026-03-20 **Status:** Complete

## 1. Context and Question

Task #878 is the RED half of the `owlbear.tools` package-root lazy-export split created under #859. The live problem is no longer `import owlbear.config`; after #850 that path stays clean. The remaining regression is narrower: bare `import owlbear.tools` still eagerly loads `owlbear.tools.github_api` and `owlbear.core.retry` even though the supported public surface is only the 10 short-path exports from #814.

The question for this research pass is what test surface should go red before #879 changes `src/owlbear/tools/__init__.py`, without baking the implementation shape into the tests.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `src/owlbear/tools/__init__.py` plus clean subprocess probes | Local | 1.0 | The current package root eagerly imports all 10 public names; live probes showed `github_api=True`, `core_retry=True`, and `__all__` length 10 after bare `import owlbear.tools` |
| `tests/test_tools_init_reexports.py` | Local | 1.0 | The supported contract is already explicit: 10 imports, identity parity with canonical modules, exact `__all__`, and bare-import attribute access |
| `tests/test_knowledge_exports.py` and `tests/test_blocked_url_error_location.py` | Local | .98 | OwlBear already uses clean-subprocess `subprocess.run([sys.executable, "-c", ...])` tests for import side-effect verification |
| `docs/research/tools-root-lazy-exports.md` and task #859 | Local | .96 | Parent research already narrowed the implementation question and explicitly kept `__dir__` out of the main AC |
| Python import system docs | External | .95 | Importing a regular package executes the package `__init__.py`, so package-root side effects must be validated in a clean process |
| Python data model docs | External | .93 | Module `__getattr__` and `__dir__` are the supported hooks for dynamic package-root attributes |
| PEP 562 | External | .94 | `from pkg import Name` remains compatible with module-level `__getattr__`, so API-preservation tests can stay focused on behavior rather than import internals |
| Scientific Python SPEC 1 | External | .82 | Lazy exports are valid but should stay narrowly scoped and avoid over-specifying non-essential ergonomics in the first pass |

## 3. Analysis

### 3.1 What must fail today

| Behavior | Current evidence | Why #878 should cover it |
|----------|------------------|--------------------------|
| Bare `import owlbear.tools` loads `owlbear.tools.github_api` | Clean subprocess probe: `github_api=True` | This is the measurable package-root side effect #879 is meant to remove |
| Bare `import owlbear.tools` loads `owlbear.core.retry` | Clean subprocess probe: `core_retry=True` | This is the downstream import cost that makes the package root non-leaf today |
| `from owlbear.tools import GitHubToolset` resolves to the canonical symbol | Existing identity test and clean probe: `GitHubToolset.__module__ == "owlbear.tools.github_api"` | The public short-path contract must survive the lazy-export rewrite |
| The supported surface is exactly 10 names | Existing `__all__` and identity tests | RED should preserve the public API while exposing the eager-import bug |

### 3.2 Test-shape comparison

| Option | Pros | Cons | Assessment |
|--------|------|------|------------|
| A. Add one clean-subprocess `sys.modules` side-effect test and keep the existing re-export contract tests | Minimal diff, directly measures the bug, keeps API coverage where it already lives | Needs a fresh-interpreter helper in the tools test file | **Recommended (.95)** |
| B. Move all `owlbear.tools` tests into subprocess-based smoke tests | Matches the side-effect probe style everywhere | Over-scopes RED, weakens identity assertions, and duplicates existing coverage | .48 |
| C. Only add in-process `hasattr` or `import` tests | Smallest change | Cannot prove package-import side effects because `sys.modules` is already contaminated in the test process | .12 |

Recommended RED surface:

1. Extend `tests/test_tools_init_reexports.py` with a dedicated clean-process test class rather than creating a second contract file.
2. Use the `tests/test_knowledge_exports.py` and `tests/test_blocked_url_error_location.py` pattern: `subprocess.run([sys.executable, "-c", ...])` plus `sys.modules` assertions.
3. Preserve the existing 10-name re-export, identity, and `__all__` tests from #814 unchanged.
4. Add an explicit `from owlbear.tools import GitHubToolset` subprocess smoke assertion only if the existing in-process identity tests are not retained; otherwise they already cover the contract.

### 3.3 What not to encode in #878

- Do not assert `importlib.import_module`, `globals()` caching, or any specific `_LAZY_IMPORTS` map shape. Those are GREEN implementation choices for #879.
- Do not fold `__dir__` parity into the main RED task. Current `dir(owlbear.tools)` exposes all 10 names today (`dir_matches=10` in a clean probe), but parent research intentionally kept that ergonomics concern out of #859's core AC.
- Do not reopen the already-resolved `import owlbear.config` path. After #850, that path is clean; the live regression is only the package root itself.

## 4. Recommendation (.95 confidence)

Proceed with #878 as a narrow RED task and do not split it further.

The test plan should be:

1. Add a clean-subprocess assertion that bare `import owlbear.tools` leaves `owlbear.tools.github_api` and `owlbear.core.retry` absent from `sys.modules`.
2. Keep the current `tests/test_tools_init_reexports.py` identity and `__all__` checks as the compatibility contract for the 10 supported names.
3. Let #879 own the cached `__getattr__` design and any internal implementation details.

This is the smallest RED suite that fails against the current eager package root, proves the behavior #879 must change, and preserves the public API added by #814.

## 5. Follow-up Tasks

1. Existing task #878 - add the RED subprocess side-effect check plus preserve the #814 re-export contract.
2. Existing task #879 - implement cached lazy package-root exports after the RED coverage lands.
3. Created task #883 - optional `__dir__` parity follow-up so `dir(owlbear.tools)` continues to expose the 10 public names after lazy exports, without reintroducing eager imports.

```powershell
kanban\kanban-md.exe create "Preserve dir() parity for owlbear.tools lazy exports" --priority nice-to-have --status ideation --tags "architecture,scope:tools,type:build" --parent 859 --depends-on 879 --body "Optional follow-up after #879. When src/owlbear/tools/__init__.py switches to module-level lazy exports, keep interactive discovery parity by implementing __dir__ so dir(owlbear.tools) contains the same 10 supported names in __all__ without eagerly importing owlbear.tools.github_api or owlbear.core.retry. Source: docs/research/tools-root-lazy-exports-red-coverage.md. AC: (1) after bare import owlbear.tools, dir(owlbear.tools) includes AskUserToolset, FileToolset, GitLocalToolset, GitHubToolset, KanbanToolset, TerminalToolset, HookedToolset, MCPServerRegistry, find_toolset, and unwrap, (2) bare import still leaves owlbear.tools.github_api and owlbear.core.retry absent from sys.modules, (3) no public names beyond the existing __all__ contract are added, (4) scoped tests pass."
```
