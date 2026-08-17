# JSON Schema Reference

> Adapted from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) (MIT).

Field reference for Excalidraw JSON elements. See `element-templates.md` for complete snippets.

---

## Element Types

| `type` value | Shape | Semantic use | `roundness` |
| --- | --- | --- | --- |
| `"rectangle"` | Box | Process, component, action | Optional (`{"type": 3}`) |
| `"diamond"` | Rotated square | Decision, conditional branch | Not supported |
| `"ellipse"` | Oval / circle | Start/end, external system, actor | Not supported |
| `"arrow"` | Directed edge | Causal flow, dependency, call | N/A |
| `"line"` | Undirected edge | Boundary, separator, non-directional link | N/A |
| `"text"` | Label | Annotation, title, inline content | N/A |

---

## Common Properties (All Element Types)

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | Yes | Must be unique across the entire document |
| `type` | string | Yes | See element types table above |
| `x` | number | Yes | Left edge in px. Start at ≥100 |
| `y` | number | Yes | Top edge in px. Start at ≥100 |
| `width` | number | Yes | Element width in px |
| `height` | number | Yes | Element height in px |
| `angle` | number | Yes | Rotation in radians. Use `0` for no rotation |
| `strokeColor` | string | Yes | Hex color string for border/line color |
| `backgroundColor` | string | Yes | Hex color or `"transparent"` |
| `fillStyle` | string | Yes | `"solid"`, `"hachure"`, `"cross-hatch"` |
| `strokeWidth` | number | Yes | Border thickness. Typically `1` or `2` |
| `strokeStyle` | string | Yes | `"solid"`, `"dashed"`, `"dotted"` |
| `roughness` | number | Yes | Hand-drawn effect. Use `0` for clean diagrams |
| `opacity` | number | Yes | 0–100 |
| `seed` | number | Yes | Random integer. Required for stable rendering |
| `versionNonce` | number | Yes | Random integer. Required for stable rendering |
| `groupIds` | array | Yes | Strings. Empty array if not grouped |
| `boundElements` | array | Yes | Bindings to arrows and contained text. See below |
| `isDeleted` | boolean | Yes | Always `false` for visible elements |

---

## Text-Specific Properties

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `fontSize` | number | Yes | Pixel size. Min 16 for labels, 20 for titles |
| `fontFamily` | number | Yes | `1` = Virgil (default), `2` = Helvetica, `3` = Cascadia |
| `text` | string | Yes | Displayed text (may include `\n`) |
| `originalText` | string | Yes | Pre-wrap source. Must match `text` unless wrapped |
| `textAlign` | string | Yes | `"left"`, `"center"`, `"right"` |
| `verticalAlign` | string | Yes | `"top"`, `"middle"`, `"bottom"` |
| `lineHeight` | number | Yes | Always `1.25` |
| `containerId` | string\|null | Yes | ID of parent shape, or `null` for free-floating |
| `autoResize` | boolean | Yes | Always `true` |

---

## Arrow-Specific Properties

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `points` | array | Yes | `[[x1,y1],[x2,y2], ...]` — relative to element origin |
| `lastCommittedPoint` | null | Yes | Always `null` |
| `startBinding` | object\|null | Yes | Binding to source element. See binding format |
| `endBinding` | object\|null | Yes | Binding to target element. See binding format |
| `startArrowhead` | string\|null | Yes | `null`, `"arrow"`, `"bar"`, `"dot"`, `"triangle"` |
| `endArrowhead` | string\|null | Yes | Usually `"arrow"` for directed flow |

---

## Binding Format

Used in `startBinding`, `endBinding` on arrows, and in `boundElements` on shapes.

**Arrow-side** (`startBinding` / `endBinding`):

```json
{
  "elementId": "rect1",
  "focus": 0,
  "gap": 4
}
```

**Shape-side** (`boundElements`):

```json
[
  { "id": "text1", "type": "text" },
  { "id": "arrow1", "type": "arrow" }
]
```

> Bindings must be symmetric: if an arrow's `startBinding.elementId` is `"rect1"`, then `rect1.boundElements` must include `{"id": "arrow1", "type": "arrow"}`.
