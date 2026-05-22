---
id: 1719
title: Make task detail tags editable
status: done
priority: important
created: 2026-05-22T11:21:58.328069+02:00
updated: 2026-05-22T12:00:38+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - tags
parent:
depends_on: []
ac:
  - Audit task detail tag display/edit flow and backend edit contract.
  - Use an editable tag treatment in task detail edit mode, preferring Porsche
    Design System v4 components where they fit.
  - Allow existing tags to be removed from the task detail edit surface.
  - Provide a clear field/control to add new tags without making the detail
    panel visually noisy.
  - Preserve readable tag display in non-edit/read-only contexts if present.
  - Validate the task detail tag edit flow with desktop screenshots at widths >=
    1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
In the Kanban task detail view, tags are shown with `p-tag` even though the panel is edit mode. Should this use `p-tag-dismissible` instead, and should there be a field to add new tags?

## Framing
Use this as a product/audit todo item for Cockpit usability, not as a pipeline handoff. Task detail is the intended place to inspect and edit task metadata, so tags should not look read-only if they are meant to be editable.

## Evaluation Notes
- Classification: user-observed functionality/affordance gap, not theoretical.
- Value question: task detail should make tag metadata editable where that is part of the task edit contract; if tags are intentionally read-only, the UI needs to communicate why.
- Impact: hurts Cockpit now if users cannot remove/add tags from the main task editing surface or if editable metadata is presented as static chrome.
- Screenshot target: task detail modal metadata/tag area before and after entering/editing tags.

## Final Evidence - 2026-05-22
- Classification: observed functionality/affordance gap, not theoretical. The detail editor displayed task tags as static `p-tag` chips even though the backend edit contract already supports full tag replacement.
- Impact: hurt Cockpit now because task detail is the main editing surface and tag metadata looked read-only, preventing normal remove/add work from the modal.
- Audit: frontend `EditRequest` and backend `POST /api/tasks/{id}/edit` already allow `tags: string[]`; backend tests cover full replacement and clearing. The missing piece was `TaskFieldsEditor` state/payload wiring.
- Implementation: replaced edit-mode static `PTag` chips with compact `PTagDismissible`, added a compact `Add tag` field plus PDS button, validates duplicate/blank/space/comma tags, includes edited `tags` in the normal save payload, and carries tags through conflict draft and force-save paths.
- Browser proof: temporary Playwright flow opened a 1440px task detail modal, confirmed `p-tag-dismissible` chips, removed `bug`, added `scope:cockpit`, saw the dirty state, saved, and asserted the edit payload was `tags: ['frontend', 'scope:cockpit']`.
- Screenshot review: captured before/after 1440px modal screenshots. Review confirmed tags look editable without crowding the details panel; after editing, the remaining and added tags appear as dismissible chips and the add field stays available.
- Validation: `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.edit-payload.test.tsx src/__tests__/DetailTab.conflict-resolution.test.tsx src/__tests__/tasks.test.ts --reporter=dot` passed 4 files / 170 tests with 1 skipped. Temporary Playwright tag-edit flow passed 1 test. ESLint on touched frontend files passed. `npm run build` passed with the existing Vite chunk-size warning. VS Code diagnostics found no errors in touched files.
