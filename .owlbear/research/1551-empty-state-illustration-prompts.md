# Empty State Illustration Prompts — Research

> **Owning task:** #1551 — P4-01: empty state illustration prompts document
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1551 requires a markdown document with image-generation prompts for 7 board column empty states (research, backlog, todo, in-progress, review, docs, done). D9 chose illustrated placeholders; D11 chose image-gen prompts as the deliverable. The enduser stance (synthesis Q1) argues illustrations should be subdued since empty columns are normal pipeline operations, not first-run events. This research validates the technical specs (dimensions, format, tone) before the prompts document is built.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | UX Planet — Empty State Design Guide | uxplanet.org/empty-state-design-a-practical-guide | 0.8 |
| 2 | Mockplus — 25 Best Empty State Examples | mockplus.com/blog/post/empty-state-ui-design | 0.7 |
| 3 | PDS v4 token reference (codebase) | `serve/cockpit/web/src/tokens.css` | 0.9 |
| 4 | Brief decisions D9, D11 | `.owlbear/briefs/draft-board-visual-design/decisions.md` | 1.0 |
| 5 | Enduser stance §2 + synthesis Q1 | `.owlbear/briefs/draft-board-visual-design/synthesis.md` | 0.9 |
| 6 | Column.tsx current implementation | `serve/cockpit/web/src/components/Column.tsx` | 0.9 |

## 3. Analysis

### Image Format

| Format | Transparency | File Size | AI-gen output | Dark/light compat | Verdict |
|--------|-------------|-----------|---------------|-------------------|---------|
| PNG | Yes | Medium | Native output | Good with transparent bg | **Recommended** |
| WebP | Yes | Small | Needs conversion | Good with transparent bg | Optimization step |
| SVG | Yes | Smallest | Not AI-gen native | Ideal but impractical | Skip |

### Dimensions

Column min-width is 200px (D13). With `--pds-spacing-md` (16px) padding each side, illustration area is ~168px. Retina displays need 2× source.

| Spec | Value | Rationale |
|------|-------|-----------|
| Render size | 160×120px | Fits 168px column body with margin |
| Source size | 320×240px | 2× for retina/HiDPI |
| Aspect ratio | 4:3 landscape | Natural fit for column-width-constrained space |
| Background | Transparent | Required for light/dark theme compatibility |

### Visual Tone

Balancing D11 ("fun, whimsical") with enduser pushback ("receding, not attention-grabbing"):

| Criterion | Direction |
|-----------|-----------|
| Color palette | Muted pastels, low saturation — aligned with PDS neutral tones |
| Style | Flat line-art with subtle fill — not 3D, not photorealistic |
| Complexity | Simple scene, 1-2 elements max — scans at 160px without clutter |
| Character | Owl-bear mascot (OwlBear brand) in each illustration for cohesion |
| Mood | Warm but quiet — communicates status without demanding attention |
| Opacity | Prompts should specify 60-80% overall opacity feel to recede visually |

### Per-Status Creative Direction

| Status | Theme | Subject | Emotional tone |
|--------|-------|---------|---------------|
| research | Discovery | Owl-bear with telescope peering at stars | Curious, exploratory |
| backlog | Organized waiting | Owl-bear arranging items on shelves | Patient, orderly |
| todo | Planning | Owl-bear with clipboard reviewing a checklist | Intentional, ready |
| in-progress | Active work | Owl-bear at a workbench with tools | Focused, productive |
| review | Inspection | Owl-bear with magnifying glass examining something | Careful, thorough |
| docs | Writing | Owl-bear with quill pen and an open book | Thoughtful, scholarly |
| done | Completion | Owl-bear relaxing in a hammock with a checkmark flag | Satisfied, restful |

## 4. Recommendation

**Specs:** PNG, 320×240 source, transparent background, flat muted-pastel line-art style with owl-bear mascot character. Each prompt targets a specific image-gen tool (DALL-E, Midjourney, or similar) with explicit style modifiers for consistency across the set.

**Confidence: 0.85** — Well-established UI pattern, clear brief direction, specs fit the column layout constraints. Main risk: AI-generated illustration consistency across 7 images (mitigated by explicit style anchors in each prompt).

**Challenge: FALLBACK — trivial docs task, no architecture decision; challenger skipped per w-research Step 3.5 ("skip for info-only or trivial research").**

## 5. Follow-up Tasks

No new follow-up tasks needed. Task #1551 itself advances through the pipeline — the builder will create the actual prompts document at the AC-specified path.

**Tier: T1 — Autonomous.** Documentation-only deliverable, no architecture or behavioral changes.
