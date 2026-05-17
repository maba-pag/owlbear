# Architect Stance — Cockpit Decisions Tab

## Architectural Stance

Route-based switching via React Router is the correct structural choice for multi-tab navigation. BrowserRouter already wraps the app; Shell's `<Routes>` block is the right dispatch point. URL becomes the source of truth for which view is active. This is unambiguous.

But the current Shell is a monolith, not a layout frame. Adding routes to a monolithic Shell without structural preparation will produce a multi-view monolith where every subsequent tab increases conditional complexity. Three structural issues must be addressed — scoped to the right delivery phase.

### 1. Shell Must Be Decomposed — Incrementally Across P1/P2

Shell.tsx is not a thin layout frame. It constructs kanbanProps with ~15 props (selection callbacks, mutation handlers, task state), manages sidecar content and collapse state, renders cross-cutting decision surfaces (DRStatusIndicator, ResolveModal), handles selectedTaskSubtab, tab-change wiring, validation/banner state, and mobile auto-selection. A route config array does not solve this — Shell is a kanban-view controller wearing a layout-frame disguise.

**Position:** Shell decomposition must happen, but scoped to what each phase requires:

**P1 (tab-shell + skeleton):** Minimal extraction — move just enough kanban orchestration out of Shell so the skeleton decisions route renders cleanly. Concretely: the sidecar content block and mobile auto-select logic should be conditional on route, not extracted into a separate component. Shell keeps its current shape but gains route-awareness for sidecar rendering. This respects P1's locked scope (tab infrastructure + skeleton page).

**P2 (decisions content):** When the decisions page needs its own workspace layout, evaluate whether a KanbanView wrapper extraction is warranted. The decisions page will set `selectedDRId` via the existing CockpitProvider contract (see §ResolveModal below), so Shell's cross-cutting surfaces work without changes.

**Post-P2 (second consumer tab):** Full KanbanView extraction becomes justified when the third route (Memory or Notebook) arrives. Until then, the cost of extraction exceeds the cost of route-conditional rendering.

A route config array (`{ path, label, icon, component, hasSidecar }`) is warranted for nav-rail rendering and route dispatch. It prevents Shell's nav-rail from accumulating per-tab JSX. But it solves the easy problem. The hard problem is incremental decomposition.

### 2. CockpitProvider Stays As-Is — With an Explicit Boundary

CockpitProvider holds four active domains: board (polling/SSE), task selection (on-demand fetch on selectedTaskId change), DRs (60s polling), and scan (polling). It also holds UI workflow state: selectedTaskId, selectedDRId, selectedTask with fetch orchestration.

Three of these four domains serve Shell-level surfaces regardless of route:

- **Board:** status-bar health indicator, health badge
- **DRs:** status-bar DRStatusIndicator (renders popover with title, agent, task_id, age), ResolveModal (renders full DR body)
- **Scan:** status-bar health badge, repair panel

**Task selection is the exception.** It serves only the kanban sidecar. On non-kanban routes, selectedTaskId persists but the fetch effect is inert (no new selectedTaskId changes trigger fetches). This is acceptable waste — no polling, no requests, just stale state in memory.

**Position:** CockpitProvider stays unchanged for P1/P2. The boundary for future tabs: **tab-specific data hooks stay in the tab component, not CockpitProvider.** If Memory or Notebook need data, they use local hooks within their route components. This must be documented as an explicit pattern constraint in the route config or a dev-facing comment, not left implicit.

### 3. Sidecar Must Be Route-Conditional Across All Breakpoints

The sidecar is coupled to kanban at three responsive levels:

- **Desktop (≥1024px):** 360px grid column — task detail, DecisionViewport, activity tabs, collapse button
- **Tablet (768–1023px):** 48px collapsed column
- **Mobile (<768px):** `<p-sheet>` modal triggered when selectedTaskId is non-null

The existing `[data-sidecar-collapsed]` attribute only zeroes the desktop column. It does not suppress the mobile sheet, the tablet column, the aside DOM, or focusable sidecar controls. Route-conditional sidecar is not a CSS tweak — it requires suppressing rendering at all three breakpoints.

