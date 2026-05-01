---
id: 1241
title: 'Test: ArchivalModal component'
status: todo
priority: needed
created: 2026-05-01T03:07:55.116658+00:00
updated: 2026-05-01T03:10:19.137835+00:00
tags:
- scope:frontend
parent: 1238
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Acceptance Criteria

- `ARCHIVAL_REASONS` constant is exported with order: `completed → dropped → wontfix → deprecated → duplicate`
- `ArchivalModal` renders with `role="dialog"`, `aria-modal="true"`, `aria-labelledby` pointing to the visible title element's id
- Focus is placed on the reason `<select>` dropdown when the modal opens
- `completed` option is hidden in the dropdown when `taskStatus !== "done"`; shown when `taskStatus === "done"`
- Refs `<input>` is visible when reason is `"deprecated"` or `"duplicate"`; hidden for all other reasons
- When reason changes from a refs-requiring reason to any non-refs-requiring reason, refs state clears to `""`
- Submit button is disabled when no reason is selected
- Submit button is disabled when reason requires refs and refs field is empty
- Submit button is disabled while `isSubmitting === true`
- When the refs field is visible, a hint text is displayed below it: "Required — enter at least one task ID"
- Non-numeric token in the refs field produces a client-side inline error; no HTTP request is fired
- On 422 response: modal stays open; `error.detail` is displayed verbatim
- On 409 response: modal stays open; a modal-local stale-snapshot error message is shown
- On success: modal closes and board refresh is triggered
- Tab and Shift+Tab cycle within the modal only (focus trap active)
- Escape key closes the modal without firing a move request

## In Scope

- `ArchivalModal` component unit and interaction tests
- `ARCHIVAL_REASONS` constant assertion

## Out of Scope

- `handleTransitionClick` integration (F3 task #1242)
- Backend validation (B3 task #1240)

## Brief reference

Brief: `.owlbear/briefs/draft-archival-ux/brief.md` — Frontend Changes F1, F2