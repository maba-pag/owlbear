# Preserve `dir()` Parity for `owlbear.tools` Lazy Exports

> **Owning task:** #883 — Preserve dir() parity for `owlbear.tools` lazy exports
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

Task #879 already moved `src/owlbear/tools/__init__.py` to cached module-level
lazy exports. A clean runtime probe now shows the heavy paths stay out of
`sys.modules`, but `dir(owlbear.tools)` no longer lists any of the 10 supported
short-path names from `__all__`.

The question for #883 is whether OwlBear should restore that interactive
discovery surface, and if so what `__dir__` shape fits the repo without
reintroducing eager imports or widening the public API.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `src/owlbear/tools/__init__.py`, clean runtime probe, `tests/test_tools_lazy_exports.py` | Local | 1.0 | Current module has cached `__getattr__`, keeps heavy imports unloaded, and exposes none of the 10 public names through `dir()`; the scoped tests still forbid `__dir__` |
| `docs/research/tools-root-lazy-exports-implementation.md`, `docs/research/package-root-lazy-export-pattern.md` | Local | .98 | Prior research intentionally kept `__dir__` out of #879 and positioned it as optional ergonomics rather than default policy |
| `src/owlbear/memory/knowledge/__init__.py` | Local | .92 | OwlBear already has another lazy package root without `__dir__`, so any tools change should stay tools-specific rather than become a repo-wide rule |
| Python data model — customizing module attribute access | External | .97 | Module-level `__dir__` is the supported hook for controlling `dir(module)` and should return names accessible on the module |
| PEP 562 | External | .97 | Lazy module attributes plus a custom `__dir__` are the standard language-supported pattern; the PEP example returns a curated export list |
| Scientific Python SPEC 1 | External | .90 | Lazy loading is specifically valuable when a package wants cheap imports and interactive exploration together |
| `lazy-loader` implementation/docs | External | .89 | Established prior art uses `__dir__` alongside `__getattr__`, and its helper returns the curated `__all__` surface for `dir()` rather than merging default module globals |

## 3. Live Findings

| Probe | Result | Meaning |
|------|--------|---------|
| Clean subprocess `import owlbear.tools` then compare the 10 supported names against `dir()` | `dir_present=[]`, `dir_count=0`, `github_api=False`, `core_retry=False` | #879 fixed eager imports but removed interactive discovery of the supported public names |
| `src/owlbear/tools/__init__.py` | Explicit `__all__`, `_LAZY_IMPORTS`, cached `__getattr__`, no `__dir__` | The smallest implementation seam is adding a module-level `__dir__` |
| `tests/test_tools_lazy_exports.py` | AC 8 currently asserts `__dir__` absent and `lazy_loader` absent | #883 should replace only the `__dir__` prohibition, not reopen the no-new-dependency rule |
| `src/owlbear/memory/knowledge/__init__.py` | Same lazy-export pattern, no `__dir__` | Repo precedent remains "no `__dir__` by default"; `tools` can be a targeted exception because this task is explicitly about the public short-path tool API |

## 4. Option Comparison

| Option | Pros | Cons | Assessment |
|--------|------|------|------------|
| A. Keep status quo and leave `__dir__` absent | Zero code/test churn; consistent with `memory.knowledge` | `dir(owlbear.tools)` exposes none of the 10 supported names; fails the stated interactive-parity goal | Reject (.31) |
| B. Add minimal `__dir__` that returns `list(__all__)` | Smallest diff; matches PEP 562 and `lazy-loader` prior art; restores curated discovery; keeps heavy imports absent; no dependency; no public API widening beyond `__all__` | `dir()` becomes a curated public-API view rather than the module's default dictionary listing | Best fit (.93) |
| C. Merge `__all__` into the default module dir listing | Preserves dunders and metadata while adding public names | Re-exposes internal globals such as `importlib` and `_LAZY_IMPORTS`; more surface churn for little user value | Acceptable (.54) |
| D. Use `lazy_loader.attach` | Standard helper already solves `__dir__` | Adds a dependency; unnecessary helper and stub complexity for a fixed 10-name surface; contradicts #879 and #882 policy | Reject (.14) |

## 5. Recommendation (.92 confidence)

Adopt Option B and implement a module-level `__dir__` in
`src/owlbear/tools/__init__.py` that returns the curated `__all__` surface.

Implementation guidance:

1. Keep `__all__` as the single source of truth for the supported 10-name API.
2. Add `def __dir__() -> list[str]: return list(__all__)` (or an equivalent
   copy) next to `__getattr__`.
3. Do not import submodules inside `__dir__`; it should be pure metadata.
4. Update `tests/test_tools_lazy_exports.py` to replace the current "no custom
   `__dir__`" assertion with positive parity checks.
5. Keep the existing no-new-dependency rule; `lazy_loader` remains out of
   scope.

Why this is the right bar:

- The Python data model docs and PEP 562 define module `__dir__` as the
  canonical way to control `dir(module)` for dynamic attributes.
- PEP 562's own example and `lazy-loader` prior art both use a curated export
  list rather than merging arbitrary module globals.
- SPEC 1 explicitly frames lazy loading as a way to keep imports cheap while
  preserving interactive exploration, which is exactly this task's goal.
- Returning `__all__` keeps the public surface constrained to the contract
  OwlBear already tests.

## 6. Verification Shape

| Check | Why it matters |
|------|----------------|
| `dir(owlbear.tools)` contains the 10 names in `__all__` after bare import | Proves interactive discovery parity is restored |
| `owlbear.tools.github_api` and `owlbear.core.retry` stay absent from `sys.modules` after calling `dir()` | Proves `__dir__` did not reintroduce eager imports |
| `tests/test_tools_lazy_exports.py` still asserts `lazy_loader` stays absent | Keeps the no-dependency constraint from #879 |
| No repo-wide `__dir__` rollout is introduced | Keeps #883 as a targeted ergonomics exception for `owlbear.tools` only |

## 7. Follow-up Tasks

1. **Existing task #883 — implement minimal `__dir__` parity at the tools
   package root**
   Priority rationale: `nice-to-have` because this is an ergonomics follow-up,
   not a regression blocker.
   Dependencies: after #879, which is already complete.
   One-line AC: bare `dir(owlbear.tools)` lists the 10 supported names while
   `owlbear.tools.github_api` and `owlbear.core.retry` stay out of
   `sys.modules`.

No new follow-up tasks were created. #883 already isolates the only recommended
action from this research, and splitting it further would duplicate the board
without introducing a second architecture decision.
