# Package-Root Lazy Export Pattern for OwlBear Public APIs

> **Owning task:** #882 - Document package-root lazy export pattern for OwlBear public APIs
> **Date:** 2026-03-21  **Status:** Complete

## 1. Context and Question

`src/owlbear/tools/__init__.py` now exposes 10 public symbols through a cached
module-level `__getattr__` map, and `src/owlbear/memory/knowledge/__init__.py`
already does the same for 14 symbols. The question is not whether Python allows
this pattern; it does. The question is when OwlBear should use it, why `__all__`
must stay explicit, and whether a helper such as `lazy-loader` is justified for
such small package-root surfaces.

## 2. Sources Studied

| Source | Kind | Relevance | What it established |
|--------|------|-----------|---------------------|
| `src/owlbear/tools/__init__.py`, `docs/research/tools-root-lazy-exports-implementation.md` | Local | 1.0 | Live 10-name package-root example and the implementation constraints adopted in #879 |
| `src/owlbear/memory/knowledge/__init__.py`, `docs/research/tools-init-side-effects.md` | Local | .98 | Existing cached `__getattr__` precedent and the risk of using lazy exports to mask a deeper layering issue |
| `docs/architecture.md` | Local | .94 | Canonical long-lived architecture document; the note belongs here rather than in another standalone doc |
| Python data model docs | External | .97 | Module-level `__getattr__` and `__dir__` are the supported hooks for dynamic package-root attributes |
| PEP 562 | External | .97 | Lazy module attributes via `__getattr__` are standard, `from pkg import Name` remains compatible, and repeated lookups can fall back to normal attribute access once cached |
| PEP 8 - Public and Internal Interfaces | External | .96 | `__all__` should explicitly declare a module's public API surface |
| Scientific Python SPEC 1 | External | .90 | Lazy loading is valid but not recommended for every project; small or cheap package roots should avoid unnecessary machinery |
| `lazy-loader` project docs | External | .83 | Helper-based lazy loading is viable, but it adds a runtime dependency and optional type-stub packaging work |

## 3. Runtime Policy Comparison

| Option | Pros | Cons | Assessment |
|--------|------|------|------------|
| A. Inline cached `__getattr__` plus explicit `__all__` for small curated package roots with measured side effects | Small diff, no new dependency, matches two live OwlBear precedents | Dynamic attribute access delays some import failures until first use | Best fit (.93) |
| B. Eager re-exports everywhere | Simplest runtime model, no dynamic lookup machinery | Reintroduces measured package-root side effects for `owlbear.tools`; keeps optional-dependency cost coupled to package import | Acceptable only for cheap roots with no measured import pressure (.63) |
| C. `lazy-loader` helper for small fixed surfaces | Standard helper, built-in `__dir__` and stub workflow | New dependency, extra packaging work, and overkill for 10- and 14-name surfaces | Reject (.27) |

## 4. Documentation Placement Comparison

| Destination | Pros | Cons | Assessment |
|-------------|------|------|------------|
| `docs/architecture.md` | Canonical architecture source of truth, already describes package structure and toolset assembly, visible to humans and agents | Slightly expands a long document | Best fit (.95) |
| New standalone architecture note file | Isolated note with narrow scope | Duplicates architecture guidance and creates another document to maintain | Reject (.33) |
| Instructions only | Helps agents immediately | Not the canonical human-facing architecture doc and mixes design rationale with execution rules | Reject (.31) |

## 5. Recommendation (.92 confidence)

Add a short subsection to `docs/architecture.md` and document this policy:

1. Default to direct imports or eager re-exports for ordinary package roots.
   Opt into cached module-level `__getattr__` only when the package root is a
   deliberate public API and eager imports cause measured side effects,
   optional-dependency pressure, or import-cycle pressure.
2. Keep `__all__` explicit and small. It is the supported API contract; the
   lazy import map is private machinery.
3. Prefer the inline `importlib.import_module` map already used in
   `owlbear.tools` and `owlbear.memory.knowledge` for small fixed surfaces.
   Do not add `lazy-loader` unless OwlBear accumulates enough repeated lazy
   export boilerplate that the dependency and stub-management cost become worth
   paying.
4. Treat `__dir__` as optional ergonomics, not default policy. Task #883 already
   isolates that choice as a separate follow-up.
5. Do not use lazy exports to hide illegal dependency edges. Fix the layering
   problem first, then apply lazy exports only if the package root still has
   measurable import pressure.

Why this is the right rule:

- PEP 562 and the Python data model make module-level `__getattr__` the
  supported mechanism for lazy package-root attributes.
- PEP 8 says `__all__` should define the public API, which matches OwlBear's
  current `tools` and `memory.knowledge` implementations.
- SPEC 1 explicitly warns against applying lazy loading indiscriminately, and
  OwlBear's 10- and 14-name surfaces are small enough that a helper dependency
  is harder to justify than an inline map.
- The repo already has the architecture note home: `docs/architecture.md`.

## 6. Follow-up Tasks

1. **#887 - Add package-root lazy-export policy note to docs/architecture.md**
   Priority rationale: `nice-to-have` because the runtime pattern is already
   live in two package roots, but the rule is not yet captured in the canonical
   architecture doc.
   Dependencies: none.
   One-line AC: add a short `docs/architecture.md` policy note that says when
   OwlBear may use cached module-level `__getattr__` maps, why `__all__` stays
   explicit, why `lazy-loader` is out of scope for small fixed surfaces, and
   names `src/owlbear/tools/__init__.py` plus
   `src/owlbear/memory/knowledge/__init__.py` as the current examples.

```powershell
kanban\kanban-md.exe create "Add package-root lazy-export policy note to docs/architecture.md" --priority nice-to-have --status ideation --tags docs,architecture,scope:tools,type:docs --parent 882 --body "Add a short subsection to docs/architecture.md under the architecture design-rules area describing OwlBear's package-root lazy-export policy. Capture when cached module-level __getattr__ import maps are allowed (only for deliberate public package roots with measured eager-import side effects or optional-dependency pressure), why __all__ stays explicit and limited to the supported surface, why lazy-loader stays out of scope for small fixed surfaces like owlbear.tools and owlbear.memory.knowledge, and that __dir__ is optional rather than default. State explicitly that lazy exports are not a substitute for fixing illegal dependency edges. Cite src/owlbear/tools/__init__.py and src/owlbear/memory/knowledge/__init__.py as the current repo examples. See docs/research/package-root-lazy-export-pattern.md. AC: (1) docs/architecture.md gains a short policy note with those rules, (2) the note names both current repo examples, (3) the note states that __all__ is the public contract and __getattr__ is an implementation detail, (4) no new standalone architecture note file is created." --dir kanban
```

No additional runtime follow-ups are needed here: #879 already shipped the
package-root behavior, and #883 already isolates the optional `__dir__`
ergonomics question.
