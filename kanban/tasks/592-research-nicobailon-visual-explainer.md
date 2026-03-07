---
id: 592
title: 'Research: nicobailon/visual-explainer'
status: backlog
priority: important
created: 2026-03-05T23:51:39.3191475+01:00
updated: 2026-03-06T21:54:55.5100419+01:00
started: 2026-03-06T21:44:33.1570697+01:00
tags:
    - research
    - phase-research
    - scope:copilot
parent: 582
class: standard
---

**Source:** https://github.com/nicobailon/visual-explainer (v0.5.1, MIT)
Analyzed for diagram generation, visual explanation patterns, and UI component ideas.

**Research doc:** See docs/visual-explainer-research.md

**Key findings:**
- Not a library -- a structured prompt engineering system (SKILL.md + templates + CSS refs)
- Core pattern: agent writes self-contained HTML file, browser opens it. No build step.
- Mermaid routing table maps content type to rendering approach (Mermaid vs CSS Grid vs table)
- Aesthetic constraint system prevents AI-slop (forbidden colors/fonts, curated palettes)
- Diff-review and project-recap commands are most valuable for OwlBear
- Integrates naturally with existing ScreenshotService + Playwright + VisualFeedbackToolset

**Recommendation (.80 confidence):** Adopt HTML diagram generation as OwlBear agent skill.
- Create visual-output skill (~100 lines SKILL.md) adapting think/structure/style/deliver workflow
- Add 2-3 adapted HTML templates (architecture, data table, flowchart)
- Implement DiagramToolset (generate_diagram + open_diagram tools)
- Defer: slides, sharing, AI images, fact-check

**Follow-up tasks:** 4 kanban tasks proposed (see research doc section 5)
**Prior art:** Anthropic skills repo (Apache-2.0), Dammyjay93/interface-design (MIT)
**Research checklist:** All 5 mandatory items completed.
