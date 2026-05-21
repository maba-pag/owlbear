---
id: 1702
title: Resize task detail history control
status: research
priority: important
created: 2026-05-21T20:23:09.378280+02:00
updated: 2026-05-21T20:23:09.378280+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - visual-system
parent:
depends_on: []
ac:
  - Audit task detail History control size relative to Edit/Preview and Save.
  - Adjust History visual weight to match secondary action importance.
  - Preserve discoverability and accessible interaction.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The History button in task detail is huge, especially compared to Edit/Preview and even bigger than Save.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current visual hierarchy issue.
- Value question: History is a secondary view/action and should not visually outrank Save or mode controls.
- Screenshot target: task detail header/action row with History, Edit/Preview, Save.

## Acceptance Criteria
- Audit task detail action sizing and hierarchy.
- Resize or reposition History so it matches its secondary importance.
- Preserve discoverability and keyboard accessibility.