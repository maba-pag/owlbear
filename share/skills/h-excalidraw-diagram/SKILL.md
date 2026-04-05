---
name: h-excalidraw-diagram
description: "Handbook: Excalidraw JSON diagram generation — elements, layout, and design methodology"
user-invocable: true
---

# Excalidraw Diagram Reference

Generate valid `.excalidraw` JSON diagrams that communicate ideas visually. Diagrams should **argue, not just display** — use layout, color, and grouping to guide the viewer's eye and convey relationships.

> Adapted from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) (MIT).

For styled HTML visuals (tables, CSS Grid, Mermaid), see `h-visual-output`.

## Design Philosophy

1. **Visual hierarchy first.** The viewer should grasp the main idea in 2 seconds. Use size, position, and color to create a clear focal point.
2. **Whitespace is structure.** Don't cram elements. Minimum 40px padding between groups, 20px between related elements.
3. **Color as meaning.** Every color choice must encode information (status, category, flow direction). Never decorative.
4. **Readable at a glance.** Text >= 16px for labels, >= 20px for titles.
5. **Consistent alignment.** Snap to a virtual grid (multiples of 20px). Align element centers or edges.

## Document Structure

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "owlbear",
  "elements": [ /* element objects */ ],
  "appState": { "gridSize": 20, "viewBackgroundColor": "#ffffff" },
  "files": {}
}
```

## Element Placement Rules

- Start the top-left element at `(100, 100)` — never at `(0, 0)`.
- 200px horizontal spacing between columns, 150px vertical between rows.
- Arrows: use `startBinding` and `endBinding` to attach to element IDs.
- Groups: assign matching `groupIds` arrays to visually related elements.

## Diagram Patterns

### Architecture (Fan-Out)

Central service box with satellite components radiating outward. Use for system overviews, microservice maps, dependency graphs.

- Hero rectangle (center, largest, primary color)
- Satellite rectangles (smaller, secondary colors by category)
- Arrows from hero to satellites (or bidirectional)
- Group label text above each cluster

### Flowchart (Diamond Decisions)

Sequential process with decision points. Use for algorithms, approval flows, CI/CD pipelines.

- Rounded rectangles for process steps
- Diamonds for decisions (Yes/No branches)
- Ellipses for start/end
- Arrows with text labels on branches

### Sequence (Timeline)

Vertical or horizontal timeline with events. Use for API call sequences, deployment phases, historical progressions.

- Vertical line as timeline spine
- Dot markers at event points
- Horizontal rectangles branching from markers
- Text labels with timestamps or step numbers

## Delivery

1. **Write** — `create_file` to `.owlbear/scratch/{name}.excalidraw`
2. **Render** — If Kroki is available, POST JSON to Kroki HTTP API with `diagram_type=excalidraw` and `output_format=svg`

## Reference Files

| File | Purpose |
|------|---------|
| `references/color-palette.md` | Semantic color mapping for fills, strokes, and text |
| `references/element-templates.md` | JSON snippets for every element type (rectangle, diamond, ellipse, arrow, text, line) |
| `references/json-schema.md` | Excalidraw JSON document structure and field reference |

These are co-located in the `skills/h-excalidraw-diagram/references/` directory. Load the relevant file when addressing a specific element type or color choice.

## Quality Checklist

Before delivering any diagram:

- [ ] **2-second test** — Main idea obvious at first glance
- [ ] **Alignment** — All elements snap to 20px grid
- [ ] **Spacing** — No elements closer than 20px, groups separated by >= 40px
- [ ] **Color** — Every color encodes meaning, palette matches reference
- [ ] **Text** — All labels >= 16px, titles >= 20px
- [ ] **Arrows** — All bound to elements via IDs, no floating arrows
- [ ] **IDs** — All unique, all cross-references valid
- [ ] **JSON** — Valid, parseable, matches schema

## Known Gotchas

- **All `id` fields must be unique strings.** Duplicate IDs cause rendering glitches and broken bindings.
- **Arrow bindings reference element IDs.** If you rename an element ID, update all `startBinding`/`endBinding` references.
- **No trailing commas in JSON.** Excalidraw parsers reject trailing commas in element arrays.
- **`groupIds` must be consistent.** All elements in a group must share the same group ID in their `groupIds` array.
