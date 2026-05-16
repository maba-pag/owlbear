# Simple Component Swaps — PDS v4 Migration

> **Owning task:** #1614 — P2-03: Simple component swaps
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Which raw HTML elements and PDS web-component tags in `serve/cockpit/web/src/` qualify as "simple swaps" to PDS React wrappers, and which belong to sibling tasks or should remain as intentional native controls?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | Codebase scan — all `.tsx` in `src/` | local grep | 1.0 |
| 2 | PDS v4 React wrapper exports | local `node_modules` | 1.0 |
| 3 | PDS GitHub — PTabs, PSheet, PTabsItem usage | github.com/porsche-design-system | 0.9 |
| 4 | PdsMigration.test.tsx (#1609) | local test spec | 0.9 |
| 5 | PDS v4 Button/Heading/Text API | designsystem.porsche.com/v4/ | 0.8 |
| 6 | Shell.tsx tabChange event contract | local + PDS CHANGELOG | 0.9 |

## 3. Analysis

### 3.1 Raw `<button>` Inventory (8 locations, 6 files)

| File | Element | Classification | Rationale |
|------|---------|---------------|-----------|
| ActivityTab.tsx:146 | `<button data-testid="session-row">` | **Simple swap → PButton** | Already imports PButton; child spans preserved |
| DRStatusIndicator.tsx:126 | `<button data-testid="resolve-button">` | **Simple swap → PButton** | Already imports PButton |
| ErrorBoundary.tsx:33 | `<button>Try again</button>` | **Simple swap → PButton** | Class component — PButton works in render() |
| Shell.tsx:229 | `<button data-testid="sidecar-collapse">` | **Intentional native** | `aria-expanded`/`aria-controls` collapse pattern; SidecarCollapse test asserts native `<button>` |
| ThemeToggle.tsx:23 | `<button data-pds-exception="theme-toggle">` | **Intentional native** | Explicit exception marker |
| HealthBadge.tsx:75 | `<button data-pds-exception="status-bar-control">` | **Intentional native** | Explicit exception marker |
| CleanupPanel.tsx:179 | `<button data-pds-exception="status-bar-control">` | **Intentional native** | Explicit exception marker |
| DRStatusIndicator.tsx:76 | `<button data-pds-exception="status-bar-control">` | **Intentional native** | Explicit exception marker |

**Summary:** 3 to swap, 5 intentional native.

### 3.2 Raw Heading Inventory (5 locations, 3 files)

| File | Element | Target |
|------|---------|--------|
| Shell.tsx:148 | `<h1>OwlBear Cockpit</h1>` | `<PHeading tag="h1">` |
| Shell.tsx:246 | `<h2>{selectedTaskHeading}</h2>` | `<PHeading tag="h2">` |
| Shell.tsx:336 | `<h2>{selectedTaskHeading}</h2>` | `<PHeading tag="h2">` |
| DetailTab.tsx:195 | `<h3>Actions</h3>` | `<PHeading tag="h3">` |
| ErrorBoundary.tsx:29 | `<h3>Something went wrong…</h3>` | `<PHeading tag="h3">` |

**Summary:** All 5 are simple swaps to PHeading.

### 3.3 Raw `<select>` — Zero

No raw `<select>` elements exist in source files outside tests. AC-1 is already satisfied.

### 3.4 Raw PDS Web Components — OUT OF SCOPE

| File | Element | Owner Task | Reason |
|------|---------|-----------|--------|
| Shell.tsx:240 | `<p-sheet>` | #1616 (sidecar IA) | Sidecar mobile view |
| Shell.tsx:254,344 | `<p-tabs>` | #1616 (sidecar IA) | Sidecar tab nav; uses deprecated `tabChange` event (PDS v3), needs `onUpdate` migration — not a simple swap |
| Shell.tsx:255,320,345,410 | `<p-tabs-item>` | #1616 (sidecar IA) | Uses `ref` + `setAttribute('label')` pattern |
| FilterPanel.tsx:221 | `<p-checkbox>` | #1617 (filter panel) | Filter panel scope |

**Key finding:** AC-2 names `<p-button>` and `<p-icon>` as examples, but neither exists as raw web-component tags in the source. All raw PDS web components (`p-sheet`, `p-tabs`, `p-tabs-item`, `p-checkbox`) belong to sibling tasks. AC-2 is satisfied for the literal examples or needs reinterpretation as "all web-component tags" — in which case those swaps are already assigned to sibling tasks.

### 3.5 Risk: Shell `tabChange` Event Contract

Shell.tsx:100 uses `addEventListener('tabChange', ...)` — a PDS v3 event name deprecated in v4 in favor of `update`. The React wrapper (`PTabs`) surfaces this as `onUpdate`. Five test files dispatch `tabChange` events. Migrating to PTabs requires updating both source and test event contracts. This is NOT a simple swap — confirmed via PDS CHANGELOG and wrapper type definitions.

### 3.6 Risk: ActivityTab Session Rows

ActivityTab `<button>` wraps 5 `<span>` children. PButton renders as a custom element with a shadow-DOM button inside. Tests at ActivityTab.test.tsx:272,290 assert click-through navigation. PButton preserves `onClick`, `data-testid`, and child slot content — but tests querying `container.querySelector('button')` may need updating to `container.querySelector('p-button')`. PdsMigration.test.tsx already expects this change.

## 4. Recommendation

**Approach:** Narrow scope to true simple swaps only (buttons + headings). Leave all raw PDS web-component tags to their assigned sibling tasks.

| Swap | Count | Complexity | Confidence |
|------|-------|-----------|------------|
| `<button>` → PButton | 3 | Low | 0.90 |
| `<h1>`-`<h3>` → PHeading | 5 | Low | 0.92 |
| Raw PDS web-comp → React wrapper | 0 (deferred to siblings) | N/A | N/A |

**Overall confidence: 0.85**

Challenge: proceed — confidence in original: 0.85 (revised down from 0.90 after challenger identified scope collapse into sibling tasks and PTabs event-contract risk; accepted both challenges; narrowed scope accordingly).

## 5. Follow-Up Tasks

Task #1614 can proceed to build with the narrowed scope. No additional follow-up tasks needed — sibling tasks already cover the deferred web-component swaps. The inventory artifact from #1608 will document intentional-native rationale.
