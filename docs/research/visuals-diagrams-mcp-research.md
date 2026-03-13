# Visuals, Diagrams & MCP Integrations — Epic Research

> **Owning task:** #582 — Research: Visuals, Diagrams & MCP Integrations
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

OwlBear is a headless AI dev daemon communicating via CLI and Slack. Task #582 asks: what diagram generation, visual output, and MCP integration patterns should OwlBear adopt? This is an epic-level synthesis of children #592 (visual-explainer), #593 (excalidraw-diagram-skill), #594 (excalidraw-mcp), and #595 (pinchtab), plus additional landscape analysis.

Key decisions: (a) which rendering approach, (b) MCP server vs native toolset vs skill, (c) delivery channels.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | hustcc/mcp-mermaid | <https://github.com/hustcc/mcp-mermaid> | .85 — 463 stars, TS MCP server, Mermaid rendering via Puppeteer |
| 2 | antoinebou12/uml-mcp | <https://github.com/antoinebou12/uml-mcp> | .80 — Python MCP server, 12+ diagram types, Kroki + PlantUML fallback |
| 3 | excalidraw/excalidraw-mcp | <https://github.com/excalidraw/excalidraw-mcp> | .75 — Official Excalidraw MCP App, 3k stars, MCP Apps extension |
| 4 | yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | .80 — 1.3k stars, 26-tool programmatic canvas, WebSocket sync |
| 5 | coleam00/excalidraw-diagram-skill | (child #593 research) | .90 — Skill-based Excalidraw JSON generation + Playwright render |
| 6 | nicobailon/visual-explainer | (child #592 research) | .85 — HTML diagram generation via agent skill + Mermaid routing |
| 7 | Kroki.io | <https://kroki.io/> | .90 — Unified HTTP API, 20+ diagram types, server-side rendering |
| 8 | peng-shawn/mermaid-mcp-server | <https://github.com/peng-shawn/mermaid-mcp-server> | .70 — 223 stars, Puppeteer-based Mermaid → PNG, MCP stdio |

## 3. Analysis

### 3.1 Rendering Approaches

| Criterion | Kroki API (.90) | Playwright headless (.80) | External MCP server (.55) |
|-----------|----------------|--------------------------|--------------------------|
| Deps | httpx (existing) | Playwright (existing) | Node.js + npx |
| KISS | High — single POST | Medium — browser lifecycle | Low — cross-language IPC |
| Diagram types | 20+ (Mermaid, PlantUML, GraphViz, Excalidraw, D2...) | Mermaid + Excalidraw JSON | Varies by server |
| Headless/daemon | Yes — HTTP only | Yes — OwlBear has BrowserManager | Requires Node.js runtime |
| Offline | Only with self-hosted Docker | Yes | Varies |
| Latency | ~200ms (remote), ~50ms (local Docker) | ~1-3s (browser startup) | ~1-5s (process startup) |
| Output formats | SVG, PNG, PDF | PNG (screenshot), SVG | PNG, SVG |
| Maintenance | Zero (API consumer) | Low (render template) | High (Node.js dep) |

### 3.2 Integration Architecture

| Criterion | Agent Skill (.85) | Native Toolset (.80) | External MCP (.55) |
|-----------|------------------|---------------------|-------------------|
| OwlBear fit | Best — SkillRegistry exists | Good — FunctionToolset | Poor — Node.js, not Python |
| Complexity | ~100 lines SKILL.md | ~200 LOC Python | 0 OwlBear code, but runtime dep |
| Flexibility | Prompt-driven, adaptable | Code-driven, typed | Depends on server's tools |
| Iterative refinement | render → view → fix loop | Same | Depends on server |
| KISS/YAGNI | High | High | Low — over-engineered for OwlBear |

### 3.3 Delivery Channels

| Channel | Image support | How |
|---------|--------------|-----|
| CLI | VisualFeedbackToolset → `send_file()` | File path printed to terminal |
| Slack | SlackChannel → `files_upload_v2()` | PNG uploaded as thread attachment |
| Browser | ScreenshotService → `capture_browser()` | Already built for error screenshots |

All channels already support image delivery. No new infrastructure needed.

### 3.4 Child Task Findings Summary

| Child | Key Finding | Recommendation |
|-------|-------------|----------------|
| #592 visual-explainer | HTML generation via agent prompts + Mermaid routing table | Adopt HTML diagram skill (.80) |
| #593 excalidraw-skill | Skill-based Excalidraw JSON generation + Playwright render | Adopt skill + render service (.85) |
| #594 excalidraw-mcp | MCP Apps need HTML host; OwlBear channels can't render | Do NOT adopt MCP Apps (.70) |
| #595 pinchtab | Dashboard/tab management patterns | Deferred — someday priority |

## 4. Recommendation (.85 confidence)

**Two-tier approach: Kroki for quick diagrams, Excalidraw skill for rich visuals.**

### Tier 1: Kroki-based diagram generation (quick wins)

- Add a `DiagramService` (~80 LOC) wrapping Kroki's HTTP API via existing `httpx`
- Single `generate_diagram` tool: takes diagram type + source text, returns PNG/SVG path
- Supports Mermaid, PlantUML, GraphViz, D2, C4 out of the box — no new deps
- Falls back to free kroki.io; optionally self-host via Docker for offline use
- Delivers via existing `VisualFeedbackToolset` → CLI/Slack channels

### Tier 2: Excalidraw skill for rich architecture diagrams (builds on #593)

- Skill teaches agents to generate `.excalidraw` JSON via LLM prompts
- `ExcalidrawRenderService` uses existing BrowserManager + Playwright to render
- Render-view-fix loop enables iterative diagram refinement
- Only deploy when Tier 1 proves insufficient for architecture diagrams

### Do NOT adopt

- External MCP servers (hustcc/mcp-mermaid, uml-mcp) — adds Node.js dep, YAGNI
- MCP Apps rendering (excalidraw/excalidraw-mcp) — requires HTML host OwlBear doesn't have
- Live canvas with WebSocket (yctimlin) — over-engineered for headless daemon
- Mermaid-to-Excalidraw conversion — YAGNI

**Risk:** Kroki free service has no SLA. Mitigation: self-host Kroki Docker image for production (`docker run -d -p 8000:8000 yuzutech/kroki`, ~50MB image).

## 5. Follow-up Tasks

```powershell
kanban\kanban-md.exe create "Implement DiagramService wrapping Kroki HTTP API" --priority needed --tags "phase-research,scope:core,tooling" --body "Create src/owlbear/tools/diagram/service.py with DiagramService wrapping Kroki HTTP API. Uses existing httpx async client. POST {diagram_type, diagram_source, output_format} to kroki.io, save result as PNG/SVG. Config: kroki_server_url (default https://kroki.io). See docs/visuals-diagrams-mcp-research.md §4 Tier 1. AC: 1. generate(type, source, format) returns image bytes. 2. Uses httpx with timeout config. 3. Supports mermaid/plantuml/graphviz/d2/c4. 4. Unit tests with mocked HTTP."

kanban\kanban-md.exe create "Create DiagramToolset exposing generate_diagram tool" --priority needed --tags "phase-research,scope:core,tooling" --body "Create src/owlbear/tools/diagram/toolset.py as FunctionToolset. Expose generate_diagram(diagram_type, source_code, output_format='png') tool. Saves output via ScreenshotService, delivers via VisualFeedbackToolset channel. See docs/visuals-diagrams-mcp-research.md §4 Tier 1. AC: 1. Tool registered via FunctionToolset. 2. Calls DiagramService.generate(). 3. Returns saved file path. 4. Error handling for invalid diagram syntax."

kanban\kanban-md.exe create "Create Excalidraw diagram skill (SKILL.md + references)" --priority important --tags "phase-research,scope:copilot,agent" --body "Port coleam00/excalidraw-diagram-skill prompt methodology to .github/skills/excalidraw-diagram/. Include SKILL.md with design philosophy, pattern library, Excalidraw JSON schema guidance. See docs/excalidraw-diagram-skill-research.md §4 and docs/visuals-diagrams-mcp-research.md §4 Tier 2. AC: 1. Skill loads via SkillRegistry. 2. SKILL.md contains diagram design methodology. 3. Reference files contain JSON templates and color palette."

kanban\kanban-md.exe create "Implement ExcalidrawRenderService using BrowserManager" --priority important --tags "phase-research,scope:core,tooling" --body "Create src/owlbear/tools/diagram/excalidraw_render.py using existing BrowserManager + Playwright to render .excalidraw JSON to PNG. Port render template from coleam00 (exportToSvg via esm.sh). See docs/excalidraw-diagram-skill-research.md §3.2. AC: 1. render(path) returns PNG bytes. 2. Uses existing BrowserManager. 3. Validates JSON before rendering. 4. Tests with sample .excalidraw fixture."

kanban\kanban-md.exe create "Add kroki_server_url to OwlBear config" --priority important --tags "phase-research,scope:core,config" --body "Add kroki_server_url: str = 'https://kroki.io' field to OwlBear settings. Used by DiagramService. See docs/visuals-diagrams-mcp-research.md §4. AC: 1. Field exists in settings model. 2. DiagramService reads it at init. 3. Documented in config docs."
```

## 6. Attribution Updates

| Source | URL | License | What | Where Used | Date |
|--------|-----|---------|------|------------|------|
| hustcc/mcp-mermaid | <https://github.com/hustcc/mcp-mermaid> | MIT | MCP Mermaid rendering patterns, output format options | `docs/visuals-diagrams-mcp-research.md` | 2026-03-07 |
| antoinebou12/uml-mcp | <https://github.com/antoinebou12/uml-mcp> | MIT | Python MCP server, Kroki fallback strategy, diagram type support | `docs/visuals-diagrams-mcp-research.md` | 2026-03-07 |
| Kroki.io | <https://kroki.io/> | MIT | Unified diagram rendering API, supported types/formats | `docs/visuals-diagrams-mcp-research.md` | 2026-03-07 |
| peng-shawn/mermaid-mcp-server | <https://github.com/peng-shawn/mermaid-mcp-server> | MIT | Puppeteer-based Mermaid rendering, file save patterns | `docs/visuals-diagrams-mcp-research.md` | 2026-03-07 |
