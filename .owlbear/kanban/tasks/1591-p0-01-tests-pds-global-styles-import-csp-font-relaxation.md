---
id: 1591
title: 'P0-01: Tests — PDS global-styles import + CSP font relaxation'
status: research
priority: critical
created: 2026-05-16T03:34:43.205432+00:00
updated: 2026-05-16T03:34:43.205432+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on: []
ac:
  - Playwright test asserts PDS CSS custom properties (--p-color-canvas, 
    --p-spacing-md, --p-font-family) resolve to non-empty values in computed 
    styles
  - Test asserts CSP meta tag includes font-src 'self' 
    https://cdn.ui.porsche.com
  - Test asserts no PDS provider console warnings about missing stylesheets
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