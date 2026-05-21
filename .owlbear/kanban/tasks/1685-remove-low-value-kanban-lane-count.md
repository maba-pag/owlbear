---
id: 1685
title: Remove low-value kanban lane count
status: research
priority: important
created: 2026-05-21T19:52:20.507771+02:00
updated: 2026-05-21T19:52:20.507771+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
parent:
depends_on: []
ac:
  - Audit the current board header summary signals and their user value.
  - Remove or replace the lane count if it is non-actionable noise.
  - Use screenshot evidence to compare the header before and after.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
On the Kanban board, `7 lanes` is shown as info, but it is not clear what signal makes it worth the space. It reads as non-information.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI noise.
- Value question: should the board header show lane count, task count, active filters, blocked count, or nothing unless there is actionable status?
- Screenshot target: Kanban header with realistic board data and no tasks.

## Acceptance Criteria
- Determine why lane count was added and whether it informs user action.
- Remove, replace, or demote lane count if it is non-actionable.
- Preserve genuinely useful board status signals.