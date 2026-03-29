# Excalidraw Color Palette

Semantic color mapping for Excalidraw diagrams. Every color must encode meaning —
never use color for decoration alone.

> Adapted from [coleam00/excalidraw-diagram-skill](https://github.com/coleam00/excalidraw-diagram-skill) (MIT).

## Excalidraw Built-in Colors

Excalidraw supports these named background/stroke colors. Use these for maximum
compatibility with the Excalidraw editor.

### Backgrounds (fill)

| Name | Hex | Semantic Use |
|------|-----|-------------|
| `transparent` | — | Default, no fill |
| `#a5d8ff` | Light blue | Primary components, active services |
| `#b2f2bb` | Light green | Success states, healthy, approved |
| `#ffec99` | Light yellow | Warnings, pending, in-progress |
| `#ffc9c9` | Light red | Errors, failures, blocked |
| `#d0bfff` | Light violet | External integrations, third-party |
| `#eebefa` | Light pink | User-facing components, UI layer |
| `#ffd8a8` | Light orange | Data/storage layer, databases |
| `#e9ecef` | Light gray | Inactive, deprecated, background context |

### Strokes

| Name | Hex | Semantic Use |
|------|-----|-------------|
| `#1e1e1e` | Near black | Default stroke, primary borders |
| `#1971c2` | Blue | Primary component borders |
| `#2f9e44` | Green | Success borders, healthy indicators |
| `#e03131` | Red | Error borders, failure indicators |
| `#f08c00` | Orange | Warning borders, caution |
| `#6741d9` | Violet | External/third-party borders |
| `#846358` | Brown | Data/storage borders |

### Text Colors

| Name | Hex | Semantic Use |
|------|-----|-------------|
| `#1e1e1e` | Near black | Default body text |
| `#1971c2` | Blue | Hyperlinks, references |
| `#2f9e44` | Green | Positive labels, success text |
| `#e03131` | Red | Error labels, failure text |

## Color Pairing Rules

1. **Background + Stroke** must be from the same semantic family (blue bg + blue stroke, not blue bg + red stroke).
2. **Text on colored backgrounds** — always use `#1e1e1e` (near black) for readability.
3. **Maximum 4 semantic colors** per diagram. More than 4 creates cognitive overload.
4. **White background** (`#ffffff`) for the overall canvas, colored fills for elements.
5. **Hero elements** use primary blue (`#a5d8ff` fill, `#1971c2` stroke). Supporting elements use lighter fills.
