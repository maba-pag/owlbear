# Research Notes — Cockpit Ideas Notebook

## Verified Findings

### Frontend Patterns

1. **Markdown edit/preview toggle** in TaskFieldsEditor uses `useState(false)` for edit mode, conditional render between `<PTextarea>` and `<ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>`. Dependencies: `react-markdown`, `remark-gfm`, `rehype-sanitize`.

2. **Dirty state tracking** uses simple field comparison: `isDirty = content !== original`. Unsaved changes indicator shown when dirty.

3. **Save confirmation** uses a 2-second auto-hide timer pattern (`setTimeout` + `setSaveConfirmed(false)`).

4. **Current routing** is a single `<Route path="/" element={<KanbanBoard />} />` in Shell.tsx. No route config array exists yet — that's task #1639's deliverable.

5. **State management** philosophy: CockpitProvider holds global data (board, tasks, DRs). UI state is component-local. The ideas page can be 100% page-local — no CockpitProvider extension needed.

6. **API client pattern**: `fetch()` + typed response parsing via helper functions. Error handling via `ApiError` class. Files in `serve/cockpit/web/src/api/`.

### Backend Patterns

7. **`atomic_write()`** in `serve/kanban/src/owlbear_kanban/storage_io.py` — mkstemp → write → fsync → os.replace. Non-negotiable for crash safety on any file write.

8. **Route registration**: `APIRouter()` in route module files under `serve/cockpit/src/owlbear_cockpit/routes/`, included via `app.include_router(router, prefix="/api")` in main.py.

9. **Request/response models**: Pydantic `BaseModel` with `ConfigDict(extra="forbid")`. Typed response models on route decorators.

10. **Error envelope**: centralized exception handlers in main.py auto-wrap domain errors into `{"code": ..., "message": ...}` JSON responses.

11. **File read**: plain `path.read_text(encoding="utf-8")` used throughout kanban module.

### Tab System Context

12. **Parent task #1638** establishes a declarative route config array. Task #1639 creates the array + `<Routes>` integration. Task #1642 wires nav-rail buttons from route config. Adding the ideas tab = one route config entry + one component, per AC on #1639: "adding a new entry (path + component) is sufficient to register a new routed tab without modifying Shell internals."

13. **Dependency**: The ideas tab depends on #1639 (route config) and #1642 (nav-rail wiring) completing first. These are in `research` status.

## Candidate Implications

- The actual implementation is very small: ~2 backend endpoints (GET/PUT for single file), ~1 page component (textarea + save button), ~1 API client module (2 functions), ~1 route config entry.
- The simplifier's Cut 2 (drop preview toggle) is worth evaluating — but the ReactMarkdown dependencies are already in the project, so the marginal cost of including preview is low. Phase 2 should decide.
- No OCC needed (single user, single file). No mtime in response (YAGNI per simplifier).
- No SSE integration needed — the file only changes when the user saves it from this very tab.
- `atomic_write` can be imported from `owlbear_kanban.storage_io` or the pattern can be replicated in the cockpit backend. Phase 2 should decide whether to import cross-package or copy the function.

## Open Research Questions

1. **Preview toggle or not?** Simplifier argues nobody previews scratch notes. Counter: the dependency stack is already present and the marginal code is ~10 lines. Phase 2 decision.
2. **File creation**: Should `.owlbear/ideas.md` be created by `setup/init.py` (seeded for new projects) or created-on-first-write by the API? Phase 2 decision.
3. **Cross-package import**: `atomic_write` lives in `owlbear_kanban.storage_io`. The cockpit backend currently doesn't import from the kanban package's internal modules. Options: (a) import it, (b) copy it, (c) extract to a shared utility. Phase 2 architecture decision.
4. **Nav-rail icon**: What icon for the Ideas tab? The route config expects an icon reference. Porsche Design System icon inventory needed.
