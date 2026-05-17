# Research Notes — Cockpit Decisions Tab

## Verified Findings

### F1 — Router architecture

- `BrowserRouter` wraps the entire app in `App.tsx`
- Single `<Routes>` block in `Shell.tsx` with one route: `<Route path="/" element={<KanbanBoard />} />`
- No nested routing, no route config object, no lazy loading
- Provider stack: PDS → BrowserRouter → EventSourceProvider → CockpitProvider → ErrorBoundary → Shell → Routes

### F2 — Nav-rail is non-functional

- Static `<nav>` with one hardcoded `<button>` (kanban icon) in `Shell.tsx`
- The button has `aria-current="page"` but **no click handler** — purely visual
- Fixed 56px width on desktop, row layout on mobile
- No data-driven nav, no active-view state

### F3 — Shell grid layout

- CSS grid: `56px minmax(0, 1fr) 360px` (nav-rail | workspace | sidecar)
- Grid areas: status-bar (full-width header), nav-rail, workspace, sidecar
- Sidecar collapses to `0fr` via `[data-sidecar-collapsed]` attribute
- Workspace area is isolated — safe to swap content components
- Responsive: mobile (≤767px) stacked, tablet (768–1023px) collapsed nav/sidecar, desktop (≥1024px) full 3-column

### F4 — CockpitProvider is data-only

- Three domain hooks: `useBoardState()`, `useTaskSelection()`, `useDRState()`
- No global navigation/view state — no "active view" field
- Tab/view switching would require Shell-local state or route-based switching

### F5 — DecisionViewport is a list-only component

- Renders pending DR items as `<ul>` with agent, request type, age, task ID, preview
- Click handler: `onItemClick(id)` to select a DR (opens ResolveModal)
- Does NOT render full DR body or detail — just metadata
- Rendered twice in Shell: once in mobile sheet sidecar, once in desktop sidecar

### F6 — SSE infrastructure is ready

- `EventSourceProvider` subscribes to `decisions-changed` events
- `useSSEEvent('decisions-changed')` returns `{ mtime, status }`
- CockpitProvider effect: when `lastDecisionsMtime` changes, calls `refetchPendingDRs()`
- No additional SSE wiring needed for the decisions tab data flow

### F7 — PDS has no top-level nav component

- Only `p-tabs` / `p-tabs-item` available (content tabs, used in sidecar)
- No horizontal navigation bar, no sidebar nav component in PDS 4.1
- Nav-rail buttons would be custom HTML buttons with PDS exception attributes

### F8 — ResolveModal is self-contained

- Full modal with radio buttons (approved/rejected/needs-info), textarea for notes, submit
- Manages its own focus trap, escape handling, error state, retry logic
- Uses `resolveDR()` API call from `api/decisions.ts`
- Could be reused as-is within a decisions tab (it's a modal overlay, not layout-coupled)

### F9 — Existing backend endpoints

- `GET /api/decisions/pending` — returns `{ count, items }` with pending DRs only
- `POST /api/decisions/{id}/resolve` — resolves a DR with response + notes
- No `GET /api/decisions` (all) or `GET /api/decisions/resolved` endpoint
- Decisions files live in `.owlbear/kanban/decisions/pending/` and `resolved/` directories

### F10 — Sidecar duplicates content for mobile/desktop

- Shell.tsx renders the sidecar content block twice: once inside `<p-sheet>` for mobile, once in a `<div>` for desktop
- Both blocks contain identical DecisionViewport + p-tabs (Detail/Activity) structures
- This duplication pattern would need consideration when restructuring for tabs

## Candidate Implications

*These are hypotheses, not locked decisions.*

- **Route-based switching** is the natural approach given BrowserRouter already wraps the app. Adding `/decisions` route is trivial. State-based switching (activeView in Shell) is an alternative but doesn't give URL persistence.
- **Nav-rail wiring** requires only adding buttons with click handlers that navigate via `useNavigate()`. The current kanban button can be wired the same way for consistency.
- **DecisionViewport can be adapted** for the list panel but needs extension — it currently shows only metadata, not full DR bodies. The decisions tab list panel may want slightly different rendering (e.g., selected-item highlighting).
- **ResolveModal can be reused** without modification in the decisions tab context — it's an overlay modal, not layout-dependent.
- **Sidecar's role changes:** With a dedicated decisions tab, the DecisionViewport in the sidecar becomes redundant. It could be removed, kept as a quick-glance summary, or replaced with just the DRStatusIndicator popover.
- **P1 tab shell** could be as simple as: add a second `<Route>` to Shell's `<Routes>`, wire nav-rail buttons to `useNavigate()`, and render a placeholder component at `/decisions`.
- **With 1–5 DRs**, a permanent two-column split may be over-engineered. Consider: list view with click-to-navigate detail page, or list with inline-expandable detail.

## Open Research Questions

- **Q1:** How do PDS tabs (`p-tabs`) handle accessibility for a nav-rail pattern? Should the nav-rail use `role="tablist"` or `role="navigation"` given it switches route-level views, not tab panels?
- **Q2:** Should the sidecar persist across views (always visible) or be view-specific? If the decisions tab has its own detail panel, the sidecar's role is unclear on that view.
- **Q3:** What happens to the DRStatusIndicator in the status bar once a decisions tab exists? Does it stay as a global notification, or does it become redundant?
- **Q4:** The sidecar content is duplicated for mobile/desktop in Shell.tsx. A tab-system refactor should address this duplication — is extracting shared content into a dedicated component part of P1 scope?
- **Q5:** Should CockpitProvider grow a navigation state domain, or should view switching stay entirely in React Router (URL is the source of truth)?
