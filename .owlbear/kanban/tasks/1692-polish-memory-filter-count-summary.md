---
id: 1692
title: Polish memory filter count summary
status: research
priority: important
created: 2026-05-21T19:53:18.742929+02:00
updated: 2026-05-21T19:53:18.742929+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
parent:
depends_on: []
ac:
  - Audit Memory count summary wording, order, and alignment with realistic 
    counts.
  - Use concise count language that emphasizes what the user is seeing now.
  - Keep parse-error/filter context clear without text-heavy chrome.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Memory page count summary shows `109 entries / 94 shown`. This may be backwards, too text-heavy/verbose, and vertical alignment in the box is off.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI clarity/alignment issue.
- Value question: should the summary read as `94 of 109`, `94 shown`, or only appear when filters are active?
- Screenshot target: Memory header/filter count at realistic high entry counts.

## Acceptance Criteria
- Decide the most readable count order and when the count is valuable.
- Fix vertical alignment and reduce verbosity.
- Preserve clarity when filters hide entries or parse errors exist.