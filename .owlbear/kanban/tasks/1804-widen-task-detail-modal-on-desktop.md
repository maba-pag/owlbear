---
id: 1804
title: Widen task detail modal on desktop
status: done
priority: important
created: 2026-05-24T06:42:36.487319+02:00
updated: 2026-05-24T07:48:02+02:00
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
  - Decision resolver also uses the wider desktop cap while remaining inside the
    PDS modal frame at the 1024px support floor.
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

[[2026-05-24T07:07:49+02:00]]
## Evidence
Captured current wide-desktop proof at `.owlbear/scratch/1716-wide-cockpit/1804-task-detail-current-2000.png`.

Current geometry after #1784:
- 1024px viewport: task detail child width 728px, inside PDS frame, ratio 0.71.
- 1440px viewport: task detail child width 920px, inside PDS frame, ratio 0.64.
- 2000px viewport: task detail child width 920px, inside PDS frame, ratio 0.46.
- 2560px viewport: task detail child width 920px, inside PDS frame, ratio 0.36.

Interpretation: #1784 preserved the support-floor frame, but the 920px cap now underuses wide desktop space for the high-frequency task detail workflow.

[[2026-05-24T07:11:14+02:00]]
## User Approval
User approved widening both task detail and decision resolver modal surfaces to `min(1440px, ...)`, preserving the frame-aware viewport guard.

[[2026-05-24T07:15:07+02:00]]
Implemented approved 1440px desktop cap for both task detail and decision resolver modal surfaces while preserving the `calc(100vw - 18.5rem)` frame guard. Focused modal suites passed (76 tests). ESLint passed for changed modal files/tests. Production build passed with the known Vite chunk-size warning only. Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/1804-task-detail-wide-1024.png`, `.owlbear/scratch/1716-wide-cockpit/1804-task-detail-wide-2000.png`, `.owlbear/scratch/1716-wide-cockpit/1804-resolve-wide-1024.png`, `.owlbear/scratch/1716-wide-cockpit/1804-resolve-wide-2000.png`. Geometry proof: task and resolver widths were 728px at 1024, 1032.84px at 1440, 1383.5px at 2000, and 1383.5px at 2560; all remained inside the PDS frame and viewport.

[[2026-05-24T07:27:42+02:00]]
## Follow-up Correction
After commit review, the committed modal cap was found to be `1280px` while the user-approved/task-recorded cap was `1440px`. Corrected task detail and resolver classes/tests to `min(1440px, calc(100vw - 18.5rem))` and reran focused modal tests, ESLint, build, and geometry. Current geometry: 728px at 1024 and 1383.5px at 2000/2560 for both task and resolver, all inside frame.

[[2026-05-24T07:48:02+02:00]]
## Latest User Correction
User clarified that they intentionally changed the preferred desktop cap from `1440px` to `1280px` because `1440px` looked poor. Restored task detail and decision resolver modal surfaces/tests to `min(1280px, calc(100vw - 18.5rem))`. Current package keeps the 1024px support-floor frame guard while honoring the final 1280px cap.
