---
id: 1496
title: 'Cockpit: Replace PDS appendChild monkeypatch with property trap on document.porscheDesignSystem.cdn'
status: backlog
priority: important
created: 2026-05-12T02:37:00.298093+00:00
updated: 2026-05-12T09:10:38.142809+00:00
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
2026-05-12T09:10:38+00:00
## Research\n- Research doc: .owlbear/research/1496-pds-property-trap.md\n- Sources: 8 studied, 5 high-relevance\n- Recommendation: Proceed with Object.defineProperty trap on document.porscheDesignSystem.cdn (confidence: 0.82)\n- Follow-up tasks created: #1510 (sync PDS local assets with npm version, at research)\n- Decision requests: none\n\n## Challenge Results\n- Challenger: block (confidence in original: 0.30)\n- Key challenges: trap lifetime after post-bootstrap fixup, version mismatch 4.0.0 vs 4.1.0, contradictory test evidence\n- Researcher response: revised — accepted version mismatch as orthogonal pre-existing issue (#1510), rebutted trap lifetime concern (post-bootstrap fixup IS the code being removed), accepted test evidence as supporting trap approach (icon CDN violations prove appendChild monkeypatch is incomplete)\n- Final confidence after rebuttal: 0.82\n\n## Key Findings\n1. PDS load() uses direct assignment: document[s].cdn = { url, prefixes } — interceptable by defineProperty setter\n2. componentsReady() Proxy has only a set trap using Reflect.set — our getter/setter survives\n3. Current appendChild monkeypatch is incomplete: only intercepts HTMLScriptElement, not icon/flag asset URLs\n4. Pre-existing version mismatch: npm 4.1.0 vs public/ v4.0.0 core chunk + missing icon files → separate follow-up #1510\n5. Post-bootstrap fixup (lines 38-41) must be removed as part of implementation — it replaces the trapped namespace