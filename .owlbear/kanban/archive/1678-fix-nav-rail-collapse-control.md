---
id: 1678
title: Fix nav rail collapse control
status: archived
priority: medium
created: 2026-05-21T19:51:15.660250+02:00
updated: 2026-05-24T10:50:00.967528+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - nav-rail
  - behavior
parent:
depends_on: []
ac:
  - Reproduce the left menu collapse button behavior in browser.
  - Clarify whether manual nav collapse is intended for the cockpit shell.
  - Fix the control or remove the misleading affordance based on product value.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
The menu on the left does not collapse when pushing the button.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current behavior defect.
- Value question: should the left workspace rail be manually collapsible on desktop, only PCanvas-controlled, or always visible as app navigation?
- Screenshot/browser target: click the collapse/open control and observe nav rail state, keyboard/focus state, and available workspace switching.

## Acceptance Criteria
- Reproduce the collapse button behavior from the user's path.
- Decide whether collapse is intended or the control should be removed/changed.
- If collapse remains, clicking it visibly changes the nav state and stays accessible.

[[2026-05-21T20:02:55+02:00]]
## Implementation Evidence
- Classification: confirmed behavior defect in code. Desktop nav visibility was computed as `isDesktopNavViewport || isSidebarStartOpen`, so a PCanvas sidebar-close event could not hide the rail on desktop.
- Change: made `isSidebarStartOpen` the source of truth for `isNavRailOpen`, while viewport changes still initialize/reset the PCanvas state for desktop vs compact layouts.
- Regression: added a Playwright guard dispatching `sidebarStartUpdate` with `{ open: false }`; the nav becomes invisible, `aria-hidden="true"`, and its buttons receive `tabindex="-1"`.
- Verification: `npm run test:e2e:all -- e2e/shell-layout-1606.spec.ts --grep "start sidebar" --reporter=line` passed 2 tests.

## Verification Evidence
- Browser reproduction on the actual visible PDS control found the rendered `p-button` text `Close navigation sidebar`; clicking it changed the nav rail from visible/`tabindex="0"` to invisible, `aria-hidden="true"`, and `tabindex="-1"` on the Kanban workspace button.
- Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/nav-collapse-before-1678.png` and `.owlbear/scratch/1716-wide-cockpit/nav-collapse-after-1678.png` at 2560x1440 desktop width.
- Browser diagnostics from the reproduction reported 0 console errors, 0 page errors, 0 request failures, and 0 response errors.
- Regression rerun: `npx playwright test e2e/shell-layout-1606.spec.ts --grep "start sidebar" --project=chromium --reporter=line` passed 2 tests.
