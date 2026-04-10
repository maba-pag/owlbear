# Excalidraw Skill Expansion — Missing Patterns and Large-Diagram Strategy

> **Owning task:** #743 — Expand Excalidraw skill with missing patterns and large-diagram strategy
> **Date:** 2026-04-10 **Status:** Complete

## 1. Context and Question

Task #736 research identified that the current `h-excalidraw-diagram` SKILL.md (106 lines) is missing 6 of 9 visual patterns from the coleam00 source, plus shape-meaning table, large-diagram strategy, container-vs-text rules, and ID naming conventions. This task researches the exact content to add and a compression strategy to stay under 200 lines.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | coleam00/excalidraw-diagram-skill SKILL.md | <https://github.com/coleam00/excalidraw-diagram-skill> | .95 — Original 450-line skill with all 9 patterns, shape table, large-diagram strategy |
| 2 | Wikipedia: Entity-relationship model | <https://en.wikipedia.org/wiki/Entity-relationship_model> | .85 — Chen notation: rectangles=entities, diamonds=relationships, ellipses=attributes |
| 3 | Prior research #736 (excalidraw-skill-reliability) | .owlbear/research/excalidraw-skill-reliability.md | .90 — Gap inventory listing all missing content |
| 4 | Current h-excalidraw-diagram SKILL.md | share/skills/h-excalidraw-diagram/SKILL.md | .95 — Baseline: 106 lines, 3 patterns |

## 3. Analysis

### 3.1 Line Budget

| Section | Current Lines | Added Lines | Notes |
|---------|--------------|-------------|-------|
| Existing content | 106 | — | Keep as-is (frontmatter, philosophy, structure, 3 patterns, delivery, refs, checklist, gotchas) |
| 6 missing patterns | 0 | ~24 | Compact: 4 lines each (heading + description + use-for + ascii hint) |
| ER diagram pattern | 0 | ~6 | Chen notation mapped to Excalidraw shapes |
| Shape-meaning table | 0 | ~16 | Direct port from coleam00, compact table |
| Large-diagram strategy | 0 | ~20 | Section-by-section build, ID namespacing, cross-section bindings |
| Container-vs-text table | 0 | ~12 | Decision table from coleam00 |
| ID naming convention | 0 | ~6 | Descriptive strings, section-namespaced seeds |
| **Total** | **106** | **~84** | **~190 lines — within 200-line limit** |

### 3.2 Missing Patterns — Content Mapping

Each pattern below is sourced from coleam00's "Visual Pattern Library" section with compression to match our existing bullet-point style (architecture/flowchart/sequence use ~10 lines each; compress new patterns to ~4 lines each).

| Pattern | coleam00 Source | OwlBear Adaptation |
|---------|----------------|-------------------|
| **Tree (Hierarchy)** | Lines + free-floating text, no boxes | 4 lines: heading, description, `line` elements for trunk/branches, use-for |
| **Convergence (Many-to-One)** | Funnel arrows merging to single output | 4 lines: heading, description, arrow pattern, use-for |
| **Spiral/Cycle** | Elements in sequence with return arrow | 4 lines: heading, description, loop layout, use-for |
| **Cloud (Abstract State)** | Overlapping ellipses, varied sizes | 3 lines: heading, description, use-for |
| **Assembly Line** | Input → Process Box → Output | 4 lines: heading, description, before/after, use-for |
| **Side-by-Side** | Parallel structures with visual contrast | 3 lines: heading, description, use-for |

### 3.3 ER Diagram Pattern — Chen Notation Mapping

Chen notation (source: Wikipedia ER model, Chen 1976) maps directly to Excalidraw element types:

| ER Concept | Excalidraw Shape | Notes |
|------------|-----------------|-------|
| Entity | `rectangle` | Primary fill color |
| Relationship | `diamond` | Secondary fill color |
| Attribute | `ellipse` | Tertiary/neutral fill |
| Primary key attribute | `ellipse` (underlined text) | Bold or underlined label |
| Cardinality | Arrow label text (`1`, `N`, `M`) | Text on connecting lines |
| Connection | `line` or `arrow` | Connects entities to relationships |

