# Implement `owlbear.tools` Package-Root Lazy Exports

> **Owning task:** #879 — Implement cached lazy exports in `owlbear.tools` package root
> **Date:** 2026-03-20  **Status:** Complete

## 1. Context and Question

Task #859 already established that package-root lazy exports are the right class
of fix for the remaining `import owlbear.tools` side effect. Task #879 narrows
the question to implementation shape: what is the smallest runtime mechanism
that preserves the 10-name public API from #814, keeps bare
`import owlbear.tools` from importing `owlbear.tools.github_api` or
`owlbear.core.retry`, and avoids any new dependency?

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `src/owlbear/tools/__init__.py`, `tests/test_tools_init_reexports.py` | Local | 1.0 | The package root still eagerly imports all 10 public names, and the compatibility contract is already explicit |
| `src/owlbear/memory/knowledge/__init__.py`, `tests/test_knowledge_exports.py` | Local | .99 | OwlBear already accepts a cached `__getattr__` import map and a subprocess side-effect test pattern |
| `pyproject.toml` | Local | .94 | No helper dependency is currently declared, and #879 explicitly forbids adding one |
| Python data model — Customizing module attribute access | External | .96 | Module `__getattr__` is the canonical hook for missing module attributes; `__dir__` is optional |
| PEP 562 | External | .96 | Lazy module attributes via `importlib.import_module` are a standard pattern, and later binding turns repeated lookups into normal attribute access |
| Scientific Python SPEC 1 | External | .88 | Lazy loading can be implemented with module `__getattr__` or a helper package, but the mechanism should stay focused and is not needed for every package |
| `lazy-loader` project docs | External | .78 | Helper-based lazy loading is viable, but it introduces an extra runtime dependency and optional type-stub packaging concerns |

## 3. Live Constraints

| Probe | Result | Meaning |
|------|--------|---------|
| `src/owlbear/tools/__init__.py` | Eager top-level imports for all 10 public names | Bare `import owlbear.tools` still loads the heavy path today |
| `tests/test_tools_init_reexports.py` | Exact 10-name `__all__`, identity checks, package-root smoke test | Runtime API compatibility is already well specified |
| `tests/test_knowledge_exports.py` | Subprocess `sys.modules` assertions for eager-import absence | The repo already has the right verification pattern for import side effects |
| `src/owlbear/memory/knowledge/__init__.py` | Cached `globals()[name] = val` inside module `__getattr__` | There is already a local precedent for the implementation shape |
| `pyproject.toml` | No `lazy-loader` dependency | Adding a helper package would expand scope and violate the task AC |

## 4. Option Comparison

| Option | Pros | Cons | Assessment |
|--------|------|------|------------|
| A. Keep explicit `__all__`, add `_LAZY_IMPORTS` + cached `__getattr__` | Smallest diff, matches local precedent, no dependency, preserves `from owlbear.tools import GitHubToolset` | `dir(owlbear.tools)` stays default unless a future task adds `__dir__` | Best fit (.94) |
| B. Same as A plus `__dir__` | Full PEP 562 surface, nicer interactive discovery | No AC or current test demand; extra map maintenance | Acceptable (.61) |
| C. Use `lazy_loader.attach` or similar helper | Standardized helper, extra features for stubs | Adds a dependency banned by AC, adds packaging/type-stub complexity, over-scoped for 10 names | Reject (.18) |

## 5. Recommendation (.93 confidence)

Adopt Option A: inline a cached `importlib.import_module` map in
`src/owlbear/tools/__init__.py`, preserve the existing 10-name `__all__`, and
leave `__dir__` and helper libraries out of scope.

Implementation guidance:

1. Import `importlib` and define `_LAZY_IMPORTS: dict[str, tuple[str, str]]`
   for the 10 exported names.
2. In `__getattr__`, import the target submodule relative to `__name__`,
   retrieve the attribute, assign it into `globals()[name]`, and return it.
3. Raise the normal `AttributeError` for unknown names.
4. Keep `__all__` unchanged so existing import and identity tests remain the
   compatibility contract.
5. Do not touch submodules like `owlbear.tools.github_api`; the current task is
   only the package root.

Why this is the right bar:

- The Python data model and PEP 562 define module `__getattr__` as the
  supported runtime hook.
- PEP 562's discussion and OwlBear's `memory.knowledge` package both support
  caching the resolved object back into module globals.
- SPEC 1 says lazy loading can be done directly with module `__getattr__`, so a
  helper package is optional, not required.
- The current `pyproject.toml` and the task AC both point away from adding a
  dependency for a 10-name surface.

## 6. Verification Shape

| Check | Why it matters | Existing anchor |
|------|----------------|-----------------|
| Bare `import owlbear.tools` leaves `owlbear.tools.github_api` and `owlbear.core.retry` out of `sys.modules` | Proves the package root stopped eagerly importing the heavy path | Sibling RED task #878; subprocess pattern in `tests/test_knowledge_exports.py` |
| `from owlbear.tools import GitHubToolset` returns the canonical class | Preserves the public API promised in #814 | `tests/test_tools_init_reexports.py` identity checks |
| `import owlbear.tools` exposes all 10 names via `hasattr` / `__all__` | Ensures the package root is still ergonomic | `tests/test_tools_init_reexports.py` smoke and `__all__` assertions |
| No new dependency is added | Keeps scope aligned with AC and KISS | `pyproject.toml` |

## 7. Follow-up Tasks

1. **#878 — Add RED coverage for `owlbear.tools` package-root lazy exports**
   Priority rationale: `important` because this is the failing proof the builder
   task must satisfy.
   Dependencies: none.
   One-line AC: add subprocess and API-compatibility tests that fail against the
   current eager package root.

2. **#879 — Implement cached lazy exports in `owlbear.tools` package root**
   Priority rationale: `important` because it removes the remaining measured
   import side effect with the smallest runtime diff.
   Dependencies: follows #878 through the normal RED -> GREEN flow.
   One-line AC: replace eager root imports with a cached `__getattr__` map while
   preserving the 10-name API.

3. **#882 — Document package-root lazy export pattern for OwlBear public APIs**
   Priority rationale: `nice-to-have` because two package roots now use the same
   pattern, and capturing the rule can prevent future eager-import regressions.
   Dependencies: after #879 lands.
   One-line AC: add a short architecture note covering when OwlBear should use
   cached package-root lazy exports and why it avoids helper dependencies for
   small public surfaces.

No new code-splitting tasks are needed because #878 and #879 already form the
intended RED/GREEN execution pair.

```powershell
kanban\kanban-md.exe create "Document package-root lazy export pattern for OwlBear public APIs" --priority nice-to-have --status ideation --tags docs,architecture,scope:tools,type:docs --parent 879 --body "AC: add a short architecture note describing when package __init__.py may use cached module-level __getattr__ import maps; document why OwlBear keeps __all__ explicit and avoids adding lazy-loader for small public surfaces; cite src/owlbear/memory/knowledge/__init__.py and src/owlbear/tools/__init__.py as the current repo examples."
```
