---
id: 1835
title: Review Kanban card move action discoverability
status: research
priority: important
created: 2026-05-24T12:17:30.160637+02:00
updated: 2026-05-24T12:17:30.160637+02:00
tags:
  - scope:cockpit-web
  - kanban
  - ux
  - interaction
  - discussion
parent: 1773
depends_on: []
ac:
  - Evaluate Kanban card move/archive discoverability now that drag/drop is 
    removed.
  - Any approved change preserves quick move/archive behavior and keyboard 
    context-menu access.
  - Any approved change keeps card density and scanning quality suitable for the
    board.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
Kanban cards visually present task identity, age, title, and tags, but they do not expose that move/archive actions are available from the card. The card DOM has `aria-haspopup="menu"`, and right-clicking opens a context menu with move targets plus Archive, but the visible card text contains no Move, Archive, menu, or action affordance.

## Evidence
- Screenshot before interaction: `.owlbear/scratch/1773-audit-continue/kanban-card-before-context.png`
- Context menu screenshot: `.owlbear/scratch/1773-audit-continue/kanban-card-context-menu.png`
- Runtime report: `.owlbear/scratch/1773-audit-continue/kanban-card-context-report.json`
- Code surface: `serve/cockpit/web/src/components/Card.tsx` sets `aria-haspopup="menu"` and handles Shift+F10/context-menu; `serve/cockpit/web/src/KanbanBoard.tsx` renders the move/archive context menu.
- Historical context: archived #1707 intentionally removed drag/drop and preserved explicit move paths through task context menu and detail actions.

## Observed User Impact
Moving tasks is a core board workflow. After drag/drop removal, the primary board view relies on a hidden context-menu gesture for quick moves. A mouse user can click a card to open detail, but may not discover right-click move/archive from the card itself; a keyboard user has an accessibility hint, but the visual workflow lacks a comparable cue. This can make the board feel read-only until the user learns the hidden interaction.

## Boundary
This is an audit finding only. Do not implement without explicit user approval. The review should decide whether the board should add a compact visible action/menu affordance on cards, surface move actions in another standard place, or intentionally keep the current hidden context-menu pattern.
