# Element Templates

> Adapted from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) (MIT).

JSON snippets for every element type. Copy, assign unique IDs, adjust position/size.
All required fields are shown — do not omit them. Additional optional fields may be added.

---

## Rectangle

Process step, component box, action block.

```json
{
  "id": "rect1",
  "type": "rectangle",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 80,
  "angle": 0,
  "strokeColor": "<stroke>",
  "backgroundColor": "<fill>",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 0,
  "opacity": 100,
  "roundness": { "type": 3 },
  "seed": 123456789,
  "versionNonce": 987654321,
  "groupIds": [],
  "boundElements": [
    { "id": "text1", "type": "text" },
    { "id": "arrow1", "type": "arrow" }
  ],
  "isDeleted": false
}
```

> `boundElements` must list BOTH contained text AND attached arrows for bidirectional binding.

---

## Text (In-Container)

Label inside a rectangle/diamond/ellipse. Must reference the container via `containerId`.

```json
{
  "id": "text1",
  "type": "text",
  "x": 110,
  "y": 128,
  "width": 180,
  "height": 24,
  "angle": 0,
  "strokeColor": "<text-primary>",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 1,
  "strokeStyle": "solid",
  "roughness": 0,
  "opacity": 100,
  "seed": 111111111,
  "versionNonce": 222222222,
  "groupIds": [],
  "boundElements": [],
  "isDeleted": false,
  "fontSize": 16,
  "fontFamily": 1,
  "text": "Label text",
  "originalText": "Label text",
  "textAlign": "center",
  "verticalAlign": "middle",
  "lineHeight": 1.25,
  "containerId": "rect1",
  "autoResize": true
}
```

---

## Text (Free-Floating)

Section header, annotation, legend entry. Not bound to any container.

```json
{
  "id": "text2",
  "type": "text",
  "x": 100,
  "y": 60,
  "width": 200,
  "height": 28,
  "angle": 0,
  "strokeColor": "<text-secondary>",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 1,
  "strokeStyle": "solid",
  "roughness": 0,
  "opacity": 100,
  "seed": 333333333,
  "versionNonce": 444444444,
  "groupIds": [],
  "boundElements": [],
  "isDeleted": false,
  "fontSize": 20,
  "fontFamily": 1,
  "text": "Section Title",
  "originalText": "Section Title",
  "textAlign": "left",
  "verticalAlign": "top",
  "lineHeight": 1.25,
  "containerId": null,
  "autoResize": true
}
```

---

## Arrow (With Bindings)

Directional relationship between two elements. Both the arrow AND each target element must reference each other.

```json
{
  "id": "arrow1",
  "type": "arrow",
  "x": 300,
  "y": 140,
  "width": 100,
  "height": 0,
  "angle": 0,
  "strokeColor": "<stroke>",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 0,
  "opacity": 100,
  "seed": 555555555,
  "versionNonce": 666666666,
  "groupIds": [],
  "boundElements": [],
  "isDeleted": false,
  "points": [[0, 0], [100, 0]],
  "lastCommittedPoint": null,
  "startBinding": {
    "elementId": "rect1",
    "focus": 0,
    "gap": 4
  },
  "endBinding": {
    "elementId": "rect2",
    "focus": 0,
    "gap": 4
  },
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```

> Each target element must include `{"id": "arrow1", "type": "arrow"}` in its own `boundElements` array.

---

## Line

Non-directional separator, boundary marker, or connector.

```json
{
  "id": "line1",
  "type": "line",
  "x": 100,
  "y": 200,
  "width": 400,
  "height": 0,
  "angle": 0,
  "strokeColor": "<stroke-muted>",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 1,
  "strokeStyle": "dashed",
  "roughness": 0,
  "opacity": 60,
  "seed": 777777777,
  "versionNonce": 888888888,
  "groupIds": [],
  "boundElements": [],
  "isDeleted": false,
  "points": [[0, 0], [400, 0]],
  "lastCommittedPoint": null,
  "startBinding": null,
  "endBinding": null,
  "startArrowhead": null,
  "endArrowhead": null
}
```

---

## Small Marker Dot

Timeline event marker, status indicator, node anchor.

```json
{
  "id": "dot1",
  "type": "ellipse",
  "x": 194,
  "y": 194,
  "width": 12,
  "height": 12,
  "angle": 0,
  "strokeColor": "<stroke>",
  "backgroundColor": "<fill-accent>",
  "fillStyle": "solid",
  "strokeWidth": 1,
  "strokeStyle": "solid",
  "roughness": 0,
  "opacity": 100,
  "seed": 101010101,
  "versionNonce": 202020202,
  "groupIds": [],
  "boundElements": [],
  "isDeleted": false
}
```

---

## Diamond

Decision node, conditional branch, gateway. Use ~120×120 for square aspect ratio.

```json
{
  "id": "diamond1",
  "type": "diamond",
  "x": 100,
  "y": 100,
  "width": 120,
  "height": 120,
  "angle": 0,
  "strokeColor": "<stroke>",
  "backgroundColor": "<fill-decision>",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 0,
  "opacity": 100,
  "seed": 303030303,
  "versionNonce": 404040404,
  "groupIds": [],
  "boundElements": [
    { "id": "text3", "type": "text" }
  ],
  "isDeleted": false
}
```

> No `roundness` field — diamonds do not support rounded corners.

---

## Ellipse

Start/end terminal, external system, actor. Use ~160×80 for oval aspect ratio.

```json
{
  "id": "ellipse1",
  "type": "ellipse",
  "x": 100,
  "y": 100,
  "width": 160,
  "height": 80,
  "angle": 0,
  "strokeColor": "<stroke>",
  "backgroundColor": "<fill-terminal>",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 0,
  "opacity": 100,
  "seed": 505050505,
  "versionNonce": 606060606,
  "groupIds": [],
  "boundElements": [
    { "id": "text4", "type": "text" }
  ],
  "isDeleted": false
}
```

> No `roundness` field — ellipses do not support rounded corners.
