---
id: 709
title: Add project-recap visual command
status: ideation
priority: nice-to-have
created: 2026-03-09T15:25:19.3510256+01:00
updated: 2026-03-09T15:26:39.4725233+01:00
tags:
    - scope:copilot
    - agent
depends_on:
    - 706
class: standard
---

Adapt visual-explainer's project-recap pattern as an OwlBear agent command. Reads git log + kanban board + codebase structure -> generates HTML mental model snapshot. Uses visual-output skill for output. Requires #707 (visual-output skill) first.
See docs/research/visual-explainer-research.md S3b.

AC:
- [ ] Agent command (instructions or prompt file) for project-recap
- [ ] Reads git log (recent commits), kanban board state, codebase top-level structure
- [ ] Generates self-contained HTML overview using visual-output skill patterns
- [ ] Output saved to .owlbear/diagrams/ directory
- [ ] Delivered via VisualFeedbackToolset (screenshot capture)
