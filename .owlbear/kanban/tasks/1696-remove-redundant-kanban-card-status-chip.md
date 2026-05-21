---
id: 1696
title: Remove redundant kanban card status chip
status: research
priority: important
created: 2026-05-21T20:21:45.242959+02:00
updated: 2026-05-21T20:21:45.242959+02:00
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