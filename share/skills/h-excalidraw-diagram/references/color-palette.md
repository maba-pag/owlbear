# Color Palette

> Adapted from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) (MIT).

Semantic color assignments for OwlBear diagrams. Every color choice must encode meaning — never decorative.

---

## Semantic Fill / Stroke Pairs

Use matching fill + stroke pairs. Never mix fills and strokes from different semantic categories.

| Semantic Role | Fill | Stroke | Use |
| --- | --- | --- | --- |
| **Primary** | `#e7f5ff` | `#1971c2` | Hero component, main subject, focal point |
| **Secondary** | `#f8f9fa` | `#495057` | Supporting component, adjacent service |
| **Success / Done** | `#ebfbee` | `#2f9e44` | Completed step, passing state, green-path |
| **Warning / Risk** | `#fff9db` | `#e67700` | In-progress, degraded, caution path |
| **Danger / Fail** | `#fff5f5` | `#c92a2a` | Error state, blocked, red-path |
| **Neutral / Muted** | `#f1f3f5` | `#868e96` | Inactive, deprecated, de-emphasised |
| **Decision** | `#fff0f6` | `#a61e4d` | Diamond decision node, conditional branch |
| **Terminal** | `#f3f0ff` | `#6741d9` | Ellipse start/end, external actor |
| **Accent** | `#1971c2` | `#1971c2` | Small marker dot, emphasis dot, selected state |

---

## Text Hierarchy Colors

| Role | Color | Font Size | Use |
| --- | --- | --- | --- |
| `<text-primary>` | `#212529` | ≥16px | Main element labels, body content |
| `<text-secondary>` | `#495057` | ≥16px | Sub-labels, supporting descriptions |
| `<text-muted>` | `#868e96` | ≥14px | Captions, legends, step numbers |
| `<text-title>` | `#1c1c1e` | ≥20px | Section headers, diagram title |
| `<text-link>` | `#1971c2` | ≥16px | Clickable references, URL annotations |

---

## Evidence Artifact Colors

Specific palette for knowledge graph and evidence diagrams (used in OwlBear analysis/research visuals).

| Artifact Type | Fill | Stroke |
| --- | --- | --- |
| Source document | `#e7f5ff` | `#1971c2` |
| Extracted claim | `#ebfbee` | `#2f9e44` |
| Entity node | `#fff9db` | `#e67700` |
| Relationship edge | transparent | `#495057` |
| Contradiction / conflict | `#fff5f5` | `#c92a2a` |
| Synthesised insight | `#f3f0ff` | `#6741d9` |

---

## Stroke Utilities

| Token | Value | Use |
| --- | --- | --- |
| `<stroke-muted>` | `#ced4da` | Divider lines, dashed separators |
| `<stroke-heavy>` | `#212529` | Emphasis border, selected element |
| `<stroke-invisible>` | `transparent` | Label-only elements with no border |

---

## Usage Rules

1. **Primary** for the one most important element per diagram (hero component, key finding).
2. **Secondary** for everything else with no special status.
3. **Decision** only on diamonds; **Terminal** only on ellipses.
4. **Danger / Warning / Success** for status — not decoration. Use consistently across diagrams.
5. **Accent** fill for small marker dots; same hex as Primary stroke for visual continuity.
