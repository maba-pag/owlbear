---
id: 1689
title: Simplify ideas notebook draft wording
status: research
priority: important
created: 2026-05-21T19:52:59.015387+02:00
updated: 2026-05-21T19:52:59.015387+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - ideas
parent:
depends_on: []
ac:
  - Audit all visible `draft` wording in the Ideas notebook.
  - Replace repeated or unclear labels with useful state/action language.
  - Align Ideas header with the shared route-header system.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Ideas notebook looks good apart from the headline not matching the shared design. The word `draft` appears in multiple places, and it is unclear what the word is supposed to communicate.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current copy/semantic noise.
- Value question: should the notebook communicate document state as saved/unsaved/conflict, not generic `draft` labels?
- Screenshot target: Ideas route header, editor toolbar, side status panel.

## Acceptance Criteria
- Inventory every visible `draft` label in Ideas.
- Remove or replace repeated wording with state language that helps the user act.
- Align the Ideas route header with the shared Cockpit header pattern.