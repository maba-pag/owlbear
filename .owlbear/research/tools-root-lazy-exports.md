# Narrow `owlbear.tools` Lazy-Export Follow-up After #850

> **Owning task:** #859 — Lazy-load owlbear.tools exports to remove config import side effects
> **Date:** 2026-03-20  **Status:** Complete

## 1. Context and Question

Task #859 was created before #850 finished. The live question is no longer
whether `import owlbear.config` preloads `owlbear.tools.github_api`; that path
now stays clean. The remaining question is whether OwlBear should still lazy-load
the `owlbear.tools` package root so `import owlbear.tools` preserves the
10-symbol API from #814 without eagerly importing `github_api.py` and
`core.retry.py`.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `src/owlbear/tools/__init__.py`, `src/owlbear/config.py`, `src/owlbear/tools/browser/config.py` | Local | 1.0 | `config.py` no longer routes through `owlbear.tools`, but the package root still eagerly imports all 10 public names |
| `tests/test_tools_init_reexports.py`, `tests/test_knowledge_exports.py`, `src/owlbear/memory/knowledge/__init__.py` | Local | .98 | The 10-name public surface is already under direct test, and OwlBear already has a cached module `__getattr__` lazy-export precedent plus a subprocess import-side-effect test pattern |
| Python import system docs | External | .95 | Importing a regular package executes its `__init__.py`, so package-root re-exports always run before submodules are reached |
| Python data model docs | External | .94 | Module `__getattr__` and `__dir__` are the language-supported hooks for dynamic module attributes |
| PEP 562 | External | .94 | Lazy module attributes via module-level `__getattr__` are a standard pattern, and `from pkg import Name` works through the hook |
| Scientific Python SPEC 1 | External | .82 | Lazy exports are useful for package roots with non-trivial import cost, but they delay some import failures and should stay minimal |

## 3. Current State

| Probe | Result | Meaning |
|------|--------|---------|
| `kanban-md show 850` | `#850` is archived | The prerequisite task is complete |
| Clean subprocess `import owlbear.config` | `github_api=False`, `core_retry=False` | The config-path side-effect clause in #859 is stale after #850 |
| Clean subprocess `import owlbear.tools` | `github_api=True`, `core_retry=True`, `all_len=10` | The remaining issue is package-root eager imports, not config imports |
| Clean subprocess `from owlbear.tools import GitHubToolset` | `GitHubToolset.__module__ == 'owlbear.tools.github_api'` | The supported public contract still points at the canonical module |

## 4. Option Comparison

| Option | Pros | Cons | Assessment |
|--------|------|------|------------|
| A. Close #859 as obsolete because `import owlbear.config` is now clean | No more work | Ignores the still-eager `import owlbear.tools` path measured today | Reject (.24) |
| B. Rewrite #859 as one executable task focused on `import owlbear.tools` | Smallest board change | Blends RED and GREEN work into one task, which fights OwlBear's TDD defaults | Acceptable (.63) |
| C. Keep #859 as a backlog tracker and create RED + GREEN child tasks for package-root lazy exports | Matches repo TDD flow, keeps scope narrow, and uses existing repo precedents for both tests and implementation | One extra layer on the board | Best fit (.91) |

## 5. Recommended Implementation Shape

| Shape | Diff | Notes |
|------|------|-------|
| Cached `__getattr__` import map plus existing `__all__` | Small | Matches `src/owlbear/memory/knowledge/__init__.py`; enough for `hasattr()` and `from owlbear.tools import GitHubToolset` |
| Add `__dir__` immediately | Medium | Standards-complete, but OwlBear has no current `dir()` contract and no test demand for it |
| Add `lazy_loader` dependency | Large | Over-scoped for 10 names and violates KISS/YAGNI |

## 6. Recommendation (.89 confidence)

Treat #859 as a now-stale tracker and split execution into RED and GREEN child
tasks that target only the package root.

Implementation guidance for the GREEN task:

1. Keep the current 10-name `__all__` contract from #814.
2. Replace eager top-level imports in `src/owlbear/tools/__init__.py` with a
   cached `importlib.import_module` lookup map in module `__getattr__`.
3. Do not add a new dependency and do not move symbols out of the package root.
4. Keep `__dir__` out of scope unless the architect explicitly wants interactive
   discovery parity; it is supported by PEP 562, but not required by current AC.

This is the smallest change that preserves the public API, removes the remaining
measured eager imports, and stays aligned with the repository's existing lazy
export pattern.

## 7. Follow-up Tasks

1. **#878 — Add RED coverage for `owlbear.tools` package-root lazy exports**
   Priority rationale: `important` because the remaining issue is measurable
   today, but it is narrowly scoped to one package root.
   Dependencies: none.
   One-line AC: add focused subprocess and re-export tests that fail against the
   current eager `src/owlbear/tools/__init__.py` implementation.

2. **#879 — Implement cached lazy exports in `owlbear.tools` package root**
   Priority rationale: `important` because this is the minimal code change that
   removes the remaining eager import side effects without changing the public
   surface.
   Dependencies: should follow #878 during architect refinement.
   One-line AC: replace eager package-root re-exports with a cached
   `__getattr__` import map while preserving the 10-name API from #814.

```powershell
kanban\kanban-md.exe create "Add RED coverage for owlbear.tools package-root lazy exports" --priority important --status ideation --tags test,architecture,bug,scope:tools,type:test --parent 859 --body "AC: add focused subprocess and re-export tests for src/owlbear/tools/__init__.py that fail against the current eager implementation; bare import owlbear.tools asserts owlbear.tools.github_api and owlbear.core.retry stay absent from sys.modules; from owlbear.tools import GitHubToolset and the existing 10-symbol API checks from #814 remain covered; use tests/test_knowledge_exports.py as the subprocess pattern."
kanban\kanban-md.exe create "Implement cached lazy exports in owlbear.tools package root" --priority important --status ideation --tags architecture,bug,scope:tools,type:build --parent 859 --body "AC: replace eager top-level imports in src/owlbear/tools/__init__.py with a cached importlib-based __getattr__ map for the 10 names in __all__; bare import owlbear.tools no longer loads owlbear.tools.github_api or owlbear.core.retry; from owlbear.tools import GitHubToolset and the existing re-export identity tests pass; no new dependency is added."
```
