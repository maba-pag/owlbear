---
id: 1806
title: Keep Kanban columns equal width
status: research
priority: important
created: 2026-05-24T07:01:29.828173+02:00
updated: 2026-05-24T07:01:29.828173+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - layout
  - discussion
parent: 1773
depends_on: []
ac:
  - Kanban columns render at equal widths across supported desktop viewports 
    when the board has multiple statuses.
  - The Done column no longer appears visually narrower than sibling columns 
    under the normal board layout.
  - Horizontal scrolling behavior remains intentional when there are more 
    columns than fit comfortably.
  - Screenshot proof captures the board at the 1024px support floor and a wide 
    desktop viewport.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback: on the Kanban board, the Done column looks narrower than the others. Expected behavior is that all columns have the same width.

## Current Interpretation
The board grid may be distributing columns unevenly, or a visual/card-density cue may be making an empty or sparse Done column read as narrower. Needs evidence before implementation.

## Value
Equal column width supports scanning and makes status lanes feel stable and deliberate.

## Boundary
Discussion task only. Do not implement until explicitly approved.