---
id: 1690
title: Clarify ideas notebook status pills
status: research
priority: important
created: 2026-05-21T19:53:07.237638+02:00
updated: 2026-05-21T19:53:07.237638+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - ideas
parent:
depends_on: []
ac:
  - Audit Ideas header pills and side-panel metrics for duplication and value.
  - Keep only actionable or high-value status in the header.
  - Move or remove static mode/word-count text if it is redundant.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Ideas notebook has status info in a corner bubble such as `Saved, Edit, 14 words`. Saved/edited might be worth it, but static `Edit` text and repeated word count are unclear.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current status-signal noise.
- Value question: what should be always visible: save state, conflict state, mode toggle, or writing metrics? Metrics may belong in the state panel, not header.
- Screenshot target: Ideas header and side panel in edit/preview/saved/dirty states.

## Acceptance Criteria
- Determine which Ideas state signals are actionable in the header.
- Remove repeated/static signals that do not change behavior or understanding.
- Keep writing metrics only where they help, without duplicating header status.