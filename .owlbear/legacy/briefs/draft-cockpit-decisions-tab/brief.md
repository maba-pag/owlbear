# Brief — Cockpit Decisions Tab

## Purpose

Establish multi-tab navigation infrastructure for the OwlBear Cockpit, using a decisions tab as the pathfinder. The tab system is the primary deliverable — it enables planned Memory and Ideas Notebook tabs to implement in parallel. The decisions tab provides a dedicated full-width workspace for pending DR resolution, replacing the current 360px sidecar slot.

## Value Proposition

- **Primary:** The cockpit becomes a multi-surface dashboard. Future tabs (Memory, Ideas Notebook) add a route + nav item — no further infrastructure work.
- **Secondary:** Decision requests get a dedicated workspace with full-page width instead of being wedged into the sidecar. The interaction model (list → modal) stays familiar.

## Deliverables

### P1 — Tab Shell

Purely additive. No regressions to existing workflows.

1. **Route config array** — declarative route entries (path, label, icon, component). Adding a tab = adding an entry.
2. **Nav-rail wiring** — buttons with `useNavigate()` handlers, `aria-current="page"` on active route. `role="navigation"` semantics. Current kanban button wired identically.
3. **React Router routes** — `<Routes>` in Shell renders the active tab component. Kanban moved into tab slot (same component, routed at `/`).
4. **Skeleton decisions page** — placeholder at `/decisions`. Validates that tab infrastructure works end-to-end.
5. **Route-conditional sidecar** — suppress sidecar DOM on non-kanban routes. Handles existing desktop breakpoint (sidecar is kanban-specific, not global).
6. **Lazy loading** — tab components loaded via `React.lazy()` with suspense boundary.

**Validation gate:** A third tab module can be added by creating a component and adding one route config entry.

### P2 — Decisions Content

Fills in the decisions tab and removes the now-redundant sidecar DR list.

1. **Pending DR list** — full-page single-column list showing all pending DRs. Each item: agent, request type, relative age, task ID, body preview (200 chars). Generous spacing (not dense rows).
2. **Click → ResolveModal** — clicking a list item opens the existing ResolveModal overlay. Modal receives a snapshot of the DR data on open (not a live reference).
3. **Modal snapshot on open** — DR data is copied into modal-local state when opened. SSE-triggered refetches do not affect the open modal. Prevents involuntary data loss.
4. **Pending count badge** — nav-rail decisions button shows pending DR count. Visible only when count > 0.
5. **Remove DecisionViewport from sidecar** — the sidecar DR list is removed. DRStatusIndicator in the status bar remains as the secondary entry path (works from any route, opens the same Shell-level ResolveModal).
6. **Pydantic response model** — typed response model on `GET /api/decisions/pending` endpoint. Coerces `task_id` (int), `created` (date string), validates shape. Catches malformed DR files at the API boundary.
7. **Notes length cap** — `max_length=10_000` on `ResolveRequest.notes` field.
8. **Empty state** — when no DRs are pending, the decisions tab shows a clear "nothing to decide" state. Tab always visible in nav-rail regardless of count.

## Entry Paths

- **Primary:** Nav-rail decisions button → decisions tab → list → click DR → ResolveModal
- **Secondary:** Status-bar DRStatusIndicator → popover → click DR → ResolveModal (works from any route, overlay appears over current view)

Both paths use the same Shell-level ResolveModal instance via the existing `selectedDRId` in CockpitProvider.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tab switching | React Router (URL = source of truth) | BrowserRouter already wraps app; URL persistence for free |
| Nav-rail semantics | `role="navigation"` with custom buttons | Route-level views, not tab panels; PDS has no nav component |
| Layout pattern | Full-page list + modal overlay | 1–5 DRs don't justify master-detail; ResolveModal reusable as-is |
| CockpitProvider | Unchanged — no new state fields | `selectedDRId` already exists; future tabs bring local hooks |
| Modal ownership | Single instance at Shell level | Shared between status-bar and decisions tab entry paths |
| Sidecar | Route-conditional (kanban-only) | Decisions tab doesn't need a sidecar; clean separation |
| Mobile | Desktop-only design; existing breakpoints handled without regression | Laptop-resident tool; no new mobile UX investment |
| Resolved DRs | Deferred (fast-follow) | Core pain is pending visibility; resolved browsing unvalidated |
| Draft persistence | Snapshot on open (SSE guard only) | Deliberate close is conscious action; localStorage adds complexity |

## Scope Boundaries

**In:**

- Tab system infrastructure (routes, nav-rail, lazy loading, sidecar conditioning)
- Decisions list + detail modal
- Pending-only filtering
- Resolution flow (existing ResolveModal)
- Pending count badge (nav-rail)
- Modal snapshot (SSE guard)
- Pydantic response model + notes cap
- Empty state design

**Out:**

- Resolved DR browsing (fast-follow after V1)
- Task context panel alongside DR
- Kanban-side cross-nav sender (deep-link from task card to DR)
- Deep-link receiver (no sender = dead code)
- DR creation from cockpit
- Quick response templates
- Threaded DR history
- Mobile-specific design work
- Host header validation (accepted risk)
- localStorage draft persistence

## Technical Context

### Existing infrastructure (no changes needed)

- `BrowserRouter` wrapping the app
- `EventSourceProvider` + SSE `decisions-changed` events
- `usePendingDRs` hook + `GET /api/decisions/pending` endpoint
- `POST /api/decisions/{id}/resolve` endpoint
- `ResolveModal` component (self-contained, reusable)
- `DRStatusIndicator` component (status bar)
- `CockpitProvider` with `useDRState()` including `selectedDRId`

### Components to adapt

- `DecisionViewport` → adapt for tab-level list (selection highlighting, generous layout)
- `Shell.tsx` → route config, nav-rail wiring, route-conditional sidecar
- `Shell.css` → sidecar suppression on non-kanban routes

### Components to create

- Route config array (or inline, architect's choice during implementation)
- Decisions page component (list + empty state)
- Nav-rail badge sub-component

## Dependencies

- P2 depends on P1 (tab system must exist before content fills it)
- No backend dependencies for P1
- P2 backend work (Pydantic model, notes cap) is independent of frontend P2 work

## Risks

| Risk | Mitigation |
|------|-----------|
| Route-conditional sidecar is highest-complexity P1 work | Architect review confirmed approach; existing responsive patterns provide the suppression mechanism |
| Removing sidecar DRs reduces discovery | DRStatusIndicator in status bar provides global awareness; badge on nav-rail reinforces |
| P1 ships a skeleton page | Acceptable for a dev tool — developer knows it's intentional; P2 follows immediately |
| SSE refetch during modal use | Modal snapshot on open (requirement, not optional) |
