---
id: 1696
title: Remove redundant kanban card status chip
status: done
priority: important
created: 2026-05-21T20:21:45.242959+02:00
updated: 2026-05-22T13:59:22+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - cards
parent:
depends_on: []
ac:
  - Audit Kanban card status chip value versus column placement.
  - Remove or demote redundant status chips where appropriate.
  - Tone regular tags so they do not dominate over task title and true alerts.
  - Re-audit task-card metadata pills after the first declutter pass.
  - Remove or demote the task number bubble so the task ID reads as quiet
    metadata.
  - Reduce pill styling where text chips make cards feel bubbly, while
    preserving true alert signals.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Stating the column/status on a Kanban task that is clearly in that column is redundant. Removing it may allow normal tags to become grey instead of dominant black.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current redundancy and visual-weight issue.
- Value question: card status is already encoded by column placement; only exceptional workflow states should need a card-level signal.
- Screenshot target: Kanban cards in populated columns, with tags/status/priority visible.

## Acceptance Criteria
- Audit current card chips for redundant status information.
- Remove or demote the status chip when column placement already communicates it.
- Rebalance tag styling so tags support scanning without dominating the card.

[[2026-05-21T22:08:37+02:00]]
## Builder Evidence
- Classification: observed current redundancy and visual-weight issue, not theoretical. Screenshot review showed card status was repeated even though the column header already provided that state.
- Impact: hurt Cockpit now by making task cards noisier than needed; also hurt the card-scanning plan because normal tags and repeated workflow labels competed with true alert signals.
- Implementation: removed the visible `card-status` chip from Kanban task cards; kept status represented by the containing column and preserved machine-readable task metadata.
- Tag rebalance: regular task tags now use secondary PDS tags so they read as supporting metadata rather than primary alerts.
- Screenshot evidence: `.owlbear/scratch/1680-route-kanban-desktop.png`, `.owlbear/scratch/1680-route-kanban-mobile.png`.
- Validation: `npm test -- --run src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx src/__tests__/CardSignalModel.test.tsx src/__tests__/BoardVisualDesign.test.tsx --reporter=dot` (81 passed); `npm run test:e2e:all -- e2e/card-density.spec.ts --reporter=line` (20 passed after stopping stale preview server); `npx eslint src/components/Card.tsx src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx e2e/card-density.spec.ts` passed; `npm run build` passed with existing Vite chunk-size warning; board accessibility sweep passed (1); dual-theme board accessibility passed (2).


## Reopened User Feedback - 2026-05-22
- Kanban tasks still feel too bubbly because too much metadata is styled as pill tags.
- The task number probably should not be in a bubble; it can read as structural metadata instead of a chip.
- Classification: user-observed card-density issue, not theoretical.
- Impact: hurts Cockpit now by making cards feel heavier and less scannable than the desired operational surface.

[[2026-05-22T13:59:22+02:00]]
## Builder Evidence
- Classification: observed current card-density issue from 2560px Cockpit screenshots, not a theoretical test concern.
- Implementation: demoted the task ID from a rounded chip to quiet monospaced metadata; replaced normal PDS tag pills with plain inline metadata text and subtle slash separators; made tag overflow quiet text (`+N tags`) instead of another pill.
- Signal preservation: retained the primary exceptional signal badge and PDS icon for blocked, claimed, dependency, and decision-pending states while removing redundant secondary cue duplication.
- Screenshot evidence: `.owlbear/scratch/1716-wide-cockpit/kanban-viewport.png` at 2560x1440 shows the updated Kanban card hierarchy with quieter IDs and tags.
- Validation: `npx vitest run src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx src/__tests__/CardSignalModel.test.tsx src/__tests__/BoardVisualDesign.test.tsx --reporter=dot` (86 passed); `npx playwright test e2e/card-density.spec.ts --project=chromium` (21 passed); `npx eslint src/components/Card.tsx src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx e2e/card-density.spec.ts` passed; `npm run build` passed with existing chunk-size warning; editor diagnostics clean for touched frontend files.
