---
id: 1687
title: Verify kanban filter behavior
status: research
priority: important
created: 2026-05-21T19:52:36.134394+02:00
updated: 2026-05-21T19:52:36.134394+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - filters
  - behavior
parent:
depends_on: []
ac:
  - Reproduce Kanban filter behavior with realistic task data.
  - Classify any failures as observed current defects or not reproduced.
  - Fix confirmed filter failures or simplify low-value filter controls.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Kanban filters may not actually work; user vaguely remembers they did not.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-suspected behavior defect; requires reproduction before treating as confirmed.
- Value question: filters are only worth their UI weight if they reliably narrow the board and clearly indicate active constraints.
- Browser target: priority/tag/blocked/search/status filters with realistic tasks.

## Acceptance Criteria
- Reproduce filter behavior using realistic board data and screenshots.
- Confirm whether each filter changes visible cards and header/filter counts as expected.
- Fix real failures; remove or simplify filters that do not provide reliable value.