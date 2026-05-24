---
id: 1682
title: Rationalize health and care menus
status: archived
priority: important
created: 2026-05-21T19:51:50.706576+02:00
updated: 2026-05-24T10:50:01.014830+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - status-bar
  - maintenance
parent:
depends_on: []
ac:
  - Audit Health and Care menu naming, overlay pattern, empty states, and clear
    actions.
  - Classify whether similarity is current confusion or acceptable domain
    separation.
  - Recommend a unified or clearly separated menu model.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Workspace Health and Workspace Care sound very similar but use different pop-in menu types. The side pop-in feels empty or like the wrong choice, maybe because it has no errors. Both have `clear` text in the corner; unclear what that means, especially in Workspace Care where there may never be an item.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current information-architecture and menu-pattern issue.
- Value question: are Health and Care separate concepts, or should they be one status/maintenance surface with clearer labels?
- Screenshot target: Health menu normal state, Care menu normal state, any problem state fixtures.

## Acceptance Criteria
- Compare naming, trigger copy, empty states, clear actions, and overlay type for Health vs Care.
- Decide whether the two concepts should merge, be renamed, or keep distinct responsibilities.
- Empty states should explain value without feeling like blank furniture.

## Implementation Evidence
- Classification: observed current information-architecture issue, not theoretical.
- Impact: hurt the current cockpit now. Health and Care were adjacent global concepts with different overlay patterns and unclear clear actions.
- Decision: merge the useful behavior into one Workspace Status popover. Scan findings, Repair, and Cleanup now live in one header surface.
- Evidence: desktop/mobile popover screenshots in `.owlbear/scratch/1672-status-route-owned-desktop-popover.png` and `.owlbear/scratch/1672-status-route-owned-mobile-popover.png`; axe sweeps cover Workspace Status and its care-action dialogs.
- Verification: `npm run test:e2e:all -- e2e/accessibility-sweep.spec.ts --reporter=line`; `npm run test:e2e:all -- e2e/accessibility-dual-theme.spec.ts --reporter=line`.