This is not in coleam00 — it's a novel addition. Confidence in mapping correctness: .90 (Chen notation is standardized and well-documented).

### 3.4 Shape-Meaning Table

Direct port from coleam00's "Shape Meaning" section. The table maps concept types to Excalidraw shapes:

| Concept Type | Shape | Rationale |
|-------------|-------|-----------|
| Labels, descriptions | **none** (free-floating text) | Typography creates hierarchy |
| Section titles | **none** (free-floating text) | Font size/weight is enough |
| Timeline markers | small `ellipse` (10-20px) | Visual anchor, not container |
| Start, trigger, input | `ellipse` | Soft, origin-like |
| End, output, result | `ellipse` | Completion, destination |
| Decision, condition | `diamond` | Classic decision symbol |
| Process, action, step | `rectangle` | Contained action |
| Abstract state, context | overlapping `ellipse` | Fuzzy, cloud-like |
| Hierarchy node | lines + text (no boxes) | Structure through lines |

Rule from coleam00: "Default to no container. Add shapes only when they carry meaning. Aim for <30% of text elements inside containers."

### 3.5 Large-Diagram Strategy

coleam00's "Large / Comprehensive Diagram Strategy" section (~80 lines) compresses to ~20 lines:

**Key principles:**
1. Build JSON one section at a time (never full diagram in single pass — output token limits + quality)
2. Use descriptive string IDs (`"trigger_rect"`, `"arrow_fan_left"`) not numeric IDs
3. Namespace seeds by section (section 1: 100xxx, section 2: 200xxx)
4. Update cross-section `boundElements` arrays when adding inter-section arrows
5. Review complete JSON after all sections: check bindings, spacing balance, ID references
6. Plan sections around natural visual groupings

### 3.6 Container-vs-Text Decision Table

Direct port from coleam00. This is a critical missing piece — without it, agents box everything:

| Use Container When | Use Free-Floating Text When |
|---|---|
| Focal point of a section | Label or description |
| Needs visual grouping | Supporting detail or metadata |
| Arrows need to connect to it | Describes something nearby |
| Shape carries meaning (diamond, etc.) | Section title, subtitle, annotation |
| Represents a distinct system component | Typography alone creates hierarchy |

### 3.7 Placement Within SKILL.md

| New Section | Insert After | Rationale |
|-------------|-------------|-----------|
| 6 new patterns + ER | Existing "Diagram Patterns" section | Extends the pattern library naturally |
| Shape-meaning table | After all patterns, before "Delivery" | Bridge between patterns and implementation |
| Container-vs-text table | After shape-meaning table | Related to shape decisions |
| Large-diagram strategy | After container table, before "Delivery" | Operational guidance before output |
| ID naming convention | Inside "Known Gotchas" or as subsection of large-diagram | Where ID issues are already discussed |

## 4. Recommendation (.88 confidence)

**Expand SKILL.md in-place with all 6 items from the AC.** The line budget works (~190 of 200). No content needs to move to references — all additions are compact operational guidance, not verbose examples.

**Implementation approach:**
- Add 6 patterns in compressed 3-4 line format after existing 3 patterns
- Add ER pattern using Chen notation mapped to Excalidraw shapes (novel addition)
- Add shape-meaning table as a new `## Shape Meaning` section
- Add container-vs-text as a new `## Container vs. Free-Floating Text` section
- Add large-diagram strategy as `## Large Diagram Strategy` section
- Fold ID convention into large-diagram strategy (descriptive IDs + seed namespacing)

**Risk:** Line count is tight (~190). If additions run long, either compress existing patterns (architecture/flowchart/sequence could lose ~3 lines each) or move the Delivery section to a reference file (~8 lines).

Challenge: FALLBACK — no challenger agent available in researcher mode.

## 5. Follow-up Tasks

Single implementation task at `research` status (the AC is already well-specified on #743 itself — no decomposition needed).
