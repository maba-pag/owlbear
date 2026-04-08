# Diagram Rendering Tool for v2 Agents

> **Owning task:** #683 — Research: diagram rendering tool for agents
> **Date:** 2026-04-08  **Status:** Complete

## 1. Context and Question

v1 had a Kroki-based `DiagramService` + `DiagramToolset` (~180 LOC) for rendering Mermaid, PlantUML, GraphViz, D2, and Excalidraw to image files. v2 operates inside VS Code Copilot Chat, not as a standalone daemon. The fundamental question: does v2 even need a rendering tool, or does VS Code already solve this?

## 2. Sources Studied

| # | Source | URL / Location | Relevance |
|---|--------|----------------|-----------|
| 1 | VS Code built-in tools list | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features#_chat-tools> | .95 — authoritative |
| 2 | VS Code Mermaid in chat | <https://code.visualstudio.com/docs/copilot/reference/copilot-vscode-features> (`mermaid-chat.enabled`) | .95 — renders Mermaid in chat UI |
| 3 | bierner/markdown-mermaid ext | <https://github.com/mjbvz/vscode-markdown-mermaid> | .85 — renders Mermaid in Markdown Preview |
| 4 | v1 DiagramService | `v1/src/owlbear/tools/diagram/service.py` | .90 — prior art |
| 5 | v1 DiagramToolset | `v1/src/owlbear/tools/diagram/toolset.py` | .90 — prior art |
| 6 | Prior research #582 | `.owlbear/research/visuals-diagrams-mcp.md` | .85 — v1-era analysis |
| 7 | Prior research #629 | `.owlbear/research/excalidraw-render-service.md` | .80 — Kroki vs Playwright |
| 8 | h-excalidraw-diagram skill | `share/skills/h-excalidraw-diagram/SKILL.md` | .80 — existing v2 skill |
| 9 | h-visual-output skill | `share/skills/h-visual-output/SKILL.md` | .80 — existing v2 skill |

## 3. Analysis

### 3.1 AC2: Does `renderMermaidDiagram` Exist as a Deferred Tool?

**No.** The complete VS Code built-in tools list (source #1) does not include `renderMermaidDiagram`. There is no such deferred tool, extension tool, or MCP tool in the workspace.

What does exist:

| Feature | Type | Agent-callable? | Output |
|---------|------|-----------------|--------|
| `mermaid-chat.enabled` | Chat UI rendering | No — automatic | Inline in chat response |
| `bierner.markdown-mermaid` | Markdown Preview | No — user-triggered | Rendered in Preview panel |
| `h-excalidraw-diagram` skill | Agent skill | Yes — agent writes JSON | `.excalidraw` file |
| `h-visual-output` skill | Agent skill | Yes — agent writes HTML | `.html` file with Mermaid CDN |

### 3.2 AC1: Rendering Options — v2 Context

v2's architecture changes the problem fundamentally:

| Criterion | v1 (daemon, CLI/Slack) | v2 (VS Code Copilot Chat) |
|-----------|----------------------|---------------------------|
| User sees diagram | Must render to file | Chat UI renders Mermaid automatically |
| Delivery channel | File path → CLI/Slack upload | Chat response, Markdown Preview, or file |
| Rendering infra | Agent must generate image | IDE handles rendering |
| File persistence | Required for delivery | Optional — only if docs/export needed |

**Rendering path comparison:**

| Path | Coverage | Effort | Image file? | KISS |
|------|----------|--------|-------------|------|
| A: Mermaid in chat (`mermaid-chat.enabled`) | Mermaid only | Zero | No | Highest |
| B: HTML + Mermaid CDN (h-visual-output) | Mermaid + styled HTML | Exists | No (HTML file) | High |
| C: `.excalidraw` JSON (h-excalidraw-diagram) | Free-form diagrams | Exists | No (JSON file) | High |
| D: Kroki MCP tool (port from v1) | 20+ diagram types | ~100 LOC | Yes (SVG/PNG) | Medium |
| E: Mermaid CLI (local) | Mermaid only | Node.js dep | Yes (SVG/PNG) | Low |
| F: Playwright render service | Excalidraw → PNG | ~120 LOC | Yes (PNG) | Low |

### 3.3 Gap Analysis

| Use Case | Already Solved? | By What? |
|----------|----------------|----------|
| Agent shows diagram to user in chat | Yes | Path A (mermaid-chat.enabled) |
| Agent creates persistent diagram file | Yes | Path B (HTML) or C (Excalidraw JSON) |
| Agent creates rendered image (PNG/SVG) | **No** | Would need Path D, E, or F |
| User previews Mermaid in markdown | Yes | bierner.markdown-mermaid extension |

The only gap is **producing standalone image files**. This matters for:
- Embedding in documentation (README, research docs)
- External delivery (Slack, email)
- Visual feedback loops (agent views rendered result)

In v2's VS Code-native model, the first two are edge cases. The third could use the chat UI.

### 3.4 Architecture Fit for Each Option (If Image Files Needed)

| Option | Integration | KISS | YAGNI risk |
|--------|-------------|------|------------|
| Kroki MCP tool on mcp-project | FastMCP tool, httpx POST | High | Medium — no proven use case yet |
| Mermaid CLI via run_in_terminal | `npx @mermaid-js/mermaid-cli` | Medium | High — Node.js dep |
| Playwright render service | New MCP tool or script | Low | High — complex for unproven need |

## 4. Recommendation (.85 confidence)

**Do nothing now. The current v2 tooling covers diagram rendering for the VS Code context.**

1. **Mermaid in chat** (`mermaid-chat.enabled`) — renders automatically when agents emit Mermaid code blocks in responses. Zero effort, zero code.
2. **h-visual-output skill** — agents can write self-contained HTML with Mermaid CDN for richer diagrams. Already exists.
3. **h-excalidraw-diagram skill** — agents can write `.excalidraw` JSON for free-form architecture diagrams. Already exists.

**If image file rendering becomes needed** (documented use case for docs or external delivery), the path is:
- Port v1's `DiagramService` pattern as a FastMCP tool on `mcp-project` (~100 LOC Python, Kroki HTTP API, httpx)
- This is well-researched (prior tasks #582, #617, #620, #627, #629) and proven in v1

**Do NOT build:**
- Mermaid CLI wrapper — adds Node.js dependency, YAGNI
- Playwright-based Excalidraw renderer — complex, deferred per #629 research
- Custom MCP diagram server — over-engineered for current needs

Challenge: FALLBACK — subagent not invoked (T1 autonomous finding, no architectural change)

### Tier Classification: T1 — Autonomous

No new capability needed. The IDE already provides diagram rendering. A follow-up task to verify the `mermaid-chat.enabled` setting is sufficient.

## 5. Follow-up Tasks

- Verify `mermaid-chat.enabled` is enabled and document rendering paths for agents
- Optional: Kroki MCP tool (only if image file output becomes a requirement)
