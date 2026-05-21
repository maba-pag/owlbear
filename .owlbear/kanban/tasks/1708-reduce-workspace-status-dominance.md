---
id: 1708
title: Reduce workspace status dominance
status: todo
priority: important
created: 2026-05-21T23:23:05.244698+02:00
updated: 2026-05-22T00:56:07.627385+02:00
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
  - Evaluate removing the visible circular bubble around the healthy status
    light while preserving a 44px keyboard/touch target.
  - Verify the workspace status light visibly changes across green, yellow, and
    red states.
  - Validate the final status control with desktop screenshots at widths >=
    1200px.
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

[[2026-05-21T23:58:38+02:00]]
## Builder Evidence
- Classification: observed current visual-weight issue, not theoretical. Screenshots showed persistent `Workspace OK` text competing with the route header and Porsche/title balance, especially on mobile where top chrome is scarce.
- Impact: hurt Cockpit now by giving utility status equal visual weight to primary workspace content; hurt the plan for a quiet operational cockpit because the global status control dominated when healthy.
- Decision: collapse healthy/persistent workspace status to a compact traffic-light trigger. Keep detailed text available through `aria-label`, `title`, keyboard focus, click, and the existing Workspace Status popover.
- Implementation: HealthBadge trigger is now a 32px circular status light with no persistent text; scan errors remain available via an accessible `scan-error` status and retry action; popover details and care actions are unchanged.
- Screenshot evidence: `.owlbear/scratch/1680-route-kanban-desktop.png` and `.owlbear/scratch/1680-route-kanban-mobile.png` show the compact top-right status light.
- Validation: focused Vitest passed (6 files, 97 tests); `npm run build` passed with existing Vite chunk-size warning; E2E passed for board view + workspace status popover accessibility, HealthBadge popover no-reflow, and status-bar control names (4 tests); eslint and diagnostics passed.


## Reopened User Feedback - 2026-05-22
- The status light still has a surrounding bubble; without the bubble it may be cleaner.
- Verify whether the light actually changes color across green/yellow/red health states; the current experience has not made that visible.
- Classification: user-observed delivered-work gap plus behavior-verification question.
- Impact: hurts Cockpit now if persistent status chrome remains visually heavier than needed or if state color is not visibly truthful.
