# Excalidraw JSON Schema Reference

The `.excalidraw` file format is a JSON document. This reference covers
the document structure and all required fields.

> Based on [Excalidraw official docs](https://docs.excalidraw.com/) and
> [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) (MIT).

## Document Structure

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "owlbear",
  "elements": [],
  "appState": {
    "gridSize": 20,
    "viewBackgroundColor": "#ffffff"
  },
  "files": {}
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | `"excalidraw"` | Yes | Format identifier |
| `version` | `2` | Yes | Schema version |
| `source` | string | No | Tool that generated the file |
| `elements` | array | Yes | List of element objects |
| `appState` | object | Yes | Canvas settings |
| `files` | object | Yes | Embedded file data (images); use `{}` when none |

## Element Common Fields

Every element (rectangle, ellipse, diamond, text, arrow, line) shares these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | string | Yes | Unique identifier. Must be unique across all elements |
| `type` | string | Yes | `"rectangle"`, `"ellipse"`, `"diamond"`, `"text"`, `"arrow"`, `"line"` |
| `x` | number | Yes | X position (top-left corner) |
| `y` | number | Yes | Y position (top-left corner) |
| `width` | number | Yes | Element width in pixels |
| `height` | number | Yes | Element height in pixels |
| `angle` | number | Yes | Rotation in radians (0 = no rotation) |
| `strokeColor` | string | Yes | Border/stroke color hex (e.g., `"#1e1e1e"`) |
| `backgroundColor` | string | Yes | Fill color hex or `"transparent"` |
| `fillStyle` | string | Yes | `"solid"`, `"hachure"`, `"cross-hatch"` |
| `strokeWidth` | number | Yes | Border width: `1` (thin), `2` (normal), `4` (bold) |
| `strokeStyle` | string | Yes | `"solid"`, `"dashed"`, `"dotted"` |
| `roughness` | number | Yes | `0` (sharp), `1` (hand-drawn), `2` (sketchy) |
| `opacity` | number | Yes | 0–100 |
| `groupIds` | string[] | Yes | Group membership; `[]` if ungrouped |
| `roundness` | object\|null | Yes | `{ "type": 3 }` for rectangles, `{ "type": 2 }` for others, `null` for text |
| `boundElements` | array | Yes | Elements bound to this one (text labels, arrows) |
| `locked` | boolean | Yes | Prevent editing |

## Text-Specific Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Display text content |
| `fontSize` | number | Yes | Font size in pixels (minimum 16 for readability) |
| `fontFamily` | number | Yes | `1` (Virgil/hand-drawn), `2` (Helvetica), `3` (Cascadia), `5` (Excalifont) |
| `textAlign` | string | Yes | `"left"`, `"center"`, `"right"` |
| `verticalAlign` | string | Yes | `"top"`, `"middle"` |
| `containerId` | string\|null | Yes | Parent element ID if text is inside a shape; `null` if freestanding |
| `originalText` | string | Yes | Original text (same as `text` unless edited) |
| `autoResize` | boolean | Yes | Auto-resize container to fit text |

## Arrow-Specific Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `points` | number[][] | Yes | Array of `[x, y]` offsets from element origin. Minimum 2 points |
| `startBinding` | object\|null | Yes | Connection to source element |
| `endBinding` | object\|null | Yes | Connection to target element |
| `startArrowhead` | string\|null | Yes | `null` (none), `"arrow"`, `"bar"`, `"dot"`, `"triangle"` |
| `endArrowhead` | string\|null | Yes | Same options as `startArrowhead` |

### Binding Object

```json
{
  "elementId": "target-element-id",
  "focus": 0,
  "gap": 1,
  "fixedPoint": null
}
```

| Field | Type | Description |
|-------|------|-------------|
| `elementId` | string | ID of the element to bind to |
| `focus` | number | `-1` to `1`; `0` = center of the element edge |
| `gap` | number | Pixel gap between arrow tip and element border |
| `fixedPoint` | null | Reserved; always `null` |

## AppState Fields

| Field | Type | Description |
|-------|------|-------------|
| `gridSize` | number | Grid snap size in pixels (use `20`) |
| `viewBackgroundColor` | string | Canvas background color (use `"#ffffff"`) |

## Validation Rules

1. **Unique IDs** — every `id` must be unique in the `elements` array.
2. **Valid bindings** — `startBinding.elementId` and `endBinding.elementId` must reference existing element IDs.
3. **Bound elements consistency** — if arrow A binds to element B, then B's `boundElements` must include `{ "id": "A", "type": "arrow" }`.
4. **Container text** — if text has `containerId: "X"`, element X must have `{ "id": "text-id", "type": "text" }` in its `boundElements`.
5. **No overlapping shapes** — check that `x`, `y`, `width`, `height` don't cause shapes to overlap unintentionally.
6. **Valid JSON** — no trailing commas, proper quoting, all required fields present.
