# ExcalidrawRenderService via BrowserManager — Research

> **Owning task:** #629 — Implement ExcalidrawRenderService using BrowserManager
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #629 proposes a Playwright-based `ExcalidrawRenderService` that renders `.excalidraw` JSON to PNG using OwlBear's existing `BrowserManager`. This is Tier 2 of the visuals strategy (see `docs/visuals-diagrams-mcp-research.md` §4). The key research questions:

1. Is browser-based rendering via Playwright a sound approach, or can Kroki handle it?
2. What rendering strategy works best: esm.sh CDN import vs `@excalidraw/utils` vs Kroki passthrough?
3. How does it integrate with the existing `DiagramService`/`DiagramToolset`/`BrowserManager`?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | coleam00/excalidraw-diagram-skill | <https://github.com/coleam00/excalidraw-diagram-skill> | .95 — Proven Playwright + esm.sh render pipeline |
| 2 | Kroki Excalidraw support | <https://kroki.io/#support> | .90 — Kroki already renders Excalidraw JSON → SVG |
| 3 | Excalidraw export API docs | <https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export> | .80 — Official `exportToSvg`/`exportToBlob` APIs |
| 4 | @excalidraw/utils (npm) | <https://www.npmjs.com/package/@excalidraw/utils> | .75 — Standalone export utils, no React needed |
| 5 | yuzutech/kroki-excalidraw | <https://docs.kroki.io/kroki/setup/install/> | .85 — Companion container docs, font issues |
| 6 | yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | .65 — Over-engineered for OwlBear but validates the format |

## 3. Analysis

### 3.1 Rendering Approaches

