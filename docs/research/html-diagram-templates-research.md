# HTML Diagram Templates for Visual-Output Skill

> **Owning task:** #708 — Add HTML diagram templates to visual-output skill
> **Date:** 2026-03-10 **Status:** Complete

## 1. Context and Question

Task #708 asks: which HTML templates should ship with the visual-output skill, and how should they be adapted from visual-explainer (MIT)? The skill (#706) instructs agents to "read the reference template before generating" — templates are learning material, not runtime code.

**Key question:** What's the minimal set of templates that teaches agents the full range of visual patterns (CSS Grid cards, HTML tables, Mermaid diagrams) without bloat?

## 2. Sources Studied

| Source | URL | What | Relevance |
|--------|-----|------|-----------|
| nicobailon/visual-explainer v0.6.3 templates/ | <https://github.com/nicobailon/visual-explainer/tree/main/plugins/visual-explainer/templates> | 4 reference HTML templates (architecture, data-table, mermaid-flowchart, slide-deck) | .90 — primary pattern |
| nicobailon/visual-explainer css-patterns.md | <https://github.com/nicobailon/visual-explainer/blob/main/plugins/visual-explainer/references/css-patterns.md> | 1800-line CSS reference: theme setup, card components, depth tiers, grid layouts, connectors, animations, Mermaid containers | .85 — design patterns |
| Dammyjay93/interface-design | <https://github.com/Dammyjay93/interface-design> | Design token persistence, system.md memory, consistency-focused UI skill (MIT) | .50 — contrast approach |
| OwlBear visual-explainer-research.md | Local `docs/research/visual-explainer-research.md` | Prior research recommending 2-3 templates, aesthetic constraints, YAGNI assessment | .85 — prior decision |

## 3. Analysis

### 3a. Template inventory and selection

| Template | Palette | Key CSS patterns | OwlBear use cases | Include? |
|----------|---------|------------------|-------------------|----------|
| architecture.html | Terracotta + sage | CSS Grid cards, flow arrows, depth tiers, pipeline steps, legend | Agent reports, system overviews | Yes (.90) |
| data-table.html | Rose + cranberry | HTML `<table>`, KPI cards, status badges, collapsible `<details>` | Requirements audits, comparisons, test results | Yes (.90) |
| mermaid-flowchart.html | Teal + cyan | Mermaid CDN + ELK layout, zoom/pan JS (~200 LOC), dot-grid background | Flowcharts, ER diagrams, state machines | Yes (.85) |
| slide-deck.html | Various | Full slide engine, keyboard nav, 10 slide types | Presentations | No — YAGNI |

**Decision:** All 3 non-slide templates. Each teaches a distinct rendering approach (CSS Grid, HTML table, Mermaid JS) with a distinct palette. The variety is intentional — it prevents agents from converging on a single aesthetic.

### 3b. Adaptation strategy comparison

| Approach | Description | Confidence | Risk |
|----------|-------------|------------|------|
| **A: Minimal adaptation** | Copy templates, update comment headers only | .85 | Low — templates are MIT, patterns are battle-tested |
| B: Strip to skeleton | 50-80 line minimal CSS/HTML | .55 | Loses depth tiers, pipelines, KPI cards, zoom/pan — the high-value patterns |
| C: OwlBear-specific content | Rewrite example content to show OwlBear architecture | .50 | Maintenance burden; content is placeholder anyway — agents replace it |

### 3c. What each template teaches the agent

**architecture.html (~280 lines):**

- Section cards with colored accent borders + dot labels (`.section--accent`, `.section--green`)
- 3 depth tiers: hero (elevated), default, recessed — visual hierarchy
- Horizontal pipeline with step boxes + arrow separators
- Vertical flow arrows between sections (inline SVG)
- Three-column output grid
- Callout box for secondary info
- Staggered fade-in animation via `--i` CSS variable

**data-table.html (~250 lines):**

- KPI summary cards above the table (visual hook before data)
- Semantic `<table>` with sticky header, alternating rows, hover highlight
- Status badges: match (green), gap (red), partial (amber) — never emoji
- `<code>` references and `<small>` secondary text in cells
- Collapsible `<details>` section for drill-down
- Summary footer row with aggregate status

**mermaid-flowchart.html (~350 lines, ~200 JS):**

