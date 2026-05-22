---
id: 1715
title: Clarify kanban card decision signals
status: done
priority: important
created: 2026-05-22T00:56:33.010224+02:00
updated: 2026-05-22T13:59:22+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - decisions
  - cards
parent:
depends_on: []
ac:
  - Remove the duplicate active-decision tag from the normal tag row when the
    top DR signal already exists.
  - Preserve one clear active-decision signal near the task identity/top
    metadata.
  - Verify the left card accent/border visibly changes for active decision
    requests compared with ordinary tasks, or replace it with a clearer signal.
  - Validate with desktop screenshots at widths >= 1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
On a kanban task with an active decision request, the DR signal appears twice: once near the task number and once with the tags. Only one is needed, probably the top one. The colored left border may also not be visibly implemented because tasks with DRs do not appear distinct from other tasks.

## Evaluation Notes
- Classification: user-observed current card signal issue, not theoretical.
- Impact: hurts Cockpit now by duplicating the same active-decision signal and possibly failing to visually distinguish blocked/decision-needed tasks.
- This can be handled as one card-signal task rather than separate duplicate-chip and border tasks.

## Acceptance Criteria
- Remove the duplicate active-decision tag from the normal tag row when the top DR signal already exists.
- Preserve one clear active-decision signal near the task identity/top metadata.
- Verify the left card accent/border visibly changes for active decision requests compared with ordinary tasks, or replace it with a clearer signal.
- Validate with desktop screenshots at widths >= 1200px.

[[2026-05-22T13:59:22+02:00]]
## Builder Evidence
- Classification: observed card-signal duplication and scannability issue, handled alongside the card metadata declutter.
- Implementation: filters the redundant `active-decision` normal tag only when `computeSignal()` resolves the card to `dr-pending`; useful ordinary tags remain visible. The top `Decision` signal remains near the task ID and uses the existing warning left rail.
- Duplicate cue cleanup: secondary cue text for the same primary signal is suppressed, while lower-priority simultaneous states can still appear as secondary text when they add new information.
- Screenshot evidence: `.owlbear/scratch/1716-wide-cockpit/dr-pending-fixture-viewport.png` at 1440x900 shows a pending-decision card with the top `Decision` signal, no `active-decision` tag in the normal tag row, and an ordinary ready task for comparison.
- Validation: `npx vitest run src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx src/__tests__/CardSignalModel.test.tsx src/__tests__/BoardVisualDesign.test.tsx --reporter=dot` (86 passed); `npx playwright test e2e/card-density.spec.ts --project=chromium` (21 passed); `npx eslint src/components/Card.tsx src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx e2e/card-density.spec.ts` passed; `npm run build` passed with existing chunk-size warning; editor diagnostics clean for touched frontend files.