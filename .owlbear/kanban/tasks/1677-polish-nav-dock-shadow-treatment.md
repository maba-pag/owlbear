---
id: 1677
title: Polish nav dock shadow treatment
status: research
priority: important
created: 2026-05-21T19:51:06.666942+02:00
updated: 2026-05-21T19:51:06.666942+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - nav-rail
parent:
depends_on: []
ac:
  - Assess current nav dock shadow with realistic desktop screenshots.
  - Remove or tune any halo/clipped-shadow effect that weakens the premium 
    cockpit feel.
  - Record observed-vs-theoretical classification and visual evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The left menu icon group has a weird shadow around the group, especially around the topmost and bottommost icons.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI issue.
- Value question: does the dock container help orientation enough to justify any visible shadow, or should it become quieter/flatter?
- Screenshot target: desktop Cockpit with the left nav rail visible, light and dark if relevant.

## Acceptance Criteria
- Assess whether the current nav dock shadow hurts the intended premium cockpit feel.
- If changed, top and bottom icons should not look haloed, clipped, or visually heavier than middle icons.
- Document before/after screenshot evidence and rationale.