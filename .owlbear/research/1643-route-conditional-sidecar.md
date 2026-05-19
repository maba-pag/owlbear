# Route-Conditional Sidecar Suppression

> **Owning task:** #1643 — P1-03: Route-conditional sidecar — suppress sidecar DOM on non-kanban routes
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

Shell.tsx renders the `<aside>` sidecar unconditionally in a 3-column CSS grid (`56px 1fr clamp(320px,24vw,380px)`). The brief (#1638) states the sidecar is kanban-specific — non-kanban routes (e.g. `/decisions`) should not have it in the DOM at all. The grid must adapt to fill the freed space.

Key constraints from AC:
- Sidecar DOM must be absent when route ≠ `/`
- Navigating back to `/` must restore previous collapse state
- Grid columns must adjust automatically

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/cockpit/web/src/Shell.tsx` (current impl) | 1.0 — target file |
| 2 | `serve/cockpit/web/src/routes.ts` (routeConfig) | 1.0 — route metadata |
| 3 | `serve/cockpit/web/src/Shell.css` (`data-sidecar-collapsed` pattern) | 0.9 — existing conditional grid pattern |
| 4 | React Router v7 `useLocation` docs (reactrouter.com) | 0.8 — hook API |
| 5 | Brief `.owlbear/briefs/draft-cockpit-decisions-tab/brief.md` | 0.9 — design intent |

## 3. Analysis

### Implementation Approaches

| Criterion | A: `useLocation` + hardcoded path | B: `routeConfig.hasSidecar` metadata | C: Layout routes (nested `<Outlet>`) |
|-----------|-----------------------------------|--------------------------------------|--------------------------------------|
| Complexity | 2 lines in Shell | ~5 lines (type + config + lookup) | Major restructure |
| KISS alignment | High | High | Low — overkill |
| Extensibility | New sidecar routes need Shell edit | New routes declare intent in config | Routes declare layout via nesting |
| Aligns with #1639 AC3 | No (Shell must change per route) | Yes (routeConfig-driven) | Partially |
| State preservation | Natural (useState persists) | Natural (useState persists) | Requires lifting state |
| Test effort | Low | Low | Medium |

### CSS Grid Adjustment Pattern

The codebase already uses `data-sidecar-collapsed` on the shell div to change `--shell-columns`. The same pattern applies:

```css
.shell[data-no-sidecar] {
  --shell-columns: var(--shell-rail-width) minmax(0, 1fr);
}
```

The `grid-template-areas` also needs a 2-column variant:
```css
.shell[data-no-sidecar] {
  grid-template-areas:
    'status-bar status-bar'
    'nav-rail workspace';
}
```

### Collapse State Preservation (AC2)

`isSidecarCollapsed` lives in Shell's `useState`. Since Shell is never unmounted during route changes (only the `<Routes>` content swaps), the state is inherently preserved. When the sidecar remounts on return to `/`, it reads the same `isSidecarCollapsed` value — no extra work needed.

## 4. Recommendation

**Option B: `routeConfig.hasSidecar` metadata** — confidence: 0.85

Rationale:
- Aligns with #1639's routeConfig-driven architecture (AC3 proved extensibility)
- Minimal complexity (~5 lines of logic)
- Future routes (Memory, Ideas Notebook per brief) just add `hasSidecar: false`
- Uses existing `data-*` attribute pattern for CSS grid switching

Implementation sketch:
1. Add `hasSidecar?: boolean` to `RouteConfigEntry` (default `false`)
2. Set `hasSidecar: true` on the `/` route only
3. In Shell: `useLocation()` → find matching route → derive `showSidecar`
4. Conditionally render `<aside>` with `{showSidecar && <aside>...</aside>}`
5. Add `data-no-sidecar={!showSidecar || undefined}` to shell div
6. CSS: `.shell[data-no-sidecar]` overrides `--shell-columns` and `grid-template-areas`

Challenge: proceed — confidence in original: 0.85. The approach is low-risk, uses existing patterns, and has no architectural trade-offs.

## 5. Follow-up Tasks

Task #1643 itself advances to backlog — implementation is straightforward T1 work (no new capabilities, no architecture changes, uses existing patterns).

### Testing Strategy (recommended)

- `MemoryRouter` with `initialEntries={['/decisions']}` → assert no `[data-region="sidecar"]` in DOM
- `MemoryRouter` with `initialEntries={['/']}` → assert sidecar present
- Collapse state persistence: render at `/`, collapse, navigate away, return — assert collapse attribute still set
