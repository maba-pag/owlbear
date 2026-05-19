# Pending Count Badge on Nav-Rail Decisions Button

> **Owning task:** #1646 — P2-03: Pending count badge on nav-rail decisions button
> **Date:** 2026-05-19 **Status:** Complete

## 1. Context and Question

The decisions nav-rail button (implemented in #1642) needs a badge overlay showing the pending DR count from `useDRState().count`. Badge must be absent from the DOM when count is 0.

**Question:** What implementation pattern best fits the existing nav-rail architecture and PDS design token system?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| Shell.tsx nav-rail (lines 448–476) | Codebase | 1.0 — direct implementation target |
| Shell.css `.shell__nav-button` (lines 257–306) | Codebase | 1.0 — button has `position: relative`, enables absolute badge |
| Column.tsx count badge (`column-count`) | Codebase | 0.8 — existing in-app badge pattern |
| DRStatusIndicator | Codebase | 0.7 — shows existing DR count access pattern |
| CockpitProvider `useDRState()` | Codebase | 1.0 — hook already used in Shell.tsx |
| Material UI Badge component pattern | Prior art | 0.6 — standard absolute-positioned badge overlay |

## 3. Analysis

### Implementation Options

| Criterion | A: Direct conditional in Shell | B: RouteConfig `badge` field |
|-----------|-------------------------------|------------------------------|
| KISS | High — 3 lines in render | Lower — new interface field, generic renderer |
| YAGNI | Only decisions needs badge | No other tab has a badge planned |
| Data-driven | Specific to one button | Extensible to future badge tabs |
| Testability | Mock `useDRState`, assert DOM | Same |
| Lines of change | ~5 TSX + ~15 CSS | ~15 TSX + ~15 CSS + routes.ts change |

### CSS Approach

The nav button already has `position: relative` (Shell.css:257). A badge span with `position: absolute` top-right is the standard overlay pattern. Use PDS design tokens:

- Background: `var(--p-color-notification-error)` (red notification color)
- Text: `var(--p-color-notification-error-contrast)` (white on dark)
- Font: `var(--p-font-size-xx-small)` with `font-weight: 700`
- Size: min 16px circle/pill, `border-radius: var(--p-radius-full)`
- Position: `top: -4px; right: -4px` (overlap the button corner)

### Accessibility

- Badge is decorative (inside a button that already has `aria-label`).
- Update `aria-label` to include count: `Decisions (3 pending)` when count > 0.
- This ensures screen readers announce the count without reading the badge span separately.

## 4. Recommendation

**Option A: Direct conditional in Shell** — confidence: 0.90

Rationale: YAGNI. Only the decisions button needs a badge. The implementation is 3 lines of TSX inside the existing `routeConfig.map()` render plus a CSS class. No architectural change to `RouteConfigEntry`.

Challenge: SKIPPED — trivial UI task, single well-understood pattern, no architectural trade-off.

### Implementation Sketch

```tsx
// Inside routeConfig.map() button render:
{route.icon === 'decisions' && pendingDRCount > 0 && (
  <span className="shell__nav-badge" aria-hidden="true">
    {pendingDRCount}
  </span>
)}
```

```css
.shell__nav-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border-radius: var(--p-radius-full);
  background: var(--p-color-notification-error);
  color: var(--p-color-notification-error-contrast);
  font-size: var(--p-font-size-xx-small);
  font-weight: 700;
  line-height: 16px;
  text-align: center;
}
```

### Testing Strategy

- **AC1:** Render Shell with mocked `useDRState` returning `count: 3` → assert badge span present with text "3" inside the decisions button.
- **AC2:** Render Shell with `count: 0` → assert no badge element in DOM (use `queryByTestId` returns null).
- Edge: verify `aria-label` updates on the decisions button when count > 0.

## 5. Follow-up Tasks

No additional research tasks needed — this is implementation-ready. The task's existing AC is sufficient and the implementation approach is clear. Task #1646 can proceed directly to `todo` for test writing and implementation.
