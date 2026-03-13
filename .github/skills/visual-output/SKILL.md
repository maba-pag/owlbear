---
name: visual-output
description: "Generate styled HTML diagrams, tables, and architecture visuals. Covers workflow (think/structure/style/deliver), Mermaid routing, aesthetic constraints, and two delivery paths (HTML+Browser, Kroki). Use when producing visual output for the user."
---

# Visual Output Skill

> **VS Code agent note:** This skill references OwlBear PydanticAI runtime tools
> (FileToolset, BrowserToolset, VisualFeedbackToolset, DiagramToolset) not available
> in VS Code Copilot agent mode. Use VS Code edit/file/terminal tools instead when
> adapting these procedures for agent use.

Produce high-quality, self-contained visual output (diagrams, tables, architecture maps)
for delivery to the user via browser screenshot or Kroki render.

> Adapted from [nicobailon/visual-explainer](https://github.com/nicobailon/visual-explainer) (MIT).

## Phase 1 — Think

Before writing any HTML or diagram code:

1. Identify the **audience** (developer, stakeholder, mixed) and **content type** (see routing table below).
2. Pick the **delivery path**: HTML+Browser for rich pages, Kroki for quick diagrams.
3. Choose a palette from the approved list (Phase 3). Never invent colors.

## Phase 2 — Structure

Use the routing table to pick the right rendering approach:

| Content type | Approach | When to use |
|-------------|----------|-------------|
| Flowchart / sequence / ER | Mermaid (`graph`, `sequenceDiagram`, `erDiagram`) | Relationships, flows, processes |
| Architecture overview | CSS Grid cards with depth tiers | System components, layers, boundaries |
| Data comparison / metrics | HTML `<table>` with status badges | Side-by-side data, KPIs, audit results |
| Tree / hierarchy | Mermaid `graph TD` or nested CSS Grid | Dependency trees, org charts |
| Timeline / phases | Mermaid `gantt` or horizontal CSS Grid | Project phases, roadmaps |
| Simple box diagram | Kroki path (PlantUML or D2) | Quick renders, no styling needed |

Build the content structure first — headings, sections, data groupings. No styling yet.

## Phase 3 — Style

### Approved palettes

| Name | Background | Primary | Accent | Text |
|------|-----------|---------|--------|------|
| Midnight | `#0f172a` | `#3b82f6` | `#22d3ee` | `#e2e8f0` |
| Forest | `#0c1a0c` | `#22c55e` | `#a3e635` | `#dcfce7` |
| Ember | `#1a0a0a` | `#ef4444` | `#f97316` | `#fef2f2` |
| Slate | `#1e293b` | `#6366f1` | `#a78bfa` | `#e2e8f0` |
| Frost | `#f0f9ff` | `#0284c7` | `#06b6d4` | `#0c4a6e` |

### Forbidden patterns

- **No** `#000000` backgrounds or pure white `#ffffff` text on dark
- **No** Comic Sans, Papyrus, cursive, or fantasy fonts
- **No** rainbow gradients or more than 3 accent colors
- **No** `!important` overrides — fix specificity instead
- **No** inline `style=` attributes — use `<style>` block
- **No** animations or transitions (static output only)
- **No** external CSS/font CDNs except Mermaid CDN (`cdn.jsdelivr.net/npm/mermaid`)

### Anti-slop checklist

Before delivering, verify:

- [ ] **Squint test** — structure visible at arm's length (clear hierarchy, not a wall of text)
- [ ] **Swap test** — would a different palette break readability? If yes, fix contrast
- [ ] **Overflow** — no horizontal scroll, no clipped content at 1200px viewport
- [ ] **Self-contained** — single `.html` file, no external deps except Mermaid CDN

## Phase 4 — Deliver

### Path A: HTML + Browser (rich pages)

For styled HTML pages, tables, CSS Grid layouts, Mermaid-embedded diagrams:

1. **Write** — `FileToolset.write_file` → `.owlbear/diagrams/{name}.html` (self-contained, inline CSS)
2. **Open** — `BrowserToolset.browser_navigate` → `file://{absolute_path}`
3. **Capture** — `VisualFeedbackToolset.share_screenshot` → deliver PNG to channel

### Path B: Kroki (quick diagrams)

For simple Mermaid, PlantUML, Graphviz, or D2 diagrams that don't need custom styling:

1. **Render** — `DiagramToolset.generate_diagram` with diagram type and source code
2. Output is SVG/PNG, delivered directly — no browser step needed

### When to use which

- **Path A** when: custom styling, multiple sections, data tables, KPI cards, or CSS Grid layouts
- **Path B** when: single diagram, standard Mermaid/PlantUML, no custom colors needed
