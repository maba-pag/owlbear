---
id: 1787
title: Clarify task detail move and archive actions
status: research
priority: important
created: 2026-05-24T01:57:03.618227+02:00
updated: 2026-05-24T02:59:23.361606+02:00
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
blocked: false
block_reason:
claimed_at:
archival_reason:
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
