---
id: 582
title: 'Research: Visuals, Diagrams & MCP Integrations'
status: archived
priority: important
created: 2026-03-05T23:50:09.6805028+01:00
updated: 2026-03-07T18:08:07.3402746+01:00
started: 2026-03-07T04:06:55.2799705+01:00
completed: 2026-03-07T18:08:07.3402746+01:00
tags:
    - research
    - phase-research
    - scope:copilot
class: standard
---

Epic: Analyze diagram generation, UI components, and Excalidraw MCP integration patterns. Children cover individual repos.

**Research doc:** See docs/research/visuals-diagrams-mcp.md

**Key findings:**
- Kroki.io (unified HTTP API, 20+ diagram types) is the simplest integration for quick diagrams  single httpx POST, zero new deps
- Excalidraw skill pattern (coleam00 #593) is best for rich architecture diagrams  LLM generates JSON, Playwright renders
- External MCP servers (hustcc/mcp-mermaid, uml-mcp) are YAGNI  adds Node.js runtime dependency
- MCP Apps rendering (excalidraw/excalidraw-mcp #594) needs HTML host, OwlBear channels can't render iframes
- All delivery channels (CLI, Slack) already support image output via VisualFeedbackToolset

**Recommendation (.85 confidence):** Two-tier approach:
- Tier 1 (needed): DiagramService wrapping Kroki API + DiagramToolset (generate_diagram tool)
- Tier 2 (important): Excalidraw skill + ExcalidrawRenderService using BrowserManager

**Follow-up tasks:** 5 kanban tasks proposed (see research doc section 5)
**Children:** #592 (visual-explainer), #593 (excalidraw-skill), #594 (excalidraw-mcp), #595 (pinchtab)
**Research checklist:** All 5 mandatory items completed.
