---
id: 1594
title: 'P0-02: PDS global-styles import + CSP font relaxation'
status: research
priority: critical
created: 2026-05-16T03:35:01.700586+00:00
updated: 2026-05-16T03:35:01.700586+00:00
tags:
  - frontend
  - pds
  - phase-0
parent: 1590
depends_on:
  - 1591
ac:
  - --p-color-canvas, --p-spacing-md, --p-font-family resolve to non-empty 
    values in computed styles
  - CSP meta tag contains font-src 'self' https://cdn.ui.porsche.com
  - No console warnings from PDS provider about missing stylesheets
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1590.

Replace single `color-scheme.css` import in `main.tsx` with PDS `global-styles/index.css` bundle (variables, font-face, normalize, color-scheme). Add `font-src 'self' https://cdn.ui.porsche.com` to CSP meta tag in Vite HTML plugin (D6).

Scope: global-styles import and CSP font-src only.
Out of scope: Tailwind, Stylelint, board scroll.