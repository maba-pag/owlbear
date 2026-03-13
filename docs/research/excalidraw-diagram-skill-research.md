# Excalidraw Diagram Skill Research

> **Owning task:** #593 — Research: coleam00/excalidraw-diagram-skill
> **Date:** 2026-03-06 **Status:** Complete

## 1. Context and Question

OwlBear needs visual diagram generation capabilities. Task #593 asks: what patterns from coleam00/excalidraw-diagram-skill (and the broader Excalidraw ecosystem) are reusable in OwlBear?

Key questions:

- Can OwlBear generate `.excalidraw` JSON diagrams via LLM prompts?
- How should rendering work given our existing Playwright browser infrastructure?
- Skill-based workflow vs. MCP server vs. native toolset — which fits OwlBear?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | coleam00/excalidraw-diagram-skill | <https://github.com/coleam00/excalidraw-diagram-skill> | .95 — Primary subject. Skill-based Excalidraw generation with render pipeline |
| 2 | yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | .80 — 1.3k stars, 26-tool MCP server with live canvas + element CRUD |
| 3 | lesleslie/excalidraw-mcp | <https://github.com/lesleslie/excalidraw-mcp> | .65 — Python FastMCP fork of yctimlin, hybrid TS+PY arch |
| 4 | Excalidraw export utilities | <https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/utils/export> | .75 — Official `exportToSvg`/`exportToCanvas` API |

## 3. Analysis

### 3.1 Architecture Approaches

| Criterion | Skill (coleam00) | MCP Server (yctimlin) | Native Toolset |
|-----------|------------------|-----------------------|----------------|
| Integration | Prompt injection (SKILL.md) | External MCP stdio server | Python FunctionToolset |
| Deps | Playwright only | Node.js + Express + WS | Playwright (existing) |
| KISS | High — just JSON + render | Low — full client-server | High |
| OwlBear fit | Good — SkillRegistry exists | Poor — Node.js, not Python | Best — native toolset |
| Live editing | No (static file output) | Yes (WebSocket canvas) | No (file output) |
| Render loop | Playwright → PNG → visual check | Frontend does rendering | Playwright → PNG |
| Complexity | ~6 reference files | ~30+ files, 2 languages | ~2 files |

### 3.2 Key Patterns from coleam00 Repo

**1. Prompt-Driven JSON Generation.** The SKILL.md is a 450-line prompt that teaches the LLM to generate valid Excalidraw JSON. Core insight: LLMs can generate the raw JSON schema directly — no intermediate DSL needed. The skill uses visual metaphors ("diagrams that argue, not display") and pattern libraries (fan-out, convergence, timeline) to guide quality.

**2. Render-View-Fix Loop.** The critical pattern: generate JSON → render via Playwright → view PNG → fix → re-render. This is a closed feedback loop where the agent validates its own visual output. OwlBear already has `BrowserManager` + `ScreenshotService` + `VisualFeedbackToolset` for exactly this.

**3. Modular Reference Files.** The skill separates concerns into `color-palette.md`, `element-templates.md`, `json-schema.md`. These are loaded on demand as context. Maps directly to OwlBear's `SkillRegistry` progressive loading.

**4. Playwright Headless Rendering.** `render_excalidraw.py` uses `exportToSvg` from `@excalidraw/excalidraw` via esm.sh CDN in a headless Chromium page. Result: `.excalidraw` → SVG → screenshot → PNG. OwlBear's `BrowserManager` can do this identically.

### 3.3 What NOT to Adopt

| Pattern | Why Skip |
|---------|----------|
| MCP server architecture (yctimlin/lesleslie) | Over-engineered for OwlBear. Adds Node.js, Express, WebSocket. YAGNI. |
| Live canvas with real-time sync | OwlBear is headless daemon, no interactive canvas needed. |
| Element-level CRUD tools (26 tools) | OwlBear agents generate complete diagrams, not incremental edits. |
| Mermaid-to-Excalidraw conversion | Nice-to-have but not needed now. YAGNI. |

## 4. Recommendation (.85 confidence)

**Adopt the Skill pattern from coleam00, adapted to OwlBear's SkillRegistry.**

Implementation approach:

1. **Create an Excalidraw skill** under `.github/skills/excalidraw-diagram/` with `SKILL.md` + reference files. The SKILL.md prompt teaches agents to generate `.excalidraw` JSON directly.
2. **Create an `ExcalidrawRenderService`** (Python, ~100 LOC) that uses OwlBear's existing `BrowserManager` to render `.excalidraw` files to PNG via the same `exportToSvg` technique.
3. **Expose a `render_excalidraw` tool** via a lightweight `DiagramToolset` (FunctionToolset) that takes a path to an `.excalidraw` file and returns the PNG path.
4. **Leverage existing infrastructure**: `BrowserManager` for Playwright, `ScreenshotService` for PNG capture, `VisualFeedbackToolset` for delivering screenshots to users.

Risk: LLM quality of raw JSON generation varies. Mitigation: the render-view-fix loop catches visual issues. The skill prompt's pattern library and element templates reduce errors.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Create Excalidraw diagram skill (SKILL.md + references)" --priority needed --tags "phase-research,scope:copilot,agent" --body "Port coleam00/excalidraw-diagram-skill prompt methodology to .github/skills/excalidraw-diagram/. Include SKILL.md with design philosophy, pattern library, and section-by-section workflow. Include references: color-palette.md, element-templates.md, json-schema.md. See docs/excalidraw-diagram-skill-research.md for details. AC: 1. Skill loads via SkillRegistry. 2. SKILL.md contains diagram design methodology. 3. Reference files contain JSON templates and color palette."

kanban\kanban-md.exe create "Implement ExcalidrawRenderService using BrowserManager" --priority needed --tags "phase-research,scope:core,tooling" --body "Create src/owlbear/tools/diagram/render.py with ExcalidrawRenderService that renders .excalidraw JSON to PNG using existing BrowserManager + Playwright headless Chromium. Port render_template.html from coleam00 repo (uses @excalidraw/excalidraw exportToSvg via esm.sh). See docs/excalidraw-diagram-skill-research.md section 3.2 pattern #4. AC: 1. render(path) returns PNG path. 2. Uses existing BrowserManager. 3. Validates JSON before rendering. 4. Tests with sample .excalidraw fixture."

kanban\kanban-md.exe create "Create DiagramToolset with render_excalidraw tool" --priority important --tags "phase-research,scope:core,tooling" --body "Create src/owlbear/tools/diagram/toolset.py wrapping ExcalidrawRenderService as a FunctionToolset. Expose render_excalidraw tool that takes .excalidraw file path and returns PNG path. Integrates with VisualFeedbackToolset for delivering rendered diagrams. See docs/excalidraw-diagram-skill-research.md. AC: 1. Tool registered via FunctionToolset. 2. Renders .excalidraw to PNG. 3. Returns path to PNG for agent use. 4. Error handling for invalid JSON."
```

## 6. Research Checklist

- [x] **Theoretical validity** — LLM-driven Excalidraw JSON generation is proven (coleam00 skill used in production with Claude Code, 1.3k+ stars on yctimlin MCP)
- [x] **Prior art** — 4 sources: coleam00 skill, yctimlin MCP (1.3k stars), lesleslie MCP (Python), official Excalidraw API
- [x] **Technical feasibility** — Playwright rendering works in Python (coleam00 demonstrates it); OwlBear already has BrowserManager
- [x] **Architecture fit** — Maps to SkillRegistry (skill) + FunctionToolset (render tool) + BrowserManager (rendering)
- [x] **Implementation approach** — Skill + RenderService + DiagramToolset; total ~200 LOC new code
