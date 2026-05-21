---
id: 1713
title: Tighten nav rail icon spacing
status: research
priority: important
created: 2026-05-21T23:23:56.241185+02:00
updated: 2026-05-21T23:23:56.241185+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - nav-rail
  - visual-system
parent:
depends_on: []
ac:
  - Audit left nav rail horizontal spacing in screenshots.
  - Tighten icon rail whitespace while preserving accessible hit targets.
  - Validate active route, badges, focus, and collapse behavior.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The nav bar on the left has a little too much white space left and right of the icons; this can maybe be reduced.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically. Related to existing nav rail spacing feedback, but scoped to the observed horizontal padding/width.

## Evaluation Notes
- Classification: user-observed current nav rail spacing issue.
- Value question: nav icons need comfortable targets, but excess rail width wastes canvas and looks less refined.
- Impact: hurts Cockpit now as top-level chrome polish; must not reduce touch/click target below accessible size.
- Screenshot target: nav rail expanded/collapsed, desktop and mobile.

## Acceptance Criteria
- Audit nav rail horizontal padding against icon size and target size.
- Reduce visual whitespace if targets remain accessible.
- Preserve focus, active route, notification badge, and collapse behavior.