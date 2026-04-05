# Remove Unused Re-exports from `core/__init__.py`

> **Owning task:** #812 — Remove unused re-exports from core **init**.py
> **Date:** 2026-03-15  **Status:** Complete

## 1. Context and Question

`owlbear.core.__init__.py` re-exports 15 symbols (OwlBearAgent, OwlBearDeps, OwlBearError,
9 Hook data classes, AgentRole, RolePolicy) and declares `__all__` with all 15. Task #812
asks: should we remove them? Two prior research docs for parent task #549 reached
**opposite conclusions** — this doc breaks the tie with fresh empirical evidence.

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| `init-reexports.md` (2026-03-07) | Local: `docs/research/init-reexports.md` | 1.0 | .85 confidence: DO NOT add re-exports, remove existing ones |
| `init-re-exports.md` (2026-03-15) | Local: `docs/research/init-re-exports.md` | 1.0 | .90 confidence: ADD re-exports to 7 more packages |
| Google Python Style Guide §2.2 | <https://google.github.io/styleguide/pyguide.html#22-imports> | .85 | Favors `from x.y import z` over package-level re-exports |
| PEP 8 — Public/Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | .80 | `__all__` defines public API; unmentioned = implementation detail |

## 3. Analysis

### 3.1 Empirical consumer count (verified 2026-03-15)

| Import style | Production (`src/`) | Tests (`tests/`) | Total |
|--------------|---------------------|-------------------|-------|
| Deep path (`from owlbear.core.agent import ...`) | **64** | 100+ | 164+ |
| Short path (`from owlbear.core import ...`) | **0** | 3 (all in `TestFromAC_CoreReExport`) | 3 |

The 3 test consumers exist solely to verify the re-export works — circular reasoning.
Zero functional code depends on short-path imports.

### 3.2 Resolving the conflicting research

| Factor | `init-reexports.md` (remove) | `init-re-exports.md` (add) |
|--------|------------------------------|----------------------------|
| Checked consumer usage? | Yes — found 0/66 | **No** — assumed demand |
| Library vs app analysis? | Yes — OwlBear is an app | No — cited library patterns |
| KISS/YAGNI assessment? | Strongly favors removal | Dismissed as "audit identified problem" |
| Cited Google Style Guide? | No | No |
| Internal prior-art examination? | Showed 0 adoption | Showed pattern exists, not adoption |

The first doc's recommendation is evidence-based; the second assumed demand existed
without verifying. The architect review on #813 independently reached the same conclusion.

### 3.3 Complication: `TestFromAC_CoreReExport` tests

Task #539 AC7 requires `OwlBearError` importable from `owlbear.core`. Three tests
enforce this. Removal would break them. Options:

| Option | Impact | Recommendation |
|--------|--------|----------------|
| Delete the 3 tests | Clean removal, -9 LOC | **.85** — tests verify a feature we're removing |
| Keep only `OwlBearError` re-export | Partial cleanup, -12 of 15 symbols | .60 — inconsistent half-measure |

### 3.4 Trade-off summary

| Criterion | Remove (.90) | Keep (.15) |
|-----------|-------------|------------|
| KISS | Removes 35 LOC of dead imports | Maintains unused indirection |
| YAGNI | Zero demand after 10+ days | No future plan requires it |
| DRY | Eliminates dual import paths | Two paths for every symbol |
| Maintenance | No `__init__.py` update on refactor | Must sync on every change |
| Risk | Must update 3 tests | None |

## 4. Recommendation (.90 confidence)

**Remove all re-exports and `__all__` from `core/__init__.py`.** Keep only the docstring
and `from __future__ import annotations`.

- Delete the `TestFromAC_CoreReExport` test class (tests verify the removed feature).
- This also unblocks #813 (which should be **closed as won't-do** — the architect already
  blocked it for the same evidence).

Risk: If OwlBear ever exposes a public API, re-exports are trivially re-added.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Implement core __init__.py re-export removal" --priority nice-to-have --status ideation --tags "refactor,scope:core" --description "Remove all re-exports and __all__ from src/owlbear/core/__init__.py. Keep docstring + from __future__ import annotations. Delete TestFromAC_CoreReExport class from tests/test_exception_hierarchy.py (3 tests). Verify 0 import breakage in src/ and tests/. See docs/research/core-init-reexport-removal.md."
```

```
kanban\kanban-md.exe create "Close #813 as won't-do per re-export research" --priority nice-to-have --status ideation --tags "audit,scope:core" --description "Task #813 (add re-exports to 5 packages) is blocked by architect and contradicted by empirical evidence (0/64 consumers use short-path imports). Mark #813 as archived/won't-do. Update #549 description to reflect the resolved decision. See docs/research/core-init-reexport-removal.md §3.2."
```
