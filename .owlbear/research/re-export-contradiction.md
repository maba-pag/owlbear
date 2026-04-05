# Re-export Contradiction Resolution

> **Owning task:** #813 — Add re-exports to auth, planning, projects, providers, safety `__init__.py`
> **Date:** 2026-03-15  **Status:** Complete

## 1. Context and Question

The architect BLOCKED #813 because two research docs for parent #549 reached opposite
conclusions. This doc synthesizes all evidence and resolves the contradiction.

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| init-reexports.md (2026-03-07) | Local: `docs/research/init-reexports.md` | 1.0 — first research, .85 conf: DO NOT add |
| init-re-exports.md (2026-03-15) | Local: `docs/research/init-re-exports.md` | 1.0 — second research, .90 conf: ADD |
| core-init-reexport-removal.md | Local: `docs/research/core-init-reexport-removal.md` | 1.0 — third research, .90 conf: REMOVE existing |
| Google Python Style Guide §2.2 | <https://google.github.io/styleguide/pyguide.html#22-imports> | .85 — favors `from x.y import z` |
| PEP 8 Public/Internal Interfaces | <https://peps.python.org/pep-0008/#public-and-internal-interfaces> | .80 — `__all__` for public API |
| PydanticAI `__init__.py` | <https://github.com/pydantic/pydantic-ai> | .85 — library with re-exports |

## 3. Analysis

### 3.1 Empirical evidence (independently verified 2026-03-15)

| Import style | Matches in `src/` | Matches in `src/bearclaw/` |
|--------------|-------------------|---------------------------|
| `from owlbear.core import X` | **0** | **0** |
| `from owlbear.{auth..safety} import X` | **0** | **0** |
| `from owlbear.{pkg}.{mod} import X` (deep) | **21** | **5** |

Three independent counts (this doc + two prior) all confirm: **0 consumers use re-exports.**

### 3.2 Root cause of contradiction

| Factor | init-reexports.md (remove) | init-re-exports.md (add) |
|--------|----------------------------|--------------------------|
| Checked actual import usage? | **Yes** — grep, 0/66 | **No** — assumed demand |
| Library vs app distinction? | **Yes** — OwlBear is internal | **No** — cited library patterns |
| KISS/YAGNI analysis? | **Yes** — cost > benefit | **Dismissed** |
| Cited INT-10 audit finding? | Referenced | Used as justification to add |

The second doc assumed INT-10's "no API surface" was a deficiency requiring re-exports.
It didn't verify whether any consumer actually wants shorter import paths. The first and
third docs checked and found zero demand.

### 3.3 Decision matrix

| Criterion | Add re-exports (.15) | Keep deep imports (.90) | Remove existing (.85) |
|-----------|---------------------|------------------------|----------------------|
| KISS | +50 LOC in 5 `__init__.py` | No change | -35 LOC in core |
| YAGNI | Zero consumers exist | Matches 100% of usage | Cleans dead code |
| DRY | Creates 22 dual import paths | Single source of truth | Reduces dual paths |
| Maintenance | Must sync `__init__.py` on every rename | Zero ongoing cost | One-time cleanup |
| IDE discoverability | Marginal gain | Deep paths resolve fine | Unchanged |
| Board consistency | Contradicts #812 | Neutral | Supports #812 |

## 4. Recommendation (.90 confidence)

**Do NOT add re-exports (#813 = won't-do). Proceed with removal (#812/#822).**

All three empirical checks confirm zero demand. OwlBear is an application with no
external consumers. The second research doc's recommendation was based on an assumption
that consumer demand exists — it doesn't. KISS, YAGNI, and DRY all favor deep imports.

A decision request is created because the architect explicitly requested user confirmation
to resolve the contradictory research documents.

## 5. Follow-up Tasks

Decision request: `docs/decisions/pending/813-re-export-feature-gate.md`

No new kanban tasks — #822 and #823 already exist with correct AC.
