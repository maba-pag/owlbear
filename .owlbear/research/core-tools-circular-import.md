# Fix Circular Import Between `core.errors` and `tools.__init__`

> **Owning task:** #849 — Fix circular import: `core/errors.py` -> `tools/__init__.py` -> `core/retry.py`
> **Date:** 2026-03-18  **Status:** Complete

## 1. Context and Question

Task #849 reports this import chain:

`daemon.py -> core/errors.py -> tools/browser/safety.py -> tools/__init__.py -> github_api.py -> core/retry.py -> core/errors.py`

Workspace reproduction confirms the report:

- `.venv\Scripts\python.exe -c "import owlbear.tools"` succeeds
- `.venv\Scripts\python.exe -c "import owlbear.daemon"` fails with `ImportError: cannot import name 'ErrorCategory' from partially initialized module 'owlbear.core.errors'`

Two codebase details matter:

- `core/errors.py` imports `BlockedURLError` from `tools/browser/safety.py`
- `tests/test_daemon_journal_async.py` pre-imports `owlbear.tools` specifically to mask this cycle before importing `owlbear.daemon`

Question: which fix should the architect scope?

## 2. Sources Studied

| Source | URL | Relevance | What we used |
|--------|-----|-----------|--------------|
| `src/owlbear/core/errors.py` | Local | 1.0 | Confirms the `core -> tools` import edge |
| `src/owlbear/tools/__init__.py` | Local | 1.0 | Confirms #814 added eager re-exports, including `GitHubToolset` |
| `src/owlbear/tools/browser/safety.py` | Local | 1.0 | Shows `BlockedURLError` is defined in a tool module but only raised there |
| `tests/test_daemon_journal_async.py` + `tests/test_imports.py` | Local | .95 | Shows the current workaround and the missing smoke coverage |
| Architecture Standards | Local: `.github/skills/architecture-standards/SKILL.md` | 1.0 | States `core/` never imports from `tools/` |
| Task #502 | Local: `kanban/tasks/502-break-memory-to-tools-upward-dependency.md` | .95 | Prior OwlBear precedent: break upward deps by inversion, not by import tricks |
| PEP 562 | <https://peps.python.org/pep-0562/> | .85 | Validates module `__getattr__` as the standard lazy-export mechanism |
| Scientific Python SPEC 1 | <https://scientific-python.org/specs/spec-0001/> | .80 | Shows lazy loading is useful but not recommended as a default for every project |
| Google Python Style Guide §2.2 | <https://google.github.io/styleguide/pyguide.html#22-imports> | .80 | Favors explicit module imports over broad package indirection |
| PEP 8 Public/Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | .75 | Clarifies that package `__init__` exports are a deliberate public-API choice, not a free import shortcut |

## 3. Analysis

### 3.1 Root cause

The root cause is the layer violation, not the mere existence of `tools/__init__.py`.

- `core/errors.py` currently imports from a higher layer (`tools/browser/safety.py`), which the architecture rules explicitly forbid.
- #814 only made the violation visible by turning `owlbear.tools` into an eager importer of `github_api.py`, which pulls `core.retry`.
- The repo already fixed a similar upward dependency in #502 by moving integration to a lower layer/bootstrap boundary instead of hiding it behind lazy imports.

### 3.2 Fix options

| Option | Fixes root cause? | Keeps current import API? | Complexity | Assessment |
|--------|-------------------|---------------------------|------------|------------|
| Move `BlockedURLError` into `core.exceptions.py` (or another lower-layer exception module) and re-export it from `tools/browser/safety.py` | Yes | Yes | Low-Medium | **Recommended (.90)** — removes the forbidden `core -> tools` edge while keeping `from owlbear.tools.browser.safety import BlockedURLError` working |
| Convert `tools/__init__.py` to lazy exports via module `__getattr__` | No, symptom fix only | Yes | Medium | Acceptable fallback (.70) — PEP 562 + SPEC 1 validate the technique, but it adds import magic to preserve a bug-triggering edge |
| Import `BlockedURLError` locally inside `classify_error()` | No | Yes | Low | Temporary patch (.55) — likely breaks the immediate cycle but leaves the architectural violation in place |
| Revert #814 re-exports from `tools/__init__.py` | No | No | Low | Avoid (.40) — removes the trigger by deleting the API instead of repairing the bad dependency edge |

### 3.3 Why lazy `tools.__init__` is second choice

Lazy re-exports are technically sound here:

- PEP 562 explicitly supports module-level `__getattr__` for lazy submodule imports
- OwlBear already uses the same pattern in `memory/knowledge/__init__.py`

But they are still the wrong default for this task:

- SPEC 1 warns lazy loading is not recommended for every project
- Google's import guidance favors explicit module imports and minimizing package-level indirection
- the cycle would stay one eager import away from returning because the forbidden `core -> tools` edge remains

## 4. Recommendation (.90 confidence)

Scope the implementation around dependency inversion, not lazy import magic:

1. Move the `BlockedURLError` definition into `core.exceptions.py` or another lower-layer exception module.
2. In `tools/browser/safety.py`, import and re-export that class, then keep raising the same exception type from the guard.
3. Remove the `from owlbear.tools.browser.safety import BlockedURLError` import from `core/errors.py`.
4. Add regression coverage for clean-process imports of `owlbear.daemon` and `owlbear.config`.
5. Remove the `import owlbear.tools` pre-seeding workaround from `tests/test_daemon_journal_async.py`.

This fix:

- resolves the actual layer violation
- preserves the #814 short-path API
- matches existing OwlBear architecture precedent
- avoids introducing new dynamic-import behavior unless it is later justified separately

Keep lazy `tools/__init__` exports as a fallback only if the exception relocation proves unexpectedly broad during implementation.

## 5. Follow-up Tasks

1. **Invert `BlockedURLError` dependency to remove the core/tools cycle**
   Priority rationale: `needed` because #849 blocks #536, #541, and #841 and currently breaks `import owlbear.daemon`.
   Dependencies: none.
   One-line AC: clean-process imports of `owlbear.daemon` and `owlbear.config` succeed without pre-seeding `owlbear.tools`, while the browser safety import path stays compatible.
   Created: #850

   ```powershell
   kanban\kanban-md.exe create --title "Invert BlockedURLError dependency to remove core-tools circular import" --priority needed --status ideation --tags "bug,architecture,scope:core,scope:tools"
   ```
