---
id: 593
title: 'Research: coleam00/excalidraw-diagram-skill'
status: backlog
priority: important
created: 2026-03-05T23:51:46.113192+01:00
updated: 2026-03-06T21:53:31.76484+01:00
started: 2026-03-06T21:44:34.8174636+01:00
tags:
    - research
    - phase-research
    - scope:copilot
parent: 582
class: standard
---

**Source:** https://github.com/coleam00/excalidraw-diagram-skill
Analyzed for Excalidraw skill patterns, diagram generation prompts, and MCP integration.

**Research doc:** See docs/excalidraw-diagram-skill-research.md

**Key findings:**
- LLM-driven Excalidraw JSON generation is proven (coleam00 skill, yctimlin MCP 1.3k stars)
- coleam00 skill pattern maps directly to OwlBear SkillRegistry
- Render-view-fix loop uses Playwright headless (OwlBear has BrowserManager)
- MCP server approach (yctimlin/lesleslie) is YAGNI for OwlBear

**Recommendation (.85):** Adopt skill pattern + render service + diagram toolset (~200 LOC)

**Follow-up tasks:** 3 tasks proposed in research doc section 5
