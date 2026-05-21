---
id: 1705
title: Clarify priority color semantics
status: research
priority: important
created: 2026-05-21T20:23:43.490277+02:00
updated: 2026-05-21T20:23:43.490277+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - visual-system
parent:
depends_on: []
ac:
  - Audit current priority color mapping and token usage.
  - Classify whether blue `important` communicates the intended priority 
    meaning.
  - Align priority color semantics across Cockpit surfaces.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Why is the `important` priority bubble blue?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current color-semantic confusion.
- Value question: priority color should have an intentional scale or be neutral; blue may imply selected/info rather than importance.
- Screenshot target: priority chips in card and detail surfaces across priority values.

## Acceptance Criteria
- Audit current priority color mapping and what blue means in the cockpit token system.
- Decide whether priority should use neutral, severity scale, or no chip color.
- Align priority color semantics across card and detail surfaces.