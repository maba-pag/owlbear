---
id: 1707
title: Remove low-value kanban drag and drop
status: done
priority: important
created: 2026-05-21T23:22:56.124550+02:00
updated: 2026-05-21T23:41:36.515240+02:00
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

[[2026-05-21T23:41:36+02:00]]
## Builder Evidence
- Classification: observed current behavior problem, not theoretical. User observed click-hold/open conflict; implementation confirmed cards had `draggable={true}`, card drag state, column drop targets, and board drag-source move handling.
- Impact: hurt Cockpit now by making the primary task-open gesture ambiguous; hurt the plan because a low-value gesture carried extra state, error, filter-cancel, toast, and drop-target test surface while explicit move workflows already existed.
- Decision: remove Kanban drag/drop rather than repair it. Preserve explicit move paths through the task context menu and detail actions.
- Implementation: removed board drag-source state and drop handler; removed column drag/drop target props/state/classes; changed cards to non-draggable clickable/context-menu buttons; retargeted tests from drag success to no-drag plus context-menu move preservation.
- Browser evidence: Chromium proof verified card `draggable === false`, `data-dragging` absent, synthetic drag/drop produced no `/api/tasks/{id}/move` request and no `data-drag-over`, while context-menu `Move to Todo` still POSTed `{status: 'todo', updated}`.
- Screenshot evidence: refreshed `.owlbear/scratch/1680-route-kanban-desktop.png` and `.owlbear/scratch/1680-route-kanban-mobile.png`; visible board composition unchanged, which is desired for this behavioral removal.
- Validation: focused Vitest passed (8 files, 59 tests); `npm run build` passed with existing Vite chunk-size warning; board-view accessibility E2E passed (1 test); `npx eslint` on touched files passed.
