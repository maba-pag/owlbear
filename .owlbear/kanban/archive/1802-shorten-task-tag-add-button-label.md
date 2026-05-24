---
id: 1802
title: Shorten task tag add button label
status: archived
priority: needed
created: 2026-05-24T06:42:25.713651+02:00
updated: 2026-05-24T10:50:02.654627+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - task-detail
  - forms
  - discussion
parent: 1773
depends_on: []
ac:
  - In task detail edit mode, the tag add action reads '+ Add' or equivalent
    concise text rather than '+ Add tag'.
  - The label remains understandable next to the tag input at the 1024px support
    floor and wide desktop widths.
  - Tag add behavior, validation, dirty state, and save payload remain
    unchanged.
  - Screenshot proof captures the revised tag add row.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback: in Kanban task detail edit mode, the '+ Add tag' button can be shortened to '+ Add' because the adjacent tag input already establishes the object being added.

## Current Interpretation
The current button repeats context and adds visual noise in an already dense edit form.

## Value
A shorter action label makes the tag row scan faster without changing meaning.

## Boundary
Discussion task only. Do not implement until explicitly approved.

[[2026-05-24T07:01:34+02:00]]
## User Approval
User approved standardizing the task detail edit form now, including shortening the tag add action per suggestion.

[[2026-05-24T07:05:56+02:00]]
Implemented concise task tag add action. The tag add button now reads Add while retaining the plus icon and compact PDS treatment. Verified focused task detail edit-form suites (183 passed, 1 skipped), ESLint, production build, and screenshot proof at .owlbear/scratch/1716-wide-cockpit/1802-1803-task-reference-edit-1024.png.
