# Excalidraw Skill Reliability for Diagram Generation

> **Owning task:** #736 — Evaluate Excalidraw skill reliability for diagram generation
> **Date:** 2026-04-10 **Status:** Complete

## 1. Context and Question

The `h-excalidraw-diagram` skill exists but hasn't been systematically tested. Can agents reliably produce valid Excalidraw JSON using it? What gaps exist?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | coleam00/excalidraw-diagram-skill SKILL.md | <https://github.com/coleam00/excalidraw-diagram-skill> | .95 — Original source; 450-line skill vs our 106-line adaptation |
| 2 | coleam00 element-templates.md | (same repo) /references/element-templates.md | .95 — Complete JSON templates for all element types |
| 3 | coleam00 json-schema.md | (same repo) /references/json-schema.md | .90 — Element types, common properties, binding format |
| 4 | coleam00 color-palette.md | (same repo) /references/color-palette.md | .85 — Semantic fill/stroke pairs, text hierarchy, evidence artifacts |
| 5 | OwlBear h-excalidraw-diagram SKILL.md | share/skills/h-excalidraw-diagram/SKILL.md | .95 — Current skill under evaluation |
| 6 | Prior research #593, #628, #629 | .owlbear/research/excalidraw-*.md | .80 — Context on adoption decisions and known gaps |

## 3. Analysis

### 3.1 Gap Inventory: OwlBear Skill vs Source

| Gap | Severity | Detail |
|-----|----------|--------|
| **Reference files missing** | Critical | `references/` directory doesn't exist. SKILL.md references 3 files (color-palette, element-templates, json-schema) that were never created |
| **No element templates** | Critical | Agents must guess JSON structure for rectangles, arrows, text, lines, dots. coleam00 provides copy-paste templates with all required fields |
| **No render pipeline** | Critical | Excalidraw not in DiagramService SUPPORTED_TYPES. Agents cannot validate output visually. coleam00 makes render-view-fix MANDATORY |
| **Heavily compressed** | Major | 106 lines vs 450 lines. Lost: 6 visual patterns, design process, large diagram strategy, container discipline, shape meaning table |
| **No complete examples** | Major | Patterns described conceptually (bullet points) but no working JSON shown |
| **Missing patterns** | Moderate | Only 3 of 9 coleam00 patterns ported (architecture, flowchart, sequence). Missing: tree, convergence, spiral/cycle, cloud, assembly line, side-by-side |

### 3.2 Diagram Type Reliability Assessment

| Diagram Type | Skill Coverage | Predicted Reliability | Failure Modes |
|---|---|---|---|
| Architecture overview | Partial — "Fan-Out" pattern | .30 | Missing element templates, no binding examples, no color palette |
| Sequence flow | Partial — "Sequence (Timeline)" pattern | .25 | No dot-marker template, no line-as-structure guidance |
| Entity relationship | None | .10 | No ER pattern exists; no diamond usage for attributes |
| Component tree | None | .15 | coleam00 has "Tree" with lines+text; OwlBear has nothing |
| Data flow | Partial — could use flowchart | .25 | No "Assembly line" or transformation pattern |

**Overall reliability: .20 (very low)**. Without reference files, agents lack the JSON schema knowledge to produce valid output consistently.

### 3.3 Common LLM Failure Modes Without Templates

| Failure Mode | Likelihood | Cause |
|---|---|---|
| Missing fields (`seed`, `versionNonce`, `lineHeight`, `originalText`) | High | No template showing required fields |
| Broken arrow bindings (missing `boundElements` on target) | High | Binding is bidirectional but skill doesn't show both sides |
| Text overflow from containers | High | No coordinate calculation guidance |
| Trailing commas in JSON arrays | Medium | Common LLM habit; skill warns but doesn't show examples |
| Duplicate element IDs | Medium | No ID naming convention (coleam00 uses descriptive strings + section namespacing) |
| Wrong `fontFamily` (1 instead of 3) | Medium | Buried in text rules, not in templates |
| Truncated JSON for 10+ element diagrams | High | No large-diagram sectioning strategy |

### 3.4 Root Cause: Incomplete Port

Task #628 research identified the deliverables: SKILL.md + 3 reference files. The SKILL.md was created but the reference files were never built. The skill was also compressed from 450 → 106 lines, dropping critical operational guidance (design process, render loop, large diagram strategy).

### 3.5 Comparison: What Would Fix It

| Fix | Effort | Impact |
|-----|--------|--------|
| Create 3 reference files from coleam00 source | Low (~170 lines total) | Critical — gives agents copy-paste templates |
| Expand SKILL.md with missing patterns | Medium (~100 lines) | Major — adds tree, convergence, assembly line, ER patterns |
| Add Excalidraw to DiagramService SUPPORTED_TYPES | Low (1 line) | Critical — enables validation via Kroki SVG |
| Add section-by-section strategy for large diagrams | Low (~30 lines) | Major — prevents truncation |

## 4. Recommendation (.85 confidence)

**Fix the skill, don't abandon it.** The approach is proven (coleam00, 1k+ stars). The gaps are execution gaps, not design gaps.

Priority order:
1. Create the 3 reference files (unblocks everything)
2. Add Excalidraw to DiagramService SUPPORTED_TYPES (enables validation)
3. Expand SKILL.md with missing patterns and the large-diagram strategy

Challenge: FALLBACK — no challenger agent available in researcher mode.

## 5. Follow-up Tasks

See created tasks below. All at `research` status per researcher workflow.
