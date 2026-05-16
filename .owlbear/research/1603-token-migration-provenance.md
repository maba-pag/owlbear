# Token Migration Provenance Map & Strategy

> **Owning task:** #1603 — P1-03: Atomic token migration — delete tokens.css + migrate references
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

`tokens.css` re-declares PDS v4 values under a `--pds-*` prefix, manually duplicating light/dark overrides that PDS provides natively via `color-scheme.css`. This creates maintenance risk and bypasses PDS's built-in `.scheme-dark`/`.scheme-light` theming mechanism (already integrated by `useTheme` hook). The question: can every `--pds-*` reference be replaced with a native PDS `--p-*` token, and what needs custom treatment?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `color-scheme.css` (PDS v4 `global-styles/`) | Primary — 33 `--p-color-*` tokens with light/dark variants | 1.0 |
| `variables.css` (PDS v4 `global-styles/`) | Primary — spacing, radius, shadow, motion, typography tokens | 1.0 |
| `tokens.css` (authored) | Primary — 33 `--pds-*` definitions + dark overrides | 1.0 |
| 8 consumer CSS/TSX files | Primary — actual token usage inventory | 1.0 |
| `useTheme.ts` + `theme-bootstrap.js` | Primary — `.scheme-dark`/`.scheme-light` class mechanism | 0.9 |
| PDS v4 design system docs (designsystem.porsche.com) | Secondary — token naming conventions | 0.8 |

## 3. Analysis — Provenance Map

### 3a. Color Tokens (20 defined → 16 consumed, 4 dead)

| tokens.css Token | PDS v4 Equivalent | Consumed? | Classification |
|---|---|---|---|
| `--pds-primary` | `--p-color-primary` | Shell (alias) | PDS equiv |
| `--pds-background-base` | `--p-color-canvas` | Shell, Card | PDS equiv |
| `--pds-background-surface` | `--p-color-surface` | Shell, Card, Column, FilterPanel, KanbanBoard | PDS equiv |
| `--pds-background-shading` | `--p-color-backdrop` | Column | PDS equiv |
| `--pds-contrast-low` | `--p-color-contrast-low` | Shell, Column | PDS equiv |
| `--pds-contrast-medium` | `--p-color-contrast-medium` | Card, ErrorBoundary.tsx | PDS equiv |
| `--pds-contrast-high` | `--p-color-contrast-high` | **not consumed** | dead-delete |
| `--pds-notification-success` | `--p-color-success` | Card | PDS equiv |
| `--pds-notification-success-soft` | `--p-color-success-frosted` | Card | PDS equiv |
| `--pds-notification-warning` | `--p-color-warning` | Card, SessionRows | PDS equiv |
| `--pds-notification-warning-soft` | `--p-color-warning-frosted` | SessionRows | PDS equiv |
| `--pds-notification-error` | `--p-color-error` | Card, SessionRows | PDS equiv |
| `--pds-notification-error-soft` | `--p-color-error-frosted` | SessionRows | PDS equiv |
| `--pds-notification-info` | `--p-color-info` | **not consumed** | dead-delete |
| `--pds-notification-info-soft` | `--p-color-info-frosted` | **not consumed** | dead-delete |
| `--pds-signal-claimed` | — (no PDS purple) | Card | **custom-keep** |
| `--pds-state-hover` | `--p-color-frosted` | Shell, Card, Column | PDS equiv |
| `--pds-state-active` | `--p-color-frosted` | **not consumed** | dead-delete |
| `--pds-state-focus` | `--p-color-focus` | Card | PDS equiv |
| `--pds-state-disabled` | `--p-color-frosted-strong` | **not consumed** | dead-delete |

### 3b. Non-Color Tokens (13 defined → 7 consumed, 6 dead)

| tokens.css Token | PDS v4 Equivalent | Consumed? | Classification |
|---|---|---|---|
| `--pds-shadow-sm` | `--p-shadow-sm` | Card, Column | PDS equiv |
| `--pds-shadow-md` | `--p-shadow-md` | KanbanBoard | PDS equiv |
| `--pds-shadow-lg` | `--p-shadow-lg` | **not consumed** | dead-delete |
| `--pds-radius-sm` | `--p-radius-sm` | Card, Column | PDS equiv |
| `--pds-radius-md` | `--p-radius-md` | Column, KanbanBoard | PDS equiv |
| `--pds-radius-lg` | `--p-radius-lg` | **not consumed** | dead-delete |
| `--pds-radius-xl` | `--p-radius-xl` | **not consumed** | dead-delete |
| `--pds-spacing-xs` | `--p-spacing-static-xs` | Card, Column | PDS equiv |
| `--pds-spacing-sm` | `--p-spacing-static-sm` | Card, Column | PDS equiv |
| `--pds-spacing-md` | `--p-spacing-static-md` | FilterPanel, KanbanBoard.tsx | PDS equiv |
| `--pds-spacing-lg` | `--p-spacing-static-lg` | **not consumed** | dead-delete |
| `--pds-spacing-xl` | `--p-spacing-static-xl` | **not consumed** | dead-delete |
| `--pds-spacing-2xl` | `--p-spacing-static-2xl` | **not consumed** | dead-delete |

