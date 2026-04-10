# Excalidraw Skill Reference Files — Content Analysis

> **Owning task:** #742 — Create Excalidraw skill reference files (element-templates, json-schema, color-palette)
> **Date:** 2026-04-10 **Status:** Complete

## 1. Context and Question

Task #742 asks for 3 reference files in `share/skills/h-excalidraw-diagram/references/`. The SKILL.md references them but the directory doesn't exist. Source material: coleam00/excalidraw-diagram-skill (MIT). Key questions: (a) Is coleam00 complete enough? (b) What adaptations are needed? (c) Are diamond/ellipse templates derivable?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | coleam00 element-templates.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/element-templates.md> | .95 — 6 of 8 required templates |
| 2 | coleam00 json-schema.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/json-schema.md> | .95 — Complete schema reference |
| 3 | coleam00 color-palette.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/references/color-palette.md> | .90 — Full semantic palette |
| 4 | coleam00 SKILL.md | <https://github.com/coleam00/excalidraw-diagram-skill/blob/main/SKILL.md> | .85 — Shape Meaning table lists diamond/ellipse usage |
| 5 | Excalidraw API docs (updateScene) | <https://docs.excalidraw.com/docs/@excalidraw/excalidraw/api/props/excalidraw-api#elements> | .70 — Confirms element structure with all fields |
| 6 | OwlBear SKILL.md + prior research #593, #628, #736 | local | .90 — Context, gap inventory, existing decisions |

## 3. Analysis

### 3.1 Source Coverage per AC

| AC Item | coleam00 Coverage | Gap |
|---------|-------------------|-----|
| Rectangle template | Complete — all required fields shown | None |
| Text (in-container) | Complete — containerId, lineHeight, originalText shown | None |
| Text (free-floating) | Complete — containerId: null shown | None |
| Arrow (with bindings) | Partial — shows startBinding/endBinding on arrow + boundElements on rectangle for text | Arrow→shape bidirectional binding not explicit (see 3.2) |
| Line | Complete — points array, no bindings | None |
| Small marker dot | Complete — 12×12 ellipse with fill | None |
| **Diamond** | **Missing** — listed in json-schema types table but no JSON template | Derive from rectangle pattern (see 3.3) |
| **Ellipse (full-size)** | **Missing** — only 12px dot variant shown | Derive from rectangle pattern (see 3.3) |

### 3.2 Bidirectional Arrow Binding Gap

AC requires: "Arrow has startBinding/endBinding AND target element has boundElements." The coleam00 arrow template shows arrow-side bindings correctly. The rectangle template shows `boundElements: [{"id": "text1", "type": "text"}]` — but this binds text, not arrows.

**Required adaptation:** The element-templates.md must show a rectangle with BOTH text AND arrow in its `boundElements` array: `[{"id": "text1", "type": "text"}, {"id": "arrow1", "type": "arrow"}]`. This makes the bidirectional contract explicit.

### 3.3 Diamond and Ellipse Templates

From json-schema.md and the Excalidraw API, diamond and ellipse use the same common properties as rectangle. Key differences:

| Property | Rectangle | Diamond | Ellipse |
|----------|-----------|---------|---------|
| `type` | `"rectangle"` | `"diamond"` | `"ellipse"` |
| `roundness` | `{"type": 3}` (optional) | Not applicable | Not applicable |
| `boundElements` | Same | Same | Same |
| Semantic use | Process, action, step | Decision, conditional | Start/end, external system |

Templates are trivially derivable — copy rectangle, change `type`, remove `roundness`, adjust dimensions (diamond: use ~120×120 for square aspect; ellipse: use ~160×80 for oval).

### 3.4 Line Count Feasibility

| File | coleam00 Lines | With Adaptations | AC Target |
|------|---------------|------------------|-----------|
| element-templates.md | ~90 (6 types) | ~115 (8 types + binding note) | ~80 |
| json-schema.md | ~45 | ~50 (add diamond/ellipse notes) | ~50 |
| color-palette.md | ~50 | ~45 (compress slightly) | ~40 |

element-templates.md will exceed ~80 lines with 8 types. Recommend accepting ~100–115 lines for completeness rather than sacrificing templates to hit a line count.

### 3.5 OwlBear Adaptations

| coleam00 Pattern | OwlBear Adaptation |
|-----------------|-------------------|
| `"source": "https://excalidraw.com"` | Not in reference files (only in SKILL.md, already `"owlbear"`) |
| Palette references with `<placeholder>` | Keep — agents resolve from color-palette.md |
| No frontmatter on reference files | Keep — reference files don't need frontmatter (only SKILL.md has it) |
| Render pipeline mentions | None present in reference files — clean |

## 4. Recommendation (.90 confidence)

**Adapt coleam00 reference files directly.** The source material is 90%+ complete. Two additions needed:

1. **Add diamond and ellipse templates** to element-templates.md (derive from rectangle pattern, ~15 lines each)
2. **Update rectangle template** to show arrow in `boundElements` array (bidirectional binding)

No other material changes. The json-schema.md and color-palette.md are directly usable with minimal formatting adjustments.

**Tier: T1 (Autonomous)** — file creation from MIT-licensed source. No architecture/security/capability changes.

Challenge: FALLBACK — challenger agent not available in researcher mode.

## 5. Follow-up Tasks

Task #742 itself moves to backlog as the implementation task. No new tasks needed — the AC is well-specified and the source material is identified.

Builder guidance appended to task body (see Channel B note).
