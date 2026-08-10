# Cockpit Board Visual Design

## Problem

The cockpit board renders a functional kanban but has almost no visual styling. The Shell layout (grid, status bar, nav rail, sidecar) has CSS, and PDS components (buttons, tabs, banners) render correctly through the design system. But the board's own elements — columns, cards, headers, empty states, filter panel, context menu — use only bare inline styles with no visual treatment.

The result is a board that looks unfinished: no column backgrounds, no card shadows or radius, no hover/drag feedback, no typography hierarchy, no empty-state design. With an empty board (all tasks archived), the first impression is 7 identical unstyled divs each saying "No tasks."

## Current State

Only 2 CSS files exist in the entire frontend:
- `Shell.css` — grid layout, status bar, nav rail, sidecar regions
- `tokens.css` — PDS design token custom properties

Components with **zero CSS** (all styling is minimal inline):
- `KanbanBoard.tsx` — board container, filter bar, context menu
- `Column.tsx` — column wrapper, header, empty indicator
- `Card.tsx` — task card with priority border
- `FilterPanel.tsx` — filter controls
- `DetailTab.tsx` — task detail sidebar content
- `ActivityTab.tsx` — activity feed sidebar content

## Proposed Feature

Add proper visual styling to all board components using PDS design tokens and CSS files. The goal is "looks like a real product" — not a redesign, just dressing up the existing structure.

### Column styling
- Background surface color, rounded corners, subtle border
- Header with column name + task count badge, typographic hierarchy
- Proper padding and spacing between cards
- Drop target visual feedback (highlight border/background when dragging over valid target)

### Card styling
- Background surface, border radius, subtle shadow
- Priority indicator (left border already exists, refine colors)
- Hover state, selected state, focus ring
- Drag state (opacity change, elevation)
- Typography: task title with proper font size/weight, truncation
- Badge styling for blocked (⛔) and claimed (▶) indicators

### Empty state
- Meaningful empty-column indicator (not just "No tasks" text)
- Board-level empty state when all columns are empty ("No active tasks — create one to get started")

### Filter panel
- Styled inputs using PDS form components where possible
- Active filter indication
- Filter result count badge

### Context menu
- Styled dropdown with proper background, shadow, border radius
- Hover states on menu items
- Keyboard focus ring

### Status bar
- Traffic light indicator styling
- Proper spacing and alignment of badges

### Responsive
- Shell.css responsive breakpoints already exist — column grid should adapt (fewer columns visible, horizontal scroll, or stacked layout on mobile)

## Scope

- Frontend only — no backend changes
- CSS files per component (or a shared `board.css` for related styles)
- Uses PDS design tokens exclusively (no hardcoded colors/spacing)
- No structural changes to JSX — styling the existing elements
- Rebuild dist/ after CSS changes

## Non-goals

- No component restructuring or new PDS component adoption (that's separate work)
- No new features (grouping, search, etc. — those have their own briefs)
- No dark theme (PDS light theme only for v1)
