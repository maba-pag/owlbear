---
id: 1679
title: Improve nav rail icon spacing
status: research
priority: important
created: 2026-05-21T19:51:24.066039+02:00
updated: 2026-05-21T19:51:24.066039+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - nav-rail
parent:
depends_on: []
ac:
  - Audit current nav icon spacing and hit targets in desktop screenshots.
  - Tune spacing so the nav rail reads as deliberate rather than cramped.
  - Preserve badge visibility and active route clarity.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The left menu icons are too close to each other; there is no spacing.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI issue.
- Value question: how much spacing preserves compact cockpit navigation while feeling deliberate and premium?
- Screenshot target: nav rail at desktop widths with all route badges visible.

## Acceptance Criteria
- Measure current hit targets, visual gaps, badge placement, and hover/focus state.
- Adjust spacing if the dock reads as cramped or accidental.
- Preserve efficient workspace switching and badge legibility.