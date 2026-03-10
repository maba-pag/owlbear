# Visual Output Skill Design

> **Owning task:** #706 — Create visual-output agent skill
> **Date:** 2026-03-10 **Status:** Complete

## 1. Context and Question

Task #706 asks: how should OwlBear's `visual-output` skill be structured? The parent research (#592, `docs/research/visual-explainer-research.md`) established that `nicobailon/visual-explainer` (MIT) is the primary pattern to adopt. This document focuses on the specific **skill design**: what to include, what to cut, and how to adapt it for OwlBear's agent stack.

**Key question:** What content belongs in a ~100-line SKILL.md that gives OwlBear agents the ability to produce high-quality HTML visual output?

## 2. Sources Studied

| Source | URL | What | Relevance |
|--------|-----|------|-----------|
| nicobailon/visual-explainer v0.6.3 | <https://github.com/nicobailon/visual-explainer> | ~400-line SKILL.md: workflow, Mermaid routing, aesthetic constraints, anti-slop guards | .90 — primary pattern |
| Anthropic Agent Skills spec | <https://agentskills.io> | Open standard for SKILL.md: YAML frontmatter + markdown instructions | .75 — format authority |
| OwlBear existing skills (15 files) | Local `.github/skills/*/SKILL.md` | OwlBear SKILL.md conventions: frontmatter, step-by-step workflows, ~50–120 lines | .85 — internal pattern |
| OwlBear DiagramToolset | Local `src/owlbear/tools/diagram/toolset.py` | Kroki-based `generate_diagram` tool already exists | .80 — existing capability |

## 3. Analysis

### 3a. Content budget (~100 lines)

visual-explainer's SKILL.md is ~400 lines because it covers 8 commands, slide decks, AI image generation, sharing, and extensive CSS/Mermaid reference material. OwlBear's skill needs only the core workflow and guards.

| Section | visual-explainer lines | OwlBear target | Notes |
|---------|----------------------|----------------|-------|
| Frontmatter + intro | ~15 | ~8 | Name, description, one-paragraph purpose |
| Workflow (4 phases) | ~80 | ~25 | Think/Structure/Style/Deliver — compress |
| Mermaid routing table | ~30 | ~20 | Content type → rendering approach |
| Aesthetic constraints | ~40 | ~15 | Forbidden patterns + curated palettes |
| Anti-slop guards | ~60 | ~12 | Condensed checklist, not prose |
| Delivery integration | ~20 | ~10 | OwlBear-specific: FileToolset, BrowserToolset, VisualFeedbackToolset |
| Slides/share/commands | ~155 | 0 | YAGNI — skip entirely |
| **Total** | **~400** | **~90** | |

### 3b. Workflow adaptation

visual-explainer's 4-phase workflow maps cleanly to OwlBear:

| Phase | visual-explainer | OwlBear adaptation |
|-------|-----------------|-------------------|
| **Think** | Pick audience, content type, aesthetic | Same — but reference OwlBear's `DiagramToolset` for Kroki-rendered diagrams as alternative |
| **Structure** | Read reference templates, choose approach | Simplified routing table (no template reading — OwlBear doesn't ship template files in skill) |
| **Style** | Font pairings, color palettes, forbidden patterns | Keep curated palettes + forbidden list, drop font-specific details (too verbose) |
| **Deliver** | Write to `~/.agent/diagrams/`, `open` command | Write to `.owlbear/diagrams/`, use `BrowserToolset.navigate()`, capture via `VisualFeedbackToolset` |

### 3c. OwlBear-specific integrations

The skill must reference tools agents already have:

| Tool | Purpose in visual workflow |
|------|--------------------------|
| `FileToolset` (`write_file`) | Write self-contained HTML to `.owlbear/diagrams/{name}.html` |
| `BrowserToolset` (`browser_navigate`) | Open the HTML file: `file://{path}` |
| `VisualFeedbackToolset` (`share_screenshot`) | Capture browser screenshot → deliver to channel |
| `DiagramToolset` (`generate_diagram`) | Alternative: Kroki-rendered SVG/PNG for simple Mermaid/PlantUML |

Decision: the skill instructs agents to choose between two paths:

- **HTML path** (visual-explainer pattern): FileToolset write → BrowserToolset open → VisualFeedbackToolset capture. For rich pages, tables, styled diagrams.
- **Kroki path** (existing DiagramToolset): `generate_diagram` for quick Mermaid/PlantUML renders. For simple flowcharts, ER diagrams, sequence diagrams.

### 3d. What to cut (YAGNI)

| Excluded | Rationale |
|----------|-----------|
| Slide deck mode | No current use case for OwlBear agents |
| Share/deploy to Vercel | OwlBear is laptop-resident |
| AI image generation (surf-cli) | External tool dependency, not needed |
| 8 slash commands | OwlBear agents use skills, not slash commands |
| Reference docs (4 files) | Too verbose; inline the essential rules |
| HTML templates (4 files) | Covered by task #707 separately |
| Chart.js integration | YAGNI — add later if needed |
| anime.js animations | YAGNI |

### 3e. KISS/YAGNI assessment

- **KISS-aligned (.85):** A single ~90-line SKILL.md with routing table + aesthetic guards + delivery steps. No templates, no external files, no build steps.
- **YAGNI risk:** Low — we're cutting 75% of visual-explainer's content. The remaining 25% is the high-value core (routing table, aesthetic anti-slop, workflow phases).
- **Architecture fit (.90):** All delivery tools already exist and are wired in `bootstrap/toolsets.py`. The skill is pure prompt engineering — zero code changes needed.

## 4. Recommendation (.85 confidence)

Create `.github/skills/visual-output/SKILL.md` with this structure:

1. **Frontmatter** — `name: visual-output`, description referencing HTML generation for diagrams/tables/architecture
2. **Workflow** — 4 phases (Think → Structure → Style → Deliver), each 3–6 lines
3. **Routing table** — Content type → approach (Mermaid vs CSS Grid vs HTML table vs Kroki)
4. **Aesthetic constraints** — Curated palettes (5), forbidden patterns (7 items), slop test checklist
5. **Delivery** — Two paths: HTML+Browser and Kroki. Reference existing toolsets by name.
6. **Quality checks** — Squint test, swap test, both themes, no overflow (4 items from visual-explainer)

**Risk:** Without the reference templates (task #707), agents rely on the skill's text instructions alone. Mitigation: the aesthetic constraints and anti-slop guards are the highest-value part — they prevent bad output even without templates.

## 5. Follow-up Tasks

The task itself (#706) is the follow-up from #592. No additional tasks needed beyond what #592 already created (#707 for templates, #708 for DiagramToolset HTML support).

Verify existing sibling tasks cover the gaps:

```
kanban\kanban-md.exe list --tag scope:copilot --compact
```

## 6. Attribution

Add to `docs/sources/overview.md`:

| Source | URL | License | What | Where Used | Date |
|--------|-----|---------|------|------------|------|
| nicobailon/visual-explainer | <https://github.com/nicobailon/visual-explainer> | MIT | Workflow phases, Mermaid routing table, aesthetic constraints, anti-slop guards | `.github/skills/visual-output/SKILL.md` | 2026-03-10 |
| Anthropic Agent Skills spec | <https://agentskills.io> | Apache-2.0 | SKILL.md format standard (YAML frontmatter + markdown) | `.github/skills/visual-output/SKILL.md` | 2026-03-10 |
