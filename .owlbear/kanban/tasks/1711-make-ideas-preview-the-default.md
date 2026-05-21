---
id: 1711
title: Make ideas preview the default
status: research
priority: important
created: 2026-05-21T23:23:33.745696+02:00
updated: 2026-05-21T23:23:33.745696+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - ideas
  - behavior
parent:
depends_on: []
ac:
  - Audit Ideas tab initial mode against expected review/edit workflow.
  - Set preview as the default mode if review-first is the higher-value
    behavior.
  - Preserve edit, save, conflict, and unsaved-state interactions.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
On the Ideas tab, edit is the default, but preview should be the default.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current default-mode issue.
- Value question: Ideas should open in a reading/preview mode unless the user explicitly starts editing, because most visits likely involve reviewing the notebook state.
- Impact: hurts Cockpit now by putting users directly into an editing posture.
- Screenshot target: Ideas tab initial load, preview/edit mode controls, unsaved state.

## Acceptance Criteria
- Audit Ideas tab default mode and primary workflow.
- Make preview the default if it better matches review-first usage.
- Preserve clear edit entry, save/conflict handling, and unsaved state feedback.