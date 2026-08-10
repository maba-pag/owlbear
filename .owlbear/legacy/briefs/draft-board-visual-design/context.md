# Context — Board Visual Design

## Problem

The cockpit board is structurally complete but visually invisible. White-on-white with floating text — no surfaces, shadows, borders, or visual hierarchy are rendered. As a human user, you cannot see where components begin and end. Buttons are invisible text; columns are undifferentiated whitespace.

The goal: apply PDS design tokens comprehensively to make the board look and feel like a finished product. Stay as close to the Porsche Design System as possible — use what others built, minimize custom invention.

## Project Type

Existing-feature/refactor — styling existing JSX structure with CSS using PDS design tokens.

## Motivation

Not a polish pass — this is the design *implementation*. The user wants a good-looking cockpit now so future feature work (grouping, search, decisions tab, etc.) inherits a solid visual baseline rather than fighting design debt as an afterthought.

## Scope Signal

- Frontend CSS only (no backend)
- Minimal structural JSX changes (class names, data attributes for selectors)
- PDS design tokens as the exclusive color/spacing source
- No new features (grouping, search, etc. have separate briefs)
- DnD for task status moves: questionable UX (user prefers intentional context-menu moves), but won't be removed — at most deactivated if trivial, otherwise styled minimally

## Current State

- 2 CSS files exist: `Shell.css` (layout grid), `tokens.css` (PDS custom properties)
- 6 components with zero CSS: KanbanBoard, Column, Card, FilterPanel, DetailTab, ActivityTab
- Native HTML DnD (`draggable`, `onDragStart`/`onDrop`) — no library
- Context menu exists for intentional task moves
- Shell already has the right structure: status bar, tab nav, board area, sidecar

## User's Mental Model of Target

- Status bar on top
- Top-left: tab selection (kanban, DR, notes, etc.)
- Top-right: status lights
- Board: visible boxes containing columns
- Optional filter bar (dropdown)
- Right panel: additional info (pipeline status, etc.)

## Open Questions (for research bridge)

- What PDS tokens are available for surfaces/elevation/shadows?
- What are PDS spacing and typography conventions?
- Are there PDS reference apps or patterns we can study for card/list styling?
- How complex is deactivating DnD on task cards (vs just not styling it prominently)?
- What does PDS `themeDark` token set look like? (generate and inspect)
- Theme toggle mechanism: `prefers-color-scheme` media query, manual toggle, or both?
- How do existing PDS React components respond to the theme attribute?

## Locked Outcomes

**Best realistic outcome:** Board looks like a finished product in both light and dark themes. Columns are visible surfaces. Cards have boundaries, shadows, priority indicators, and typography hierarchy. Empty states, filter, context menu look native. Theme-agnostic token layer means future features and Shell.css all get dark mode from one attribute change.

**Minimum viable win:** Board is visible and coherent in both themes. Basic surfaces, spacing, typography in place. Hover/focus states work. Secondary polish can be thinner.

**Scope:**
- Frontend CSS + token restructuring (both themes)
- Theme-agnostic var names + dark override block in tokens.css
- Per-component CSS files (Column.css, Card.css, etc.)
- JSX changes as needed for visual quality (className additions, inline style extraction, minor structural tweaks) — no new features or behavioral changes
- DnD: keep, style minimally
- PDS tokens exclusively

**Active Tensions (for Phase 2):**
- Auto-responsive tokens (prefers-color-scheme) vs manual toggle vs both?
- Card height constraints: keep tight density or let cards grow?
- Empty state design: minimal text vs illustrated
- "Finished product" quality bar needs concrete definition per component
