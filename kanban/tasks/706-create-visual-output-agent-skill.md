---
id: 706
title: Create visual-output agent skill
status: ideation
priority: important
created: 2026-03-09T15:24:42.3394502+01:00
updated: 2026-03-09T15:24:42.3394502+01:00
tags:
    - scope:copilot
    - agent
class: standard
---

Adapt visual-explainer's core workflow (think/structure/style/deliver) into a .github/skills/visual-output/SKILL.md. Include Mermaid routing table, aesthetic constraint rules, forbidden patterns. Target ~100 lines. Agents use existing filesystem_tools to write HTML, BrowserToolset to open it, VisualFeedbackToolset to capture/deliver.
See docs/research/visual-explainer-research.md S4.

AC:
- [ ] .github/skills/visual-output/SKILL.md exists (~100 lines)
- [ ] Mermaid routing table included (content type -> Mermaid vs CSS Grid vs table)
- [ ] Aesthetic constraint block (forbidden colors/fonts, curated palettes)
- [ ] Workflow section: think -> structure -> style -> deliver
- [ ] Delivery section references existing tools: filesystem write, BrowserToolset navigate, VisualFeedbackToolset capture
- [ ] Source attribution entry in docs/sources/overview.md for visual-explainer (MIT)
