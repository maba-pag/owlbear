---
id: 1697
title: Clarify task detail edit/display split
status: research
priority: important
created: 2026-05-21T20:21:57.574554+02:00
updated: 2026-05-21T20:21:57.574554+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - information-architecture
parent:
depends_on: []
ac:
  - Audit task detail duplicate summary and editable fields.
  - Ensure dropdown/edit controls are not presented as passive read-only 
    content.
  - Simplify or rename the Details section based on actual value.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Task detail top box is perfect: task number, task name, priority, status. But below it is another box with the same info in editable fields under the title `Details`; it feels redundant. If not in edit mode, why is priority a dropdown?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current information-architecture/control-mode issue.
- Value question: display mode should read as a polished detail page; edit controls should appear only when editing or clearly be inline-edit affordances.
- Screenshot target: task detail modal in preview/display mode and edit mode.

## Acceptance Criteria
- Audit duplicate title/priority/status presentation in task detail.
- Separate read-only display from edit controls or make inline editing intentionally clear.
- Remove redundant `Details` heading if it adds no meaning.