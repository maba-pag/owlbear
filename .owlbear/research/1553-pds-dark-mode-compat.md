# PDS Component Dark-Mode Compatibility

> **Owning task:** #1553 — P4-03: PDS component dark-mode compatibility verification
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

The Cockpit board's theme system uses `data-theme="dark"|"light"` on `<html>` with custom CSS variables in `tokens.css`. The question: do PDS v4 web components respond to this attribute and switch their internal styling?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | PDS v4 Migration Guide | designsystem.porsche.com/v4/news/migration-guide/porsche-design-system/ | 1.0 |
| 2 | PDS v4 Theme docs | designsystem.porsche.com/v4/must-know/theme/ | 1.0 |
| 3 | PDS v4 Color Scheme stylesheet | designsystem.porsche.com/v4/stylesheets/color-scheme/introduction/ | 0.9 |
| 4 | PDS GitHub — color-scheme.css build | github.com/porsche-design-system/.../buildColorSchemeCss.ts | 0.9 |
| 5 | PDS GitHub Issue #1185 (Provider theme prop) | github.com/.../issues/1185 | 0.7 |
| 6 | PDS CHANGELOG v4.0.0-beta.0 | github.com/.../CHANGELOG.md#L765 | 0.8 |
| 7 | Cockpit codebase: tokens.css, useTheme.ts, theme-bootstrap.js, main.tsx, App.tsx | local | 1.0 |

## 3. Analysis

### Finding 1: PDS v4 does NOT use `data-theme`

PDS v4 replaced the per-component `theme` prop with CSS `color-scheme` property + `light-dark()` CSS function. Components read the inherited `color-scheme` value, not any `data-*` attribute.

Theme control in PDS v4 is via `.scheme-*` CSS classes on any ancestor:
- `.scheme-light` → `color-scheme: light`
- `.scheme-dark` → `color-scheme: dark`
- `.scheme-light-dark` → `color-scheme: light dark` (follows OS)

**Evidence:** v4 migration guide explicitly removes `theme` prop from Provider and all components; CHANGELOG v4.0.0-beta.0 confirms removal.

### Finding 2: Our Cockpit theming is disconnected from PDS

| Layer | Mechanism | Responds to `data-theme`? |
|-------|-----------|--------------------------|
| Custom tokens (`tokens.css`) | `[data-theme="dark"]` selector | Yes |
| Custom CSS (Shell.css, Card.css) | `var(--pds-*)` custom properties | Yes (via tokens) |
| PDS web components (shadow DOM) | `color-scheme` CSS property + `light-dark()` | **No** |

Our `theme-bootstrap.js` sets `document.documentElement.dataset.theme` only. Our `useTheme` hook sets `document.documentElement.dataset.theme` only. Neither sets `color-scheme` or `.scheme-*` classes.

**Result:** PDS components currently render in light mode regardless of `data-theme` value.

### Finding 3: Missing PDS v4 mandatory global styles

PDS v4 requires importing `@porsche-design-system/components-react` CSS (global styles including `color-scheme.css`). Our Cockpit does not import this — we only call `load()` from `components-js` and use `PorscheDesignSystemProvider`. The `color-scheme.css` polyfill and utility classes are therefore absent.

### Component inventory (14 PDS components in Cockpit)

| Component | Usage count | Will respond to `.scheme-*`? |
|-----------|------------|------------------------------|
| `PButton` | 14+ files | Yes — once bridge is added |
| `PText` | 6 files | Yes |
| `PSelect` | 3 files | Yes |
| `PInputText` | 2 files | Yes |
| `PTextarea` | 2 files | Yes |
| `PSpinner` | 2 files | Yes |
| `PMultiSelect` | 1 file | Yes |
| `PIcon` | 1 file | Yes |
| `PHeading` | 1 file | Yes |
| `PInlineNotification` | 2 files | Yes |
| `p-tabs` (native) | 1 file | Yes |
| `p-tabs-item` (native) | 1 file | Yes |
| `p-banner` (via PBanner) | 1 file | Yes |
| `PMultiSelectOption` | 1 file | Yes |

**All 14 components** will correctly respond to `color-scheme` changes once the bridge is implemented. No component needs individual CSS treatment — PDS v4 handles theming uniformly via `color-scheme` inheritance.

## 4. Recommendation

**Bridge approach** (confidence: 0.85): Synchronize `data-theme` and `color-scheme` by having `theme-bootstrap.js` and `useTheme` also set the `.scheme-*` class on `<html>`. Import PDS v4 global styles CSS.

| Option | Pros | Cons | Confidence |
|--------|------|------|------------|
| A: Bridge (set both `data-theme` + `.scheme-*`) | Minimal change; both custom tokens and PDS components work; backwards-compatible | Two parallel mechanisms on `<html>` | 0.85 |
| B: Full migration to `color-scheme` | Single mechanism; aligns 100% with PDS v4 | Larger change: rewrite tokens.css to use `light-dark()`, update all `[data-theme]` selectors, update tests | 0.60 |
| C: No action (status quo) | Zero effort | PDS components stuck in light mode during dark theme | 0.00 |

**Recommended: Option A.** Two changes needed:
1. Import PDS v4 global styles (`@import '@porsche-design-system/components-react'` in a CSS entry point)
2. In `theme-bootstrap.js` and `useTheme.ts`: add/remove `.scheme-dark`/`.scheme-light` class alongside `data-theme`

Challenge: skipped (T1 — config/integration fix, no architecture change).

## 5. Follow-up Tasks

1. **Import PDS v4 global styles + add scheme class bridge** — update `theme-bootstrap.js`, `useTheme.ts`, and add CSS import. Single implementation task.
2. **Verify PDS components render correctly in dark mode** — visual/behavioral test after bridge is implemented.
