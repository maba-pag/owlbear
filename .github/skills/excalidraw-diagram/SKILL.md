---
name: excalidraw-diagram
description: "Generate Excalidraw JSON diagrams with design methodology, element library, and layout patterns. Use when the user asks for hand-drawn style diagrams, architecture visuals, flowcharts, or sequence diagrams in Excalidraw format."
---

# Excalidraw Diagram Skill

> **VS Code agent note:** This skill references OwlBear PydanticAI runtime tools
> (FileToolset, DiagramToolset) not available in VS Code Copilot agent mode. Use
> VS Code edit/file/terminal tools instead when adapting these procedures for agent use.

Generate valid `.excalidraw` JSON diagrams that communicate ideas visually.
Diagrams should **argue, not just display** — use layout, color, and grouping to
guide the viewer's eye and convey relationships.

> Adapted from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) (MIT).

## Design Philosophy

1. **Visual hierarchy first.** The viewer should grasp the main idea in 2 seconds.
   Use size, position, and color to create a clear focal point.
2. **Whitespace is structure.** Don't cram elements. Give each group breathing room.
   Minimum 40px padding between groups, 20px between related elements.
3. **Color as meaning.** Every color choice must encode information (status, category,
   flow direction). Never use color for decoration alone.
4. **Readable at a glance.** Text ≥ 16px for labels, ≥ 20px for titles. If you need
   to squint, the diagram fails.
5. **Consistent alignment.** Snap to a virtual grid (multiples of 20px). Align element
   centers or edges — never float randomly.

## Workflow

### Step 1 — Plan

Before writing JSON:

1. Identify the **diagram type**: architecture (fan-out), flowchart (diamond), sequence (timeline), or freeform.
2. List **all elements** needed: boxes, arrows, text labels, groups.
3. Sketch the **layout grid** mentally: how many columns/rows, where the focal point is.
4. Choose colors from the palette in `references/color-palette.md`.

### Step 2 — Build Elements

Create each element as a JSON object. See `references/element-templates.md` for
copy-paste templates of every element type.

**Element placement rules:**

- Start the top-left element at `(100, 100)` — never at `(0, 0)`.
- Use consistent spacing: 200px horizontal between columns, 150px vertical between rows.
- Arrows: use `startBinding` and `endBinding` to attach to element IDs.
- Groups: assign matching `groupIds` arrays to visually related elements.

### Step 3 — Assemble Document

Wrap elements in the Excalidraw document structure. See `references/json-schema.md`
for the full schema. Key fields:

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

### Step 4 — Validate

Before delivering, check:

- [ ] All `id` fields are unique strings
- [ ] All arrow `startBinding`/`endBinding` reference valid element IDs
- [ ] All `groupIds` arrays reference consistent group IDs
- [ ] No overlapping elements (check x/y/width/height don't collide)
- [ ] Text is readable (fontSize ≥ 16)
- [ ] Color palette matches `references/color-palette.md`
- [ ] JSON is valid (parseable, no trailing commas)

### Step 5 — Deliver

Save the JSON to a `.excalidraw` file:

1. **Write** — `FileToolset.write_file` → `.owlbear/diagrams/{name}.excalidraw`
2. **Render** — If Kroki is available: `DiagramToolset.generate_diagram(diagram_type="excalidraw", source=json_string, output_format="svg")`

## Diagram Patterns

### Architecture (Fan-Out)

Central service box with satellite components radiating outward. Use for system
overviews, microservice maps, dependency graphs.

- Hero rectangle (center, largest, primary color)
- Satellite rectangles (smaller, secondary colors by category)
- Arrows from hero to satellites (or bidirectional)
- Group label text above each cluster

### Flowchart (Diamond Decisions)

Sequential process with decision points. Use for algorithms, approval flows,
CI/CD pipelines.

- Rounded rectangles for process steps
- Diamonds for decisions (Yes/No branches)
- Ellipses for start/end
- Arrows with text labels on branches

### Sequence (Timeline)

Vertical or horizontal timeline with events. Use for API call sequences,
deployment phases, historical progressions.

- Vertical line as timeline spine
- Dot markers at event points
- Horizontal rectangles branching from markers
- Text labels with timestamps or step numbers

## Quality Checklist

Before delivering any diagram:

- [ ] **2-second test** — Main idea is obvious at first glance
- [ ] **Alignment** — All elements snap to 20px grid
- [ ] **Spacing** — No elements closer than 20px, groups separated by ≥ 40px
- [ ] **Color** — Every color encodes meaning, palette matches reference
- [ ] **Text** — All labels ≥ 16px, titles ≥ 20px
- [ ] **Arrows** — All bound to elements via IDs, no floating arrows
- [ ] **IDs** — All unique, all cross-references valid
- [ ] **JSON** — Valid, parseable, matches schema in `references/json-schema.md`

## Reference Files

| File | Purpose |
|------|---------|
| `references/color-palette.md` | Semantic color mapping for fills, strokes, and text |
| `references/element-templates.md` | JSON snippets for every element type (rectangle, diamond, ellipse, arrow, text, line) |
| `references/json-schema.md` | Excalidraw JSON document structure and field reference |
