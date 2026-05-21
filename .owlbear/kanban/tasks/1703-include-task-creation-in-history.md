---
id: 1703
title: Include task creation in history
status: research
priority: important
created: 2026-05-21T20:23:20.827522+02:00
updated: 2026-05-21T20:23:20.827522+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - history
parent:
depends_on: []
ac:
  - Verify availability of task creation timestamp in task detail data.
  - Show task creation in History when available.
  - Use consistent readable timestamp formatting for history events.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Task detail History misses the creation event. It should have a usable timestamp that can be used there, shouldn't it?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current history completeness gap.
- Value question: creation is foundational audit context and should be visible if the backend/task model provides `created`.
- Screenshot target: task detail History with task created timestamp and subsequent events.

## Acceptance Criteria
- Confirm whether task creation timestamp is available in the task detail payload.
- Add creation as the first history event when available.
- Format timestamp consistently and usefully for cockpit review.