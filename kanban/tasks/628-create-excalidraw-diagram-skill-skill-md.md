---
id: 628
title: Create Excalidraw diagram skill (SKILL.md + references)
status: backlog
priority: nice-to-have
created: 2026-03-07T05:21:58.5384709+01:00
updated: 2026-03-07T13:56:52.5500563+01:00
started: 2026-03-07T13:56:52.5500563+01:00
tags:
    - phase-research
    - scope:copilot
    - agent
class: standard
---

Tier 2 (YAGNI until Tier 1 Kroki proves insufficient for architecture diagrams). Port coleam00 prompt methodology.

AC:

- [ ] .github/skills/excalidraw-diagram/SKILL.md with diagram design methodology
- [ ] Adapts coleam00 prompt patterns for Excalidraw JSON generation
- [ ] Includes element library reference (rectangles, arrows, text, groups)
- [ ] Includes curated color palette and layout guidelines
- [ ] Skill loads via SkillRegistry (test manually)
- [ ] Reference files contain 2-3 JSON templates (architecture, flowchart, sequence)

Ref: docs/excalidraw-diagram-skill-research.md, docs/visuals-diagrams-mcp-research.md section 4 Tier 2

[[2026-03-07]] Sat 13:56
## Research Notes (2026-03-07)

Research complete. See docs/excalidraw-skill-creation-research.md.

Key decisions:
- Adapt coleam00 SKILL.md (compress from 450 to ~150 lines)
- Remove render pipeline instructions (separate task)
- Add YAML frontmatter per OwlBear skill conventions
- Include 3 reference files: color-palette.md, element-templates.md, json-schema.md
- Include 3 JSON diagram templates: architecture (fan-out), flowchart (diamond), sequence (timeline)
- Prerequisite: ExcalidrawRenderService for full validate loop (not a blocker for skill creation)