- Mermaid ESM import + `@mermaid-js/layout-elk` for better node positioning
- `theme: 'base'` with full `themeVariables` matching page palette
- `diagram-shell` pattern: `.mermaid-wrap` > `.zoom-controls` + `.mermaid-viewport` > `.mermaid-canvas`
- Smart fit algorithm (contain → width-priority → height-priority)
- Zoom controls: +/−/fit/1:1/expand buttons
- Scroll-to-zoom, drag-to-pan, pinch-to-zoom (touch)
- Click-to-expand opens full-size in new tab
- ResizeObserver re-fits on container resize

### 3d. Adaptation details

Minimal changes needed:

| Change | Why | Scope |
|--------|-----|-------|
| Update HTML comment block | Reference "visual-output skill" instead of "visual-explainer skill" | All 3 files |
| Keep distinct palettes | Terracotta/sage, rose/cranberry, teal/cyan — teaches variety | No change |
| Keep `prefers-color-scheme` | Both themes must work per quality checks | No change |
| Keep `prefers-reduced-motion` | Accessibility requirement | No change |
| Keep example content | Generic enough (system architecture, requirements audit, CI/CD pipeline) | No change |
| Keep responsive breakpoint | 768px single breakpoint per css-patterns.md | No change |
| Keep Mermaid CDN import | `mermaid@11` + `@mermaid-js/layout-elk` — no local deps | No change |

### 3e. KISS/YAGNI assessment

- **KISS (.85):** 3 self-contained HTML files. No build step, no dependencies, no config. Agent reads template, absorbs patterns, generates similar output.
- **YAGNI applied:** Slide-deck template excluded. Chart.js dashboard template not created. Templates are read-only reference material, not active code.
- **Size trade-off:** Templates total ~880 lines. Large for prompt context, but agents read only 1 template per generation (routed by content type). The SKILL.md routing table directs which template to read.

## 4. Recommendation (.85 confidence)

**Adopt all 3 non-slide templates with minimal adaptation (Approach A).** Specifically:

1. Place `architecture.html`, `data-table.html`, `mermaid-flowchart.html` in `.github/skills/visual-output/templates/`
2. Update HTML comment blocks to reference the visual-output skill
3. Keep all CSS, JS, and example content intact — the patterns are the value
4. Ensure the visual-output SKILL.md (task #706) references templates in its Structure phase routing table

**Risk:** Template file size (~880 lines total) may be large for LLM context windows. **Mitigation:** Agents read only 1 template per generation, routed by the SKILL.md's content-type table. An architecture overview reads only architecture.html (~280 lines).

**Dependency:** Task #708 depends on #706 (visual-output SKILL.md). The templates can be created independently, but the SKILL.md needs a Structure section that routes agents to the correct template. If #706 is built first, it should include template routing instructions even before templates exist.

## 5. Follow-up Tasks

```
kanban\kanban-md.exe create "Add architecture.html template to visual-output skill" --priority important --status backlog --tags "scope:copilot,docs" --body "Copy architecture.html from visual-explainer (MIT), update comment header to reference visual-output skill. Place at .github/skills/visual-output/templates/architecture.html. Template demonstrates: CSS Grid cards, depth tiers, flow arrows, pipeline steps, staggered animation. See docs/research/html-diagram-templates-research.md S3c."

kanban\kanban-md.exe create "Add data-table.html template to visual-output skill" --priority important --status backlog --tags "scope:copilot,docs" --body "Copy data-table.html from visual-explainer (MIT), update comment header. Place at .github/skills/visual-output/templates/data-table.html. Template demonstrates: HTML table with sticky header, KPI cards, status badges, collapsible details. See docs/research/html-diagram-templates-research.md S3c."

kanban\kanban-md.exe create "Add mermaid-flowchart.html template to visual-output skill" --priority important --status backlog --tags "scope:copilot,docs" --body "Copy mermaid-flowchart.html from visual-explainer (MIT), update comment header. Place at .github/skills/visual-output/templates/mermaid-flowchart.html. Template demonstrates: Mermaid CDN + ELK layout, zoom/pan/fit JS engine, diagram-shell pattern. See docs/research/html-diagram-templates-research.md S3c."
```

**Note:** These 3 tasks decompose #708 into atomic units. Alternatively, #708 itself can serve as the single builder task — the 3 templates are small enough to create in one pass. The follow-up tasks above are provided in case the architect prefers finer granularity.
