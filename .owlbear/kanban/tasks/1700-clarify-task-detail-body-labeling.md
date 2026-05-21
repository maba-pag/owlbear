---
id: 1700
title: Clarify task detail body labeling
status: research
priority: important
created: 2026-05-21T20:22:45.699635+02:00
updated: 2026-05-21T20:22:45.699635+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - copy
parent:
depends_on: []
ac:
  - Audit `Brief` and `Body` labels in task detail preview/edit modes.
  - Choose consistent wording that matches the actual task content.
  - Remove or align labels so mode changes do not introduce contradictory copy.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Why does task detail say `Brief` above the task body? In edit mode a text `Body` suddenly appears below it.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current copy/labeling confusion.
- Value question: labels should match the underlying task artifact and user mental model; preview/edit labels should not contradict each other.
- Screenshot target: task detail body preview and edit mode.

## Acceptance Criteria
- Audit task body labels in preview and edit modes.
- Choose consistent wording for task body/brief content.
- Remove duplicate or contradictory labels across mode switches.