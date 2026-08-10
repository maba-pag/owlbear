# Brief — Board Visual Design

## Problem

The Cockpit board is structurally complete but visually invisible. White-on-white rendering with no surfaces, shadows, borders, or visual hierarchy. Components lack any CSS treatment beyond minimal inline styles. The board cannot be scanned or used effectively in its current state.

## Outcome

**Best realistic outcome:** Board looks and feels like a finished product in both light and dark themes. Columns are visible surfaces. Cards communicate operational state through left-border color. Empty columns display fun status-appropriate illustrations. Theme switching works automatically (OS preference) and manually (toggle). The visual baseline is solid enough that future feature work inherits good design without fighting debt.

**Minimum viable win:** Board is visible and coherent in both themes. Surfaces, spacing, and borders in place. Card signal model working. Theme toggle functional. Secondary polish (illustrations, DnD styling) can be thinner.

---

## Token Architecture

### Token Rename

Restructure `tokens.css` from light-only (`--pds-theme-light-*`) to theme-agnostic names (`--pds-*`). Light values in `:root`, dark values in `[data-theme="dark"]`. Auto-responsive via `@media (prefers-color-scheme: dark)` as fallback when no `data-theme` is set.

### Token Expansion

Current tokens cover only colors (17 vars). Expand to include:
- Shadow tokens: `--pds-shadow-sm`, `--pds-shadow-md`, `--pds-shadow-lg`
- Border-radius: `--pds-radius-sm` through `--pds-radius-xl`
- Spacing: `--pds-spacing-xs` through `--pds-spacing-2xl`

Non-color tokens (shadow, radius, spacing) are theme-independent — single `:root` definition, no dark overrides.

### Theme Bootstrap

Synchronous script in `index.html` (before React mount) that reads localStorage and applies `data-theme` to `<html>`. Prevents flash-of-wrong-theme. localStorage value validated against `["dark", "light"]`; absent/invalid = auto (follows OS).

### `useTheme` Hook

React hook providing: current theme, toggle function, OS preference listener. No React Context — theme is a DOM attribute, CSS cascade propagates it. Zero re-renders on theme change.

### Toggle UI

Theme toggle button in status bar, right side.

### PDS Component Compatibility

Verification task: confirm PDS web components (buttons, tabs, banners) respond correctly to `data-theme` attribute changes. If they don't, document what additional treatment is needed.

### Migration Verification

Grep gate (script or test assertion) that fails if any `--pds-theme-light-*` reference remains in source files after migration. Shell.css and test files included in scope.

---

## Card Signal Model

### Left-Border State Encoding

| Signal | Color | Condition | Precedence |
|--------|-------|-----------|------------|
| DR/AR pending | Orange | Task has pending decision request | 1 (highest) |
| Blocked | Red | `blocked === true`, no DR | 2 |
| Claimed | Purple | `claimed === true` | 3 |
| Deps unmet | Grey | `dep_status === 'blocked'` | 4 |
| Ready | White/Black (theme-aware) | Default — no other condition | 5 (lowest) |

### Data Wiring

- Add `dep_status` to frontend `Task` type (backend already serves it on tasks endpoint)
- Connect `usePendingDRs` data to card rendering (cross-reference task IDs with pending DRs feed)
- Remove `PRIORITY_COLORS` map and emoji badges (⛔, ▶)
- Priority remains invisible; sort-by-priority maintained in columns

### UI States (layered on top, different CSS channels)

- Selected: outline or box-shadow (green from PDS success) — doesn't replace border
- Drag target: column highlight (not card)

---

## Component Specifications

### Card

- Content: title only
- Height: unconstrained (`overflow-wrap: break-word` as guard)
- Left border: 4px, color from signal model
- Background: transparent (no tints)
- Hover: subtle background shift (PDS `state-hover` token)
- Focus: PDS focus ring
- Selected: box-shadow or outline (green from PDS success)
- Data attributes: `data-signal="ready|blocked|claimed|deps-unmet|dr-pending"`, `data-selected`

### Column

- Surface: background color (PDS `background-surface`), border-radius-md, subtle border
- Fixed header: column name + task count badge, stays visible during scroll
- Body: flex with `overflow-y: auto`
- Empty state: fun status-appropriate illustration + status name (text fallback until images exist)
- Drop target feedback: border color change when dragging over valid target
- Minimum width: 200px

### Context Menu

- Surface: PDS `background-surface`, `shadow-md`, `radius-md`
- Items: hover/focus states, keyboard navigation (already implemented)
- Z-index: above cards and columns

### Filter Panel

- Styled with PDS tokens (background, border, spacing)
- No PDS component replacement (kept as native inputs)

### DetailTab / ActivityTab

- Token-updated styling (follows the agnostic rename)
- `styles.ts` → `rowStyleForState()` absorbed into CSS selectors on `[data-state]` attributes, file deleted

---

## Layout & Responsive

### Board Container

- Horizontal scroll (`overflow-x: auto`) when columns exceed available width
- Gap between columns: `--pds-spacing-md` (16px)

### Sidecar

- Collapsible (default open)
- Toggle button to collapse/expand
- CSS transition for smooth collapse

### Column Grid

- `grid-template-columns: repeat(7, minmax(200px, 1fr))` (fixed 7 columns matching topology)
- All columns always rendered; horizontal scroll provides access

### Existing Responsive Breakpoints

Shell.css breakpoints (mobile/tablet/desktop) remain. This brief doesn't redesign responsive layout — just adds horizontal scroll for overflow and sidecar collapse for space.

---

## Empty States

- Fun, status-appropriate illustrated placeholders per column status
- Deliverable: file with image-gen prompts (dimensions, file type, creative direction per status)
- Text fallback ("No {status} tasks") until images are supplied
- User runs prompts, supplies images; implementation renders them

---

## DnD

- Keep active (not removed or deactivated)
- Style minimally: drag opacity reduction on card, drop-target highlight on column

---

## Scope

### In Scope

- 6 per-component CSS files + Shell.css token migration
- `tokens.css` restructure (agnostic names + dark overrides + new non-color tokens)
- Theme bootstrap + `useTheme` hook + toggle button
- Card signal model (data wiring + rendering logic)
- Sidecar collapse toggle
- Column fixed header + scroll body
- Context menu visual treatment
- Empty state placeholder infrastructure + image-gen prompts
- Mechanical migration verification (grep gate)
- PDS component dark-mode compatibility verification

### Out of Scope

- New features (grouping, search, decisions tab redesign)
- PDS component adoption (replacing native inputs with PDS form components)
- Full responsive redesign (column hiding, mobile-specific layouts)
- Card content enrichment (tags, priority labels, metadata beyond title)
- Backend API changes (all data is already served)

---

## Key Decisions

| # | Decision | Choice |
|---|----------|--------|
| D1 | Project type | Existing-feature/refactor |
| D2 | Investment tier | Shared |
| D3 | DnD | Keep, style minimally |
| D4 | Dark theme | Ship both themes now |
| D5 | JSX boundary | Visual changes + card signal model (amended) |
| D6 | Theme toggle | Both auto + manual override |
| D7 | Card height | Release constraint |
| D8 | Column scroll | Fixed header + scrolling body |
| D9 | Empty states | Illustrated placeholders |
| D10 | Card signal model | Operational state border (not priority) |
| D11 | Illustration approach | Image-gen prompts as deliverable |
| D12 | Toggle placement | Status bar, right side |
| D13 | Column min-width | 200px |
| D14 | Signal precedence | Orange > Red > Purple > Grey > White/Black |
| D15 | Responsive overflow | Sidecar collapsible + horizontal scroll |
