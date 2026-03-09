---
id: 708
title: Add HTML diagram templates to visual-output skill
status: ideation
priority: important
created: 2026-03-09T15:25:10.3927354+01:00
updated: 2026-03-09T15:26:38.7750332+01:00
tags:
    - scope:copilot
    - docs
depends_on:
    - 706
class: standard
---

Adapt 2-3 reference HTML templates from visual-explainer (MIT): architecture overview, data table, Mermaid flowchart. Place in .github/skills/visual-output/templates/.
See docs/research/visual-explainer-research.md S3b.

AC:
- [ ] .github/skills/visual-output/templates/ directory exists with 2-3 .html files
- [ ] Architecture overview template: self-contained HTML with inline CSS, Mermaid CDN
- [ ] Data table template: CSS Grid layout, responsive, curated palette
- [ ] Each template is a complete, valid HTML document (no build step)
- [ ] Templates follow aesthetic constraints defined in the visual-output skill
- [ ] Source attribution in docs/sources/overview.md for adapted templates
