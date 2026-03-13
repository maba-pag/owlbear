# ExcalidrawRenderService — Research Update

> **Owning task:** #629 — Implement ExcalidrawRenderService using BrowserManager
> **Date:** 2026-03-12 **Status:** Complete

## 1. Context and Question

Task #629 proposes a Playwright-based `ExcalidrawRenderService` that renders Excalidraw JSON to PNG via `BrowserManager`. Prior research (docs/research/excalidraw-render-service.md) recommended deferring this as Tier 2 in favor of a Tier 0 Kroki passthrough. This update re-evaluates: should #629 proceed, or should the Kroki passthrough be created first?

Key questions:

1. Has the Kroki font issue (#1742) been resolved?
2. Is the Tier 0 Kroki passthrough sufficient, or is PNG output now needed?
3. What is the minimal viable implementation if #629 proceeds?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | coleam00/excalidraw-diagram-skill | <https://github.com/coleam00/excalidraw-diagram-skill> | .95 — render pipeline (1k stars, MIT) |
| 2 | Kroki support matrix | <https://kroki.io/#support> | .90 — Excalidraw → SVG only (no PNG) |
| 3 | Kroki #1742 (font bug) | <https://github.com/yuzutech/kroki/issues/1742> | .85 — Still open; workaround: self-hosted 0.23.0 |
| 4 | @excalidraw/utils (npm) | <https://www.npmjs.com/package/@excalidraw/utils> | .75 — Standalone `exportToSvg`/`exportToBlob` |
| 5 | OwlBear BrowserManager | src/owlbear/tools/browser/manager.py | .95 — Existing async CM |
| 6 | OwlBear DiagramService | src/owlbear/tools/diagram/service.py | .95 — Kroki wrapper |

## 3. Analysis

### 3.1 Current State

| Component | Status |
|-----------|--------|
| Excalidraw skill (.github/skills/) | Done (#628) |
| DiagramService (Kroki) | Done — `"excalidraw"` NOT in SUPPORTED_TYPES |
| Tier 0 Kroki passthrough | **Never created** (recommended but not executed) |
| Playwright ExcalidrawRenderService | Not started (#629) |

### 3.2 Tier 0 vs Tier 2 Decision Matrix

| Criterion | Tier 0: Kroki passthrough (.88) | Tier 2: Playwright render (.72) |
|-----------|--------------------------------|--------------------------------|
| New code | ~1 line | ~120 LOC new service |
| Output | SVG only | PNG (screenshot) + SVG |
| Fonts | Broken on kroki.io free tier (#1742) | Correct via esm.sh CDN |
| Latency | ~200ms | ~2-4s (browser startup) |
| Visual feedback loop | No (SVG string) | Yes (PNG → agent views) |
| New deps | None | None (Playwright installed) |
| KISS | Highest | Medium |
| YAGNI risk | Low | Medium-high |

### 3.3 Kroki Font Issue (#1742)

Still open since 2024-04. Root cause: upstream `PKG_VERSION` → `VITE_PKG_VERSION` mismatch causes font URLs to resolve to `@excalidraw/excalidraw@undefined/dist/...`. Workaround exists for self-hosted Docker (kroki-excalidraw:0.23.0) but OwlBear uses the free kroki.io service. **Excalidraw via kroki.io uses fallback fonts, losing the hand-drawn aesthetic.**

### 3.4 coleam00 Render Pipeline (Reference Implementation)

Proven pattern (1k+ stars, MIT):

1. HTML template loads `exportToSvg` from `https://esm.sh/@excalidraw/excalidraw?bundle`
2. Exposes `window.renderDiagram(jsonData)` → appends SVG to DOM
3. Signals readiness via `window.__moduleReady` / `window.__renderComplete`
4. Python: `page.set_content(html)` → `wait_for_function` → `evaluate` → screenshot

OwlBear adaptation: embed HTML as string constant, `async with BrowserManager()`, `ScreenshotService.save()`. ~120 LOC.

### 3.5 Architecture Fit (If Implemented)

| Component | Integration | Pattern to follow |
|-----------|------------|-------------------|
| `BrowserManager` | Async CM for Playwright | Same as `BrowserToolset` |
| `ScreenshotService` | Save PNG + deliver | Same as `DiagramToolset` |
| `DiagramToolset` | Add `render_excalidraw` tool | Extend existing |
| HTML template | Embedded string constant | ~30 lines, per AC |
| Validation | `type=="excalidraw"`, `elements` non-empty list | Per coleam00 |

## 4. Recommendation (.85 confidence)

**Create Tier 0 first, keep #629 deferred.**

1. Add `"excalidraw"` to `SUPPORTED_TYPES` (1-line change) → agents get SVG output now
2. Keep #629 at `someday` — build Playwright service only when PNG output or correct fonts are needed
3. Risk: font quality degraded on kroki.io. If hand-drawn aesthetic matters, escalate #629

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Add excalidraw to DiagramService SUPPORTED_TYPES" --priority needed --status backlog --tags "scope:core,tooling" --body "One-line change: add 'excalidraw' to SUPPORTED_TYPES in src/owlbear/tools/diagram/service.py. Kroki supports Excalidraw JSON -> SVG. See docs/research/excalidraw-render-update.md.`n`nAC:`n- [ ] SUPPORTED_TYPES includes 'excalidraw'`n- [ ] Test: generate(diagram_type='excalidraw', source=valid_json) calls Kroki`n- [ ] Existing tests pass, ruff clean"
```

Task #629 remains at `someday` with updated body noting Tier 0 covers immediate needs.
