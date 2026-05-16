---
id: 1591
title: 'P0-01: Tests — PDS global-styles import + CSP font relaxation'
status: backlog
priority: critical
created: 2026-05-16T03:34:43.205432+00:00
updated: 2026-05-16T04:10:39.712398+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on: []
ac:
  - Playwright test asserts PDS CSS custom properties (--p-color-canvas, 
    --p-spacing-static-md, --p-font-porsche-next) resolve to non-empty values in
    computed styles on document.documentElement
  - Test asserts CSP meta tag includes font-src 'self' 
    https://cdn.ui.porsche.com
  - Test asserts no console errors or warnings containing 'porsche' during shell
    load (covers font-load failures, CSP violations, and PDS runtime errors)
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for PDS foundation CSS import and CSP font-src directive.
Out of scope: Tailwind, board scroll, implementation.



## Research Notes
- AC1 corrected: `--p-spacing-md` → `--p-spacing-static-md`, `--p-font-family` → `--p-font-porsche-next` (verified against PDS v4.1.0 `variables.css`)
- AC3 rewritten: PDS v4 does NOT emit console warnings about missing stylesheets; replaced with browser-level console error/warning assertion
- D6 (user decision) governs AC2: CDN font loading approved, self-hosting rejected
- Downstream tasks #1594, #1602, #1607 have same property name errors — flag during their research
- Test pattern: follow `e2e/pds-runtime-csp.spec.ts` (LIFO route stubs, `stubApis()`, workspace wait)
- RED mechanism: `color-scheme.css` `@supports not` block skipped in modern Chromium → no `--p-*` on `:root`; no `font-src` in CSP
- Research doc: `.owlbear/research/1591-pds-global-styles-test-approach.md`

[[2026-05-16T06:10:39+02:00]]
## Research
- Research doc: .owlbear/research/1591-pds-global-styles-test-approach.md
- Sources: 8 studied, 6 high-relevance
- Recommendation: Correct AC property names and rewrite AC3 before test-writing (confidence: 0.85)
- Challenge: block → reconsider (confidence in original: 0.24 → 0.85 after corrections)

### Key corrections applied:
- AC1: --p-spacing-md → --p-spacing-static-md, --p-font-family → --p-font-porsche-next (PDS v4 namespace verified)
- AC3: PDS does NOT emit console warnings about missing stylesheets; rewritten to assert no console errors/warnings containing 'porsche' during shell load
- D6 (user decision) governs CSP: CDN font loading approved

### Downstream drift noted:
- #1594 AC has same incorrect property names — flag during its research
- #1602, #1607 reference --p-spacing-md — correct during their research passes
