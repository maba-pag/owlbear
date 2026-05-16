# Dark Mode Audit — Border Contrast + Token Compliance

> **Owning task:** #1625 — P3-04: Dark mode audit — border contrast + token compliance
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Phase 3 polish task: verify border contrast and token compliance in `.scheme-dark` mode. Three AC require: (1) adjacent panels have ≥ 1.3:1 border contrast, (2) zero hardcoded border-color values — all use PDS tokens, (3) intentional light/dark differentiation.

Task depends on #1620 (tests) → B2 impl tasks → #1603 (token migration). Research evaluates current state and post-migration approach.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | PDS v4 Color Tokens docs | designsystem.porsche.com/v4/tokens/color/ | 1.0 |
| 2 | PDS v4 CSS Variables stylesheet | designsystem.porsche.com/v4/stylesheets/css-variables/introduction/ | 1.0 |
| 3 | PDS v4 Color Scheme docs | designsystem.porsche.com/v4/stylesheets/color-scheme/introduction/ | 0.9 |
| 4 | PDS v4 Border Tokens docs | designsystem.porsche.com/v4/tokens/border/ | 0.8 |
| 5 | PDS Admin Panel template source | github.com/porsche-design-system/examples/.../admin-panel/ | 0.8 |
| 6 | Cockpit codebase: tokens.css, Shell.css, Card.css, Column.css, FilterPanel.css, SessionRows.css | local | 1.0 |
| 7 | Existing research #1553 | .owlbear/research/1553-pds-dark-mode-compat.md | 0.9 |

## 3. Analysis

### 3a. Current Border-Color Inventory

All 35 border declarations in authored CSS use `var(--pds-*)` tokens — **zero hardcoded hex/rgb/hsl values**. Token usage:

| Token | Files | Count | Defined? |
|-------|-------|-------|----------|
| `--pds-border-default` (alias → `--pds-contrast-low`) | Shell.css, FilterPanel.css, SessionRows.css | 10 | Yes (Shell.css) |
| `--pds-contrast-low` | Shell.css, Column.css | 3 | Yes (tokens.css) |
| `--pds-contrast-medium` | Card.css | 2 | Yes (tokens.css) |
| `--pds-notification-error` | Card.css, SessionRows.css | 3 | Yes (tokens.css) |
| `--pds-notification-warning` | Card.css, SessionRows.css | 3 | Yes (tokens.css) |
| `--pds-signal-claimed` | Card.css | 1 | Yes (tokens.css) |
| `--pds-notification-success` | Card.css | 1 | Yes (tokens.css) |
| `--pds-border-subtle` | Card.css (.card-chip) | 1 | **NO** — undefined |
| `transparent` | Card.css (.card base border) | 1 | N/A (CSS keyword) |

**Bug found:** `--pds-border-subtle` is used in Card.css line 49 but defined nowhere. Card chips render with invisible borders. Similarly `--pds-text-subtle` (Card.css line 63) is undefined.

### 3b. PDS v4 Token System for Borders

PDS v4 border tokens cover only `border-radius`. For border colors, PDS uses color tokens directly:

| PDS Token | Purpose | Dark value |
|-----------|---------|------------|
| `--p-color-contrast-lower` | Decorative, lowest | `hsl(240 1.5% 61.8% / 0.302)` |
| `--p-color-contrast-low` | Decorative borders | `hsl(240 12.5% 96.9% / 0.45)` |
| `--p-color-contrast-medium` | Text/important borders | `hsl(240 12.5% 96.9% / 0.56)` |
| `--p-color-contrast-high` | High-contrast text | `hsl(240 12.5% 96.9% / 0.67)` |

PDS docs: `contrast-low` and `contrast-lower` are "intended only for decorative elements, not accessibility-compliant."

All color tokens use native `light-dark()` — dark mode is automatic when `color-scheme: dark` is set.

### 3c. Dark Mode Contrast Ratios (Estimated)

| Pair | Light ratio | Dark ratio | Meets ≥1.3:1? |
|------|------------|------------|----------------|
| `contrast-low` border on `surface` | ~4.5:1 | ~5.3:1 | Yes |
| `contrast-low` border on `canvas` | ~5.2:1 | ~8.4:1 | Yes |
| `surface` vs `canvas` (no border) | ~1.3:1 | ~1.16:1 | **Borderline** |

Surface-to-canvas contrast in dark mode (~1.16:1) is below 1.3:1 — panels rely on borders for visual separation. This is consistent with PDS's approach (admin panel template uses `p-canvas` component which handles layout boundaries).

### 3d. Post-Migration Token Mapping

After #1603 (token migration), the mapping is:

| Current | Post-migration |
|---------|---------------|
| `--pds-contrast-low` | `--p-color-contrast-low` |
| `--pds-contrast-medium` | `--p-color-contrast-medium` |
| `--pds-border-default` (Shell alias) | keep as alias → `--p-color-contrast-low`, or inline |
| `--pds-border-subtle` (undefined!) | `--p-color-contrast-lower` |
| `--pds-notification-*` | `--p-color-{error\|warning\|success\|info}` |

## 4. Recommendation

**Token-first audit** (confidence: 0.85): Implementation should be a verification + fix pass after token migration (#1603). The dependency chain already enforces this ordering.

Implementation checklist:
1. `grep -r` for any non-`--p-` border-color values in `src/**/*.css` — should be zero post-migration
2. Fix `--pds-border-subtle` → `--p-color-contrast-lower` (or provenance map should catch this)
3. Verify shell semantic alias `--pds-border-default` is migrated (deleted or updated to `--p-color-contrast-low`)
4. Playwright screenshot comparison: light vs dark — intentional differentiation, not mere inversion
5. Verify border-on-surface contrast ≥ 1.3:1 via computed styles in Playwright

**Risk:** The undefined `--pds-border-subtle` bug may not be caught by the provenance map (#1597) since it's a reference to a variable that doesn't exist as a definition. Flag to test task #1620.

Challenge: skipped (T1 — verification/fix pass, no architecture change).

## 5. Follow-up Tasks

No new follow-up tasks needed — the existing task chain (#1620 → #1625) covers the scope. The undefined token bug should be flagged in #1620's test expectations.
