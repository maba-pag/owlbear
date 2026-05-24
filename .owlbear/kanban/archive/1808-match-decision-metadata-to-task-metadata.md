---
id: 1808
title: Match decision metadata to task metadata
status: archived
priority: important
created: 2026-05-24T07:33:19.208395+02:00
updated: 2026-05-24T10:50:02.736533+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - decisions
  - resolver
  - metadata
  - discussion
parent: 1773
depends_on: []
ac:
  - Decision resolver metadata uses the same visual pattern as Kanban task
    detail metadata as closely as practical.
  - Decision metadata no longer relies on the current line-heavy grid treatment.
  - The resolver remains readable and usable at the 1024px support floor and
    wide desktop widths.
  - Screenshot proof captures the updated decision metadata block.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback: Decision resolver metadata exists, but it is formatted differently from Kanban task detail metadata, with line-heavy dividers. It should be almost identical to the task detail metadata block rather than a different metadata language.

## Current Interpretation
Cockpit metadata blocks should share a common visual grammar across task detail and decision resolver surfaces.

## User Direction
Implement this now. Match task metadata styling as closely as practical without changing resolver behavior.

[[2026-05-24T07:48:02+02:00]]
Implemented task-style Decision resolver metadata: framed `Metadata` section, `PHeading size="small"`, text-sm `dl` grid, and no per-item divider lines. Verified focused Memory/Decision/Shell suites (213 tests passed), ESLint, production build, and screenshot proof at `.owlbear/scratch/1716-wide-cockpit/1808-decision-metadata-task-style-1024.png` and `.owlbear/scratch/1716-wide-cockpit/1808-decision-metadata-task-style-2000.png`. Geometry stayed inside the modal frame with the final 1280px cap.