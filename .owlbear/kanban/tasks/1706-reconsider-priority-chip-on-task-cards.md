---
id: 1706
title: Reconsider priority chip on task cards
status: research
priority: important
created: 2026-05-21T20:23:55.395881+02:00
updated: 2026-05-21T20:23:55.395881+02:00
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