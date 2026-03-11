# Excalidraw Element Templates

JSON snippets for every core element type. Copy, modify IDs and coordinates,
and assemble into the `elements` array.

> Adapted from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) (MIT).

## Rectangle

```json
{
  "id": "rect-1",
  "type": "rectangle",
  "x": 100,
  "y": 100,
  "width": 200,
  "height": 80,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#a5d8ff",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "roundness": { "type": 3 },
  "boundElements": [],
  "locked": false
}
```

## Diamond

```json
{
  "id": "diamond-1",
  "type": "diamond",
  "x": 100,
  "y": 100,
  "width": 160,
  "height": 120,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#ffec99",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "roundness": { "type": 2 },
  "boundElements": [],
  "locked": false
}
```

## Ellipse

```json
{
  "id": "ellipse-1",
  "type": "ellipse",
  "x": 100,
  "y": 100,
  "width": 140,
  "height": 80,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "#b2f2bb",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "roundness": { "type": 2 },
  "boundElements": [],
  "locked": false
}
```

## Text

```json
{
  "id": "text-1",
  "type": "text",
  "x": 100,
  "y": 100,
  "width": 120,
  "height": 25,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "roundness": null,
  "boundElements": [],
  "locked": false,
  "text": "Label Text",
  "fontSize": 20,
  "fontFamily": 5,
  "textAlign": "center",
  "verticalAlign": "middle",
  "containerId": null,
  "originalText": "Label Text",
  "autoResize": true
}
```

**Bound text** (inside a shape): set `containerId` to the parent shape's `id`,
and add `{ "id": "text-1", "type": "text" }` to the parent's `boundElements`.

## Arrow

```json
{
  "id": "arrow-1",
  "type": "arrow",
  "x": 300,
  "y": 140,
  "width": 200,
  "height": 0,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "roundness": { "type": 2 },
  "boundElements": [],
  "locked": false,
  "points": [[0, 0], [200, 0]],
  "startBinding": {
    "elementId": "rect-1",
    "focus": 0,
    "gap": 1,
    "fixedPoint": null
  },
  "endBinding": {
    "elementId": "rect-2",
    "focus": 0,
    "gap": 1,
    "fixedPoint": null
  },
  "startArrowhead": null,
  "endArrowhead": "arrow"
}
```

**Binding rules:**

- `startBinding.elementId` / `endBinding.elementId` must match existing element `id` values.
- Add `{ "id": "arrow-1", "type": "arrow" }` to both connected elements' `boundElements`.
- Set `focus: 0` for center connection; `-1` to `1` shifts the anchor point.

## Line

```json
{
  "id": "line-1",
  "type": "line",
  "x": 100,
  "y": 100,
  "width": 0,
  "height": 300,
  "angle": 0,
  "strokeColor": "#1e1e1e",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 2,
  "strokeStyle": "solid",
  "roughness": 1,
  "opacity": 100,
  "groupIds": [],
  "roundness": { "type": 2 },
  "boundElements": [],
  "locked": false,
  "points": [[0, 0], [0, 300]]
}
```

## Grouping

To group elements, assign the same group ID in each element's `groupIds` array:

```json
{ "id": "rect-a", "groupIds": ["group-1"], ... },
{ "id": "text-a", "groupIds": ["group-1"], ... }
```

Nested groups: `"groupIds": ["inner-group", "outer-group"]` — inner listed first.

## Example: Architecture (Fan-Out)

