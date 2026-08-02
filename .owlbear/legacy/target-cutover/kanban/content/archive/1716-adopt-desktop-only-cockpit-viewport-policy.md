---
id: 1716
title: Adopt desktop-only Cockpit viewport policy
status: archived
priority: medium
created: 2026-05-22T00:56:41.749806+02:00
updated: 2026-05-24T10:50:01.455536+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - screenshots
  - testing
parent:
depends_on: []
ac:
  - Update Cockpit visual-audit and screenshot helpers used for polish work to
    capture desktop widths >= 1200px only.
  - Revisit Playwright coverage that exists solely for mobile/narrow route
    screenshots and either retarget it to desktop or document why it remains as
    legacy regression coverage.
  - Prefer at least one wide-desktop screenshot near 2560px for major layout
    decisions when practical.
  - Update task evidence language to avoid claiming mobile screenshots as
    product proof for new Cockpit polish tasks.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Cockpit only develops for desktop. Test and screenshot resolution width should be no less than 1200px; the user's display is 2560px.

## Evaluation Notes
- Classification: user-stated product/platform constraint, not theoretical.
- Impact: hurts the plan if polish work optimizes mobile/narrow layouts or uses mobile screenshots as proof for a desktop-only cockpit.

## Acceptance Criteria
- Update Cockpit visual-audit and screenshot helpers used for polish work to capture desktop widths >= 1200px only.
- Revisit Playwright coverage that exists solely for mobile/narrow route screenshots and either retarget it to desktop or document why it remains as legacy regression coverage.
- Prefer at least one wide-desktop screenshot near 2560px for major layout decisions when practical.
- Update task evidence language to avoid claiming mobile screenshots as product proof for new Cockpit polish tasks.

## Completion Evidence
- Active Cockpit viewport proof now targets desktop widths only. The responsive contract suite exercises 1280x800, 1440x900, and 2560x1440; shell layout, accessibility sweep, dual-theme light proof, overlay behavior, and column-body accessibility specs use >=1280px viewports.
- Former narrow/mobile route language in active Playwright coverage was retargeted to the desktop product contract: the 1280px minimum is treated as supported desktop, while the 2560x1440 pass is the wide-layout proof target for major cockpit decisions.
- Current screenshot evidence for polish work is desktop-only: `.owlbear/scratch/1716-wide-cockpit/` contains wide Cockpit captures, including 2560px route shots and the #1687 Kanban filter proof at `.owlbear/scratch/1716-wide-cockpit/kanban-filters-1687.png`.
- Legacy narrow/mobile scratch artifacts are not product proof for new Cockpit polish tasks. They may remain as historical debugging artifacts, but task evidence for new cockpit polish should cite desktop screenshots >=1200px.
- Observed separate issue: the dual-theme dark accessibility scan still exposes header identity contrast over the PCanvas header surface. PDS dark color-scheme bridge coverage passes, so this is not a viewport-policy blocker; it belongs with the reopened #1712 theme/top-bar discussion before implementation changes.

## Verification
- `npm run test:e2e:all -- e2e/responsive-contract.spec.ts e2e/shell-layout-1606.spec.ts e2e/accessibility-sweep.spec.ts e2e/column-body-a11y.spec.ts --reporter=json > /Users/markus/Projects/owlbear-dev/.owlbear/scratch/1716-e2e-desktop-policy-subset.json` -> 33 expected, 0 unexpected.
- `npm run test:e2e:all -- e2e/accessibility-dual-theme.spec.ts --grep "light theme" --reporter=json > /Users/markus/Projects/owlbear-dev/.owlbear/scratch/1716-dual-theme-light.json` -> 13 expected, 0 unexpected.
- `npm run test:e2e:all -- e2e/pds-scheme-dark.spec.ts --reporter=json > /Users/markus/Projects/owlbear-dev/.owlbear/scratch/1716-pds-scheme-dark.json` -> 2 expected, 0 unexpected.
- `npx eslint e2e/responsive-contract.spec.ts e2e/shell-layout-1606.spec.ts e2e/accessibility-dual-theme.spec.ts e2e/accessibility-sweep.spec.ts e2e/column-body-a11y.spec.ts e2e/overlay-behavior.spec.ts` -> passed.