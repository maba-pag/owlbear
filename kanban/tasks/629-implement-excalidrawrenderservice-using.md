---
id: 629
title: Implement ExcalidrawRenderService using BrowserManager
status: backlog
priority: nice-to-have
created: 2026-03-07T05:22:03.4218241+01:00
updated: 2026-03-07T14:06:09.516857+01:00
started: 2026-03-07T14:06:09.516857+01:00
tags:
    - phase-research
    - scope:core
    - tooling
depends_on:
    - 628
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
