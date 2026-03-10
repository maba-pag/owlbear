---
id: 708
title: Add HTML diagram templates to visual-output skill
status: todo
priority: important
created: 2026-03-09T15:25:10.3927354+01:00
updated: 2026-03-10T02:44:08.6333668+01:00
tags:
    - scope:copilot
    - docs
depends_on:
    - 706
class: standard
---

Adapt 3 reference HTML templates from visual-explainer v0.6.3 (MIT): architecture overview, data table, Mermaid flowchart. Place in .github/skills/visual-output/templates/.
Adaptation strategy: copy from source, update HTML comment headers to reference visual-output skill only -- keep all CSS, JS, and example content intact (research Approach A).
See docs/research/html-diagram-templates-research.md for full analysis.

AC:
- [ ] .github/skills/visual-output/templates/ directory exists with exactly 3 files: architecture.html, data-table.html, mermaid-flowchart.html
- [ ] architecture.html: self-contained HTML with inline CSS, CSS Grid card layout, depth tiers (hero/default/recessed), pipeline steps with arrow separators, inline SVG flow arrows, staggered fade-in animation
- [ ] data-table.html: semantic table with sticky header, KPI summary cards, status badges (green/red/amber -- no emoji), collapsible details section, summary footer row
- [ ] mermaid-flowchart.html: Mermaid ESM CDN import (mermaid@11 + @mermaid-js/layout-elk), zoom/pan/pinch controls, diagram-shell pattern (.mermaid-wrap > viewport > canvas), smart-fit algorithm
- [ ] Each template is a complete valid HTML document (no build step, no local dependencies; only mermaid-flowchart uses CDN imports)
- [ ] All 3 templates include prefers-color-scheme dark/light support and prefers-reduced-motion: reduce media query
- [ ] Each template uses a distinct curated palette (architecture=terracotta/sage, data-table=rose/cranberry, flowchart=teal/cyan) -- palettes must not be changed
- [ ] HTML comment block at top of each file references visual-output skill (not visual-explainer)
- [ ] Source attribution: verify existing entry in docs/sources/overview.md covers template adoption (already added by researcher -- confirm, do not duplicate)

[[2026-03-10]] Tue 02:43
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| 2-3 .html files in templates/ | Vague count, no file names | REWRITTEN: exactly 3 named files |
| Architecture template: HTML + CSS + Mermaid CDN | WRONG: architecture.html uses CSS Grid + SVG, NOT Mermaid | REWRITTEN: correct patterns listed |
| Data table: CSS Grid, responsive, curated palette | Incomplete: misses KPI cards, status badges, sticky header | REWRITTEN: full pattern list |
| (missing) mermaid-flowchart template | Missing entirely from original AC | ADDED: CDN import, zoom/pan, diagram-shell |
| Valid HTML, no build step | Clear | KEPT (refined: clarified CDN exception for flowchart) |
| Follow aesthetic constraints from skill | References future #706 output | REPLACED: explicit palette + media query ACs |
| Source attribution | Clear | KEPT (clarified: verify existing entry, do not duplicate) |

### Architecture Notes
- Pure asset task: 3 static HTML files in .github/skills/visual-output/templates/
- No Python code, no module layering concerns, no security surface
- TDD N/A: static HTML reference templates, not testable code
- depends_on #706 is correct: skill SKILL.md must exist before templates dir
- Research doc is thorough (.85 confidence): all 3 templates analyzed in detail
- Adaptation strategy A (minimal) is correct: copy + comment header update only
- Attribution already in docs/sources/overview.md line 35 by researcher

### Changes Made
- Rewrote all AC lines for precision (9 verifiable criteria)
- Fixed factual error: Mermaid CDN removed from architecture AC, added to flowchart AC
- Added explicit mermaid-flowchart.html AC (was missing)
- Added prefers-color-scheme + prefers-reduced-motion AC (from research section 3d)
- Added palette constraint AC (distinct palettes per template)
- Added adaptation strategy in body description
- Added research doc reference in body

### Dependencies
- Verified: depends_on #706 (Create visual-output agent skill) -- status: todo. Correct ordering.
- No additional dependencies needed
