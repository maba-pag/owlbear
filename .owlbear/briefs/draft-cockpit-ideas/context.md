# Context — Cockpit Ideas Notebook

## Problem

The OwlBear cockpit has no capture surface for pre-task ideas. Ideas that aren't ready for structured task format either get lost or require context-switching to the filesystem. The user wants a freeform markdown scratchpad inside the cockpit so ideas can be captured and revisited without leaving the dashboard.

## Scope

This discovery is focused on the Ideas Notebook feature specifically — a freeform markdown scratchpad as a cockpit tab. The tab system infrastructure is already planned and decomposed (parent #1638, tasks #1639-1644, #1645-1649), so the notebook tab would plug into the route config as a new entry once the tab shell lands.

## Current State

- Cockpit is a kanban board with sidecar detail/activity panel, DR resolution, and SSE real-time updates.
- Tab system is in progress (#1638): declarative route config, nav-rail, React Router, lazy loading, sidecar conditioning.
- The task body editor already has markdown edit/preview toggle (in TaskFieldsEditor).
- No freeform capture surface exists outside task editing.
- `.owlbear/ideas.md` does not exist yet.
- Existing markdown edit/preview in TaskFieldsEditor is the closest reuse target.

## Key Decisions So Far

- Project type: existing-feature/refactor (plugs into tab system)
- Investment tier: Tool
- Save: explicit button, no auto-save
- No agent integration — filesystem visibility is sufficient
- Feature justified as workspace completeness preference (challengers noted VS Code is the superior editor; accepted)

## Outcomes (M2 lock)

- **Best realistic:** A cockpit "Ideas" tab where you type markdown, see it rendered, and save to `.owlbear/ideas.md`. Plugs into route config with zero infrastructure work. Backend is two endpoints. Frontend reuses edit/preview toggle. Opening the tab feels instant.
- **Minimum viable win:** Tab exists, edit and save work, markdown renders.
- **Scope boundary In:** GET/PUT API, page component with edit/preview, route config entry, save button with unsaved indicator.
- **Scope boundary Out:** Auto-save, multiple files, search, agent wiring, mobile design, preview toggle (simplifier cut — considered for Phase 2 to evaluate).

## Active Tensions

- Simplifier suggests dropping the preview toggle entirely ("nobody previews scratch notes"). Worth evaluating in Phase 2 whether textarea-only is the right v1 or whether preview adds enough value.
- Tab system coupling: feature depends on #1638 completing. Acceptable dependency since the tab system is the deliberate infrastructure play.
- mtime in API response: YAGNI per simplifier. Return content only.
