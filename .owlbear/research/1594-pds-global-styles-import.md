# PDS Global-Styles Import + CSP Font Relaxation — Implementation Research

> **Owning task:** #1594 — P0-02: PDS global-styles import + CSP font relaxation
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1594 (builder) should replace the single `color-scheme.css` import in `main.tsx` with the full PDS `global-styles/index.css` bundle and add `font-src 'self' https://cdn.ui.porsche.com` to the CSP meta tag. Research must verify current state, correct AC drift from #1591, and define the remaining implementation scope.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | PDS v4 React Getting Started docs (`designsystem.porsche.com/v4/developing/react/getting-started/`) | 1.0 |
| S2 | `components-react/package.json` exports map (`"style": "./global-styles/index.css"`) | 1.0 |
| S3 | PDS `global-styles/index.css` — full bundle content (variables, scheme classes, font-face) | 1.0 |
| S4 | `color-scheme.css` — subset (scheme classes + @supports fallback only) | 0.9 |
| S5 | Commit `ad6e9f05` (#1591 builder) — added `index.css` import + CSP font-src | 1.0 |
| S6 | #1591 research doc (`.owlbear/research/1591-pds-global-styles-test-approach.md`) | 0.9 |
| S7 | E2E test `pds-foundation-1591.spec.ts` — 8/8 passing | 1.0 |

## 3. Analysis

### F1: Core implementation already committed (CRITICAL)

The #1591 builder (commit `ad6e9f05`) implemented both production changes:
- Added `@import '../node_modules/.../global-styles/index.css'` to `tokens.css` line 2
- Added `font-src 'self' https://cdn.ui.porsche.com` to CSP policy in `vite.config.ts`

All 8 E2E tests in `pds-foundation-1591.spec.ts` pass. AC1, AC2, AC3 are satisfied.

### F2: AC1 property names corrected

| Original AC name | PDS v4 actual name | Status |
|------------------|--------------------|--------|
| `--p-color-canvas` | `--p-color-canvas` | ✅ Correct |
| `--p-spacing-md` | `--p-spacing-static-md` | ❌ Fixed during this research |
| `--p-font-family` | `--p-font-porsche-next` | ❌ Fixed during this research |

### F3: Remaining cleanup (builder scope)

| Item | Current state | Target | Impact |
|------|--------------|--------|--------|
| `main.tsx` line 4 | `import '...color-scheme.css'` | Remove (redundant — `index.css` is superset) | Removes duplicate CSS |
| Vite alias | Maps `components-react/...` → `components-js/...` | Remove (no longer referenced) | Simplifies config |
| `pdsColorSchemeCssPath` const | Computes path for alias | Remove (unused after alias removal) | Dead code cleanup |

### F4: #1555 test contracts guard the old pattern (CRITICAL — from challenger)

Two test files from #1555 explicitly assert the color-scheme.css import and Vite alias must exist:
- `PdsColorSchemeBridge_1555.test.ts` (lines 115–132): asserts `main.tsx` contains the `color-scheme.css` import
- `ViteConfigAlias_1555.test.ts` (lines 52–73): asserts Vite alias maps `color-scheme.css` key

**Builder must update these tests** to assert the new pattern (full bundle via `tokens.css`) instead of the old `color-scheme.css` import. Simply deleting the import/alias without updating these tests breaks the vitest suite.

### F5: PDS-recommended import (advisory, not required)

PDS v4 docs [S1] recommend: `@import '@porsche-design-system/components-react'` in CSS. The exports map [S2] has `"style": "./global-styles/index.css"`. Current `tokens.css` uses a bare `../node_modules/...` path. Switching is **optional** — the current path works; the recommended path is cleaner but unproven in this project's Vite/CSS pipeline.

### F6: No new follow-up tasks needed

This task (#1594) IS the implementation task. The builder's work is:
1. Remove redundant `color-scheme.css` import from `main.tsx` + alias + const
2. Update #1555 unit tests to verify the new pattern
3. Verify all E2E + vitest suites still pass

## 4. Recommendation (confidence: 0.85)

Builder scope is cleanup + test update: remove redundant `color-scheme.css` import from `main.tsx`, remove Vite alias + const, and update #1555 unit tests to assert the new pattern (full bundle import in `tokens.css`). All AC items are already GREEN from #1591's builder. The import-path upgrade (`@import '@porsche-design-system/components-react'`) is advisory — builder may skip it.

Challenge: reconsider → revised. Challenger (confidence 0.63) correctly identified #1555 test-contract regression and scope-drift risks. Response: accepted F4 test-contract finding (critical), accepted scope narrowing (removed optional import-path change from required scope), rebutted scope-drift on alias cleanup (removing orphaned code after import change is task-inherent). Revised confidence: 0.85.

## 5. Follow-up Tasks

None needed. Task #1594 proceeds through pipeline with corrected AC and documented reduced scope.
