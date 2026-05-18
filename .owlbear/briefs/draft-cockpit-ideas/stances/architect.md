# Architectural Stance — Cockpit Ideas Notebook

## Architectural Stance

The Ideas Notebook is a structurally clean addition to the cockpit. It requires no new packages, no new dependencies, and no domain boundary changes. The four open architecture questions all have clear answers grounded in existing patterns.

## Structural Reasoning

### Q1 — `atomic_write` sourcing: Direct cross-package import

**Import `atomic_write` from `owlbear_kanban.storage_io`.**

- The boundary test already declares `owlbear_cockpit → owlbear_kanban` as permitted.
- The cockpit already imports from non-`__all__` kanban submodules (`owlbear_kanban.decisions` in `routes/decisions.py`). `storage_io` follows the same pattern with lower coupling risk — it's a pure I/O primitive with zero domain semantics.
- Copy (option b) violates DRY: two identical crash-safe write functions to maintain.
- Extract to shared utility (option c) is YAGNI: two consumers don't justify a new package. The third consumer is the extraction signal.

### Q2 — File creation: Create-on-first-write in the API

**GET returns empty content when file absent. PUT creates file + parents on first save. No seeding via `setup/init.py`.**

- The ideas file is optional and cockpit-specific. Seeding it adds noise to every new project initialization.
- The absence of the file is a valid state (user hasn't written ideas yet), not an error. GET should return `{"content": ""}`, not 404.
- PUT calls `target.parent.mkdir(parents=True, exist_ok=True)` before `atomic_write`.

**Path derivation**: Add a `get_ideas_path` dependency in `deps.py` that returns `Path(engine.kanban_dir).parent / "ideas.md"`. This uses the existing DI seam — the kanban engine already resolves the `.owlbear/kanban/` directory, and ideas.md sits one level up at `.owlbear/ideas.md`. When `KANBAN_DIR` is overridden, the ideas file stays in the correct relative position. No new environment variable needed.

### Q3 — Route module: `routes/ideas.py`

**New route module at `serve/cockpit/src/owlbear_cockpit/routes/ideas.py`.**

- Bare `APIRouter()` — the `/api` prefix is applied at mount time in `main.py` via `app.include_router(ideas_router, prefix="/api")`, matching the existing convention used by all four current routers.
- Route paths: `GET /ideas` and `PUT /ideas` (relative to the `/api` prefix).
- The route depends on `get_ideas_path` (a `Path` dependency), not on `KanbanEngine` directly. The engine is only used transitively to derive the path in the DI chain.
- Response model: Pydantic `BaseModel` with `content: str` field, `ConfigDict(extra="forbid")`, matching the existing response model pattern.
- Request model: Pydantic `BaseModel` with `content: str` field for the PUT body.

### Q4 — Frontend component: Defer specifics to #1638

**The ideas page is a self-contained component with page-local state. Exact placement depends on #1638's conventions.**

- The current Shell.tsx has hardcoded nav and a single route — this structure will be replaced by #1638's declarative route config and nav-rail wiring.
- The ideas page needs: one route config entry (path + lazy-loaded component), one nav-rail icon reference. These are #1638 deliverables.
- The component holds all state locally (`useState` for content, dirty flag, save status). No `CockpitProvider` extension needed — the page doesn't consume board, task, or DR data.
- If #1638 introduces a `pages/` directory: `pages/IdeasPage.tsx`. If pages stay flat at `src/`: `src/IdeasPage.tsx`. Follow the convention #1638 establishes.

## Key Trade-offs

| Decision | Trade-off | Why acceptable |
|----------|-----------|----------------|
| Cross-package `atomic_write` import | Deepens `cockpit → kanban` coupling surface | The boundary already exists; the function is domain-free; alternatives (copy/extract) are worse |
| Create-on-first-write | No file until user saves for the first time | Clean empty-state semantics; avoids init noise |
| No OCC (last-write-wins) | Two cockpit tabs editing ideas simultaneously → silent overwrite | Freeform text has no merge strategy; OCC adds complexity for a near-zero-probability scenario |
| Defer frontend placement to #1638 | Cannot specify exact file path now | The tab system is the infrastructure dependency; specifying placement before it lands creates coupling to unknowns |

## Warnings

1. **#1638 is the critical dependency.** The ideas tab cannot ship until the route config (#1639) and nav-rail wiring (#1642) are complete. Plan accordingly.
2. **CockpitProvider eager state.** Board polling and DR scanning run on all routes via the shell-level provider. The ideas page doesn't consume this data but pays the cost. This is a #1638 concern (route-level lazy loading / conditional polling), not ideas-specific — but worth flagging so #1638 addresses it.
3. **`atomic_write` docstring drift.** The function's docstring says "for kanban task files" but it's now used for non-kanban files. Update the docstring when the ideas feature ships to reflect its general-purpose nature.

## Confidence

0.82 — Position is structurally sound after Critic refinement. Remaining uncertainty is in #1638's output conventions affecting frontend placement.
