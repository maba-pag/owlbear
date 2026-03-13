---
id: 628
title: Create Excalidraw diagram skill (SKILL.md + references)
status: archived
priority: nice-to-have
created: 2026-03-07T05:21:58.5384709+01:00
updated: 2026-03-11T18:28:58.5047115+01:00
started: 2026-03-07T13:56:52.5500563+01:00
completed: 2026-03-11T18:28:58.5047115+01:00
tags:
    - phase-research
    - scope:copilot
    - agent
claimed_by: auditor
claimed_at: 2026-03-11T18:28:48.3016613+01:00
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

Ref: docs/research/excalidraw-diagram-skill.md, docs/research/visuals-diagrams-mcp.md section 4 Tier 2

[[2026-03-07]] Sat 13:56
## Research Notes (2026-03-07)

Research complete. See docs/research/excalidraw-skill-creation.md.

Key decisions:
- Adapt coleam00 SKILL.md (compress from 450 to ~150 lines)
- Remove render pipeline instructions (separate task)
- Add YAML frontmatter per OwlBear skill conventions
- Include 3 reference files: color-palette.md, element-templates.md, json-schema.md
- Include 3 JSON diagram templates: architecture (fan-out), flowchart (diamond), sequence (timeline)
- Prerequisite: ExcalidrawRenderService for full validate loop (not a blocker for skill creation)

[[2026-03-11]] Wed 10:45
## Architecture Review
**Verdict:** APPROVED

### Refined AC
- [ ] Create .github/skills/excalidraw-diagram/SKILL.md (~150 lines) with design methodology, quality checklist, workflow steps
- [ ] SKILL.md has YAML frontmatter with name: excalidraw-diagram and description
- [ ] Adapts coleam00 SKILL.md: compress ~450 to ~150 lines, remove render pipeline instructions (#629), keep design methodology
- [ ] Create references/color-palette.md with semantic color mapping
- [ ] Create references/element-templates.md with JSON snippets for core element types
- [ ] Create references/json-schema.md with Excalidraw JSON format reference
- [ ] Include 3 complete JSON diagram examples: architecture (fan-out), flowchart (diamond), sequence (timeline)
- [ ] All files are pure Markdown/JSON  no Python code
- [ ] VS Code Copilot recognizes the skill (frontmatter validates, skill appears in list)
- [ ] Log coleam00/excalidraw-diagram-skill in docs/sources/overview.md

### Architecture Notes
- Domain: scope:copilot only, no layering concerns
- Pattern: follows kanban-md (SKILL.md + references/) structure
- TDD: N/A for Markdown-only deliverable
- SkillRegistry subdir limitation is pre-existing, not a blocker
- No dependency on #629 (render service)

[[2026-03-11]] Wed 10:45
## Architecture Review
**Verdict:** APPROVED

### Refined AC
- [ ] Create .github/skills/excalidraw-diagram/SKILL.md (~150 lines) with design methodology, quality checklist, workflow steps
- [ ] SKILL.md has YAML frontmatter with name: excalidraw-diagram and description
- [ ] Adapts coleam00 SKILL.md: compress ~450 to ~150 lines, remove render pipeline instructions (#629), keep design methodology
- [ ] Create references/color-palette.md with semantic color mapping
- [ ] Create references/element-templates.md with JSON snippets for core element types
- [ ] Create references/json-schema.md with Excalidraw JSON format reference
- [ ] Include 3 complete JSON diagram examples: architecture (fan-out), flowchart (diamond), sequence (timeline)
- [ ] All files are pure Markdown/JSON  no Python code
- [ ] VS Code Copilot recognizes the skill (frontmatter validates, skill appears in list)
- [ ] Log coleam00/excalidraw-diagram-skill in docs/sources/overview.md

### Architecture Notes
- Domain: scope:copilot only, no layering concerns
- Pattern: follows kanban-md (SKILL.md + references/) structure
- TDD: N/A for Markdown-only deliverable
- SkillRegistry subdir limitation is pre-existing, not a blocker
- No dependency on #629 (render service)

[[2026-03-11]] Wed 10:45
## Architecture Review
**Verdict:** APPROVED

### Refined AC
- [ ] Create .github/skills/excalidraw-diagram/SKILL.md (~150 lines) with design methodology, quality checklist, workflow steps
- [ ] SKILL.md has YAML frontmatter with name: excalidraw-diagram and description
- [ ] Adapts coleam00 SKILL.md: compress ~450 to ~150 lines, remove render pipeline instructions (#629), keep design methodology
- [ ] Create references/color-palette.md with semantic color mapping
- [ ] Create references/element-templates.md with JSON snippets for core element types
- [ ] Create references/json-schema.md with Excalidraw JSON format reference
- [ ] Include 3 complete JSON diagram examples: architecture (fan-out), flowchart (diamond), sequence (timeline)
- [ ] All files are pure Markdown/JSON  no Python code
- [ ] VS Code Copilot recognizes the skill (frontmatter validates, skill appears in list)
- [ ] Log coleam00/excalidraw-diagram-skill in docs/sources/overview.md

### Architecture Notes
- Domain: scope:copilot only, no layering concerns
- Pattern: follows kanban-md (SKILL.md + references/) structure
- TDD: N/A for Markdown-only deliverable
- SkillRegistry subdir limitation is pre-existing, not a blocker
- No dependency on #629 (render service)

[[2026-03-11]] Wed 16:20
## Test-Writer Notes
Non-implementation task (Markdown/JSON skill files only, no Python code). Architecture review confirms TDD: N/A. Passing through to builder.

-t

-t

-t

[[2026-03-11]] Wed 17:32
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Skill file only, no behavior/API/convention change; skills auto-discovered via frontmatter |
| 2 | Docstrings complete | No | N/A | Markdown/JSON-only deliverable, no Python modules changed |
| 3 | sources/overview.md | Yes | Updated | Added coleam00/excalidraw-diagram-skill attribution row under Task #628 section |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | Yes | Pass | docs/research/excalidraw-skill-creation.md exists and referenced in task body |
| 6 | No impact | -- | -- | Items 3 and 5 apply |

### Files Updated
- docs/sources/overview.md (added Excalidraw Diagram Skill section with coleam00 attribution)

### Scratch Files Cleaned
- None found for 628-*

[[2026-03-11]] Wed 18:28
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SKILL.md ~150 lines with methodology | 136 lines, design philosophy, workflow, quality checklist, diagram patterns | PASS |
| YAML frontmatter name+description | Lines 1-4: name: excalidraw-diagram, description present | PASS |
| Adapts coleam00, compress ~450 to ~150 | 136 lines, coleam00 attribution in file, no render pipeline | PASS |
| references/color-palette.md | 63 lines, semantic backgrounds/strokes/text, pairing rules | PASS |
| references/element-templates.md | 658 lines, rectangle/diamond/ellipse/arrow/text/line templates | PASS |
| references/json-schema.md | Document structure, element fields, arrow bindings, validation rules | PASS |
| 3 JSON diagram examples | Architecture (L202), Flowchart (L326), Sequence (L532) | PASS |
| All pure Markdown/JSON | 4 .md files, 0 .py files confirmed | PASS |
| VS Code recognizes skill | Appears in VS Code Copilot skills context list | PASS |
| docs/sources/overview.md attribution | coleam00/excalidraw-diagram-skill row at L63 | PASS |

### Test Results
- pytest: N/A (Markdown-only deliverable, no Python code changed)
- ruff: N/A (no Python files in skill directory)
- Collection: 4134 tests collect without error

### Confidence: .97
### Action: archive
