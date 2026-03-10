---
id: 706
title: Create visual-output agent skill
status: review
priority: important
created: 2026-03-09T15:24:42.3394502+01:00
updated: 2026-03-10T03:59:35.3851142+01:00
started: 2026-03-10T00:52:04.7209317+01:00
tags:
    - scope:copilot
    - agent
claimed_by: builder
claimed_at: 2026-03-10T03:59:35.3851142+01:00
class: standard
---

Adapt visual-explainer's core workflow (think/structure/style/deliver) into a .github/skills/visual-output/SKILL.md. Include Mermaid routing table, aesthetic constraint rules, forbidden patterns. Target ~100 lines. Agents use existing filesystem_tools to write HTML, BrowserToolset to open it, VisualFeedbackToolset to capture/deliver.
See docs/research/visual-explainer-research.md S4.
See docs/research/visual-output-skill-research.md for detailed design.

AC:
- [ ] .github/skills/visual-output/SKILL.md exists (~100 lines)
- [ ] YAML frontmatter follows OwlBear SKILL.md conventions (name, description fields)
- [ ] Mermaid routing table included (content type -> Mermaid vs CSS Grid vs table)
- [ ] Aesthetic constraint block (forbidden colors/fonts, curated palettes)
- [ ] Workflow section: think -> structure -> style -> deliver (each phase 3-6 lines)
- [ ] Delivery section covers TWO paths: (a) HTML path: FileToolset write_file -> BrowserToolset browser_navigate -> VisualFeedbackToolset share_screenshot; (b) Kroki path: DiagramToolset generate_diagram for quick Mermaid/PlantUML renders
- [ ] Source attribution entry in docs/sources/overview.md for visual-explainer (MIT)

[[2026-03-10]] Tue 02:32
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| SKILL.md exists (~100 lines) | Clear, verifiable | Keep |
| YAML frontmatter conventions | Added  ensures pattern consistency with 15 existing skills | Added |
| Mermaid routing table | Clear, verifiable | Keep |
| Aesthetic constraint block | Clear enough  research doc has detail (5 palettes, 7 forbidden items) | Keep |
| Workflow 4 phases | Clear, verifiable  added line budget (3-6 lines per phase) | Refined |
| Delivery section (was: HTML path only) | REFINED  research explicitly identifies TWO delivery paths (HTML+Browser and Kroki). Original AC omitted DiagramToolset. Now covers both paths with exact tool names. | Refined |
| Source attribution | Clear, verifiable | Keep |

### Architecture Notes
- Pure prompt engineering  zero code changes, no module layering concerns
- All 4 toolsets verified in codebase: FileToolset (src/owlbear/tools/filesystem.py), BrowserToolset (src/owlbear/tools/browser/toolset.py), VisualFeedbackToolset (src/owlbear/tools/visual_feedback.py), DiagramToolset (src/owlbear/tools/diagram/toolset.py)
- Exact tool names for AC: write_file, browser_navigate, share_screenshot, generate_diagram
- Existing SKILL.md pattern: YAML frontmatter (name + description) then markdown workflow steps (~50-120 lines across 15 skills)
- #708 (templates) is a sibling enhancement, NOT a dependency  skill works standalone
- TDD N/A  markdown skill file, no Python code to test
- KISS/YAGNI: research cuts 75% of visual-explainer source material. ~90 line target is appropriate.

### Changes Made
- Refined AC#5 (delivery): split into two paths with exact tool names (HTML path + Kroki path)
- Added AC: YAML frontmatter convention
- Added: per-phase line budget (3-6 lines)
- Added: research doc reference in body

### Dependencies
- No depends_on needed
- #708 (templates) is optional sibling, not a blocker

[[2026-03-10]] Tue 03:14
## Test-Writer Notes
- Non-implementation task (scope:copilot, agent  markdown SKILL.md creation)  no tests applicable.
- Architecture review confirms: 'TDD N/A  markdown skill file, no Python code to test'
- Passing through to builder.
