# Reduce `owlbear.tools` `__init__` Eager Import Side Effects

> **Owning task:** #857 — Reduce owlbear.tools `__init__` eager import side effects
> **Date:** 2026-03-19  **Status:** Complete

## 1. Context and Question

Task #857 asks how to stop `import owlbear.config` from eagerly loading
`owlbear.tools.github_api` and `owlbear.core.retry` while keeping the
`owlbear.tools` public API added by #814.

Current behavior is subtle because Python executes a parent package's
`__init__.py` before loading a submodule. Importing
`owlbear.tools.browser.config` from `src/owlbear/config.py` therefore preloads
`src/owlbear/tools/__init__.py`, which currently imports all 10 re-exported
symbols eagerly.

The question is: what is the smallest architecture-safe change that preserves
the #814 API, removes the measured side effects, and does not turn lazy imports
into another way to hide the unresolved `core -> tools` edge tracked by #850?

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `src/owlbear/tools/__init__.py`, `src/owlbear/config.py`, `src/owlbear/tools/browser/config.py` | Local | 1.0 | `import owlbear.config` necessarily touches the parent `owlbear.tools` package, which eagerly imports `github_api.py` today |
| `tests/test_tools_init_reexports.py` and archived task #814 notes | Local | 1.0 | The 10-symbol `owlbear.tools` surface is intentional and already under direct test; narrowing it is a product decision, not a refactor |
| `src/owlbear/memory/knowledge/__init__.py` | Local | .95 | OwlBear already uses cached module-level `__getattr__` lazy exports to break an import cycle |
| Python import system docs | External | .95 | Importing a submodule executes the parent package `__init__.py`, and imported submodules bind into the parent namespace |
| PEP 562 | External | .90 | Module `__getattr__` and `__dir__` are the standard lazy-export mechanism for package namespaces |
| Scientific Python SPEC 1 | External | .85 | Lazy exports are a valid pattern, but they delay some import failures and are not the default answer for every project |

## 3. Analysis

### 3.1 Current behavior

| Probe | Result | Meaning |
|------|--------|---------|
| `uv run python -c "import owlbear.config"` | `owlbear.tools.github_api` = loaded, `owlbear.core.retry` = loaded | `config.py` currently triggers the side effects named in the AC |
| `uv run python -c "import owlbear.tools"` | PASS, but loads `github_api.py` and `core.retry.py` immediately | The public surface works today because `tools/__init__.py` imports everything eagerly |
| `uv run python -c "import owlbear.daemon"` | FAIL | The direct `core.errors -> tools.browser.safety -> tools.__init__ -> github_api -> core.retry` cycle still exists before #850 |
| `uv run python -c "import owlbear.config; import owlbear.daemon"` | PASS | The config import preloads `owlbear.tools` first and masks the direct daemon failure |

### 3.2 Option comparison

| Option | Change | Pros | Cons | Assessment |
|--------|--------|------|------|------------|
| A. Lazy-map all 10 supported `owlbear.tools` exports with cached `__getattr__`, `__dir__`, and `__all__` | Preserve full API, remove eager submodule loading | Keeps the #814 surface, removes the measured config side effects, matches existing OwlBear precedent in `memory/knowledge/__init__.py` | Import errors move from package import time to first attribute access; dynamic exports are slightly less explicit | Best fit (.90) |
| B. Lazy-load only `GitHubToolset` and `github_api.py` | Smallest diff that satisfies current AC | Removes the specific `core.retry` side effect with less code than a full map | Leaves most of `owlbear.tools` eager, creates an inconsistent package policy, and future re-exports can repeat the problem | Acceptable fallback (.72) |
| C. Move `BrowserConfig` out of `owlbear.tools.browser` | Avoid touching `owlbear.tools` during `import owlbear.config` | Removes the masking preload path entirely | Broader rename with higher churn; does not improve `import owlbear.tools` side effects; over-scoped for this task | Over-scoped (.45) |
| D. Remove `GitHubToolset` from the `owlbear.tools` public API | No lazy-import machinery | Simplifies import behavior | Breaks the #814 contract and current tests; requires a decision request per task AC | Reject (.20) |

### 3.3 Architecture fit

- Option A works only as a follow-up to task #850, not as a substitute for it.
- If #857 lands before #850, the lazy package would stop the crash path while
  leaving the forbidden `core.errors -> tools.browser.safety` dependency
  intact, which recreates the same masking problem in a quieter form.
- The implementation task should therefore depend on #850 and keep a
  clean-process `import owlbear.daemon` smoke test alongside the new
  `import owlbear.config` side-effect assertions.
- The existing re-export tests already cover the supported surface. The new
  tests only need clean-subprocess `sys.modules` assertions and one explicit
  `from owlbear.tools import GitHubToolset` smoke path.

## 4. Recommendation (.90 confidence)

After #850 is complete, convert `src/owlbear/tools/__init__.py` from eager
imports to an explicit lazy export map for the 10 names established in #814.

Implementation shape:

1. Keep the same `__all__` names.
2. Replace eager top-level imports with a cached module-level `__getattr__` map.
3. Add `__dir__` so the public surface remains discoverable.
4. Keep `import owlbear.daemon` coverage from #850 so lazy exports never become
   the mechanism that "fixes" the architectural cycle.
5. Add clean-process assertions that `import owlbear.config` does not load
   `owlbear.tools.github_api` or `owlbear.core.retry`.

This is the smallest change that preserves the supported public API and removes
the measured side effects without converting #857 into a stealth replacement for
task #850.

## 5. Follow-up Tasks

1. **Lazy-load `owlbear.tools` exports to remove config import side effects**
   Priority rationale: `important` because the side effect is measurable today,
   but it should land after #850 removes the underlying `core -> tools`
   violation.
   Dependencies: #850.
   One-line AC: after #850, clean subprocess `import owlbear.config` does not
   load `owlbear.tools.github_api` or `owlbear.core.retry`, while the 10-symbol
   `owlbear.tools` API from #814 still works.
   Created: #859

  ```powershell
  kanban\kanban-md.exe create "Lazy-load owlbear.tools exports to remove config import side effects" --priority important --status ideation --tags architecture,bug,scope:tools --parent 857 --depends-on 850 --body "See docs/research/tools-init-side-effects.md §4. AC: after #850, clean subprocess import owlbear.config does not load owlbear.tools.github_api or owlbear.core.retry; import owlbear.tools and from owlbear.tools import GitHubToolset preserve the 10-symbol public surface from #814; targeted import smoke and re-export tests pass."
  ```
