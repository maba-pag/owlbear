---
id: 1717
title: Replace nav rail icons and order
status: todo
priority: important
created: 2026-05-22T01:01:09.630391+02:00
updated: 2026-05-22T01:01:11.846050+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - navigation
  - icons
parent:
depends_on: []
ac:
  - Replace nav rail icon mapping with Kanban steering-wheel, Decisions route,
    Memory brain, Ideas user-manual when supported by PDS.
  - Reorder route navigation so Memory appears before Ideas.
  - Preserve accessible labels, active-page state, pending badges, keyboard
    order, and route URLs.
  - Validate with desktop screenshots at widths >= 1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The menu bar icons are not ideal. Suggested Porsche icon mapping: Kanban `steering-wheel`, Decisions `route`, Memory `brain`, Ideas `user-manual`. Memory should appear above Ideas instead of after it.

## Evaluation Notes
- Classification: user-observed navigation clarity issue, not theoretical.
- Impact: hurts Cockpit now because icon-only navigation depends on recognizable destination symbols and predictable ordering.

## Acceptance Criteria
- Replace nav rail icon mapping with Kanban `steering-wheel`, Decisions `route`, Memory `brain`, Ideas `user-manual` when supported by PDS.
- Reorder route navigation so Memory appears before Ideas.
- Preserve accessible labels, active-page state, pending badges, keyboard order, and route URLs.
- Validate with desktop screenshots at widths >= 1200px.