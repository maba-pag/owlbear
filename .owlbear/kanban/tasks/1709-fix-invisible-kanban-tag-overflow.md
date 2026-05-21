---
id: 1709
title: Fix invisible kanban tag overflow
status: research
priority: important
created: 2026-05-21T23:23:14.191883+02:00
updated: 2026-05-21T23:23:14.191883+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - kanban
  - cards
  - bug
parent:
depends_on: []
ac:
  - Reproduce the Kanban card tag visibility/overflow mismatch with browser
    evidence.
  - Fix tag preview layout so visible tags and overflow count remain truthful.
  - Validate card tag behavior across expanded/collapsed sidebar and wide/narrow
    widths.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
On Kanban task cards there seem to be invisible tags. When removing the sidebar on high resolution, a third tag can be seen in some tasks while the `+x` tag stays the same.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current rendering/overflow bug.
- Value question: tag previews should show a truthful visible count; overflow indicators must match actually hidden tags.
- Impact: hurts Cockpit now by making card metadata untrustworthy.
- Screenshot target: task cards with 3+ tags across sidebar collapsed/expanded and wide/narrow viewports.

## Acceptance Criteria
- Reproduce tag preview/overflow mismatch in browser screenshots.
- Make visible tag count and `+x` overflow count truthful across responsive widths.
- Ensure no hidden tag is counted as visible or vice versa.