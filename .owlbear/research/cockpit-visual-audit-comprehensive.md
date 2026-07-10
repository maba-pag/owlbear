# Cockpit Visual Audit — Comprehensive Synthesis

> Audit date: 2026-05-16
> Method: Live screenshots + code inspection + PDS v4.1.0 docs cross-reference
> Scope: All visible surfaces at 1440px (light + dark), sidecar detail, filter panel, context menu
> Previous audit: `cockpit-visual-audit.md` (May 14)

---

## Executive Summary

The cockpit is structurally functional — data flows, routes work, SSE updates arrive. But visually it scores roughly **10/100**. The root cause is not cherry-picking from the design system. The root cause is **not importing the design system's foundation at all**.

PDS v4 provides a complete CSS variable system (`--p-color-*`, `--p-typescale-*`, `--p-spacing-*`, `--p-radius-*`, `--p-shadow-*`, `--p-font-*`, `--p-duration-*`), a required font-face import (Porsche Next), and a CSS normalize — all via a single `@import '@porsche-design-system/components-react'`. The cockpit imports only `color-scheme.css` (the optional file) and substitutes a hand-rolled `tokens.css` with a non-standard `--pds-*` prefix that partially duplicates PDS but misses key variables. Some referenced variables (`--pds-border-default`, `--pds-border-subtle`, `--pds-text-default`, `--pds-text-subtle`) are defined in neither system, meaning those styles silently resolve to nothing.

Of 73 available PDS React components, the cockpit uses **14 (19%)**. Nine raw `<button>` elements, five raw `<option>` elements, seven raw `<ul>` lists, five raw `<h1-h3>` headings, and six raw `<p-tabs>` / `<p-tabs-item>` web component elements remain in production code where PDS wrappers exist.

---

## 0. Root Cause: PDS Foundation Not Installed

### F-0.1 Missing required PDS stylesheet imports (CRITICAL)

**What PDS v4 requires** (per designsystem.porsche.com/v4/stylesheets/introduction/):
```css
@import '@porsche-design-system/components-react';
```
This single import includes:
- `variables.css` — **REQUIRED** — all `--p-*` CSS custom properties
- `font-face.css` — **REQUIRED** — Porsche Next font family
- `normalize.css` — recommended — CSS reset
- `color-scheme.css` — recommended — light/dark scheme support

**What `main.tsx` imports:**
```ts
import '@porsche-design-system/components-react/global-styles/color-scheme.css'
import './tokens.css'
```

Only the optional color-scheme file. The two required files are missing. This means:
- No PDS CSS variables available (`--p-color-*`, `--p-typescale-*`, `--p-spacing-*`, `--p-radius-*`, etc.)
- Porsche Next font is never loaded — all text renders in fallback system fonts
- No CSS normalize — browser defaults leak through everywhere

### F-0.2 Custom token system duplicates PDS with wrong prefix

`tokens.css` defines `--pds-*` variables. PDS provides `--p-*` variables. The custom system:
- Partially overlaps PDS but uses different names and values
- Misses PDS typography scale entirely (`--p-typescale-2xs` through `--p-typescale-5xl`)
- Misses PDS fluid spacing (`--p-spacing-fluid-*`)
- Misses PDS font weights (`--p-font-weight-normal/semibold/bold`)
- Misses PDS transitions (`--p-ease-*`, `--p-duration-*`)
- References 4 variables that don't exist in either system:
  - `--pds-border-default` (Card.css, Column.css)
  - `--pds-border-subtle` (Card.css)
  - `--pds-text-default` (Card.css)
  - `--pds-text-subtle` (Card.css)

### F-0.3 Tailwind CSS integration not configured

PDS v4 recommends `@porsche-design-system/components-react/tailwindcss` for utility-class integration. This provides classes like `bg-canvas`, `bg-surface`, `rounded-lg`, `gap-fluid-md`, `m-static-lg`, `p-fluid-lg`, `prose-heading-4xl`. Not installed or configured.

### Remediation direction

