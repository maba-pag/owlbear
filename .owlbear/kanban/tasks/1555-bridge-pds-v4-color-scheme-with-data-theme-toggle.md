---
id: 1555
title: Bridge PDS v4 color-scheme with data-theme toggle
status: research
priority: important
created: 2026-05-14T05:57:42.186424+00:00
updated: 2026-05-14T05:57:42.186424+00:00
tags:
  - phase-4
  - scope:cockpit
  - theme
  - frontend
parent: 1534
depends_on:
  - 1553
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Context

PDS v4 web components do NOT respond to `data-theme` attribute — they use CSS `color-scheme` property via `.scheme-*` utility classes. Our Cockpit currently only sets `data-theme` on `<html>`, leaving PDS components permanently in light mode during dark theme.

Research ref: #1553

## Objectives

1. Import PDS v4 mandatory global styles CSS (`@import '@porsche-design-system/components-react'`) so `.scheme-*` utility classes are available
2. Update `theme-bootstrap.js` to also add `.scheme-dark`/`.scheme-light` class on `<html>` alongside `data-theme`
3. Update `useTheme.ts` to add/remove `.scheme-dark`/`.scheme-light` class when theme changes (keep `data-theme` for non-PDS styling)
4. Verify all 14 PDS components switch correctly between light and dark

## Acceptance Criteria

- [ ] PDS global styles CSS is imported so `.scheme-*` utility classes are defined
- [ ] `theme-bootstrap.js` sets both `data-theme` and `.scheme-dark`/`.scheme-light` class on `<html>` at page load
- [ ] `useTheme.ts` toggles `.scheme-dark`/`.scheme-light` class on `<html>` alongside `data-theme` on every theme change
- [ ] Old `.scheme-*` class is removed before new one is added (no class accumulation)
- [ ] All 14 PDS components render in dark mode when dark theme is active (visual verification or snapshot)
- [ ] Light mode continues to work correctly (no regression)
- [ ] No duplicate or conflicting color-scheme declarations in the CSS