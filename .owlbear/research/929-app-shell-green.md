# App Shell GREEN Phase — Implementation Approach

> **Owning task:** #929 — P2-03: GREEN — App shell implementation
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #929 implements the cockpit app shell to pass RED tests from #927. The RED phase (#927) created `Shell.test.tsx` (14 tests). A minimal `Shell.tsx` was also created with the correct DOM structure — **all tests already pass**. However, several AC items require implementation work beyond test-passing: CSS Grid layout, component extraction, PDS token usage, and App/Router integration.

**Key question:** What implementation approach satisfies all AC items while keeping tests green and following PDS/KISS conventions?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/cockpit/web/src/Shell.tsx` — current implementation | 1.00 |
| S2 | `serve/cockpit/web/src/__tests__/Shell.test.tsx` — 14 RED tests | 1.00 |
| S3 | `serve/cockpit/web/src/tokens.css` — PDS light theme tokens | 0.95 |
| S4 | `serve/cockpit/web/src/App.tsx` / `main.tsx` — app entry | 0.95 |
| S5 | `.owlbear/research/922-cockpit-layout-mockup.md` — layout pixel budget | 0.90 |
| S6 | `.owlbear/research/927-app-shell-tests.md` — test strategy | 0.90 |
| S7 | `.owlbear/briefs/draft-cockpit/decisions.md` — D7, D14 | 1.00 |
| S8 | React Router v7 library docs — BrowserRouter, layout routes | 0.85 |
| S9 | `serve/cockpit/web/package.json` — deps (react-router already installed) | 0.90 |

## 3. Analysis

### 3.1 Current State

| Artifact | Status | Notes |
|----------|--------|-------|
| `Shell.tsx` | Exists, minimal | Flat `<div>` wrapper, correct DOM structure, no CSS Grid |
| `Shell.test.tsx` | 14 tests, all PASS | Queries `data-region`, `data-testid`, `data-surface` |
| `Shell.css` | Missing | No visual layout applied |
| `NavRail.tsx` | Missing | Inline in Shell.tsx |
| `StatusBar.tsx` | Missing | Inline in Shell.tsx |
| `Sidecar.tsx` | Missing | Inline in Shell.tsx |
| `tokens.css` | Exists | PDS light theme custom properties |
| `App.tsx` | Old PHeading placeholder | Not wired to Shell |
| `main.tsx` | No BrowserRouter | Uses bare `<App />` |
| TypeScript | Clean | `tsc --noEmit` passes |
| Build | Clean | Vite build succeeds |

### 3.2 CSS Grid Layout

From #922 layout research: viewport 1440×900, nav-rail 56px, sidecar 360px, workspace 1024px remainder.

**Grid definition (recommended):**

```css
.shell {
  display: grid;
  grid-template-areas:
    "status-bar status-bar status-bar"
    "nav-rail   workspace  sidecar";
  grid-template-columns: 56px 1fr 360px;
  grid-template-rows: auto 1fr;
  height: 100vh;
}
```

The `contextual` region is "reserved, empty" per AC. It sits in the DOM as `<div data-region="contextual" />` but has no grid area — hidden via `display: none` until a future task activates it. This avoids wasting layout space on a placeholder.

**PDS token usage:** Background colors (`--pds-theme-light-background-base`, `--pds-theme-light-background-surface`), contrast for borders (`--pds-theme-light-contrast-low`), no hand-rolled hex. All from `tokens.css`.

### 3.3 Component Extraction

Tests query `data-region` attributes from the container — they don't import individual components. Extraction is safe:

| Component | Responsibility | Test impact |
|-----------|---------------|-------------|
| `StatusBar.tsx` | Renders `<header data-region="status-bar">` children | None — queried by attribute |
| `NavRail.tsx` | Renders `<nav data-region="nav-rail">` children | None — queried by attribute |
| `Sidecar.tsx` | Renders `<aside data-region="sidecar">` + PDS tabs + tab switching | None — queried by attribute + `p-tabs`/`p-tabs-item` |
| `Shell.tsx` | Grid container, region wrappers, `<Routes>` | None — still the rendered component |

The `data-region` attributes must remain on the same elements. Two patterns:

| Pattern | Description | Recommendation |
|---------|-------------|----------------|
| A. Region wrapper in Shell, children in component | Shell renders `<header data-region="status-bar"><StatusBar /></header>` | **Recommended** — Shell owns layout, components own content |
| B. Component owns its region element | `StatusBar` renders `<header data-region="status-bar">...</header>` | Simpler, but couples layout to component |

**Recommendation: Pattern A** (confidence: 0.85). Shell controls the grid; components provide content. This keeps the grid definition in one place and allows components to be reused or tested independently.

### 3.4 App/Router Integration

Current `main.tsx` renders `<App />` without a router. Per React Router v7 docs (S8):

```tsx
// main.tsx
import { BrowserRouter } from 'react-router'
// ...
<BrowserRouter>
  <App />
</BrowserRouter>
```

`App.tsx` replaces PHeading with Shell inside `PorscheDesignSystemProvider`. The `App.test.tsx` (2 tests for PHeading) will need updating — these tests assert the old placeholder content.

### 3.5 Extensibility (D7/AC)

The current `<Routes>` inside Shell with `<Route path="/" />` and `<Route path="/hello" />` satisfies AC. For future extensibility (D7: "shell design informs future surfaces"), the Outlet pattern is cleaner — Shell as layout route renders `<Outlet />` in the workspace region.

However, the current tests render `<Shell />` directly with `<MemoryRouter>`, and Shell contains `<Routes>`. Switching to Outlet would require test changes (wrapping Shell in a parent `<Route>`). Since AC says "All RED tests from #927 pass," the current pattern should be preserved. Extensibility refactoring is a separate future task.

### 3.6 Trade-Off Summary

| Concern | Approach | Confidence |
|---------|----------|------------|
| CSS Grid | Named grid areas, 3-column, 2-row | 0.92 |
| Component extraction | Pattern A (Shell owns regions, components own content) | 0.85 |
| Router integration | BrowserRouter in main.tsx, Shell in App.tsx | 0.90 |
| Contextual region | `display: none` (reserved) | 0.90 |
| PDS tokens | All colors from `tokens.css` custom props | 0.95 |
| Extensibility | Keep current Routes-in-Shell; refactor to Outlet later | 0.85 |

## 4. Recommendation

Straightforward GREEN implementation — no architectural choices needed. All patterns are established in prior research (#922, #927) and brief decisions (D7, D14).

1. Create `Shell.css` with CSS Grid layout using PDS tokens
2. Extract `StatusBar.tsx`, `NavRail.tsx`, `Sidecar.tsx` using Pattern A
3. Update `App.tsx` to render Shell; update `main.tsx` with BrowserRouter
4. Update `App.test.tsx` to match new App content
5. Verify all 14 Shell tests + build still pass

Confidence: **0.90**

Challenge: N/A — deterministic GREEN implementation of fully-specified AC. No alternatives to evaluate.

## 5. Follow-up Tasks

No new tasks needed. The AC is self-contained and #929 is the GREEN implementation task itself.

**Builder notes:**
- `App.test.tsx` assertions will change (PHeading → Shell content). This is expected — the test verified the old placeholder.
- Tab switching in `Sidecar.tsx` uses a `useRef`+`useEffect` pattern for PDS `tabChange` custom event. Keep this in the extracted component.
- The grid should import `tokens.css` — it's already imported in `main.tsx`.
