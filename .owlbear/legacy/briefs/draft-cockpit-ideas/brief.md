# Brief — Cockpit Ideas Notebook

## Summary

Add an "Ideas" tab to the OwlBear Cockpit — a freeform markdown scratchpad backed by `.owlbear/ideas.md`. The tab provides capture and re-reading of pre-task ideas without leaving the dashboard. Value is cockpit co-location alongside VS Code, not editor superiority.

## Dependencies

- **#1638 (Tab System)** must land first: provides the route config array, nav-rail wiring, and page lifecycle that this feature plugs into.

## Backend

### Endpoints

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/api/ideas` | Returns `{"content": "..."}`. If `.owlbear/ideas.md` is absent, returns `{"content": ""}`. |
| PUT | `/api/ideas` | Accepts `{"content": "..."}`. Creates file on first write if absent. Uses `atomic_write` for crash safety. Returns `204 No Content`. |

### Implementation Details

- **Route module:** `serve/cockpit/src/owlbear_cockpit/routes/ideas.py` with bare `APIRouter()`. Prefix applied at mount in `main.py` per existing convention.
- **DI dependency:** `get_ideas_path` → `Path` resolving to `kanban_dir.parent / "ideas.md"`. The route depends on this, not on `KanbanEngine`.
- **Write primitive:** Import `atomic_write` from `owlbear_kanban.storage_io`. Update its docstring to remove kanban-specific framing (it's a generic crash-safe write utility).
- **Request/response models:** Pydantic `BaseModel` with `ConfigDict(extra="forbid")` per existing cockpit convention.
- **Error handling:** Standard error envelope via centralized exception handlers in `main.py`.

## Frontend

### Page Component

- **Name:** `IdeasPage` (exact placement follows #1638's page conventions)
- **Default mode:** Edit (textarea visible and focused on mount) — NOT preview mode
- **Textarea:** Full-page height, monospace font, standard `<PTextarea>` from PDS
- **Preview toggle:** Button switches between edit (textarea) and preview (rendered markdown via `ReactMarkdown` + `remark-gfm` + `rehype-sanitize`)
- **Save button:** Explicit save via PUT. Disabled while content is clean.
- **Dirty-state indicator:** Visual indicator when `content !== lastSavedContent`
- **State:** 100% page-local. No CockpitProvider extension.

### Unsaved-Changes Guard

Intercept all exit paths when dirty:
1. **Route navigation** — block via React Router's navigation blocking API (`useBlocker` or equivalent provided by #1638)
2. **Browser refresh / close** — `beforeunload` event listener
3. **Browser back/forward** — covered by route navigation blocking (SPA)

Show a confirmation dialog: "You have unsaved changes. Leave anyway?"

### External-Edit Awareness

Re-fetch content on two triggers:
1. **`visibilitychange`** — fires when alt-tabbing back to the browser
2. **Route activation** — fires when navigating back to the Ideas tab from another cockpit route

Behavior on re-fetch:
- **If clean (no local edits):** Silently update textarea with fetched content. Update `lastSavedContent` baseline.
- **If dirty (local edits exist):** Show a conflict notice with two action buttons:
  - **Overwrite** — keep local content, dismiss notice, re-enable Save (user's next Save will overwrite the external version)
  - **Discard & Reload** — drop local changes, adopt fetched content, reset dirty state

Regular Save is disabled while the conflict notice is showing — forces an explicit choice.

### Route Config Entry

One entry in the #1638 route config array:
- Path: `/ideas`
- Component: `IdeasPage` (lazy-loaded)
- Nav-rail icon: TBD from PDS icon inventory (e.g. `edit` or `document`)
- Label: "Ideas"

### API Client

- Module: `serve/cockpit/web/src/api/ideas.ts`
- Functions: `fetchIdeas(): Promise<{content: string}>` and `saveIdeas(content: string): Promise<void>`
- Uses existing `fetch()` + error handling pattern via `ApiError` class

## Storage

- **File:** `.owlbear/ideas.md` — single flat file, git-tracked, plain markdown
- **Creation:** Created on first PUT (not seeded by `setup/init.py`)
- **No OCC:** Last-write-wins is accepted. Single user, single file.
- **No SSE:** File only changes via cockpit save or external editor — no real-time push needed.

## Out of Scope

- Auto-save (D3: explicit save only)
- Multiple idea files / file picker
- Agent integration (D4: filesystem visibility is sufficient)
- CockpitProvider eager-polling fix (owned by #1638)
- Mobile / responsive design
- Search within ideas
- File-watcher / real-time sync (best-effort freshness via re-fetch triggers is the contract)

## Acceptance Criteria

1. GET `/api/ideas` returns file content or empty string when absent
2. PUT `/api/ideas` saves content atomically; creates file on first write
3. Ideas tab opens in edit mode with textarea focused
4. Save button is disabled when content matches last-saved state
5. Unsaved-changes guard fires on route navigation, refresh, and close
6. Preview toggle renders markdown with GFM support and sanitization
7. Re-fetch fires on `visibilitychange` and route activation
8. Clean re-fetch silently updates editor content
9. Dirty re-fetch shows conflict notice with Overwrite / Discard & Reload
10. Regular Save is disabled while conflict notice is showing
11. `atomic_write` docstring updated to generic framing
12. Ideas page does not depend on CockpitProvider state
