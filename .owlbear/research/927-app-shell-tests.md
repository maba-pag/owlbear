# App Shell RED Phase — Test Strategy

> **Owning task:** #927 — P2-02: RED — App shell tests
> **Date:** 2026-04-18 **Status:** Complete

## 1. Context and Question

Task #927 writes failing tests for the cockpit app shell: CSS Grid layout regions, routing, status bar, nav rail, and sidecar tab structure. The scaffold (#925) is complete — Vite + React 19 + TS + PDS 3.34 + Vitest + RTL are configured. The current `App.tsx` is a bare PHeading placeholder.

**Key questions:** (a) How to test CSS Grid regions in jsdom? (b) What router dependency and test pattern? (c) How to test PDS Tabs switching in jsdom?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | `serve/cockpit/web/package.json` — current deps | 0.95 |
| S2 | `serve/cockpit/web/vitest.setup.ts` — PDS jsdom polyfill + CDN skip | 0.95 |
| S3 | `serve/cockpit/web/src/App.test.tsx` — existing test pattern | 0.90 |
| S4 | React Router v7 API docs (`api.reactrouter.com/v7`) | 0.90 |
| S5 | React Router v7 library install + routing docs (`reactrouter.com`) | 0.90 |
| S6 | PDS v3.34 Tabs examples + API (`designsystem.porsche.com/v3`) | 0.85 |
| S7 | Brief decisions D7/D14 (`.owlbear/briefs/draft-cockpit/decisions.md`) | 1.00 |
| S8 | Layout research #922 (`.owlbear/research/922-cockpit-layout-mockup.md`) | 0.85 |

## 3. Analysis

### 3.1 CSS Grid Region Testing

jsdom does not compute CSS layout — `getComputedStyle().gridArea` returns empty. The test must verify **DOM structure**, not visual layout.

| Strategy | How | Confidence |
|----------|-----|------------|
| A. `data-region` attributes | Query `[data-region="status-bar"]` etc. | **0.90** |
| B. ARIA landmarks | `role="navigation"`, `role="main"` etc. | 0.75 |
| C. CSS class names | `.shell-status-bar` etc. | 0.70 |

**Recommendation: Option A** — `data-region` is explicit, test-stable, and decoupled from styling/ARIA which serve other purposes. The 5 regions from D14/AC: `status-bar`, `nav-rail`, `workspace`, `sidecar`, `contextual`.

### 3.2 Router Dependency

React Router v7 (package: `react-router`) provides `MemoryRouter` for testing — no real browser history needed. All imports from `"react-router"` (unified package in v7).

| Aspect | Value |
|--------|-------|
| Package | `react-router` (single package in v7) |
| Test wrapper | `<MemoryRouter initialEntries={["/"]}>` |
| Shell pattern | Layout route with `<Outlet />` for workspace content |
| Route `/` | Index route → kanban surface placeholder |
| Route `/hello` | Extensibility proof — same shell, different workspace content |

**Dependency action:** Test-writer must `npm install react-router` before tests compile. This is the only new dependency.

### 3.3 PDS Tabs in Sidecar

PDS React wrappers render as custom elements in jsdom. Confirmed working by existing `App.test.tsx` (`querySelector('p-heading')`).

| PDS Component | Custom Element | Key Props |
|---------------|---------------|-----------|
| `PTabs` | `<p-tabs>` | `activeTabIndex` (number) |
| `PTabsItem` | `<p-tabs-item>` | `label` (string) |

**Tab switching test:** PDS web component event propagation in jsdom is unreliable. Test tab **presence** (two `<p-tabs-item>` with labels "Detail" and "Activity") and controlled state switching (React state drives `activeTabIndex` → assert correct content panel renders). Do NOT rely on simulating click events on PDS tab bar internals.

### 3.4 Test File Structure and Patterns

| Aspect | Recommendation |
|--------|---------------|
| File location | `serve/cockpit/web/src/__tests__/Shell.test.tsx` (per AC) |
| Matchers | Native Vitest (`not.toBeNull()`, `toBeTruthy()`) — no `@testing-library/jest-dom` in deps |
| Helper | `renderShell(route?: string)` wrapper that provides `<PorscheDesignSystemProvider>` + `<MemoryRouter>` |
| Groups | 4 describe blocks: Grid Regions, Nav Rail, Status Bar, Routing, Sidecar Tabs |

### 3.5 AC → Test Mapping

| AC Item | Test Assertion | Expect (RED) |
|---------|---------------|-------------|
| 5 CSS Grid regions | 5 `[data-region=*]` elements present | FAIL — Shell component doesn't exist |
| Nav rail icons + kanban active | Button/icon elements in nav-rail region; kanban has `aria-current="page"` | FAIL |
| Status bar placeholders | Traffic-light + count elements via `data-testid` | FAIL |
| Route `/` → kanban | `MemoryRouter` at `/`, text "kanban" in workspace region | FAIL |
| Route `/hello` → workspace | `MemoryRouter` at `/hello`, all 5 regions still present + hello content | FAIL |
| Sidecar tabs | `p-tabs` with 2 `p-tabs-item` (Detail, Activity) | FAIL |
| Tab switching | Change `activeTabIndex`, verify content area text changes | FAIL |

## 4. Recommendation

Straightforward test scaffolding with one new dependency (`react-router`). No architectural choices — the AC is fully specified.

- Test DOM structure via `data-region` attributes (not computed CSS)
- Use `MemoryRouter` for route testing
- Test PDS tabs via controlled `activeTabIndex` state, not click simulation
- All tests will fail because `Shell` component doesn't exist yet

Confidence: **0.92**

Challenge: N/A — deterministic test scaffolding following established patterns and explicit AC. No alternatives to evaluate.

## 5. Follow-up Tasks

None. The AC is self-contained. The GREEN implementation (#929) already exists as the follow-up.
