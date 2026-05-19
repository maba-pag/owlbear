# Tab Routing Infrastructure — Route Config Pattern

> **Owning task:** #1639 — P1-01: Tab routing infrastructure
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

Shell.tsx has a single inline `<Route path="/" element={<KanbanBoard ... />} />`. The task introduces a declarative route config array that drives both route rendering and (in sibling tasks) nav-rail buttons and lazy loading. The key design question: what schema does the route config entry use, and how does Shell consume it?

Constraints from sibling tasks:
- **#1642 (nav-rail):** iterates route config to render one button per entry — needs `label` and `icon`
- **#1644 (lazy loading):** wraps config entries in `React.lazy()` — needs `component` (ComponentType), not pre-built elements

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| React Router v7 Declarative Mode — Routing | reactrouter.com/start/declarative/routing | 0.9 |
| React Router v7 `useRoutes` hook docs | reactrouter.com/api/hooks/useRoutes | 0.7 |
| React Router v7 SPA guide | reactrouter.com/how-to/spa | 0.5 |
| Cockpit Shell.tsx (live code) | serve/cockpit/web/src/Shell.tsx | 1.0 |
| Cockpit App.tsx (live code) | serve/cockpit/web/src/App.tsx | 0.8 |
| Brief — Cockpit Decisions Tab | .owlbear/briefs/draft-cockpit-decisions-tab/brief.md | 1.0 |
| SPA catch-all in backend | serve/cockpit/src/owlbear_cockpit/main.py:133 | 0.6 |

## 3. Analysis

### Option Comparison

| Criterion | A: Config with `component` (ComponentType) | B: Config with `element` (ReactElement) | C: `useRoutes` hook (RouteObject[]) |
|-----------|---------------------------------------------|------------------------------------------|--------------------------------------|
| AC match ("path, label, icon, component") | Direct match | Diverges from AC wording | Needs custom wrapper for label/icon |
| Lazy loading compatibility (1644) | `React.lazy()` returns ComponentType ✓ | Breaks — elements can't be lazy-wrapped | Works but loses metadata |
| Nav-rail reuse (1642) | Same array drives buttons ✓ | Same array drives buttons ✓ | Separate metadata needed |
| KanbanBoard prop injection | Conditional in render loop | Natural (built in Shell scope) | Conditional in RouteObject builder |
| Module-level exportable | Yes (static const) | No (needs render scope for props) | Partially (loses metadata) |
| KISS / minimal diff | ~30 LOC new file + ~10 LOC Shell edit | ~15 LOC Shell edit | ~25 LOC + import change |
| Future extensibility | Add entry = new tab | Add entry = new tab | Add entry = new tab |

### KanbanBoard Prop Tension

KanbanBoard receives 10+ props from Shell state (board, tasks, selection, callbacks). The route config stores `component: ComponentType`, but rendering KanbanBoard requires prop injection. Resolution:

- Shell's rendering loop has a transitional conditional: if `route.component === KanbanBoard`, render with props; otherwise render `<route.component />`
- This does NOT violate AC3 ("adding a new entry is sufficient without modifying Shell internals") because new entries use the generic path
- Future refactoring can move KanbanBoard to consume CockpitProvider hooks directly, eliminating the conditional

### Vite + Backend SPA Support

- **Dev:** Vite dev server has built-in SPA fallback (all routes → index.html)
- **Production:** Backend `_spa_catchall` at `/{path:path}` already serves index.html for all unknown paths
- **No infrastructure work needed** for `/decisions` to resolve

## 4. Recommendation

**Option A: Route config with `component` (ComponentType) — Confidence: .82**

```typescript
// routes.ts
export interface RouteEntry {
  path: string
  label: string
  icon: string  // SVG path data for nav-rail icon
  component: ComponentType
}

export const routeConfig: RouteEntry[] = [
  { path: '/', label: 'Kanban', icon: 'M2 3h5v4...', component: KanbanBoard },
  { path: '/decisions', label: 'Decisions', icon: '...', component: DecisionsPage },
]
```

Shell rendering:
```tsx
<Routes>
  {routeConfig.map(route => (
    <Route
      key={route.path}
      path={route.path}
      element={
        route.component === KanbanBoard
          ? <KanbanBoard {...kanbanProps} />
          : <route.component />
      }
    />
  ))}
</Routes>
```

Challenge: reconsider → revised from original `element`-based approach. Challenger identified that `element` field breaks lazy loading (1644) and diverges from AC wording. Original confidence: .63 → revised: .82.

### Implementation Sketch

1. **New file:** `serve/cockpit/web/src/routes.ts` — type + const array (exported)
2. **New file:** `serve/cockpit/web/src/pages/DecisionsPage.tsx` — skeleton with `data-testid="decisions-page"`
3. **Edit:** `Shell.tsx` — replace inline `<Route>` with `.map()` over `routeConfig`
4. **No new dependencies** — uses existing react-router APIs

### Testing Strategy

- Render Shell with `MemoryRouter initialEntries={['/decisions']}` → assert `data-testid="decisions-page"` present
- Render Shell with `MemoryRouter initialEntries={['/']}` → assert KanbanBoard renders unchanged
- Import `routeConfig` directly → assert array has ≥2 entries with required fields
- Validate adding a third entry renders correctly (extensibility gate)

## 5. Follow-up Tasks

Research is complete for this task. No new follow-up tasks needed — sibling tasks #1642, #1643, #1644 already cover nav-rail, sidecar conditioning, and lazy loading respectively.
