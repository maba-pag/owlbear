# Architect — Critic Debate Log

## Round 1

### Draft Position Summary

- P1: Import `atomic_write` directly from `owlbear_kanban.storage_io` (allowed by boundary test, function is domain-free).
- P2: Create-on-first-write in API — GET returns empty when file absent, PUT creates on first save, no seeding.
- P3: New `routes/ideas.py` with own APIRouter and `/api/ideas` prefix, no KanbanEngine dependency.
- P4: Frontend placement follows #1638's page convention; component is self-contained with local state only.
- Overall: well-scoped, no new packages, no boundary violations. Confidence 0.85.

### Critic Challenges

**Critical — P3 router prefix convention mismatch.** The draft said the ideas router should own a prefix like `/api/ideas`. But existing cockpit routers are bare `APIRouter()` instances with the `/api` prefix applied at mount time in `main.py` (`app.include_router(router, prefix="/api")`). Mixing conventions is inconsistent.

**Verdict: Accepted.** The draft was sloppy on this. The ideas router must follow the existing pattern: bare `APIRouter()`, prefix applied in `main.py`. Routes inside the module use paths like `/ideas` (relative to the `/api` prefix).

**Critical — P2/P3 workspace root ambiguity.** The backend only knows `kanban_dir` (default: `cwd / ".owlbear" / "kanban"`). There is no "workspace root" abstraction. The draft said the ideas route derives the file path from "the same workspace root" — but that root doesn't exist as a backend concept. When `KANBAN_DIR` is overridden, the ideas file location becomes ambiguous.

**Verdict: Accepted with mitigation.** Valid gap. The fix: add a `get_ideas_path` dependency in `deps.py` that derives `Path(engine.kanban_dir).parent / "ideas.md"`. This uses the existing DI seam (engine → kanban_dir → parent) without introducing a new abstraction. The ideas route depends on this `Path`, not on `KanbanEngine` directly. If `KANBAN_DIR` is overridden to `/foo/bar/kanban`, ideas.md lands at `/foo/bar/ideas.md` — which is the correct relative position.

**Moderate — `atomic_write` not in `__init__.__all__`.** The function is not part of `owlbear_kanban`'s public export surface. The boundary test permits the cross-package import, but reaching into a low-level write primitive is a different kind of coupling than importing models/errors.

**Verdict: Defended.** The cockpit already imports from `owlbear_kanban.decisions` (line 16 of `routes/decisions.py`), which is also not in `__init__.__all__`. The precedent exists. `storage_io` is a single pure-IO function with no domain coupling — less risky than importing `decisions` which has kanban-domain semantics. The boundary test enforces the contract; the `__init__` exports are a convenience layer, not a security boundary.

**Moderate — P4 understates frontend coupling.** Shell.tsx has hardcoded nav and a single route. The ideas tab isn't "one component + one route entry" — it collides with hardcoded nav and active-state assumptions.

**Verdict: Acknowledged as #1638 scope.** The context.md explicitly states the ideas tab depends on #1638 completing first. The hardcoded nav and route structure are #1638's deliverables to fix. The architect's role is to specify what the ideas feature needs from #1638 (route config entry, nav-rail wiring), not to solve #1638's problems. The draft should be clearer about this dependency boundary.

**Moderate — Multi-tab concurrency.** The cockpit already supports concurrent browser clients via SSE. Two tabs editing ideas → last-write-wins with no detection. The draft dismissed OCC without defending why ideas can opt out.

**Verdict: Accepted with defense.** Fair observation. Two tabs → last-write-wins IS the behavior. Defense: ideas is a single text blob with no structured fields to conflict. There's no meaningful merge strategy for freeform markdown. OCC would mean adding mtime tracking, 409 responses, and retry UI — complexity that solves a problem that barely exists (editing the same scratchpad in two tabs simultaneously). Explicitly document last-write-wins as the v1 behavior. If friction emerges, mtime-based OCC is a clean v2 addition.

**Blind spot — CockpitProvider eager state.** Board polling and DR scanning run on all routes via the shell-level CockpitProvider. The ideas page doesn't need this data but pays the cost.

**Verdict: Acknowledged as #1638 scope.** Route-level lazy loading and conditional polling are #1638 responsibilities (the tab system decides when to mount providers). The ideas page is self-contained — it doesn't consume CockpitProvider state, so the wasted work is a performance concern for #1638, not a structural concern for ideas.

### Outcome

Two critical challenges accepted with concrete fixes (router convention, workspace root). One moderate challenge defended (atomic_write precedent). Two moderate challenges acknowledged as #1638 scope. One moderate challenge accepted with explicit defense (multi-tab last-write-wins).

Position refined. Confidence adjusted to 0.82.
