---
id: 1682
title: Rationalize health and care menus
status: research
priority: important
created: 2026-05-21T19:51:50.706576+02:00
updated: 2026-05-21T19:51:50.706576+02:00
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
archival_reason:
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