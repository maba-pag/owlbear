---
id: 1680
title: Unify workspace route headers
status: research
priority: important
created: 2026-05-21T19:51:31.249907+02:00
updated: 2026-05-21T19:51:31.249907+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - route-chrome
parent:
depends_on: []
ac:
  - Compare route headers across Kanban, Decisions, Ideas, and Memory using 
    screenshots.
  - Define a shared route-header pattern, using Kanban as the preferred visual 
    reference.
  - Apply or document route-specific exceptions based on product value.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
When switching between pages with the left menu, pages look very different. Headlines have different sizes and positions, and headline-row icons use very different styles. The Kanban header look is preferred.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current product cohesion issue.
- Value question: what is the shared Cockpit route-header system, and which route-specific signals deserve exceptions?
- Screenshot target: Kanban, Decisions, Ideas, Memory at the same viewport, side-by-side comparison.

## Acceptance Criteria
- Define a shared route-header pattern using the Kanban header as the visual reference.
- Align title scale, position, icon style, and status affordances across main routes where appropriate.
- Explicitly document any route-specific exception and why it helps the intended tab functionality.