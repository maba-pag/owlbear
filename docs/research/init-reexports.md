# Re-exports in Empty `__init__.py` Files

> **Owning task:** #549 — Add re-exports to empty `__init__.py` files
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

INT-10 flagged 7 packages with empty `__init__.py`: auth, planning, projects, providers,
safety, tools, tools/browser. Should we add re-exports (`from .module import Foo`) with
`__all__` to make the public API discoverable via `from owlbear.auth import ...`?

## 2. Sources Studied

| Source | URL | Relevance | What |
|--------|-----|-----------|------|
| Python import system docs | <https://docs.python.org/3/reference/import.html#regular-packages> | .70 | `__init__.py` purpose; submodule binding semantics |
| PydanticAI `__init__.py` | <https://github.com/pydantic/pydantic-ai> (main) | .85 | 100+ re-exports for library consumers |
| httpx `__init__.py` | <https://github.com/encode/httpx> (master) | .80 | Heavy re-exports + `__all__` for library consumers |
| OwlBear codebase (internal) | `src/owlbear/core/__init__.py`, `src/owlbear/memory/knowledge/__init__.py` | .95 | Existing re-exports with zero adoption |

## 3. Analysis

### 3.1 Current state of the 7 packages

| Package | Modules | Key public types | Current `__init__` |
|---------|---------|------------------|--------------------|
| auth | 1 | `load_token`, `load_or_refresh_token`, `derive_base_url` | Docstring only |
| planning | 3 | `ProjectDefinition`, `Requirement`, `ProjectDefinitionExtractor` | Empty |
| projects | 4 | `Project`, `ProjectStore`, `ProjectToolset`, `ProjectWorkspace` | Docstring only |
| providers | 2 | `create_copilot_model` | Docstring only |
| safety | 2 | `ApprovalPolicy`, `ApprovalSession`, `ApprovalGateToolset` | Docstring only |
| tools | 16 | 15+ toolset classes, `ScreenshotService`, `MCPServerRegistry` | Docstring only |
| tools/browser | 11 | `BrowserToolset`, `BrowserManager`, `WebCrawler`, `URLSafetyGuard` | Docstring only |

### 3.2 Evidence: existing re-exports are not used

| Package with re-exports | Symbols in `__all__` | Short-path imports | Deep-path imports |
|--------------------------|---------------------|--------------------|-------------------|
| `owlbear.core` | 6 | **0** | 58 |
| `owlbear.memory.knowledge` | 35 | **0** | 8 |

100% of consumers use deep import paths (`from owlbear.core.agent import OwlBearAgent`).
Zero consumers use re-exports (`from owlbear.core import OwlBearAgent`).

### 3.3 Library vs application context

| Criterion | Library (PydanticAI, httpx) | Application (OwlBear) |
|-----------|----------------------------|-----------------------|
| External consumers | Yes — PyPI users | No — internal only |
| API stability contract | Semver, public surface | No external contract |
| Import convenience | Critical for UX | Irrelevant — devs know the codebase |
| Two-path problem | Accepted trade-off | Pure downside |
| `__all__` maintenance | Worth the cost | Cost without benefit |

### 3.4 Trade-off matrix: add re-exports vs document as intentional

| Criterion | Add re-exports (.25) | Document as intentional (.85) |
|-----------|----------------------|-------------------------------|
| KISS | Adds ~50 symbols across 7 `__init__.py` files | Zero code change |
| YAGNI | No external consumers exist or are planned | Correct scope |
| DRY | Creates second import path for every symbol | Single source of truth |
| Maintenance | Every new class requires `__init__.py` update | No ongoing cost |
| Consistency | Existing re-exports already unused (0/66) | Aligns with actual usage |
| Discoverability | Marginally better for IDE autocomplete | Deep paths already resolve |
| Refactoring | Harder — must update `__init__.py` on rename | Tools handle module-level renames |

## 4. Recommendation (.85 confidence)

**Do NOT add re-exports. Document as intentional. Remove existing unused re-exports.**

Rationale:

- OwlBear is an application, not a library — no external consumers need short import paths.
- 100% of 66+ existing imports use deep paths. Zero use existing re-exports.
- Adding re-exports violates KISS (more code), YAGNI (no demand), and DRY (two import paths).
- INT-11 already flags `knowledge` as *over-exporting* — adding more contradicts that finding.

Risk: If OwlBear ever becomes a library, re-exports would be needed. Mitigation: cross that
bridge when we get there — adding re-exports to a stable API is trivial.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Remove unused re-exports from core and knowledge __init__.py" --priority nice-to-have --tags "audit,architecture,scope:core" --description "owlbear.core exports 6 symbols, owlbear.memory.knowledge exports 35 symbols, but 0/66 consumers use them. Remove re-exports, keep docstrings. See docs/research/init-reexports.md §3.2."
```

```
kanban\kanban-md.exe edit 549 --description "RESOLVED: Do not add re-exports. See docs/research/init-reexports.md. Existing re-exports (core, knowledge) have 0 consumers across 66+ imports — 100% use deep paths. OwlBear is an application, not a library. KISS/YAGNI/DRY all favor deep imports. Follow-up: #TBD to remove unused core/knowledge re-exports."
```