A central service with two satellite components:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "owlbear",
  "elements": [
    {
      "id": "hero",
      "type": "rectangle",
      "x": 300, "y": 100, "width": 240, "height": 100,
      "strokeColor": "#1971c2", "backgroundColor": "#a5d8ff",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 3 },
      "boundElements": [
        { "id": "hero-label", "type": "text" },
        { "id": "arrow-1", "type": "arrow" },
        { "id": "arrow-2", "type": "arrow" }
      ],
      "locked": false
    },
    {
      "id": "hero-label",
      "type": "text",
      "x": 340, "y": 130, "width": 160, "height": 40,
      "text": "API Gateway", "fontSize": 24, "fontFamily": 5,
      "textAlign": "center", "verticalAlign": "middle",
      "containerId": "hero",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "API Gateway", "autoResize": true, "locked": false
    },
    {
      "id": "sat-1",
      "type": "rectangle",
      "x": 100, "y": 320, "width": 200, "height": 80,
      "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": ["group-services"], "roundness": { "type": 3 },
      "boundElements": [
        { "id": "sat-1-label", "type": "text" },
        { "id": "arrow-1", "type": "arrow" }
      ],
      "locked": false
    },
    {
      "id": "sat-1-label",
      "type": "text",
      "x": 130, "y": 345, "width": 140, "height": 30,
      "text": "Auth Service", "fontSize": 20, "fontFamily": 5,
      "textAlign": "center", "verticalAlign": "middle",
      "containerId": "sat-1",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "Auth Service", "autoResize": true, "locked": false
    },
    {
      "id": "sat-2",
      "type": "rectangle",
      "x": 500, "y": 320, "width": 200, "height": 80,
      "strokeColor": "#6741d9", "backgroundColor": "#d0bfff",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": ["group-services"], "roundness": { "type": 3 },
      "boundElements": [
        { "id": "sat-2-label", "type": "text" },
        { "id": "arrow-2", "type": "arrow" }
      ],
      "locked": false
    },
    {
      "id": "sat-2-label",
      "type": "text",
      "x": 530, "y": 345, "width": 140, "height": 30,
      "text": "Data Store", "fontSize": 20, "fontFamily": 5,
      "textAlign": "center", "verticalAlign": "middle",
      "containerId": "sat-2",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "Data Store", "autoResize": true, "locked": false
    },
    {
      "id": "arrow-1",
      "type": "arrow",
      "x": 380, "y": 200, "width": 100, "height": 120,
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 }, "boundElements": [],
      "points": [[0, 0], [-180, 120]],
      "startBinding": { "elementId": "hero", "focus": 0, "gap": 1, "fixedPoint": null },
      "endBinding": { "elementId": "sat-1", "focus": 0, "gap": 1, "fixedPoint": null },
      "startArrowhead": null, "endArrowhead": "arrow", "locked": false
    },
    {
      "id": "arrow-2",
      "type": "arrow",
      "x": 460, "y": 200, "width": 100, "height": 120,
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 }, "boundElements": [],
      "points": [[0, 0], [140, 120]],
      "startBinding": { "elementId": "hero", "focus": 0, "gap": 1, "fixedPoint": null },
      "endBinding": { "elementId": "sat-2", "focus": 0, "gap": 1, "fixedPoint": null },
      "startArrowhead": null, "endArrowhead": "arrow", "locked": false
    }
  ],
  "appState": { "gridSize": 20, "viewBackgroundColor": "#ffffff" },
  "files": {}
}
```

## Example: Flowchart (Diamond Decision)

A process with a decision branch:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "owlbear",
  "elements": [
    {
      "id": "start",
      "type": "ellipse",
      "x": 200, "y": 60, "width": 140, "height": 60,
      "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 },
      "boundElements": [
        { "id": "start-label", "type": "text" },
        { "id": "a-start-proc", "type": "arrow" }
      ],
      "locked": false
    },
    {
      "id": "start-label",
      "type": "text",
      "x": 235, "y": 75, "width": 70, "height": 30,
      "text": "Start", "fontSize": 20, "fontFamily": 5,
      "textAlign": "center", "verticalAlign": "middle",
      "containerId": "start",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "Start", "autoResize": true, "locked": false
    },
    {
      "id": "process",
      "type": "rectangle",
      "x": 190, "y": 180, "width": 160, "height": 70,
      "strokeColor": "#1971c2", "backgroundColor": "#a5d8ff",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 3 },
      "boundElements": [
        { "id": "proc-label", "type": "text" },
        { "id": "a-start-proc", "type": "arrow" },
        { "id": "a-proc-decide", "type": "arrow" }
      ],
      "locked": false
    },
    {
      "id": "proc-label",
      "type": "text",
      "x": 215, "y": 200, "width": 110, "height": 30,
      "text": "Validate", "fontSize": 20, "fontFamily": 5,
      "textAlign": "center", "verticalAlign": "middle",
      "containerId": "process",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "Validate", "autoResize": true, "locked": false
    },
    {
      "id": "decide",
      "type": "diamond",
      "x": 190, "y": 310, "width": 160, "height": 120,
      "strokeColor": "#f08c00", "backgroundColor": "#ffec99",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 },
      "boundElements": [
        { "id": "decide-label", "type": "text" },
        { "id": "a-proc-decide", "type": "arrow" },
        { "id": "a-decide-yes", "type": "arrow" },
        { "id": "a-decide-no", "type": "arrow" }
      ],
      "locked": false
    },
    {
      "id": "decide-label",
      "type": "text",
      "x": 225, "y": 355, "width": 90, "height": 30,
      "text": "Valid?", "fontSize": 20, "fontFamily": 5,
      "textAlign": "center", "verticalAlign": "middle",
      "containerId": "decide",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "Valid?", "autoResize": true, "locked": false
    },
    {
      "id": "end-yes",
      "type": "ellipse",
      "x": 80, "y": 500, "width": 140, "height": 60,
      "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 },
      "boundElements": [
        { "id": "end-yes-label", "type": "text" },
        { "id": "a-decide-yes", "type": "arrow" }
      ],
      "locked": false
    },
    {
      "id": "end-yes-label",
      "type": "text",
      "x": 110, "y": 515, "width": 80, "height": 30,
      "text": "Deploy", "fontSize": 20, "fontFamily": 5,
      "textAlign": "center", "verticalAlign": "middle",
      "containerId": "end-yes",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "Deploy", "autoResize": true, "locked": false
    },
    {
      "id": "end-no",
      "type": "ellipse",
      "x": 330, "y": 500, "width": 140, "height": 60,
      "strokeColor": "#e03131", "backgroundColor": "#ffc9c9",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 },
      "boundElements": [
        { "id": "end-no-label", "type": "text" },
        { "id": "a-decide-no", "type": "arrow" }
      ],
      "locked": false
    },
    {
      "id": "end-no-label",
      "type": "text",
      "x": 365, "y": 515, "width": 70, "height": 30,
      "text": "Reject", "fontSize": 20, "fontFamily": 5,
      "textAlign": "center", "verticalAlign": "middle",
      "containerId": "end-no",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "Reject", "autoResize": true, "locked": false
    },
    {
      "id": "a-start-proc",
      "type": "arrow",
      "x": 270, "y": 120, "width": 0, "height": 60,
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 }, "boundElements": [],
      "points": [[0, 0], [0, 60]],
      "startBinding": { "elementId": "start", "focus": 0, "gap": 1, "fixedPoint": null },
      "endBinding": { "elementId": "process", "focus": 0, "gap": 1, "fixedPoint": null },
      "startArrowhead": null, "endArrowhead": "arrow", "locked": false
    },
    {
      "id": "a-proc-decide",
      "type": "arrow",
      "x": 270, "y": 250, "width": 0, "height": 60,
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 }, "boundElements": [],
      "points": [[0, 0], [0, 60]],
      "startBinding": { "elementId": "process", "focus": 0, "gap": 1, "fixedPoint": null },
      "endBinding": { "elementId": "decide", "focus": 0, "gap": 1, "fixedPoint": null },
      "startArrowhead": null, "endArrowhead": "arrow", "locked": false
    },
    {
      "id": "a-decide-yes",
      "type": "arrow",
      "x": 220, "y": 430, "width": 80, "height": 70,
      "strokeColor": "#2f9e44", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 }, "boundElements": [],
      "points": [[0, 0], [-70, 70]],
      "startBinding": { "elementId": "decide", "focus": 0, "gap": 1, "fixedPoint": null },
      "endBinding": { "elementId": "end-yes", "focus": 0, "gap": 1, "fixedPoint": null },
      "startArrowhead": null, "endArrowhead": "arrow", "locked": false
    },
    {
      "id": "a-decide-no",
      "type": "arrow",
      "x": 320, "y": 430, "width": 80, "height": 70,
      "strokeColor": "#e03131", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 }, "boundElements": [],
      "points": [[0, 0], [80, 70]],
      "startBinding": { "elementId": "decide", "focus": 0, "gap": 1, "fixedPoint": null },
      "endBinding": { "elementId": "end-no", "focus": 0, "gap": 1, "fixedPoint": null },
      "startArrowhead": null, "endArrowhead": "arrow", "locked": false
    }
  ],
  "appState": { "gridSize": 20, "viewBackgroundColor": "#ffffff" },
  "files": {}
}
```