Replace `tokens.css` + single color-scheme import with the full PDS stylesheet import. Migrate all `--pds-*` references to `--p-*`. Evaluate Tailwind CSS integration for layout utility classes.

---

## 1. Board Layout

### F-1.1 Columns wrap into multi-row grid instead of horizontal scroll (CRITICAL)

**Expected:** `grid-template-columns: repeat(7, minmax(200px, 1fr))` with `overflow-x: auto` (per brief).
**Actual:** Inline style in `KanbanBoard.tsx`: `gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))'`.
`auto-fit` causes columns to wrap — 4 columns on the top row, 3 on the bottom at 1440px. The board looks like a random grid, not a kanban.

### F-1.2 Board layout is entirely inline styles

`KanbanBoard.css` contains ONLY the `.kanban-context-menu` rule. All board layout — the flex container, the grid, the toolbar, the padding — is written as React inline `style={{}}` props (5 occurrences in KanbanBoard.tsx). This:
- Cannot respond to media queries / breakpoints
- Cannot be themed
- Cannot be inspected/debugged normally
- Is inconsistent with the CSS-file approach used elsewhere

### F-1.3 Board toolbar is unstyled

The filter toggle + result count strip is `<div style={{ display: 'flex', ... }}>` with no class, no background, no border — just items floating in space.

### F-1.4 Loading state is a bare `<div>`

```tsx
if (loading) return <div data-testid="loading-indicator">Loading…</div>
```
Should be `PSpinner` centered in the board area.

### F-1.5 Error state is a bare `<div>`

```tsx
if (error) return <div data-testid="error-message">{error}</div>
```
Should be `PInlineNotification` with error state.

---

## 2. Status Bar

### F-2.1 No visible application identity

`<h1 className="shell__product-identity">OwlBear Cockpit</h1>` has `clip: rect(0,0,0,0)` — it's screen-reader-only. No logo, app name, or brand mark is visible. The status bar looks like an anonymous row of secondary buttons.

PDS provides `PWordmark` and `PCrest` for brand identity.

### F-2.2 Traffic-light span is invisible

`<span data-testid="traffic-light" data-health={statusHealth} />` — empty span with no CSS rule targeting `[data-health]`. Zero-width invisible element.

### F-2.3 Task count span is always empty

`<span data-testid="task-count" />` — never populated with text. Dead placeholder.

### F-2.4 All status bar actions look identical

Health badge, Cleanup button, DR indicator, and ThemeToggle all render as `PButton variant="secondary"` or custom `.icon-button`. No visual differentiation between status indicators and action buttons.

PDS provides `PTag` for compact labeled indicators, `PPopover` for disclosures.

### F-2.5 HealthBadge popover is in-flow (expands header)

`HealthBadge.tsx` line 94: `<div style={{ position: 'fixed', ... }}>` — inline-styled popover. Should be `PPopover` or `PFlyout`.

### F-2.6 DRStatusIndicator popover is in-flow (expands header)

`DRStatusIndicator.tsx` line 95: `<div style={{ position: 'fixed', ... }}>` — same pattern. Uses inline `style={{}}` with JS-computed positioning instead of PDS overlay component.

### F-2.7 CleanupPanel confirms inline in status bar

The cleanup confirmation renders inline in the status bar, displacing other items. Should be `PModal`.

### F-2.8 ThemeToggle is a raw `<button>` with custom class

`ThemeToggle.tsx` line 23: `<button className="icon-button">`. Should be `PButtonPure` with icon.

---

## 3. Sidecar (Worst Area)

### F-3.1 Sidecar has zero internal padding

`<div id="shell-sidecar-content">` has no padding. Content touches the sidecar border directly. This is the single most visible "unstyled" indicator.

### F-3.2 Collapse button is a raw `<button>` with custom class

`Shell.tsx` line 229: `<button className="icon-button">`. No icon, text says "Collapse sidecar". Should be `PButtonPure` with arrow icon, pinned to sidecar edge.

### F-3.3 Task heading is unstyled

`<h2>{selectedTaskHeading}</h2>` — raw h2 with no padding, no typography class, no PDS `PHeading` wrapper.

