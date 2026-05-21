---
id: 1698
title: Fix task detail field label layout loss
status: research
priority: important
created: 2026-05-21T20:22:11.464140+02:00
updated: 2026-05-21T20:22:11.464140+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - behavior
parent:
depends_on: []
ac:
  - Reproduce task detail label disappearance after priority and mode changes.
  - Fix label/control stability and alignment across edit interactions.
  - Use browser evidence to confirm labels remain visible and aligned.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
When changing priority, text labels disappear and alignment gets messed up: `Title`, `Depends on`, and `Parent` vanish immediately. Same when switching preview/edit; the priority text field also disappears.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current behavior/layout defect.
- Value question: edit controls must keep stable labels and alignment, especially when a user is changing task metadata.
- Browser target: task detail priority change, preview/edit toggle, dependency/parent fields.

## Acceptance Criteria
- Reproduce label disappearance and alignment shift in task detail.
- Fix field label stability across priority changes and mode switches.
- Verify no text/control overlap or vanishing labels in light/dark if applicable.