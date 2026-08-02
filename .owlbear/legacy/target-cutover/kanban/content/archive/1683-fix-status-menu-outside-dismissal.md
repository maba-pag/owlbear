---
id: 1683
title: Fix status menu outside dismissal
status: archived
priority: medium
created: 2026-05-21T19:52:00.709405+02:00
updated: 2026-05-24T10:50:01.027118+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - status-bar
  - behavior
parent:
depends_on: []
ac:
  - Reproduce Health and Decision menu dismissal behavior in browser.
  - Menus close on outside click and when another status menu opens, unless a
    modal interaction is active.
  - Keyboard dismissal and focus return remain clear.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Workspace health and decision dropdown menus do not close when clicking somewhere else or on the other one; they have to be closed by clicking the opener again.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current interaction defect.
- Value question: status menus should behave like mature overlays: outside click, Escape, and switching triggers should close the previous menu unless a modal interaction is active.
- Browser target: open Health, click elsewhere; open DR while Health is open; Escape behavior; focus return.

## Acceptance Criteria
- Reproduce current dismissal behavior for Health and Decision menus.
- Implement standard outside-click / alternate-trigger dismissal if confirmed.
- Preserve keyboard accessibility and focus management.

## Implementation Evidence
- Classification: observed interaction defect, not theoretical.
- Impact: hurt current use now. Header overlays stayed open until the opener was clicked again, which made the cockpit feel unfinished.
- Decision: Workspace Status now closes on outside click and Escape. The retired global decision popover no longer competes for header overlay state.
- Evidence: `overlay-behavior.spec.ts` covers outside click, Escape, modal interactions, and status care dialogs. Mobile screenshots also caught and verified the portaled popover geometry.
- Verification: `npm run test:e2e:all -- e2e/overlay-behavior.spec.ts --reporter=line`; `npm run test:e2e:all -- e2e/focus-visible-pds-1626.spec.ts --reporter=line`.