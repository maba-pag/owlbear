---
id: 1192
title: 'P3-04: Implement DR status indicator + popover'
status: research
priority: needed
created: 2026-04-30T00:52:21.318056+00:00
updated: 2026-04-30T00:53:58.143949+00:00
tags:
- phase-3
- scope:cockpit-fe
- type:impl
parent: 1179
depends_on:
- 1190
- 1191
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- DR StatusBarIndicator component renders in Shell status bar (alongside HealthBadge)
- Shows count of pending DRs from polling hook
- Attention color when count > 0, dormant/neutral when 0
- Click opens DRPopover list component
- Popover shows: title, agent, task_id, age for each pending DR
- Popover item click opens resolve modal (or emits event for modal)
- Polling hook uses same pattern as existing useBoard.ts
- All tests from #1191 pass

## Scope

- IN: StatusBarIndicator + DRPopover components + usePendingDRs hook
- OUT: resolve modal (handled by #1194)

Brief: see parent #1179
