---
id: 683
title: 'Research: diagram rendering tool for agents'
status: research
priority: nice-to-have
created: 2026-04-08T19:18:21.6102963+02:00
updated: 2026-04-08T19:18:21.6102963+02:00
tags:
    - scope:tools
    - ' type:research'
    - ' source:analysis'
class: standard
---

## Context

v1 had a Kroki API-based diagram tool — agents could render Mermaid, PlantUML, or other diagram source to PNG and deliver/persist images. v2 has the `h-excalidraw-diagram` skill (agents can write Excalidraw JSON) and Mermaid knowledge in prompts, but no tool that renders diagram source to an image file.

Currently agents can *write* diagram source but can't *render* it — the user must manually render or paste into a viewer.

## Research Questions

1. **What rendering options exist?**
   - Kroki API (v1 approach — external service, supports many formats)
   - Mermaid CLI (`@mermaid-js/mermaid-cli` — local, Mermaid only)
   - Excalidraw export (headless Puppeteer-based, Excalidraw JSON → PNG/SVG)
   - VS Code extension integration (Mermaid Preview, Excalidraw editor — already installed?)
   - `renderMermaidDiagram` tool already exists in deferred tools list — is this sufficient?

2. **What's the integration surface?**
   - MCP tool on a new/existing server?
   - Standalone script agents call via run_in_terminal?
   - Leverage existing VS Code deferred tool (`renderMermaidDiagram`)?

3. **What formats matter?** Mermaid covers most use cases (architecture, sequence, flowcharts). Is PlantUML/Excalidraw rendering needed?

## Acceptance Criteria

- [ ] AC1: Evaluate rendering options (local vs API, format coverage, complexity)
- [ ] AC2: Check if `renderMermaidDiagram` deferred tool already solves this
- [ ] AC3: Recommendation on approach with trade-offs
- [ ] AC4: Follow-up implementation task if warranted
