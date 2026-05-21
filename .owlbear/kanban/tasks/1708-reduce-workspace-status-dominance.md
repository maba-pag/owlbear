---
id: 1708
title: Reduce workspace status dominance
status: research
priority: important
created: 2026-05-21T23:23:05.244698+02:00
updated: 2026-05-21T23:23:05.244698+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - top-bar
  - status
parent:
depends_on: []
ac:
  - Audit Workspace Status visual dominance in desktop and mobile screenshots.
  - Decide whether persistent status text is needed or should collapse to a
    status light.
  - Preserve accessible status details through hover/focus/click behavior.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Top bar `Workspace OK` is optically dominant. A green/amber/red status light may be enough, with the dropdown coming from that light and hover text showing the status without requiring a click.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current visual-weight issue.
- Value question: does the top status need a full text badge at all times, or should persistent chrome be reduced to a state light with details on hover/click?
- Impact: hurts Cockpit now if status chrome competes with route content and brand/header balance.
- Screenshot target: top bar desktop and mobile with status OK/yellow/red states.

## Acceptance Criteria
- Audit the current Workspace Status top-bar value and visual weight.
- Decide text badge versus compact status light behavior.
- Preserve discoverability, tooltip/hover text, keyboard access, and dropdown details.