| Criterion | Kroki passthrough (.85) | Playwright + esm.sh (.75) | @excalidraw/utils in browser (.65) |
|-----------|------------------------|--------------------------|-----------------------------------|
| New code | ~1 line (add `"excalidraw"` to `SUPPORTED_TYPES`) | ~120 LOC new service | ~100 LOC new service |
| New deps | None | None (Playwright already installed) | None |
| Output formats | SVG only (Kroki limitation) | PNG (screenshot), SVG | SVG, PNG (via `exportToBlob`) |
| Font rendering | Open issue (#1742 — fonts broken) | Fonts load via esm.sh CDN (reliable) | Same as esm.sh |
| Offline | Requires self-hosted Kroki + companion container | Requires internet for esm.sh first load | Same as esm.sh |
| Latency | ~200ms (HTTP POST) | ~2–4s (browser startup + CDN load) | ~2–4s |
| Render fidelity | Kroki uses its own Excalidraw renderer | Uses official `exportToSvg` | Uses official `exportToSvg` |
| Visual feedback loop | No (static SVG) | Yes (screenshot → agent views PNG) | Yes |
| KISS | Highest — zero new code | Medium | Medium |
| YAGNI risk | Low — reuses existing DiagramService | High — adds service for unproven need | High |

### 3.2 Critical Finding: Kroki Already Supports Excalidraw

Kroki accepts raw Excalidraw JSON as `diagram_source` with `diagram_type: "excalidraw"` and returns SVG. This means OwlBear's existing `DiagramService` can render Excalidraw today with a **one-line change**: adding `"excalidraw"` to `SUPPORTED_TYPES`. No new service, no Playwright overhead, no CDN dependency.

Limitations of the Kroki path:

- **SVG only** — no PNG output from Kroki for Excalidraw (per the support matrix)
- **Font issues** — Kroki issue #1742 (open since 2024-04, partially fixed by #1998 self-hosted fonts)
- **Requires companion container** for self-hosted (`yuzutech/kroki-excalidraw`); the free kroki.io service includes it but has no SLA

### 3.3 When Would Playwright Rendering Be Needed?

The Playwright path only justifies itself when:

1. PNG output is required (Slack image previews, visual feedback loop)
2. Kroki font rendering remains broken for handwritten Excalidraw styles
3. Offline rendering is needed without Docker companion containers

None of these are current requirements. The task AC says "Tier 2 (YAGNI until Tier 1 Kroki proves insufficient)."

### 3.4 Architecture Fit (If/When Implemented)

| Component | Integration point | Pattern |
|-----------|------------------|---------|
| `BrowserManager` | `ExcalidrawRenderService` uses it as async context manager | Same as `BrowserToolset.setup()` |
| `DiagramToolset` | Add `render_excalidraw` tool alongside `generate_diagram` | Or: make `generate_diagram` handle `excalidraw` type transparently |
| `ScreenshotService` | Save rendered PNG, deliver via channel | Same pattern as `DiagramToolset.generate_diagram` |
| HTML template | Embedded as string constant (per AC) — no external file | `render_template.html` from coleam00 is ~30 lines |
| Validation | Check `type == "excalidraw"`, `elements` is list, not empty | Matches coleam00's `validate_excalidraw()` |

### 3.5 The coleam00 Render Pipeline (Reference Implementation)

The proven pattern from coleam00/excalidraw-diagram-skill:

1. **HTML template** loads `exportToSvg` from `https://esm.sh/@excalidraw/excalidraw?bundle`
2. Template exposes `window.renderDiagram(jsonData)` that calls `exportToSvg` and appends SVG to DOM
3. Template signals readiness via `window.__moduleReady = true` and completion via `window.__renderComplete = true`
4. Python side: `page.goto(template_url)` → `wait_for_function("__moduleReady")` → `page.evaluate("renderDiagram(...)")` → `wait_for_function("__renderComplete")` → `page.query_selector("#root svg").screenshot()`

For OwlBear adaptation: embed the HTML as a string constant, use `page.set_content(html)` instead of `page.goto()` (removes file dependency). Use `async with BrowserManager() as mgr:` for lifecycle.

## 4. Recommendation

### Tier 0: Add Kroki Excalidraw passthrough (.90 confidence)

Add `"excalidraw"` to `SUPPORTED_TYPES` in `DiagramService`. **Zero new classes, zero new files.** This gives agents `generate_diagram(diagram_type="excalidraw", source=excalidraw_json, output_format="svg")` today. Satisfies the most likely use case (architecture diagrams as SVG).

### Tier 2: ExcalidrawRenderService — DEFER (.75 confidence)

Build the Playwright-based render service **only if** Kroki Excalidraw proves insufficient (font issues, PNG needed, offline required). The coleam00 pattern is proven and maps cleanly to OwlBear's architecture. When triggered:

- `ExcalidrawRenderService` (~120 LOC) in `src/owlbear/tools/diagram/excalidraw_render.py`
- Embedded HTML template, `BrowserManager` lifecycle, `ScreenshotService` save/deliver
- Register as alternative backend in `DiagramToolset`

**Risk:** esm.sh CDN availability. Mitigation: pin version (`https://esm.sh/@excalidraw/excalidraw@0.18.0?bundle`). Fallback: bundle the JS locally if CDN fails (YAGNI for now).

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add excalidraw to DiagramService SUPPORTED_TYPES (Kroki passthrough)" --priority needed --status todo --tags "phase-7,scope:core,tooling" --body "One-line change: add 'excalidraw' to SUPPORTED_TYPES frozenset in src/owlbear/tools/diagram/service.py. Kroki already supports Excalidraw JSON as diagram_source. Output: SVG only (Kroki limitation). See docs/excalidraw-render-service-research.md section 4 Tier 0.`n`nAC:`n- [ ] SUPPORTED_TYPES includes 'excalidraw'`n- [ ] Test: generate(diagram_type='excalidraw', source=valid_json, output_format='svg') calls Kroki correctly`n- [ ] Test: generate with excalidraw rejects output_format='png' (Kroki only supports SVG for excalidraw)`n- [ ] Existing tests still pass`n- [ ] ruff clean"

kanban\kanban-md.exe edit 629 --priority someday --body "DEFERRED: Kroki passthrough (Tier 0) covers Excalidraw rendering with zero new code. Build the Playwright-based ExcalidrawRenderService only if Kroki proves insufficient (font issues, PNG needed, offline). See docs/excalidraw-render-service-research.md section 4."
```

## 6. Research Checklist

- [x] **Theoretical validity** — Browser-based rendering via Playwright is sound and proven (coleam00, 693 stars). However, Kroki already handles Excalidraw rendering server-side, making a browser-based service YAGNI.
- [x] **Prior art** — 6 sources: coleam00 skill (Playwright render), Kroki (server-side), official Excalidraw API, @excalidraw/utils, yuzutech/kroki-excalidraw, yctimlin/mcp_excalidraw.
- [x] **Technical feasibility** — esm.sh serves `@excalidraw/excalidraw@0.18.0` successfully. `BrowserManager` provides the Playwright lifecycle. But the simpler Kroki path works today.
- [x] **Architecture fit** — Kroki passthrough: 1-line change to existing `DiagramService`. Playwright path: maps to `BrowserManager` + `ScreenshotService` patterns.
- [x] **Implementation approach** — Tier 0: add `"excalidraw"` to `SUPPORTED_TYPES`. Tier 2 (deferred): embed coleam00 HTML template, use `BrowserManager`, `ScreenshotService`.
- [x] **Testing strategy** — Tier 0: mock Kroki HTTP response in existing test pattern. Tier 2: sample `.excalidraw` fixture, mock Playwright page.
- [x] **Findings documented** — This document.
