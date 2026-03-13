# Excalidraw Diagram Skill — Creation Research

> **Owning task:** #628 — Create Excalidraw diagram skill (SKILL.md + references)
> **Date:** 2026-03-07 **Status:** Complete

## 1. Context and Question

Task #628 asks: should we create an Excalidraw diagram skill now, and how should it be structured? This is labeled Tier 2 (YAGNI until Tier 1 Kroki proves insufficient). The research gate must answer: (a) is the concept sound, (b) what exactly goes into the deliverables, (c) what are the risks and prerequisites?

Prior research: `docs/research/excalidraw-diagram-skill.md` (task #593), `docs/research/visuals-diagrams-mcp.md` (task #582).

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | coleam00/excalidraw-diagram-skill | <https://github.com/coleam00/excalidraw-diagram-skill> | .95 — Primary model. 693 stars, SKILL.md + 3 references + render pipeline |
| 2 | yctimlin/mcp_excalidraw | <https://github.com/yctimlin/mcp_excalidraw> | .70 — 1.3k stars. `read_diagram_guide` design prompt validates skill approach |
| 3 | Excalidraw official docs | <https://docs.excalidraw.com/> | .75 — Element model, JSON schema, export API |
| 4 | OwlBear existing skills | `.github/skills/kanban-md/SKILL.md` | .90 — OwlBear skill structure precedent |

## 3. Analysis

### 3.1 YAGNI Assessment — Do We Need This Now?

| Criterion | Tier 1 (Kroki, implemented) | Tier 2 (Excalidraw skill, proposed) |
|-----------|----------------------------|-------------------------------------|
| Diagram types | Mermaid, PlantUML, GraphViz, D2, C4 | Free-form architecture, visual arguments |
| Visual style | Text-DSL rendered, structured | Hand-drawn aesthetic, brand-customizable |
| Expressiveness | Box-and-arrow, constrained by DSL grammar | Arbitrary layout, evidence artifacts, multi-zoom |
| Dependencies | httpx (existing) | Playwright (existing via BrowserManager) + render service (not yet built) |
| Blocker for other work? | No | No |

**Verdict (.80 confidence):** Tier 2 is **not needed now**. Kroki covers standard diagrams. Excalidraw adds value for rich architecture visuals and educational diagrams, but no current task requires it. The skill itself (SKILL.md + references) is low-cost to create, but the render pipeline (ExcalidrawRenderService) is a prerequisite for the skill to be *useful* — without rendering, agents generate JSON they can't validate.

**Recommendation:** Keep at `nice-to-have` priority. The skill creation is safe to move to backlog as a self-contained deliverable, but don't prioritize implementation until a concrete use case demands visual-argument diagrams.

### 3.2 Skill Structure — What Goes In

Based on coleam00 repo structure and OwlBear skill conventions:

| File | Purpose | Lines (est.) | Source |
|------|---------|-------------|--------|
| `SKILL.md` | Design methodology, workflow, quality checklist | ~150 | Adapted from coleam00 SKILL.md |
| `references/color-palette.md` | Semantic color palette (fills, strokes, text) | ~40 | Adapted from coleam00 |
| `references/element-templates.md` | JSON templates: rect, arrow, text, line, dot, diamond | ~80 | Adapted from coleam00 |
| `references/json-schema.md` | Excalidraw JSON format reference | ~50 | Adapted from coleam00 + official docs |

**Key adaptations from coleam00 to OwlBear:**

| coleam00 pattern | OwlBear adaptation |
|-----------------|-------------------|
| `.claude/skills/` path | `.github/skills/excalidraw-diagram/` |
| No YAML frontmatter | Add `name`, `description` frontmatter per OwlBear convention |
| Render via `uv run python render_excalidraw.py` | Remove — OwlBear handles via DiagramToolset (separate task) |
| 450-line SKILL.md | Compress to ~150 lines — remove render instructions, keep methodology |
| `pyproject.toml` + `render_template.html` in references | Omit — render infra is a separate task (#629-class tasks) |

### 3.3 Technical Feasibility

| Question | Answer | Evidence |
|----------|--------|----------|
| Can LLMs generate valid Excalidraw JSON? | Yes | coleam00 skill used in production with Claude Code; yctimlin `read_diagram_guide` validates approach |
| Can VS Code/OwlBear skills load this? | Yes | Existing skills (kanban-md, tdd-workflow) use identical SKILL.md + references/ pattern |
| Are there token budget risks? | Yes — element-templates.md (~80 lines) + json-schema.md (~50 lines) load as context | Mitigated: SkillRegistry loads references on-demand, not all at once |
| Can agents validate without render pipeline? | No — JSON coordinate math is error-prone | Render pipeline is a separate dependency; skill works but quality suffers without it |

### 3.4 Template Inventory for References

The AC asks for 2-3 JSON templates. Proposed templates per reference file:

**Architecture template** — fan-out pattern with central service, satellite components, arrows:

- 1 hero rectangle (service), 4 satellite rectangles, 5 arrows, section title text
- Demonstrates: grouping, binding, color-as-meaning

**Flowchart template** — decision diamond with branching paths:

- Start ellipse, 2 process rectangles, 1 diamond, 2 end ellipses, arrows with labels
- Demonstrates: diamond decisions, conditional flow, timeline pattern

**Sequence template** — timeline with evidence artifacts:

- Vertical timeline line, 4 marker dots, free-floating labels, 1 code-snippet rectangle
- Demonstrates: lines-as-structure, evidence artifacts, multi-zoom

### 3.5 Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| No render pipeline = agents can't validate output | High | Medium | Document dependency on ExcalidrawRenderService; skill is still useful as a reference even without rendering |
| LLM generates invalid JSON (wrong bindings, overlapping elements) | Medium | Low | Quality checklist in SKILL.md; render-view-fix loop when pipeline exists |
| Token budget exceeded when loading all references | Low | Low | SkillRegistry loads references on-demand |

## 4. Recommendation (.75 confidence)

**Move #628 to backlog.** The skill is well-defined, low-risk, and self-contained. Implementation is straightforward — adapt coleam00 patterns to OwlBear conventions. Keep priority at `nice-to-have` since Tier 1 Kroki covers current needs.

**Prerequisites to track:**

- ExcalidrawRenderService (separate task) is needed for the skill to be fully functional
- Without rendering, the skill still teaches methodology but agents can't validate output

## 5. Follow-up Tasks

Task #628 itself IS the follow-up. No new tasks needed — the existing AC is well-specified. Refine AC with these notes:

```
kanban\kanban-md.exe edit 628 --append-body "## Research Notes (2026-03-07)

Research complete. See docs/research/excalidraw-skill-creation.md.

Key decisions:
- Adapt coleam00 SKILL.md (compress from 450 to ~150 lines)
- Remove render pipeline instructions (separate task)
- Add YAML frontmatter per OwlBear skill conventions
- Include 3 reference files: color-palette.md, element-templates.md, json-schema.md
- Include 3 JSON diagram templates: architecture (fan-out), flowchart (diamond), sequence (timeline)
- Prerequisite: ExcalidrawRenderService for full validate loop (not a blocker for skill creation)" --timestamp
```

## 6. Research Checklist

- [x] **Theoretical validity** — Sound concept; YAGNI for now but low-cost. Kroki Tier 1 covers standard diagrams; Excalidraw adds visual-argument capability for architecture/educational use.
- [x] **Prior art** — 4 sources: coleam00 skill (693 stars), yctimlin MCP (1.3k stars), Excalidraw official docs, OwlBear existing skills.
- [x] **Technical feasibility** — LLMs can generate valid Excalidraw JSON (coleam00 proves it). OwlBear SkillRegistry loads SKILL.md + references/ pattern identically to existing skills.
- [x] **Architecture fit** — Maps to `.github/skills/excalidraw-diagram/` with SKILL.md + `references/` directory. Same pattern as kanban-md skill.
- [x] **Implementation approach** — Compress coleam00 SKILL.md to ~150 lines, remove render instructions, add OwlBear frontmatter. 3 reference files adapted from coleam00 repo.
- [x] **Testing strategy** — Manual: verify SkillRegistry loads skill. Validate YAML frontmatter parses. Functional: generate test diagram JSON and validate structure.
- [x] **Findings documented** — This document.
