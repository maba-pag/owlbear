---
id: 1699
title: Harmonize unsaved-change UX
status: research
priority: important
created: 2026-05-21T20:22:33.606455+02:00
updated: 2026-05-21T20:22:33.606455+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - ideas
  - behavior
parent:
depends_on: []
ac:
  - Audit dirty-state indicators and leave guards in Ideas and task detail.
  - Define a consistent unsaved-change UX policy for Cockpit editing surfaces.
  - Implement consistent warning/indicator behavior where data loss can occur.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Task detail shows `unsaved changes` all the time but has no popup warning when leaving after changes. The note/Ideas page shows a popup but does not show unsaved changes. It does not necessarily need a popup, but the UX should be consistent.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current cross-surface consistency issue.
- Value question: unsaved-state UX should be predictable across editing surfaces: visible state, navigation guard, or both.
- Browser target: Ideas notebook edit/leave, task detail edit/close/route change.

## Acceptance Criteria
- Audit unsaved-change signaling and navigation guards in Ideas and task detail.
- Define one cockpit-wide policy for visible dirty state and leave confirmation.
- Apply consistently where data loss is possible.