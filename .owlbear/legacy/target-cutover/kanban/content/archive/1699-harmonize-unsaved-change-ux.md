---
id: 1699
title: Harmonize unsaved-change UX
status: archived
priority: medium
created: 2026-05-21T20:22:33.606455+02:00
updated: 2026-05-24T10:50:01.232768+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - ideas
  - behavior
parent:
depends_on: []
ac:
  - Audit dirty-state indicators and leave guards in Ideas and task detail.
  - Define a consistent unsaved-change UX policy for Cockpit editing surfaces.
  - Implement consistent warning/indicator behavior where data loss can occur.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Task detail shows `unsaved changes` all the time but has no popup warning when leaving after changes. The note/Ideas page shows a popup but does not show unsaved changes. It does not necessarily need a popup, but the UX should be consistent.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current cross-surface consistency issue.
- Value question: unsaved-state UX should be predictable across editing surfaces: visible state, navigation guard, or both.
- Browser target: Ideas notebook edit/leave, task detail edit/close/route change.

## Acceptance Criteria
- Audit unsaved-change signaling and navigation guards in Ideas and task detail.
- Define one cockpit-wide policy for visible dirty state and leave confirmation.
- Apply consistently where data loss is possible.

## Outcome
- Audit: Ideas already had a dirty-state model, visible unsaved state, route-change confirmation, and `beforeunload` protection. Task detail had a visible `Unsaved changes` indicator once fields were edited, but closing the detail modal, switching cards, or switching workspaces could discard local edits without confirmation.
- Policy: every Cockpit editing surface that can lose local edits must show visible dirty state and require an explicit leave confirmation before abandoning dirty edits through route changes, modal dismissal, or equivalent in-app navigation. Browser/tab close should use `beforeunload` while dirty.
- Implementation: `TaskFieldsEditor` now reports dirty-state changes through `DetailTab` to `Shell`; `Shell` uses a pending-action guard for task-detail close, card switch, detail-linked task switch, nav-rail workspace switch, and browser unload. The confirmation uses the same core copy as Ideas: `You have unsaved changes. Leave anyway?`
- Screenshot follow-up: the first browser proof caught a real visual issue where stacked PDS modals left the task-detail confirmation present in the DOM but not visible. The final implementation renders the confirmation as an in-modal alert layer above the dirty task detail, with PDS buttons and the dirty form blocked behind it.

## Evidence
- Red proof: focused #1699 tests failed before implementation for missing dirty-state propagation and Shell guards around card switch, modal close, nav-rail navigation, and `beforeunload`.
- Focused green: `npx vitest run src/__tests__/Shell.callbacks.test.tsx src/__tests__/Shell.card-selection.integration.test.tsx --testNamePattern="unsaved-change guard|dirty task detail asks"` passed after the visible in-modal confirmation fix, 5 passed selected tests.
- Affected regression: `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.invalid-parent.test.tsx src/__tests__/Shell.callbacks.test.tsx src/__tests__/Shell.card-selection.integration.test.tsx src/__tests__/IdeasPage.test.tsx src/__tests__/IdeasPage_1664.test.tsx` passed, 160 passed and 1 existing skipped test.
- Quality: `npx eslint src/Shell.tsx src/components/DetailTab.tsx src/components/TaskFieldsEditor.tsx src/__tests__/DetailTab.test.tsx src/__tests__/Shell.callbacks.test.tsx src/__tests__/Shell.card-selection.integration.test.tsx` passed; `npm run build` passed with only the known Vite chunk-size warning.
- Editor diagnostics: VS Code reported no errors in the touched Shell, task-detail, editor, and test files.
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/task-detail-unsaved-1699.png` at 2560x1440 shows task #1699 with dirty edits blocked behind a visible `Leave task detail?` confirmation; browser diagnostics were empty.