## Example: Sequence (Timeline)

A vertical timeline with three events:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "owlbear",
  "elements": [
    {
      "id": "timeline",
      "type": "line",
      "x": 200, "y": 60, "width": 0, "height": 400,
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "dotted",
      "roughness": 0, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": { "type": 2 }, "boundElements": [],
      "points": [[0, 0], [0, 400]], "locked": false
    },
    {
      "id": "dot-1",
      "type": "ellipse",
      "x": 190, "y": 90, "width": 20, "height": 20,
      "strokeColor": "#1971c2", "backgroundColor": "#1971c2",
      "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
      "roughness": 0, "opacity": 100, "angle": 0,
      "groupIds": ["event-1"], "roundness": { "type": 2 },
      "boundElements": [], "locked": false
    },
    {
      "id": "event-1",
      "type": "rectangle",
      "x": 240, "y": 75, "width": 260, "height": 50,
      "strokeColor": "#1971c2", "backgroundColor": "#a5d8ff",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": ["event-1"], "roundness": { "type": 3 },
      "boundElements": [{ "id": "event-1-label", "type": "text" }],
      "locked": false
    },
    {
      "id": "event-1-label",
      "type": "text",
      "x": 260, "y": 85, "width": 220, "height": 30,
      "text": "1. Request received", "fontSize": 18, "fontFamily": 5,
      "textAlign": "left", "verticalAlign": "middle",
      "containerId": "event-1",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "1. Request received", "autoResize": true, "locked": false
    },
    {
      "id": "dot-2",
      "type": "ellipse",
      "x": 190, "y": 220, "width": 20, "height": 20,
      "strokeColor": "#f08c00", "backgroundColor": "#f08c00",
      "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
      "roughness": 0, "opacity": 100, "angle": 0,
      "groupIds": ["event-2"], "roundness": { "type": 2 },
      "boundElements": [], "locked": false
    },
    {
      "id": "event-2",
      "type": "rectangle",
      "x": 240, "y": 205, "width": 260, "height": 50,
      "strokeColor": "#f08c00", "backgroundColor": "#ffec99",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": ["event-2"], "roundness": { "type": 3 },
      "boundElements": [{ "id": "event-2-label", "type": "text" }],
      "locked": false
    },
    {
      "id": "event-2-label",
      "type": "text",
      "x": 260, "y": 215, "width": 220, "height": 30,
      "text": "2. Processing...", "fontSize": 18, "fontFamily": 5,
      "textAlign": "left", "verticalAlign": "middle",
      "containerId": "event-2",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "2. Processing...", "autoResize": true, "locked": false
    },
    {
      "id": "dot-3",
      "type": "ellipse",
      "x": 190, "y": 350, "width": 20, "height": 20,
      "strokeColor": "#2f9e44", "backgroundColor": "#2f9e44",
      "fillStyle": "solid", "strokeWidth": 1, "strokeStyle": "solid",
      "roughness": 0, "opacity": 100, "angle": 0,
      "groupIds": ["event-3"], "roundness": { "type": 2 },
      "boundElements": [], "locked": false
    },
    {
      "id": "event-3",
      "type": "rectangle",
      "x": 240, "y": 335, "width": 260, "height": 50,
      "strokeColor": "#2f9e44", "backgroundColor": "#b2f2bb",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": ["event-3"], "roundness": { "type": 3 },
      "boundElements": [{ "id": "event-3-label", "type": "text" }],
      "locked": false
    },
    {
      "id": "event-3-label",
      "type": "text",
      "x": 260, "y": 345, "width": 220, "height": 30,
      "text": "3. Response sent", "fontSize": 18, "fontFamily": 5,
      "textAlign": "left", "verticalAlign": "middle",
      "containerId": "event-3",
      "strokeColor": "#1e1e1e", "backgroundColor": "transparent",
      "fillStyle": "solid", "strokeWidth": 2, "strokeStyle": "solid",
      "roughness": 1, "opacity": 100, "angle": 0,
      "groupIds": [], "roundness": null, "boundElements": [],
      "originalText": "3. Response sent", "autoResize": true, "locked": false
    }
  ],
  "appState": { "gridSize": 20, "viewBackgroundColor": "#ffffff" },
  "files": {}
}
```
