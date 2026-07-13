---
id: 1787
title: Clarify task detail move and archive actions
status: archived
priority: medium
created: 2026-05-24T01:57:03.618227+02:00
updated: 2026-05-24T10:50:02.453626+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - discussion
parent: 1773
depends_on: []
ac:
  - Task detail exposes valid state movement consistently across statuses,
    including Research where appropriate.
  - Archive is discoverable from task detail and uses a safe confirmation/data
    collection flow if needed.
  - Actions are backed by engine/API capabilities rather than direct file
    writes.
  - No implementation begins until the user approves this task.
  - Task detail move targets are based on the same valid-transition model used
    by the board context menu.
  - Task detail Archive reuses the existing archival modal flow.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User noted that task detail actions are inconsistent: tasks in Done have an action to move backward, but tasks in Research have no move-forward action. Task details should also expose archive, possibly with any required additional information requested in a popup/modal.

## Current Interpretation
Workflow/interaction issue. Task detail should be a trustworthy place to advance, regress, or archive a task without needing hidden board gestures or filesystem knowledge.

## Value
Task detail is where a user reads context and decides what to do next. Missing or asymmetric transition actions slow down normal Kanban work and make task state rules harder to discover.

## Discussion Questions
- Should task detail show all valid engine transitions, only primary next/previous transitions, or a menu of status moves?
- Should Archive always be visible but require confirmation/details in a modal?
- What information is required for archive, and is that already supported by the engine/API?

## Boundary
No direct filesystem mutation is allowed. All state changes must go through the Kanban engine/API contract.

[[2026-05-24T02:59:23+02:00]]
## Decision
User chose `Move menu + Archive`, with a preference to reuse the existing board context-menu transition model where possible. Task detail should expose valid move targets through a task-detail Move menu and expose Archive through the existing archival modal flow.

## Implementation Direction To Discuss Later
- Reuse the same valid-transition source as the board context menu.
- Reuse `ArchivalModal` for archive reason/refs instead of posting archived directly.
- Avoid direct filesystem writes; all moves/archive calls stay API/engine-backed.

[[2026-05-24T04:51:24+02:00]]
## Implementation Proof
- Task detail now uses the same valid-transition model as the board context menu via shared transition helpers.
- Replaced the asymmetric `Move Backward` action with a `Move` menu listing valid engine/API transition targets for the selected task status. Research tasks now expose forward movement from task detail.
- Added a task-detail `Archive` action that opens the existing `ArchivalModal` flow; archival still posts through `/api/tasks/{id}/move` with archival reason/refs rather than direct file writes.
- Verification: focused DetailTab/Kanban archive tests passed (`121 passed, 1 skipped`); focused ESLint passed; `npm run build` passed with the known chunk-size warning.
- Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/1787-task-detail-move-menu.png` shows task #1787 with Move targets Backlog/Todo/In Progress/Review/Docs/Done plus Archive; `.owlbear/scratch/1716-wide-cockpit/1787-task-detail-archive-modal.png` shows the existing Archive task modal opened from detail.

[[2026-05-24T04:54:04+02:00]]
Completed #1787. Task detail now exposes a valid-transition Move menu and Archive action using the existing archival modal/API flow. Proof screenshots and verification are recorded in the implementation note.
