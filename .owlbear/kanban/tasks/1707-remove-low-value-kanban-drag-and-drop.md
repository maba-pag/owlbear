---
id: 1707
title: Remove low-value kanban drag and drop
status: research
priority: important
created: 2026-05-21T23:22:56.124550+02:00
updated: 2026-05-21T23:22:56.124550+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - behavior
parent:
depends_on: []
ac:
  - Audit whether Kanban drag and drop has real workflow value in Cockpit.
  - Classify the current click-hold/open conflict as observed or theoretical
    with browser evidence.
  - Remove or repair drag/drop behavior according to product value.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Kanban drag and drop is blocked by task opening: clicking and holding a task opens it instead of moving it. Since moving tasks is available by right click or task edit, drag and drop may be unnecessary rather than worth fixing.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current behavior problem.
- Value question: does drag and drop provide enough real workflow value to justify accidental task opens, gesture ambiguity, and extra implementation complexity?
- Impact: hurts Cockpit now if the gesture conflicts with opening tasks; may hurt the plan if a low-value interaction keeps adding bugs.
- Screenshot/browser target: Kanban task interaction, drag gesture, right-click/task-detail move alternatives.

## Acceptance Criteria
- Audit drag/drop value versus existing move paths.
- Decide whether to remove drag/drop or repair gesture behavior.
- If removed, preserve clear non-drag move workflows.