**Position:** P1 introduces a `data-has-sidecar` attribute (or equivalent) on the Shell grid container, driven by route config. On non-sidecar routes:

- Desktop/Tablet: grid template omits the sidecar column entirely (`56px minmax(0,1fr)`)
- Mobile: `<p-sheet>` is not rendered (conditional on route, not just selectedTaskId)
- Aside DOM: not rendered (not just visually hidden — removed from DOM to eliminate focusable orphans)

The sidecar content duplication for mobile/desktop (F10 from research) should be addressed during this work — maintaining route-conditional rendering across two duplicated content blocks is a maintenance trap. Extract shared sidecar content into a single component rendered in both containers.

### ResolveModal Ownership

**One global ResolveModal at Shell level.** This is the current contract: DRStatusIndicator and DecisionViewport both set `selectedDRId` via CockpitProvider → ResolveModal renders when `selectedDR` is non-null. The decisions page follows the same contract — clicking a DR item sets `selectedDRId`, which triggers the existing Shell-level ResolveModal. No second modal instance. No ownership ambiguity.

This is correct because ResolveModal is an overlay (z-index 999, focus trap, escape handling) that floats above all layout. It is not tied to any route's content area.

### Lazy Loading

`React.lazy()` + `<Suspense>` for non-default route components. KanbanBoard stays eagerly loaded as the default route. Decisions page and future tab pages lazy-load.

Shell-level imports (DecisionViewport for sidecar, DRStatusIndicator for status bar, ResolveModal) remain eager — they serve cross-cutting Shell surfaces. This is correct, not a problem. The lazy boundary is at route-page components, not shared Shell infrastructure.

### Nav-Rail

`role="navigation"` with `useNavigate()` buttons. Active state derived from `useLocation()`. Two-tier navigation is preserved and independent: route-level nav-rail (`role="navigation"`) and within-view sidecar tabs (`<p-tabs>`, `role="tablist"`). Different ARIA semantics, different navigation levels. Correct.

### DRStatusIndicator Fate

Research Q3 flags whether DRStatusIndicator becomes redundant once a decisions tab exists. **This is not a P1/P2 decision.** The indicator provides global pending-DR awareness regardless of active route — equivalent to a notification badge. Keep it. If user testing shows redundancy after the decisions tab ships, remove it as a fast-follow.

## Key Trade-offs

| Decision | Cost | Benefit |
|----------|------|---------|
| Route-conditional sidecar in P1 | CSS grid changes at 3 breakpoints + conditional rendering | Clean decisions skeleton, no kanban debris on non-kanban routes |
| CockpitProvider unchanged | Task selection state is inert waste on non-kanban routes | Zero refactoring of consumers, clear boundary for future tabs |
| Single Shell-level ResolveModal | All routes share one modal instance and one selectedDRId state | No ownership ambiguity, no duplicate focus-trap logic |
| Deferred Shell decomposition | P1 Shell has route-conditional patches, not clean extraction | P1 stays scoped to tab infrastructure, not internal refactor |
| Route config array | Minor indirection for 3-5 entries | Nav-rail + route dispatch driven from data, not JSX accumulation |

## Warnings

1. **P1 sidecar conditioning is the highest-risk work.** It touches CSS grid at 3 breakpoints, conditional DOM rendering, mobile sheet suppression, and existing test contracts that assert sidecar as a persistent Shell region. These tests will need updates.
2. **ResolveModal ownership must be explicit from day one.** If the decisions page creates its own ResolveModal instance instead of using the shared selectedDRId contract, focus management and selection state will diverge. One modal, one state source.
3. **CockpitProvider boundary is a convention, not enforcement.** Without explicit documentation, the next tab developer will add their data hook to CockpitProvider because it's the obvious place. A code comment or pattern doc is cheap insurance.
4. **Mobile auto-select (`onMobileAutoSelect`) must be route-guarded.** Currently fires on initial load regardless of route. In P1, guard it to kanban route only. This is the most likely regression from multi-route introduction.

## Confidence

0.80
