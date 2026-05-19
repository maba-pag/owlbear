# Nav-Rail Tab Navigation — Dynamic Buttons from Route Config

> **Owning task:** #1642 — P1-02: Nav-rail tab navigation — dynamic buttons from route config
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

Shell.tsx has a hardcoded `<button>` in the nav-rail with static `aria-current="page"` and a kanban SVG icon. Task #1639 (archived) introduced `routeConfig` array in `routes.ts` with `{ path, label, icon, component }` entries. This task wires the nav-rail to render buttons dynamically from that config, with `useNavigate()` handlers and location-based active state.

**Question:** What's the correct React Router v7 pattern for a nav-rail driven by a route config array?

## 2. Sources Studied

| # | Source | Relevance | What taken |
|---|--------|-----------|------------|
| 1 | `serve/cockpit/web/src/routes.ts` (codebase) | 1.0 | Existing `RouteConfigEntry` interface: `{ path, label, icon, component }` |
| 2 | `serve/cockpit/web/src/Shell.tsx` L293–316 (codebase) | 1.0 | Current hardcoded nav-rail button, existing Routes map from routeConfig |
| 3 | React Router v7 docs (useNavigate, useLocation) | 0.9 | Standard hooks — `useNavigate()` returns navigate fn, `useLocation()` returns `{ pathname }` |
| 4 | `serve/cockpit/web/src/__tests__/Shell.test.tsx` (codebase) | 0.8 | Durable tests query `[data-surface="kanban"]`, `[aria-current="page"]`, `[data-region="nav-rail"]` |

## 3. Analysis

### Implementation Options

| Criterion | Option A: useLocation + exact match | Option B: useMatch per button | Option C: NavLink component |
|-----------|------|------|------|
| Hook rules compliance | ✓ single hook call | ✗ can't call hooks in loop | ✓ built-in |
| KISS | ✓ one comparison | N/A | ✗ requires NavLink props API |
| Control over markup | ✓ full control | N/A | ✗ renders `<a>`, not `<button>` |
| Active state logic | `pathname === route.path` | N/A | className fn |
| Compatibility with existing CSS | ✓ keeps `aria-current` pattern | N/A | ✗ different markup |
| Test selector stability | ✓ keeps `data-surface`, `aria-current` | N/A | Requires adaptation |

**Option A dominates.** NavLink (Option C) renders anchors, not buttons — incompatible with existing nav-rail CSS and test selectors. Option B is invalid (hooks rules).

### Implementation Approach (Option A)

1. Import `useNavigate`, `useLocation` from `react-router`
2. Call both hooks in Shell body
3. Add `role="navigation"` to `<nav>` (explicit per AC, redundant with `<nav>` semantics)
4. Replace hardcoded button with `routeConfig.map(route => ...)`:
   - `onClick={() => navigate(route.path)}`
   - `aria-current={location.pathname === route.path ? 'page' : undefined}`
   - `aria-label={route.label}`
   - `data-surface={route.icon}` (preserves test selectors)
5. Icon rendering: inline SVG map `Record<string, ReactNode>` — keeps KISS, no new deps

### Active State: Exact vs Prefix Match

Exact match (`pathname === route.path`) is sufficient. All current paths are leaf routes (`/`, `/decisions`). If nested routes are introduced later, a prefix-match strategy can be added then (YAGNI).

### Icon Strategy

Current kanban button uses inline SVG. The `icon` field is a string identifier. A module-level icon map:
```ts
const navIcons: Record<string, ReactNode> = {
  kanban: <svg ...>...</svg>,
  decisions: <svg ...>...</svg>,
}
```
This is simpler than importing a PDS icon library for 2 icons and keeps the same visual approach.

## 4. Recommendation

**Option A: `useLocation()` + exact pathname match + icon map.** Confidence: **0.92**

Challenge: SKIP — trivial pattern, single viable option (B invalid, C incompatible with existing markup).

### Risk

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Durable Shell.test.tsx selectors break | Medium | Keep `data-surface="kanban"` on first button; map `icon` → `data-surface` |
| Root "/" match ambiguity with nested routes | Low | Exact match sufficient for current config; YAGNI |

## 5. Follow-up Tasks

No new follow-up tasks needed. Sibling tasks already cover:
- #1643: sidecar conditioning
- #1644: lazy loading
- #1646: pending count badge on nav-rail decisions button

### Classification: T1 — Standard React Router pattern, no architecture change.
