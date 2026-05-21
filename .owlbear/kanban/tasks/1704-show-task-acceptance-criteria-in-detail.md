---
id: 1704
title: Show task acceptance criteria in detail
status: research
priority: important
created: 2026-05-21T20:23:32.985106+02:00
updated: 2026-05-21T20:23:32.985106+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - acceptance-criteria
parent:
depends_on: []
ac:
  - Verify task detail payload includes acceptance criteria when tasks have 
    them.
  - Render acceptance criteria in task detail when present.
  - Use a clear absent state when no AC exist rather than leaving the user 
    guessing.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Where are the AC of this task? Current tasks should have some, or the view may be missing them.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current information gap, pending data check.
- Value question: AC are core task context; task detail should show them when present and clearly show absence when not.
- Screenshot target: task detail for a task with AC and one without AC.

## Acceptance Criteria
- Verify whether acceptance criteria are present in the task detail API payload for current tasks.
- Render AC prominently enough for review/build work when present.
- Provide a useful empty/absent state when a task has no AC.