### F-3.4 Tabs use raw web components, not React wrappers

`Shell.tsx` lines 254-410: `<p-tabs ref={tabsRef}>` and `<p-tabs-item ref={(el) => el?.setAttribute('label', 'Detail')}>`.

This is wrong for three reasons:
1. Uses raw custom elements instead of `<PTabs>` / `<PTabsItem>` React wrappers
2. Sets `label` via ref callback instead of the prop
3. The ESLint `no-restricted-syntax` rules don't catch `p-tabs` or `p-tabs-item`

Visual result: tabs render as "DetailActivity" — two text strings with no separator, no underline, no active indicator.

### F-3.5 Decision request list is raw `<ul><li>` with bullet points

`DecisionViewport.tsx` line 49: `<ul>` with `<li>` children containing `<button>` elements with stacked `<PText>` nodes. No CSS file exists for DecisionViewport. Visible: bullet points "•" followed by raw text. No hierarchy between task ID, agent name, body preview.

### F-3.6 Detail metadata has no layout structure

`DetailTab.tsx`: read-only metadata (ID, Status, Priority, Created, Claimed, etc.) renders as plain `<p><strong>Label:</strong> value</p>` tags. No grid, no background, no grouping, no visual hierarchy.

### F-3.7 Raw data shown to user

- Timestamps: `2026-05-14T17:24:27.895979+00:00` — ISO format, not human-readable
- Boolean: `Claimed: false` — raw boolean
- Empty fields: `Claimed at:` with empty value displayed
- Tags: `scope:knowledge,type:ideation,blocked-by-design` — raw comma-separated string, not PDS `PTag` chips

### F-3.8 "Actions" section is unstyled

`<h3>Actions</h3>` followed by `PButton` elements with no card/panel treatment, no divider above, no grouping.

### F-3.9 Edit fields have no section grouping

Title, Priority, Tags, Body edit fields use PDS inputs but have no `PFieldset`, no section headers, no spacing between groups.

### F-3.10 Body text is unstyled

Task body renders as raw markdown output with no margins, no max-width constraint, no typography treatment.

### F-3.11 No dividers between sections

No `PDivider` used anywhere in the sidecar. Metadata, edit fields, actions, and body all run together.

### F-3.12 "History" button floats randomly

The History button appears inside the detail tab area with no visual context for what it does or where it leads.

---

## 4. Cards

### F-4.1 Cards show almost no metadata

