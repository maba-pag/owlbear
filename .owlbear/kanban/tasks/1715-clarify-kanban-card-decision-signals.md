---
id: 1715
title: Clarify kanban card decision signals
status: todo
priority: important
created: 2026-05-22T00:56:33.010224+02:00
updated: 2026-05-22T00:56:35.124216+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - decisions
  - cards
parent:
depends_on: []
ac:
  - Remove the duplicate active-decision tag from the normal tag row when the
    top DR signal already exists.
  - Preserve one clear active-decision signal near the task identity/top
    metadata.
  - Verify the left card accent/border visibly changes for active decision
    requests compared with ordinary tasks, or replace it with a clearer signal.
  - Validate with desktop screenshots at widths >= 1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
On a kanban task with an active decision request, the DR signal appears twice: once near the task number and once with the tags. Only one is needed, probably the top one. The colored left border may also not be visibly implemented because tasks with DRs do not appear distinct from other tasks.

## Evaluation Notes
- Classification: user-observed current card signal issue, not theoretical.
- Impact: hurts Cockpit now by duplicating the same active-decision signal and possibly failing to visually distinguish blocked/decision-needed tasks.
- This can be handled as one card-signal task rather than separate duplicate-chip and border tasks.

## Acceptance Criteria
- Remove the duplicate active-decision tag from the normal tag row when the top DR signal already exists.
- Preserve one clear active-decision signal near the task identity/top metadata.
- Verify the left card accent/border visibly changes for active decision requests compared with ordinary tasks, or replace it with a clearer signal.
- Validate with desktop screenshots at widths >= 1200px.