---
id: 1804
title: Widen task detail modal on desktop
status: research
priority: important
created: 2026-05-24T06:42:36.487319+02:00
updated: 2026-05-24T06:42:36.487319+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - task-detail
  - pds
  - desktop
  - discussion
parent: 1773
depends_on: []
ac:
  - Task detail modal remains visually inside the PDS modal frame at the 1024px 
    support floor.
  - Task detail modal uses substantially more width on wide desktop viewports, 
    including 2000px and above.
  - 'Decision resolver frame alignment from #1784 remains intact unless explicitly
    changed by this task.'
  - The detail view remains comfortable in display and edit modes, with no 
    horizontal overflow or backdrop overhang.
  - Screenshot and geometry proof cover 1024px and at least one 2000px+ desktop 
    viewport.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback after #1784: the Kanban task details modal is now too narrow for normal resolutions, and is hardly usable on a desktop viewport of 2000px+.

## Current Interpretation
The #1784 frame-aware sizing fixed the 1024px overhang, but the same maximum width may be too conservative on wide desktop screens. The task detail modal likely needs responsive widening that preserves the PDS frame constraint at the support floor.

## Value
Task details are a core repeated workflow; wide desktop users should get a comfortable reading and editing surface rather than a narrow modal column.

## Boundary
Discussion task only. Do not implement until explicitly approved.