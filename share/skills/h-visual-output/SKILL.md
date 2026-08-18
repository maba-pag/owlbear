---
name: h-visual-output
description: "Handbook: Styled HTML diagrams, tables, and architecture visuals"
user-invocable: true
---

# Visual Output Reference

Produce high-quality, self-contained visual output (diagrams, tables, architecture maps) for delivery via browser or Kroki render.

Boundary: this skill is for explanatory artifacts, reports, and diagrams. It is not the source of truth for production frontend app design; use `h-frontend-design` and `h-frontend-conventions` for Cockpit UI work.

> Adapted from [nicobailon/visual-explainer](https://github.com/nicobailon/visual-explainer) (MIT).

For Excalidraw-specific diagrams, see `h-excalidraw-diagram`.

## Content Type Routing

| Content type | Approach | When to use |
| --- | --- | --- |
| Flowchart / sequence / ER | Mermaid (`graph`, `sequenceDiagram`, `erDiagram`) | Relationships, flows, processes |
| Architecture overview | CSS Grid cards with depth tiers | System components, layers, boundaries |
| Data comparison / metrics | HTML `<table>` with status badges | Side-by-side data, KPIs, audit results |
| Tree / hierarchy | Mermaid `graph TD` or nested CSS Grid | Dependency trees, org charts |
| Timeline / phases | Mermaid `gantt` or horizontal CSS Grid | Project phases, roadmaps |
| Simple box diagram | Kroki path (PlantUML or D2) | Quick renders, no styling needed |

## Approved Palettes

| Name | Background | Primary | Accent | Text |
| --- | --- | --- | --- | --- |
| Midnight | `#0f172a` | `#3b82f6` | `#22d3ee` | `#e2e8f0` |
| Forest | `#0c1a0c` | `#22c55e` | `#a3e635` | `#dcfce7` |
| Ember | `#1a0a0a` | `#ef4444` | `#f97316` | `#fef2f2` |
| Slate | `#1e293b` | `#6366f1` | `#a78bfa` | `#e2e8f0` |
| Frost | `#f0f9ff` | `#0284c7` | `#06b6d4` | `#0c4a6e` |

## Forbidden Patterns

- **No** `#000000` backgrounds or pure white `#ffffff` text on dark
- **No** Comic Sans, Papyrus, cursive, or fantasy fonts
- **No** rainbow gradients or more than 3 accent colors
- **No** `!important` overrides — fix specificity instead
- **No** inline `style=` attributes — use `<style>` block
- **No** animations or transitions (static output only)
- **No** external CSS/font CDNs except Mermaid CDN (`cdn.jsdelivr.net/npm/mermaid`)

## Delivery Paths

### Path A: HTML + Browser (rich pages)

For styled HTML pages, tables, CSS Grid layouts, Mermaid-embedded diagrams:

1. **Write** — `create_file` to `.owlbear/scratch/{name}.html` (self-contained, inline CSS)
2. **Open** — `open_browser_page` to preview

### Path B: Kroki (quick diagrams)

For simple Mermaid, PlantUML, Graphviz, or D2 diagrams without custom styling:

1. **Render** — POST diagram source to Kroki HTTP API with appropriate `diagram_type` and `output_format`
2. Output is SVG/PNG, delivered directly

### When to use which

- **Path A** when: custom styling, multiple sections, data tables, KPI cards, or CSS Grid layouts
- **Path B** when: single diagram, standard Mermaid/PlantUML, no custom colors needed

## Anti-Slop Checklist

Before delivering, verify:

- [ ] **Squint test** — structure visible at arm's length (clear hierarchy, not a wall of text)
- [ ] **Swap test** — would a different palette break readability? If yes, fix contrast
- [ ] **Overflow** — no horizontal scroll, no clipped content at 1200px viewport
- [ ] **Self-contained** — single `.html` file, no external deps except Mermaid CDN

## Known Gotchas

- **Mermaid CDN is the only allowed external dependency.** All CSS, fonts, and scripts must be inline in the HTML file.
- **No `style=` inline attributes.** Use a `<style>` block in the `<head>`. Inline styles cause specificity battles.
- **Static output only.** No animations, transitions, or interactive JavaScript. Output must render identically as a screenshot.
- **Viewport target: 1200px.** Test for no horizontal overflow at this width.
