---
id: 1245
title: 'Implement: ArchivalModal component and ARCHIVAL_REASONS constant'
status: todo
priority: needed
created: 2026-05-01T03:08:07.623554+00:00
updated: 2026-05-01T03:11:06.817331+00:00
tags:
- scope:frontend
parent: 1238
depends_on:
- 1241
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `ARCHIVAL_REASONS` constant defined with order: `completed → dropped → wontfix → deprecated → duplicate`
- `ArchivalModal` component created at `components/ArchivalModal.tsx`
- All state, rendering, a11y, submission, and error-handling behaviours specified in brief F2 are implemented:
  - `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to visible title
  - Focus on reason dropdown at open; focus trap for Tab/Shift+Tab; Escape closes without move
  - `completed` option hidden when `taskStatus !== "done"`
  - Refs field visible only for `deprecated` and `duplicate`; refs state cleared on reason change
  - Submit disabled when no reason, when refs required and empty, or when `isSubmitting`
  - Client-side NaN guard before firing POST; inline error shown on validation failure
  - 422: stays open, renders `error.detail` verbatim; 409: stays open, stale error; success: close and refresh
- All tests from #1241 pass

## In Scope

- `components/ArchivalModal.tsx` (new file)
- `ARCHIVAL_REASONS` constant (in `KanbanBoard.tsx` or a shared constants file)

## Out of Scope

- `handleTransitionClick` intercept (F3 task #1246)
- Backend changes

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F1, F2