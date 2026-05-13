# Sidecar Collapse Toggle — Test Approach

> **Owning task:** #1541 — P3-07: test — sidecar collapse toggle
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1541 requires Vitest tests for sidecar collapse/expand functionality. The sidecar (`<aside data-region="sidecar">` in Shell.tsx) is currently a fixed panel with no collapse mechanism. The brief specifies: "Collapsible (default open), toggle button to collapse/expand, CSS transition for smooth collapse." Tests must be RED against current code.

**Key questions:** (a) What ARIA pattern should tests expect? (b) Where should the toggle button live? (c) How to test state persistence across re-renders? (d) What mocking is needed?

## 2. Sources Studied

| # | Source | Relevance | What was used |
|---|--------|-----------|---------------|
| S1 | `src/KanbanBoard.tsx` — filter toggle pattern (L78, L269-271) | 1.0 | `useState` + `aria-expanded` + `aria-controls` + `onClick` toggle pattern |
| S2 | `src/__tests__/FilterAccessibility.test.tsx` — toggle tests | 1.0 | Test pattern: `fireEvent.click` + `getAttribute('aria-expanded')` verification |
| S3 | `src/__tests__/Shell.test.tsx` — Shell render + mock setup | 0.95 | Provider wrapping, fetch stub, sidecar region queries |
| S4 | WAI-ARIA `aria-expanded` spec (webability.io) | 0.90 | Disclosure pattern: button with `aria-expanded`, controlled panel visibility |
| S5 | `src/Shell.css` — sidecar grid layout | 0.85 | Current `grid-template-columns: 56px 1fr 360px`, `.shell__sidecar` area |
| S6 | Brief `draft-board-visual-design/brief.md` — Sidecar section | 1.0 | "Collapsible (default open), toggle button, CSS transition" |

## 3. Analysis

### 3.1 ARIA Pattern — Disclosure Widget

The standard pattern for show/hide toggles is the ARIA disclosure widget:

| Element | Attribute | Value |
|---------|-----------|-------|
| Toggle button | `aria-expanded` | `"true"` (open) / `"false"` (collapsed) |
| Toggle button | `aria-controls` | ID of controlled panel |
| Sidecar panel | `id` | Matches `aria-controls` value |
| Sidecar panel | visibility | Driven by CSS class or `hidden` attribute |

This matches the existing filter toggle pattern in KanbanBoard exactly.

### 3.2 Toggle Button Placement — Options

| Option | Location | Pros | Cons |
|--------|----------|------|------|
| A — Inside sidecar header | Top of `<aside>`, before tabs | Discoverable, adjacent to content | Hidden when collapsed (needs persistent anchor) |
| B — Adjacent to sidecar | Between workspace and sidecar | Always visible regardless of state | Extra DOM element outside natural regions |
| C — Status bar (right side) | In `.shell__status-bar` | Brief says theme toggle goes here; consistent | Distant from controlled element |

**Recommendation (confidence: 0.80):** Option A with a persistent button. The toggle lives inside the sidecar but remains visible when collapsed (sidecar collapses to a thin strip showing only the toggle, not fully `display:none`). This is the most common sidebar collapse pattern and keeps the toggle co-located with what it controls.

Tests should query `data-testid="sidecar-collapse"` regardless of exact placement — the testid contract decouples test from layout.

### 3.3 Visibility Mechanism

| Approach | How hidden | Test assertion |
|----------|-----------|---------------|
| CSS class toggle | `.shell__sidecar--collapsed` class, `grid-template-columns` change | Check `aria-expanded`, check sidecar has collapsed class |
| `hidden` attribute | `<aside hidden>` | Check `aria-expanded`, check `hidden` attribute |
| Conditional render | `{!collapsed && <aside>}` | Check `aria-expanded`, check sidecar not in DOM |

**Recommendation (confidence: 0.85):** CSS class toggle. Conditional render unmounts the sidecar (loses tab state, scroll position). The `hidden` attribute is coarser. CSS class + grid column change matches the existing responsive layout approach in Shell.css.

### 3.4 AC-2: State Persistence Test Strategy

"Collapsed state persists across component re-renders via local React state" means `useState` preserves value when React re-renders without unmounting. Test approach:

1. Render Shell → click collapse toggle → verify collapsed
2. Trigger re-render via `rerender()` (same props) — simulates parent state change
3. Verify sidecar remains collapsed and `aria-expanded="false"`

This is trivial with `@testing-library/react`'s `rerender()`. The state persists because `useState` is tied to the fiber, not the render cycle.

### 3.5 Mock Requirements

Same as existing Shell.test.tsx:
- `vi.mock('../hooks/EventSourceProvider')` — SSE mock
- `vi.stubGlobal('fetch', ...)` — never-resolving fetch to keep KanbanBoard in loading
- PDS + Router + CockpitProvider wrapping

No additional mocks needed for the collapse toggle.

## 4. Recommendation

**Approach (confidence: 0.85):** Write tests in a new file `SidecarCollapse_1541.test.tsx` using the Shell.test.tsx render helper pattern. Tests query `data-testid="sidecar-collapse"` for the toggle button, assert `aria-expanded` state changes on click, and verify sidecar visibility via CSS class or `aria-hidden`. AC-2 uses `rerender()` to confirm state persistence.

Challenge: FALLBACK — trivial test task, pattern established by S1+S2; challenger skip justified per gate checklist item 1-4 one-liner threshold.

**Tier: T1** — Test implementation, no architecture change, no DR needed.

## 5. Follow-Up Tasks

No new tasks needed. Task #1541 advances to backlog for test-writer execution. Implementation task #1549 already exists and depends on #1541.
