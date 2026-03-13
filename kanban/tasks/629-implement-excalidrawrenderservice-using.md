---
id: 629
title: Implement ExcalidrawRenderService using BrowserManager
status: backlog
priority: someday
created: 2026-03-07T05:22:03.4218241+01:00
updated: 2026-03-12T15:21:54.150768+01:00
started: 2026-03-07T14:06:09.516857+01:00
tags:
    - phase-research
    - scope:core
    - tooling
depends_on:
    - 628
blocked: true
block_reason: 'YAGNI: Kroki passthrough (add excalidraw to SUPPORTED_TYPES) must be tried first. Only build Playwright render service if Kroki proves insufficient.'
class: standard
---

Tier 2 (YAGNI until Tier 1 Kroki proves insufficient). Render .excalidraw JSON to PNG via Playwright.

AC:

- [ ] src/owlbear/tools/diagram/excalidraw_render.py with ExcalidrawRenderService
- [ ] async render(excalidraw_json: str) -> bytes (PNG)
- [ ] Uses existing BrowserManager to load Excalidraw via esm.sh and call exportToSvg
- [ ] Validates JSON structure (elements array, appState) before rendering
- [ ] HTML render template embedded as string constant (no external file)
- [ ] Tests with sample .excalidraw JSON fixture in tests/fixtures/
- [ ] Integrates with DiagramToolset as alternative render backend
- [ ] All tests pass, ruff clean

Pattern: follow ScreenshotService (stateless) + BrowserToolset (Playwright lifecycle)
Ref: docs/excalidraw-diagram-skill-research.md section 3.2, docs/visuals-diagrams-mcp-research.md section 4 Tier 2

[[2026-03-12]] Thu 13:18
## Architecture Review
See docs/scratch/629-architect.md for full review.

[[2026-03-12]] Thu 15:21
## Research (2026-03-12)
Recommendation (.85): Create Tier 0 Kroki passthrough first, keep #629 deferred.
Kroki supports Excalidraw JSON -> SVG (confirmed). Font bug #1742 still open.
coleam00 render pipeline proven (1k+ stars). Tier 0 = 1-line change; Tier 2 = ~120 LOC.
Doc: docs/research/excalidraw-render-update-research.md
