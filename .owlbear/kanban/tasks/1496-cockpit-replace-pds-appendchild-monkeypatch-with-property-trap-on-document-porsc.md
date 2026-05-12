---
id: 1496
title: 'Cockpit: Replace PDS appendChild monkeypatch with property trap on document.porscheDesignSystem.cdn'
status: research
priority: important
created: 2026-05-12T02:37:00.298093+00:00
updated: 2026-05-12T02:37:12.525237+00:00
tags:
  - cockpit
  - frontend
parent: 1495
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Replace the global `Element.prototype.appendChild` monkeypatch in main.tsx with an `Object.defineProperty` trap on `document.porscheDesignSystem.cdn` that always returns `window.location.origin` as the URL. This eliminates prototype pollution, handles the double `load()` call from PorscheDesignSystemProvider, and correctly redirects all PDS asset URLs (JS chunks and non-JS assets like icons/flags) to localhost. See `.owlbear/research/1495-pds-v4-local-hosting.md` for full analysis.

## Acceptance Criteria

1. No `Element.prototype.appendChild` override exists in main.tsx
2. `document.porscheDesignSystem.cdn.url` always returns `window.location.origin`
3. Existing E2E tests in pds-runtime-csp.spec.ts pass
4. PDS custom elements render correctly in dev and build modes