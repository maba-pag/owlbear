---
id: 1592
title: 'P0-03: Tests — Tailwind v4 Vite plugin + Stylelint config'
status: backlog
priority: critical
created: 2026-05-16T03:34:43.226946+00:00
updated: 2026-05-16T04:08:32.155021+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on: []
ac:
  - Test asserts PDS Tailwind utility classes (bg-canvas, text-contrast-high, 
    gap-md, rounded-sm) compile without error in vite build
  - Test asserts light-dark() CSS functions are preserved in build output (not 
    compiled away)
  - Test asserts npm run lint:css passes on files containing @theme, @utility, 
    @apply at-rules
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Scope: Failing tests for Tailwind v4 Vite plugin integration and Stylelint at-rule recognition.
Out of scope: Token migration, layout, board scroll, implementation.

2026-05-16T04:08:04+00:00


## Research Findings

### AC-1 Discrepancy: `gap-md` is invalid
The brief's AC says `bg-canvas, text-contrast-high, gap-md, rounded-sm`. However, PDS Tailwind theme does NOT define `--spacing-md`. PDS uses `--spacing-fluid-{xs..2xl}` and `--spacing-static-{2xs..2xl}`. The correct class is `gap-fluid-md` or `gap-static-md`. Tests should use `gap-fluid-md`.

### Key Technical Details
- PDS theme file: `@porsche-design-system/components-react/tailwindcss/index.css` (789 lines)
- At-rules in PDS theme: `@theme` (1), `@utility` (47), `@layer` (1), `@supports` (1)
- `light-dark()` used in ALL color variables; lightningcss `Features.LightDark` exclusion already in vite.config.ts
- Stylelint fix: manual `ignoreAtRules` on `at-rule-no-unknown` (no new dependency needed)
- Tailwind at-rules to allow: `theme`, `utility`, `apply`, `source`, `reference`, `variant`, `custom-variant`, `plugin`

### Test Approaches
- AC-1: Verify `@tailwindcss/vite` plugin registered + build-output scan for compiled PDS utilities
- AC-2: Scan `dist/assets/*.css` for `light-dark(` after build
- AC-3: Run Stylelint on fixture CSS file with `@theme`/`@utility`/`@apply`, assert exit 0

Research doc: `.owlbear/research/1592-tailwind-v4-stylelint-tests.md`

[[2026-05-16T06:08:32+02:00]]
## Research
- Research doc: .owlbear/research/1592-tailwind-v4-stylelint-tests.md
- Sources: 8 studied, 5 high-relevance (≥0.85)
- Key finding: AC-1 `gap-md` is invalid — PDS uses `gap-fluid-md` / `gap-static-md`. Tests should use `gap-fluid-md`.
- Recommendation: Manual `ignoreAtRules` for Stylelint (confidence: 0.80), build-output scan for light-dark() and utility compilation (confidence: 0.82)
- No follow-up tasks needed — builder #1595 already exists as dependency
