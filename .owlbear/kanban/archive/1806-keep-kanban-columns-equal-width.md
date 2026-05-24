---
id: 1806
title: Keep Kanban columns equal width
status: archived
priority: important
created: 2026-05-24T07:01:29.828173+02:00
updated: 2026-05-24T10:50:02.709408+02:00
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
archival_reason: completed
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

[[2026-05-24T07:54:19+02:00]]
## Evidence
Captured controlled board screenshots at `.owlbear/scratch/1716-wide-cockpit/1806-kanban-columns-current-1024.png` and `.owlbear/scratch/1716-wide-cockpit/1806-kanban-columns-current-2000.png`.

Measured geometry:
- 1024px viewport: all rendered tracks are equal at 248px. The strip intentionally scrolls horizontally; Done is off-screen at initial scroll.
- 2000px viewport: all rendered tracks are equal at 280px, but the strip still overflows (`scrollWidth: 2064`, `clientWidth: 1865`). Done's actual track is 280px, but only 136px is visible, so it appears narrower/clipped.

Interpretation: the visual bug is not unequal CSS grid tracks. The column minimum grows to 280px too early (`--kanban-column-min: clamp(248px,15vw,280px)`), so seven normal lanes cannot fit even on a 2000px viewport. Reducing the responsive middle term, while preserving the 248px support-floor minimum and the 280px upper bound, should let wide desktop show all seven lanes equally while keeping intentional horizontal scroll at 1024px.

[[2026-05-24T08:11:02+02:00]]
Implemented approved `--kanban-column-min: clamp(248px,12.5vw,280px)` rule. Focused KanbanBoard tests passed (42 tests), ESLint passed for changed Kanban files, and production build passed with the known Vite chunk-size warning only.

Screenshot proof:
- `.owlbear/scratch/1716-wide-cockpit/1806-kanban-columns-equal-1024.png`
- `.owlbear/scratch/1716-wide-cockpit/1806-kanban-columns-equal-2000.png`

Geometry proof:
- 1024px viewport: all tracks equal at 248px; horizontal scrolling remains intentional.
- 2000px viewport: strip no longer overflows (`scrollWidth: 1865`, `clientWidth: 1865`); all seven lanes, including Done, are fully visible at about 251.56px each with only subpixel rounding differences.