---
id: 1194
title: 'P3-06: Implement resolve modal'
status: research
priority: important
created: 2026-04-30T00:52:29.646843+00:00
updated: 2026-04-30T00:54:03.916600+00:00
tags:
- phase-3
- scope:cockpit-fe
- type:impl
parent: 1179
depends_on:
- 1192
- 1193
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- ResolveModal component shows full DR body rendered as markdown
- Response selector with 3 options: approved, rejected, needs-info
- Optional notes textarea for user markdown input
- Submit button calls `POST /api/decisions/{id}/resolve` with payload
- Modal closes on successful submission, refreshes pending list
- Error state displayed on failed submission
- Cancel/close dismisses without side effects
- Follows existing modal/dialog patterns in the Cockpit codebase
- All tests from #1193 pass

## Scope

- IN: ResolveModal component + integration with DRPopover item click
- OUT: status indicator (done in #1192), backend endpoints

Brief: see parent #1179
