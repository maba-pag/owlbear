---
id: 1718
title: Default cockpit lists to useful sorting
status: todo
priority: important
created: 2026-05-22T01:01:18.310876+02:00
updated: 2026-05-22T01:01:20.667266+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - sorting
  - kanban
  - decisions
  - memory
parent:
depends_on: []
ac:
  - Sort Kanban tasks within columns by priority descending, then updated
    timestamp descending, unless a user-selected sort overrides it.
  - Sort pending Decisions oldest first by created timestamp.
  - Sort Memory entries by confidence descending by default.
  - Add focused tests proving the default order for each route with ties and
    malformed/missing values handled predictably.
  - Validate with desktop screenshots at widths >= 1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Default route ordering should match how the cockpit is used: Kanban tasks could sort by priority first, highest first, then last edit newest first; Decisions should sort oldest first by creation date; Memories should sort by highest confidence.

## Evaluation Notes
- Classification: user-observed workflow-ordering request, not theoretical.
- Impact: hurts Cockpit now if the first visible items are not the most actionable or trustworthy for each tab.
- Decisions oldest-first is also tracked on #1710 because it belongs to the current Decisions IA pass.

## Acceptance Criteria
- Sort Kanban tasks within columns by priority descending, then updated timestamp descending, unless a user-selected sort overrides it.
- Sort pending Decisions oldest first by created timestamp.
- Sort Memory entries by confidence descending by default.
- Add focused tests proving the default order for each route with ties and malformed/missing values handled predictably.
- Validate with desktop screenshots at widths >= 1200px.