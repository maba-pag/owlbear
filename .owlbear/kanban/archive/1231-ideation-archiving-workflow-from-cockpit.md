---
id: 1231
title: Ideation — archiving workflow from cockpit
status: archived
priority: medium
created: 2026-04-30 16:31:18.665338+00:00
updated: 2026-05-01T17:00:34.989323+00:00
tags:
- cockpit
- needs-ideation
parent:
depends_on: []
blocked: true
block_reason: 'Needs UX ideation: archival prompts when moving to terminal status'
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Design and implement archival UX in the cockpit when moving tasks to terminal status.

## Context
The backend `move_task` API already supports `archival_reason` and `archival_refs` parameters. The frontend `handleTransitionClick` only sends `{status, updated}`. When moving to a terminal status (done/archived), the user should be prompted for archival metadata.

## Needs Ideation
- What triggers the archival prompt? (moving to 'done'? explicit 'archive' action?)
- What fields? (reason dropdown, refs input)
- Is archival a separate action or part of the move flow?