# PDS Global-Styles Test Approach — AC Validation & Feasibility

> **Owning task:** #1591 — P0-01: Tests — PDS global-styles import + CSP font relaxation
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1591 needs failing Playwright E2E tests for three concerns: (a) PDS CSS custom properties resolve on `:root`, (b) CSP meta tag includes `font-src` for Porsche CDN, (c) no PDS provider console warnings about missing stylesheets. Research must validate AC property names against PDS v4.1.0 source and confirm each AC is testable.

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| `components-react/global-styles/variables.css` | PDS v4.1.0 shipped CSS | 1.0 — definitive variable namespace |
| `components-react/global-styles/color-scheme.css` | Currently imported CSS | 0.9 — shows what's NOT on `:root` |
| `components-react/global-styles/font-face.css` | PDS font declarations | 0.9 — all URLs hardcoded to cdn.ui.porsche.com |
| `components-react/esm/provider.mjs` | Provider source | 0.9 — no warning emission |
| `components-js/index.js` | PDS `load()` source | 0.8 — no stylesheet checks |
| `vite.config.ts` cspPlugin | Current CSP policy | 0.9 — no font-src directive |
| `e2e/pds-runtime-csp.spec.ts` | Existing test pattern | 0.8 — API stubs, CSP collection |
| `decisions.md` D6 | User decision | 1.0 — CDN fonts approved |

## 3. Analysis

### Finding F1: AC1 property names incorrect (CRITICAL)

| AC name | PDS actual name | Exists? |
|---------|----------------|---------|
| `--p-color-canvas` | `--p-color-canvas` | ✅ in `variables.css` `:root` |
| `--p-spacing-md` | — | ❌ Does not exist |
| `--p-font-family` | — | ❌ Does not exist |

Correct PDS v4 equivalents: `--p-spacing-static-md` (16px) and `--p-font-porsche-next` ("Porsche Next"...).

**Impact:** Tests using incorrect names will NEVER go GREEN, even after builder imports `global-styles/index.css`. This breaks the TDD cycle permanently.

**Downstream drift:** Same incorrect names appear in #1594 (builder AC), #1602, #1607. These tasks need correction during their own research pass.

### Finding F2: AC3 untestable as written (CRITICAL)

PDS v4 does NOT emit console warnings about missing stylesheets:
- `load()` in `index.js` — sets up CDN script loading only, no stylesheet checks
- `PorscheDesignSystemProvider` in `provider.mjs` — calls `load()` in useEffect, no warnings
- `hooks.mjs` — throws Error for missing provider wrapper, unrelated to stylesheets
- No `console.warn` in `components-js/cjs/` or `esm/` runtime bundles

**Correct test target:** Console errors/warnings from browser itself (network failures, CSP violations) when fonts or styles fail to load. A `page.on('console')` listener filtering for error/warning severity catches these without depending on PDS-internal warning strings.

### Finding F3: CSP font-src — D6 is binding

D6 (user decision) explicitly chose CDN font loading: "Add `font-src 'self' https://cdn.ui.porsche.com`... Rejected: self-hosting fonts via sync-pds-assets.mjs." This overrides the pre-decision security stance (R1). AC2 correctly tests for `font-src 'self' https://cdn.ui.porsche.com`.

### Finding F4: RED/GREEN mechanism is sound

| State | `--p-color-canvas` on `:root` | CSP `font-src` | Console clean |
|-------|-------------------------------|----------------|---------------|
| Current (RED) | Empty — `color-scheme.css` `@supports not` skipped in Chromium 123+ | Missing — falls back to `default-src 'self'` | Likely has errors |
| After #1594 (GREEN) | Resolved — `variables.css` defines on `:root` via `light-dark()` | Present — `font-src 'self' https://cdn.ui.porsche.com` | Clean |

### Finding F5: Test implementation approach

Follow existing `pds-runtime-csp.spec.ts` patterns: LIFO route stubs, `stubApis()` helper, `data-region="workspace"` wait. New file: `e2e/pds-foundation-1591.spec.ts`.

| AC | Playwright technique | DOM target |
|----|---------------------|------------|
| AC1 | `page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--p-color-canvas'))` | `document.documentElement` (`:root`) |
| AC2 | `page.evaluate(() => document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content)` then assert `font-src` substring | `<meta>` in `<head>` |
| AC3 | `page.on('console', ...)` collector before `goto()`, filter severity error/warning + 'porsche' keyword | Console API |

## 4. Recommendation (confidence: 0.85)

Correct AC1 property names and rewrite AC3 before test-writing. All three ACs are technically feasible with the corrections.

**Challenge:** `block` (confidence in original: 0.24). Challenger identified AC quality gaps, contract drift, and CSP authority conflict. Re-evaluation accepted F1 and F2 fully; F3 (CSP conflict) resolved via D6 precedence. Revised AC3 addresses untestability. Confidence raised from 0.24 → 0.85 after corrections.

## 5. Follow-up Tasks

- AC corrections applied to #1591 directly (T1 — factual fix)
- Downstream AC drift (#1594, #1602, #1607) noted for their own research passes
