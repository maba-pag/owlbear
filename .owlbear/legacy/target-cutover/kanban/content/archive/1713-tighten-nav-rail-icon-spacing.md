---
id: 1713
title: Tighten nav rail icon spacing
status: archived
priority: medium
created: 2026-05-21T23:23:56.241185+02:00
updated: 2026-05-24T10:50:01.413887+02:00
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
archival_reason: completed
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

## Evidence - 2026-05-22
- Classification: observed current UX issue. Desktop screenshots showed the left workspace rail consuming more horizontal chrome than the icon-only controls needed.
- Impact: hurts Cockpit now as visual polish and available work-surface width; not merely theoretical. Constraint: must preserve at least 44px interactive targets and avoid clipped notification badges.
- Audit: the rail width came from `--p-canvas-sidebar-start-width: 96px`. The visible buttons were 40px, and PDS canvas supplied 24px internal sidebar padding. A naive 72px lane clipped badges because 72px minus 48px PDS padding left only 24px content width.
- Decision: keep a tighter 72px start-sidebar lane, set the nav buttons to 44px, and extend the focused PDS canvas shadow-root override to reduce start-sidebar inline padding to 14px. Pending badges now sit inside the 44px button bounds rather than outside the rail edge.
- Browser proof: refreshed `.owlbear/scratch/1680-route-kanban-desktop.png` and `.owlbear/scratch/1680-route-kanban-mobile.png`; desktop shows the narrower rail, full circular badges, and unchanged compact top chrome. Mobile remains unchanged because the start sidebar is hidden there.
- Validation: `npx vitest run src/__tests__/Shell.test.tsx src/__tests__/NavRailButtons_1642.test.tsx src/__tests__/NavBadge_1646.test.tsx --reporter=dot` passed 3 files / 62 tests. `npm run build` passed with the existing Vite chunk-size warning. Focused Playwright rail tests passed 7 tests covering width, icon-only labels, badge geometry, collapse, tab reachability, and focus styling. `npx eslint ...` on touched nav files/tests passed. VS Code diagnostics found no errors in touched files.
