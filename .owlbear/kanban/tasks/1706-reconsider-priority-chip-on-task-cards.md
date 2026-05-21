---
id: 1706
title: Reconsider priority chip on task cards
status: done
priority: important
created: 2026-05-21T20:23:55.395881+02:00
updated: 2026-05-21T22:08:55.523865+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - cards
  - priority
parent:
depends_on: []
ac:
  - Audit Kanban card priority chip value relative to border-based priority 
    signal.
  - Define priority/alert signal hierarchy for cards.
  - Remove or demote priority chip on cards if it is redundant visual noise.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Why is there a priority bubble on the Kanban task card? In detail view it may be fine, but not on the task card. The card can show priority by left-border tone in grey colors, unless overridden by stronger signals like blocked state, DR, or similar.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current card signal redundancy/visual-weight issue.
- Value question: card-level priority should help scanning without adding chip noise; border encoding may be enough for normal priority.
- Screenshot target: cards across priority levels and alert states.

## Acceptance Criteria
- Audit priority chip value on Kanban cards versus left-border signal.
- Decide normal priority display rules and override hierarchy for blocked/decision/high-risk signals.
- Remove or demote priority chip from cards if border/status cues provide better scanning.

[[2026-05-21T22:08:45+02:00]]
## Builder Evidence
- Classification: observed current card signal redundancy and visual-weight issue, not theoretical. Screenshot review showed the priority bubble competed with task title, tags, and alert cues.
- Impact: hurt Cockpit now by adding chip noise to every card; hurt the priority-signal plan because the left rail already communicates normal priority while stronger states need the attention budget.
- Decision: remove the visible `card-priority` chip from Kanban task cards. Keep priority on `data-priority`, in the accessible card label, and in the left border hierarchy; blocked, pending decision, claimed, and dependency signals continue to override normal priority emphasis.
- Screenshot evidence: `.owlbear/scratch/1680-route-kanban-desktop.png`, `.owlbear/scratch/1680-route-kanban-mobile.png`.
- Validation: `npm test -- --run src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx src/__tests__/CardSignalModel.test.tsx src/__tests__/BoardVisualDesign.test.tsx --reporter=dot` (81 passed); `npm run test:e2e:all -- e2e/card-density.spec.ts --reporter=line` (20 passed after stopping stale preview server); `npx eslint src/components/Card.tsx src/__tests__/Card.visual-treatment.test.tsx src/__tests__/Card.signal.test.tsx e2e/card-density.spec.ts` passed; `npm run build` passed with existing Vite chunk-size warning; board accessibility sweep passed (1); dual-theme board accessibility passed (2).