### 3c. Semantic Aliases & Undeclared Tokens (6 total)

| Token | Defined In | Used In | Replacement |
|---|---|---|---|
| `--pds-border-default` | Shell.css (alias → contrast-low) | Shell, FilterPanel, SessionRows | `--p-color-contrast-low` |
| `--pds-text-default` | Shell.css (alias → primary) | Shell | `--p-color-primary` |
| `--pds-border-subtle` | **never declared** | Card | `--p-color-contrast-low` |
| `--pds-text-subtle` | **never declared** | Card | `--p-color-contrast-medium` |
| `--pds-grid-gap` | **never declared** (fallback 8px) | Shell | `--p-spacing-static-sm` (8px) |
| `--pds-grid-margin` | **never declared** (fallback 16px) | Shell | `--p-spacing-static-md` (16px) |

### 3d. Summary

| Classification | Count | Action |
|---|---|---|
| PDS equivalent | 23 consumed | Replace `--pds-*` → `--p-*` in consumer files |
| Semantic alias | 4 | Inline the PDS token at usage site, remove alias declarations |
| Layout pass-through | 2 | Replace with PDS spacing tokens |
| Custom-keep | 1 (`signal-claimed`) | Move to `custom-tokens.css` with `--custom-` prefix |
| Dead (defined, never consumed) | 11 | Deleted with tokens.css |

## 4. Recommendation (confidence: 0.88)

**Proceed with atomic migration.** Every consumed `--pds-*` token has an exact PDS v4 equivalent with matching values. No visual regressions expected for any PDS-equivalent token.

**custom-tokens.css** should contain only `--custom-signal-claimed` using `light-dark()`:
```css
:root { --custom-signal-claimed: light-dark(hsl(270 58% 46%), hsl(270 80% 70%)); }
```

**PDS global-styles import** relocates from tokens.css to `main.tsx` (direct CSS import) or the new `custom-tokens.css`.

**Dark mode:** Fully handled by PDS's `.scheme-dark`/`.scheme-light` class mechanism + `useTheme` hook. Manual `[data-theme="dark"]` and `@media prefers-color-scheme` blocks in tokens.css are eliminated by deletion.

**Risk:** `--pds-border-subtle` and `--pds-text-subtle` are consumed in Card.css but never declared anywhere — they currently resolve to nothing. Replacing with actual PDS tokens is a visual *improvement* (borders and text colors will appear). Builder should verify Card rendering post-migration.

Challenge: FALLBACK — challenger subagent unavailable. Risk mitigated by value-level verification against PDS source CSS.

## 5. Follow-up Tasks

- #1597 (Token provenance map) — this research supersedes its scope; recommend archive as `duplicate` with ref to #1603.
- No new tasks needed — #1603 already has complete AC for the implementation.

### Test Impact (for builder reference)

| Test File | Action | Rationale |
|---|---|---|
| `TokenArchitecture_1543.test.ts` | **Retire** | Validates tokens.css structure (deleted) |
| `TokenArchitecture_1535.test.ts` | **Retire** | Same — earlier iteration |
| `BoardVisualDesign.test.tsx` | **Update** | Remove `[data-theme="dark"]` assertions; update token names |
| `ShellSecondaryCSS_1542.test.tsx` | **Update** | `--pds-*` → `--p-*` in regex patterns |
| `ShellSecondaryCSS_1550.test.tsx` | **Update** | Same |
| `Card.css.test.ts` | **Update** | `--pds-*` → `--p-*` in assertions |
| `ColumnCSS_1547.test.ts` | **Update** | `--pds-*` → `--p-*` in assertions |
| `PdsColorSchemeBridge_1555.test.ts` | **Update** | AC-1 (tokens.css import) → rework for custom-tokens.css; AC-7 constraint guard survives |
| `ResponsiveLayout_1391.test.tsx` | **Update** | `--pds-grid-gap/margin` → `--p-spacing-static-*` |
| `ThemeLightTokenScan_1552.test.ts` | **Keep** | Checks `--pds-theme-light-*` (different prefix, unaffected) |
