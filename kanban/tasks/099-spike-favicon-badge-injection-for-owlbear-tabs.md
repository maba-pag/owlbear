---
id: 99
title: 'Spike: favicon badge injection for OwlBear tabs'
status: todo
priority: low
created: 2026-02-27T03:15:19.317906+01:00
updated: 2026-02-27T03:47:13.964812+01:00
started: 2026-02-27T03:32:44.8825842+01:00
tags:
    - phase-6
    - browser
    - research
class: standard
---

Research spike: prototype canvas-based favicon overlay that shows an 'OB' badge on OwlBear-controlled tabs. Provides additional visual differentiation beyond title prefix.

See docs/cdp-tab-groups-research.md section 4 for context.

## Scope
- JS prototype only — no production code changes
- Prototype lives in docs/scratch/99-favicon-badge.js (deleted after spike)
- Deliverable is a go/no-go decision + documented approach

## Approach
1. Write JS snippet: create 16x16 canvas, draw original favicon, overlay 'OB' badge
2. Set as new favicon via link[rel=icon] href = canvas.toDataURL()
3. Test manually via page.evaluate() on sites with: no favicon, PNG favicon, SVG favicon, multi-size favicon

AC:
- [ ] JS prototype in docs/scratch/99-favicon-badge.js
- [ ] Tested on 3+ sites: one with no favicon, one with simple PNG, one with SVG favicon
- [ ] Cross-origin favicon handling documented (canvas tainted by CORS? fallback needed?)
- [ ] Visual quality assessed — screenshot evidence or description of result
- [ ] Go/no-go recommendation: worth integrating into BrowserToolset? Under what conditions?
- [ ] If go: follow-up implementation task created on kanban board
- [ ] If no-go: rationale documented, no follow-up task needed
- [ ] docs/scratch/99-* files deleted after spike completion
