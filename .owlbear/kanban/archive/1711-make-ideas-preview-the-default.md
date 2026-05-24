---
id: 1711
title: Make ideas preview the default
status: archived
priority: important
created: 2026-05-21T23:23:33.745696+02:00
updated: 2026-05-24T10:50:01.387624+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - ideas
  - behavior
parent:
depends_on: []
ac:
  - Audit Ideas tab initial mode against expected review/edit workflow.
  - Set preview as the default mode if review-first is the higher-value
    behavior.
  - Preserve edit, save, conflict, and unsaved-state interactions.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
On the Ideas tab, edit is the default, but preview should be the default.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current default-mode issue.
- Value question: Ideas should open in a reading/preview mode unless the user explicitly starts editing, because most visits likely involve reviewing the notebook state.
- Impact: hurts Cockpit now by putting users directly into an editing posture.
- Screenshot target: Ideas tab initial load, preview/edit mode controls, unsaved state.

## Acceptance Criteria
- Audit Ideas tab default mode and primary workflow.
- Make preview the default if it better matches review-first usage.
- Preserve clear edit entry, save/conflict handling, and unsaved state feedback.

## Evidence - 2026-05-22
- Classification: observed current behavior issue. The Ideas workspace opened in edit mode by default, which put users directly into an editing posture even when the likely first action is reading/reviewing the notebook.
- Impact: hurts Cockpit now by making the Ideas tab feel more like a raw editor than a reviewable workspace; not theoretical.
- Decision: default `IdeasPage` to preview mode, keep the existing compact toggle as the clear edit entry, and leave save/conflict/unsaved-state behavior intact once the user enters edit mode.
- Implementation: `previewMode` now initializes to `true`. Existing Ideas unit helpers were updated so edit/save/conflict tests explicitly enter edit mode before touching the textarea. The Ideas Playwright flow now asserts preview is visible on open, then clicks `Edit` before editing and saving.
- Screenshot proof: refreshed `.owlbear/scratch/1680-route-ideas-desktop.png` and `.owlbear/scratch/1680-route-ideas-mobile.png`; both show rendered markdown on direct `/ideas` load, `Preview` mode in the header/state panel, and an `Edit` action.
- Additional observed issue fixed: the Ideas dark-mode axe run caught the `Cockpit` header word at insufficient contrast because it used opacity. Removed the opacity from the header identity text; this hurts us now because it was an actual WCAG AA failure, not a theoretical risk.
- Validation: `npx vitest run src/__tests__/IdeasPage_1662.test.tsx src/__tests__/IdeasPage_1663.test.tsx src/__tests__/IdeasPage_1664.test.tsx src/__tests__/IdeasPage_1665.test.tsx src/__tests__/IdeasPage.test.tsx src/__tests__/Shell.test.tsx --reporter=dot` passed 6 files / 156 tests. `npm run build` passed with the existing Vite chunk-size warning. `npm run test:e2e:all -- e2e/ideas-page.spec.ts` passed 2 tests across light and dark including WCAG scans. `npx eslint ...` on touched files passed. VS Code diagnostics found no errors in touched files.