Card renders: title (truncated), left-border color signal. Missing from card face:
- Task ID (users can't identify tasks without clicking)
- Priority indicator (critical looks identical to someday)
- Tags (no visual tags at all on card face)
- Blocked/claimed state (color-only, no text/icon — fails color-blind users)

### F-4.2 Card title truncation is too aggressive

`text-overflow: ellipsis` with `white-space: nowrap` means many titles only show 3-4 words when columns are narrow. For a kanban board, titles need to be scannable.

### F-4.3 Card chips are too small (0.72rem = ~11.5px)

ID chip, priority chip, updated-at chip render at 0.72rem — below minimum readable size for scanning.

### F-4.4 Undefined CSS variables in Card.css

`--pds-border-subtle` and `--pds-text-subtle` are referenced but defined nowhere. These silently fall back to initial value (transparent/inherit), meaning borders and text colors are partially broken.

### F-4.5 State cue chips have no icons

"Blocked", "Decision pending", "Dependencies blocked" cue chips are text-only at tiny size. PDS `PIcon` would add visual recognition.

---

## 5. Columns

### F-5.1 Column headers are too small (0.8125rem = 13px)

Section headers for major workflow stages (Backlog, In Progress, Review, etc.) render at 13px — smaller than body text. Should use PDS typography scale.

### F-5.2 Empty states are minimal

"No Todo tasks" and "No Docs tasks" — plain centered text at 0.75rem. No illustration, no encouragement ("Tasks will appear here when..."), no visual treatment.

### F-5.3 Column body gap too tight (4px)

Cards are only 4px apart (`--pds-spacing-xs`). Makes them feel cramped and hard to scan.

### F-5.4 Scrollable column bodies not keyboard-accessible

`axe-core` failure: `.column-body` scrollable regions have no `tabindex="0"` — keyboard users can't scroll column content.

### F-5.5 Status names expose internal API strings

"In-progress" instead of "In Progress", "No in-progress tasks" instead of "Nothing in progress".

---

## 6. Filter Panel

### F-6.1 Filter toggle is a raw `<button>`

`KanbanBoard.tsx`: `<button ref={filterToggleRef} type="button" tabIndex={-1}>Filters</button>` — no className, no CSS, native browser style. Also `tabIndex={-1}` (keyboard-inaccessible).

### F-6.2 `PSelect` uses raw `<option>` children instead of `<PSelectOption>`

`FilterPanel.tsx` line 193, `TaskFieldsEditor.tsx` line 194, `ArchivalModal.tsx` line 283: `<PSelect>` wrapping native `<option>` elements. PDS expects `<PSelectOption>`. This causes console warnings and likely affects dropdown styling.

### F-6.3 Blocked filter is a raw checkbox

No `PSwitch` or `PCheckbox` wrapper. Renders as browser-default checkbox.

### F-6.4 Filter panel pushes board content down

The panel opens inline below the filter button in document flow, pushing the board grid down. Should be a floating overlay (`PFlyout` or positioned panel).

### F-6.5 Filter panel has excessive internal whitespace

Large blank space around the search input while filter controls are minimal. Layout is unstructured.

### F-6.6 No "Clear all filters" button

When filters are active, there's no obvious way to clear them all at once.

---

## 7. Context Menu

### F-7.1 Menu items are unstyled text

Context menu container has PDS surface/shadow/radius, but individual menu items (`Move to docs`, `Move to done`, `Archive`) are plain text divs with no hover states, no focus indicators, no icons.

### F-7.2 "Archive" action not differentiated as destructive

Archive is visually identical to other menu items. Destructive actions should use error color.

---

## 8. Modals & Overlays

### F-8.1 ArchivalModal uses custom overlay, not PDS `PModal`

`ArchivalModal.tsx` line 262: `style={{ position: 'fixed', ... }}` — hand-rolled modal with inline styles. PDS provides `PModal` with proper overlay, focus trap, backdrop, and z-index management.

### F-8.2 ResolveModal uses custom overlay, not PDS `PModal`

`ResolveModal.tsx` line 209: same pattern.

### F-8.3 ConfirmDialog uses custom overlay, not PDS `PModal`

`ConfirmDialog.tsx` line 108: same pattern.

### F-8.4 All overlays use JS-computed positioning

Health popover, DR popover, and modals all compute position in JavaScript and apply via inline styles. PDS overlay components (PModal, PPopover, PFlyout, PSheet) handle this natively.

---

## 9. Dark Mode

### F-9.1 Cards and columns have no visible borders in dark mode

Dark rectangles on dark background — no contrast between card surfaces and column backgrounds.

### F-9.2 Column count badges barely visible in dark mode

`--pds-background-shading` against dark background provides insufficient contrast.

### F-9.3 Status bar buttons maintain light-mode border style

Buttons don't adapt their border treatment to dark mode.

### F-9.4 Sidecar has no border differentiation in dark mode

The sidecar panel blends into the board area.

---

## 10. Typography

### F-10.1 No PDS type scale in use

The cockpit defines custom font sizes (0.72rem, 0.75rem, 0.8125rem, etc.) that don't correspond to any PDS typescale step. PDS provides `--p-typescale-2xs` (0.75rem) through `--p-typescale-5xl` (clamp).

### F-10.2 No heading hierarchy

`<h1>` is screen-reader-only, `<h2>` is raw in sidecar, `<h3>` is raw for "Actions". No `PHeading` with `tag` and `size` props to create a deliberate scale.

### F-10.3 PText used without size/weight props

Where `PText` is used, it's typically `<PText>{content}</PText>` without `size`, `weight`, or `color` props that would create hierarchy.

### F-10.4 No Porsche Next font loaded

Without `font-face.css`, all text renders in system fallback fonts. The Porsche brand typography is absent.

---

## 11. Inline Styles Audit

15 inline `style={{}}` occurrences in production code:

| File | Count | Purpose |
|------|-------|---------|
| KanbanBoard.tsx | 5 | Board layout, toolbar, filter offscreen, grid, context menu |
| ConfirmDialog.tsx | 1 | Modal overlay |
| HealthBadge.tsx | 1 | Popover positioning |
| CleanupPanel.tsx | 1 | Popover positioning |
| DRStatusIndicator.tsx | 1 | Popover positioning |
| ResolveModal.tsx | 1 | Modal overlay |
| ArchivalModal.tsx | 1 | Modal overlay |
| HistorySubtab.tsx | 1 | Cursor pointer |
| ErrorBoundary.tsx | 3 | Error UI layout |

All of these bypass the design system and cannot respond to theme changes or breakpoints.

---

## 12. Raw HTML vs PDS Component Audit

| Raw element | Count | PDS replacement |
|------------|-------|-----------------|
| `<button>` | 9 | `PButton`, `PButtonPure` |
| `<option>` (inside PSelect) | 5 | `PSelectOption` |
| `<ul>` | 7 | `PTextList` + `PTextListItem`, or custom styled list |
| `<h1>/<h2>/<h3>` | 5 | `PHeading` |
| `<p-tabs>/<p-tabs-item>` (raw WC) | 6 | `PTabs` / `PTabsItem` (React) |
| `<input>` (in ResolveModal) | 3 | `PInputText`, `PCheckbox` |

---

## 13. PDS Component Adoption Matrix

**Used in production (14/73 = 19%):**
PBanner, PButton, PHeading (2 files), PInlineNotification (2 files), PInputSearch (1), PInputText (2), PMultiSelect (1), PMultiSelectOption (1), PSelect (3), PSpinner (2), PTag (1), PText (scattered), PTextarea (2), PorscheDesignSystemProvider

**Applicable but not used:**
| PDS Component | Where it should be used |
|---------------|------------------------|
| PButtonPure | Nav rail, sidecar collapse, icon-only actions |
| PCheckbox | Filter panel blocked toggle |
| PDivider | Sidecar section separators, everywhere |
| PFieldset | Form groups in sidecar edit, filter panel |
| PFlyout | Filter panel (floating), health/DR popovers |
| PHeading | All headings (replace raw h1-h3) |
| PIcon | Card state cues, context menu items, nav |
| PModal | ArchivalModal, ResolveModal, ConfirmDialog, CleanupPanel confirm |
| PPopover | Health badge, DR indicator |
| PScroller | Board horizontal scroll container |
| PSelectOption | All PSelect children (replace raw option) |
| PSheet | Sidecar on mobile/tablet |
| PSwitch | Filter panel blocked toggle |
| PTable | Detail metadata display (structured key-value) |
| PTabsItem | Sidecar tabs (replace raw p-tabs-item) |
| PTabs | Sidecar tabs (replace raw p-tabs) |
| PTextList/PTextListItem | DR list, health issues list, repair results |
| PToast | Transient feedback (edit saved, move completed) |
| PWordmark | Status bar brand identity |

---

## 14. ESLint Config Review

The user's new `no-restricted-syntax` rules ban 5 raw PDS custom elements:
- `p-select` ✓
- `p-button` ✓
- `p-input-search` ✓
- `p-input-text` ✓
- `p-tag` ✓

**Missing from the ban list:**
- `p-tabs` — actively used in Shell.tsx production code
- `p-tabs-item` — actively used in Shell.tsx production code
- `p-text` — could appear
- `p-heading` — could appear
- `p-spinner` — could appear
- `p-banner` — could appear
- `p-inline-notification` — could appear
- `p-textarea` — could appear
- `p-multi-select` — could appear
- `p-multi-select-option` — could appear

**Recommendation:** Ban ALL PDS custom elements via a single pattern or maintain a comprehensive list. The current list will let new raw elements slip through.

Also missing: a rule banning raw `<option>` inside `<PSelect>` (should use `<PSelectOption>`).

---

## 15. Summary: What Must Change

### Tier 1: Foundation (fixes everything downstream)
1. Import full PDS stylesheet (`@import '@porsche-design-system/components-react'`)
2. Remove custom `tokens.css` or migrate to PDS `--p-*` variables
3. Load Porsche Next font via PDS `font-face.css`
4. Add PDS CSS normalize
5. Evaluate and configure Tailwind CSS integration for layout utility classes

### Tier 2: Component Migration (biggest visual impact)
6. Replace raw `<p-tabs>`/`<p-tabs-item>` with `<PTabs>`/`<PTabsItem>`
7. Replace raw `<option>` with `<PSelectOption>` in all `<PSelect>` instances
8. Replace raw `<button>` elements with `PButton`/`PButtonPure`
9. Replace raw `<h1-h3>` with `PHeading`
10. Replace raw `<ul>` lists with `PTextList`/`PTextListItem` or styled alternatives
11. Replace raw `<input>` elements with PDS input components
12. Replace custom modal overlays with `PModal`
13. Replace custom popovers with `PPopover`/`PFlyout`

### Tier 3: Layout Redesign (composition)
14. Fix board grid: `repeat(7, ...)` with `overflow-x: auto` or `PScroller`
15. Move all inline styles to CSS files
16. Design sidecar interior: padding, sections, dividers, typography hierarchy
17. Redesign filter panel as floating overlay with proper form layout
18. Add card metadata: ID, priority badge, tags, blocked icon
19. Improve column headers, empty states, spacing

### Tier 4: Polish & Quality Gates
20. Format timestamps as human-readable
21. Hide empty/false metadata fields
22. Add dark mode border contrast
23. Make scrollable column bodies keyboard-accessible
24. Expand ESLint ban list to all PDS custom elements
25. Add screenshot regression tests for visual gates

---

## Decision Gates — RESOLVED

All gates decided 2026-05-16 during audit walkthrough.

| # | Gate | Decision |
|---|------|----------|
| 1 | **Styling Architecture** | PDS full stylesheet import + Tailwind CSS with PDS theme (`@porsche-design-system/components-react/tailwindcss`). PDS components for interactive elements, Tailwind utilities for layout/spacing/typography, custom CSS only for complex unique styling. |
| 2 | **tokens.css fate** | Delete `tokens.css`. Create minimal `custom-tokens.css` for app-specific values only (signal colors like `--signal-claimed`). All standard tokens from PDS via Tailwind theme or `--p-*` variables. |
| 3 | **Sidecar architecture** | Inspector panel with collapsible PAccordion sections. Sections: metadata, edit fields, dependencies, body preview, actions. DR list above tabs in compact section. Collapse button as icon-only PButtonPure. |
| 4 | **Mobile contract** | Desktop-only with controlled message. `min-width: 1024px` on board area, polite message below breakpoint. Zero responsive work. |
| 5 | **Visual regression gates** | Baselines after redesign. Complete the visual redesign first, then take Playwright screenshot baselines of the finished product. |
| 6 | **ESLint raw element bans** | Explicit ban list for known PDS v4 components (error level) + `p-*` regex catch-all (warning level). On version bumps, promote new warnings to error list. |

---

## Appendix: Screenshot Evidence

All screenshots in `.owlbear/scratch/`:
- `audit-board-1440.png` — Full board at 1440px (columns wrapping visible)
- `audit-detail-panel.png` — Board with task selected (sidecar visible)
- `audit-sidecar-detail.png` — Isolated sidecar (zero padding, raw tabs visible)
- `audit-sidecar-scrolled-dark.png` — Sidecar scrolled in dark mode
- `audit-context-menu.png` — Context menu open
- `audit-dark-actual.png` — Dark mode (border contrast issues visible)
- `audit-filter-panel.png` — Filter panel open (whitespace, raw toggle visible)
