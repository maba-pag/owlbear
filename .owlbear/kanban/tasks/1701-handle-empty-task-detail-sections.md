---
id: 1701
title: Handle empty task detail sections
status: research
priority: important
created: 2026-05-21T20:22:56.770746+02:00
updated: 2026-05-21T20:22:56.770746+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - information-architecture
parent:
depends_on: []
ac:
  - Audit empty Actions and Metadata sections in task detail.
  - Eliminate clickable no-op affordances and misleading empty boxes.
  - Provide useful empty states or hide sections until they have value.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Task detail has an Actions box and a Metadata box that are empty. Metadata is clickable but does nothing. This may be because tasks are new, but it still feels weird.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current empty-state/affordance issue.
- Value question: empty sections should either be hidden, explain their value, or show disabled/coming context; clickable non-actions erode trust.
- Screenshot target: new task detail with empty actions/metadata; populated task if available.

## Acceptance Criteria
- Audit Actions and Metadata sections in empty and populated task states.
- Remove, collapse, or provide meaningful empty states for empty sections.
- Ensure clickable affordances have visible effects or are not interactive.