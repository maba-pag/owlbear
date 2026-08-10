# Research Notes — Board Visual Design

## Verified Findings

### F1. PDS v4 token structure (not simple themeLight/themeDark swap)

PDS v4.1.0 does NOT export a single `themeDark` object. Instead it provides:
- **Light-suffixed tokens:** `colorErrorLight`, `colorSurfaceLight`, etc.
- **Dark-suffixed tokens:** `colorErrorDark`, `colorSurfaceDark`, etc.
- **Auto tokens (no suffix):** `colorError`, `colorSurface`, etc. — these automatically respond to `prefers-color-scheme` at the browser level.

Available token categories: color, breakpoint, border-radius, font, spacing (static + fluid), motion (duration + ease), shadow, gradient.

### F2. Current tokens.css is light-only, manually extracted

`tokens.css` contains 17 hand-extracted CSS custom properties from `themeLight`, all prefixed `--pds-theme-light-*`. These are hardcoded light values (not auto-responsive).

### F3. Inline styles in board components

- **KanbanBoard.tsx:** Flex container, grid columns (`repeat(auto-fit, minmax(80px, 1fr))`), filter toolbar flex, context menu fixed positioning.
- **Column.tsx:** Minimal — only `overflowY` conditional and `minWidth: 0`.
- **Card.tsx:** Most complex — conditional `border`, `borderLeft` (priority color), `backgroundColor` (selection), fixed heights, flexbox, padding, cursor. Uses `--pds-theme-light-*` vars directly in inline styles.

### F4. Shell.css uses light tokens directly

Shell.css references `var(--pds-theme-light-background-base)`, `var(--pds-theme-light-background-surface)`, `var(--pds-theme-light-contrast-low)`, `var(--pds-theme-light-primary)`. Dark theme must address Shell.css too.

### F5. PDS components are CSS-var driven (no theme prop)

`PorscheDesignSystemProvider` wraps the app. PDS React components (`PButton`, `PBanner`, `p-tabs`) are Web Component wrappers that respond to CSS custom properties. No theme prop exists — all theming is CSS-based.

### F6. Responsive breakpoints already exist

Shell.css: mobile ≤767px, tablet 768-1023px, desktop ≥1024px. PDS breakpoint tokens available: xs(480), sm(768), md(1024), lg(1440), xl(1920), 2xl(2560). Board's `repeat(auto-fit, minmax(80px, 1fr))` grid adapts columns automatically.

### F7. Card priority colors already use PDS vars

```ts
const PRIORITY_COLORS: Record<string, string> = {
  critical: 'var(--pds-theme-light-notification-error)',
  needed: 'var(--pds-theme-light-notification-warning)',
  ...
}
```

These reference the light tokens directly — for dark mode they need to reference theme-agnostic vars.

---

## Candidate Implications

### I1. Theme-agnostic strategy: rename existing vars

The simplest dark-mode architecture: rename the 17 existing `--pds-theme-light-*` vars in `tokens.css` to theme-agnostic names (e.g., `--pds-background-base`), set light values by default, override with dark values in a `[data-theme="dark"]` or `@media (prefers-color-scheme: dark)` block. All consumers (Shell.css, Card.tsx, future CSS) reference the agnostic names. This IS the alias layer — it's just the existing file restructured.

### I2. PDS auto-responsive tokens might simplify further

PDS's no-suffix tokens (e.g., `colorError`) auto-respond to `prefers-color-scheme`. If we generate tokens.css from those instead of from `themeLight`, the browser handles theme switching natively. A manual toggle would still need a class/attribute override for users who want dark-in-daylight.

### I3. Card.tsx inline style extraction is the hardest single task

Card has conditional styles (selected, priority, drag state) inline. Extracting to CSS requires:
- Class-based state selectors: `[data-selected="true"]`, `[data-priority="critical"]`
- The priority color map moves into CSS custom properties or per-priority classes
- Selection highlight becomes a class rule rather than ternary logic

### I4. Context menu needs elevation (shadow + z-index)

Currently just `position: fixed` with no visual treatment. Needs: background surface, border-radius, shadow (PDS shadow tokens available), proper z-index stacking.

### I5. Column empty states need design thought

Currently just text. Options: subdued message with icon, dashed border invite, or PDS-style empty illustration. This is a design decision for the Brief.

---

## Open Research Questions (for Phase 2)

### Q1. Auto-responsive tokens vs manual toggle?

Should we use PDS's auto tokens (`prefers-color-scheme`), a manual toggle (`data-theme` attribute), or both (auto by default + manual override)? Trade-off: auto is simpler but users can't override. Manual gives control but needs UI (toggle button) and persistence (localStorage).

### Q2. PDS shadow/elevation token values?

What are the actual shadow token values? Are there multiple elevation levels (card, context menu, modal)?

### Q3. PDS spacing scale specifics?

What are the static/fluid spacing values available? Do they map to 4px/8px/16px grid?

### Q4. PDS border-radius scale?

What are xs through 4xl radius values? Which is appropriate for cards vs columns vs context menu?

### Q5. Card height constraint

Card currently has `minHeight: 48px`, `maxHeight: 56px`. Is this intentional for density, or should cards grow with content?

### Q6. Column scroll behavior

Column has conditional `overflowY`. When columns have many cards, what's the scroll experience? Does the column header stay fixed?
