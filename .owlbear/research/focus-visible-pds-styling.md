# Focus-Visible Rings — PDS Focus Styling

> **Owning task:** #1626 — P3-06: Focus-visible rings — PDS focus styling
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1626 requires PDS-compliant `:focus-visible` styling on all interactive elements. Two questions:
1. Which elements need focus styling vs. which handle it themselves?
2. What is the PDS-canonical focus token and pattern?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | PDS v4 Tailwind Focus examples | designsystem.porsche.com/v4/tailwindcss/focus/examples/ | 0.95 |
| S2 | PDS GitHub TailwindFocusVisible.tsx | porsche-design-system/packages/styles/.../TailwindFocusVisible.tsx | 0.95 |
| S3 | PDS GitHub getFocusVisibleStyle.ts | porsche-design-system/packages/styles/.../getFocusVisibleStyle.ts | 0.90 |
| S4 | PDS GitHub common-styles.ts (getFocusBaseStyles) | porsche-design-system/packages/components/.../common-styles.ts | 0.90 |
| S5 | PDS Storefront AGENTS.md (focus pattern) | porsche-design-system/packages/storefront/AGENTS.md | 0.90 |
| S6 | PDS Tailwind @theme (local: node_modules/.../tailwindcss/index.css) | Local package | 0.85 |
| S7 | PDS SCSS focus-visible mixin | porsche-design-system/packages/styles/projects/scss/src/_focus.scss | 0.80 |

## 3. Analysis

### PDS v4 Canonical Focus Pattern

All PDS styling APIs converge on the same values (S1–S7):

```css
:focus-visible {
  outline: 2px solid var(--color-focus);   /* #1a44ea both themes */
  outline-offset: 2px;
}
```

| API | Invocation | Resolves to |
|-----|-----------|-------------|
| Tailwind | `focus-visible:outline outline-focus outline-offset-2` | `outline-color: var(--color-focus)` |
| SCSS | `@include pds.focus-visible($offset: 2px)` | `outline: 2px solid $color-focus` |
| Emotion/VE | `getFocusVisibleStyle({ offset: '2px' })` | `outline: 2px solid var(--_color-focus, #1a44ea)` |
| Components | `getFocusBaseStyles(2)` | `outline: 2px solid var(--p-color-focus)` |
| Plain CSS (Storefront AGENTS.md) | `outline: 2px solid var(--p-color-focus)` | Same color |

### Element Classification

| Category | Elements | Focus owner | Action needed |
|----------|----------|-------------|---------------|
| PDS components | PButton, PInputText, PInputSearch, PSelect, PMultiSelect, PTextarea, p-tabs, p-sheet | Shadow DOM (self-managed) | None |
| Card | `div[role="button"]` | Card.css (existing rule) | Update token + offset |
| Shell buttons | `.icon-button` (ThemeToggle, Shell) | Missing | Add rule |
| HealthBadge | `button` | Missing | Add rule |
| ErrorBoundary | `button` (inline styles) | Missing | Add rule |
| Context menu | `div[role="menuitem"]` | Missing | Add rule |
| Radio inputs | `input[type="radio"]` in ResolveModal | Missing | Add rule |

### Current State vs. Target

| Element | Current | Target |
|---------|---------|--------|
| `.card` | `outline: 2px solid var(--pds-state-focus); offset: 1px` | `outline: 2px solid var(--color-focus); offset: 2px` |
| `.icon-button` | No `:focus-visible` | PDS focus pattern |
| HealthBadge `button` | No `:focus-visible` | PDS focus pattern |
| ErrorBoundary `button` | No `:focus-visible` | PDS focus pattern |
| `[role="menuitem"]` | No `:focus-visible` | PDS focus pattern |
| `input[type="radio"]` | Browser default | PDS focus pattern |

### Implementation Approach Trade-offs

| Approach | Mechanism | Pro | Con | Score |
|----------|-----------|-----|-----|-------|
| A: Global CSS | Single rule targeting `button, [role="button"], [role="menuitem"], input, a` selectors in `tokens.css` | DRY; covers new elements automatically | Broad selector may need refinement | **0.82** |
| B: Per-component CSS | `:focus-visible` in each component's `.css` file | Precise control; no side effects | 5+ files to edit; DRY violation | 0.65 |
| C: Tailwind classes | `focus-visible:outline outline-focus outline-offset-2` on each TSX element | PDS-prescribed Tailwind method | TSX changes; verbose; misses inline-style elements | 0.60 |

### Token Choice

Our `--pds-state-focus` in `tokens.css` is a custom property with the same value as PDS `--color-focus`. AC2 requires "PDS focus tokens (not custom ring styles)." The canonical PDS Tailwind token is `--color-focus` (provided by `@theme` block in the imported PDS Tailwind CSS). Implementation should use `var(--color-focus)`.

Card.css should migrate from `var(--pds-state-focus)` → `var(--color-focus)` and offset from `1px` → `2px`.

## 4. Recommendation (confidence: 0.82)

**Approach A: Global CSS rule** using `var(--color-focus)` from PDS Tailwind theme.

Add to `tokens.css` (or a dedicated `focus.css` imported from `main.tsx`):
```css
button:focus-visible,
[role="button"]:focus-visible,
[role="menuitem"]:focus-visible,
input:focus-visible,
a:focus-visible {
  outline: 2px solid var(--color-focus);
  outline-offset: 2px;
}
```

Update Card.css `.card:focus-visible` to use `var(--color-focus)` and `offset: 2px` for consistency.

PDS components are unaffected — Shadow DOM encapsulates their own focus styling.

Challenge: skipped (T1 autonomous — CSS-only change, no arch/security/breaking impact).

### Playwright test strategy

Tab through each interactive element type; assert `outline-style !== 'none'` and `outline-color` resolves to `rgb(26, 68, 234)` (PDS focus blue).

## 5. Follow-up Tasks

Task #1626 itself is the implementation task. No additional follow-up tasks needed — this is a direct T1 implementation.
