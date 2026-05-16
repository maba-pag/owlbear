---
id: 1594
title: 'P0-02: PDS global-styles import + CSP font relaxation'
status: research
priority: critical
created: 2026-05-16T03:35:01.700586+00:00
updated: 2026-05-16T12:36:59.513945+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on:
  - 1591
ac:
  - --p-color-canvas, --p-spacing-static-md, --p-font-porsche-next resolve to 
    non-empty values in computed styles
  - CSP meta tag contains font-src 'self' https://cdn.ui.porsche.com
  - No console errors or warnings containing 'porsche' during shell load
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at: 2026-05-16T12:23:33.257595+00:00
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Replace single `color-scheme.css` import in `main.tsx` with PDS `global-styles/index.css` bundle (variables, font-face, normalize, color-scheme). Add `font-src 'self' https://cdn.ui.porsche.com` to CSP meta tag in Vite HTML plugin (D6).

Scope: global-styles import and CSP font-src only.
Out of scope: Tailwind, Stylelint, board scroll.

## Research Findings

Core implementation already committed by #1591 builder (commit ad6e9f05):
- `tokens.css` imports `global-styles/index.css` (full PDS bundle)
- CSP `font-src 'self' https://cdn.ui.porsche.com` present in `vite.config.ts`
- All 8 E2E tests in `pds-foundation-1591.spec.ts` pass

Remaining builder work (cleanup):
1. Remove redundant `import '...color-scheme.css'` from `main.tsx` line 4 (subset of already-imported `index.css`)
2. Remove Vite alias + `pdsColorSchemeCssPath` const from `vite.config.ts`
3. **Update #1555 unit tests** that guard the old pattern:
   - `PdsColorSchemeBridge_1555.test.ts` (lines 115–132): asserts `color-scheme.css` import in `main.tsx` → update to assert `global-styles/index.css` import in `tokens.css`
   - `ViteConfigAlias_1555.test.ts` (lines 52–73): asserts Vite alias exists → remove or repurpose
4. Verify all E2E + vitest suites pass

AC property names corrected: `--p-spacing-md` → `--p-spacing-static-md`, `--p-font-family` → `--p-font-porsche-next`.
See `.owlbear/research/1594-pds-global-styles-import.md` for full analysis.
