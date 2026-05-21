---
id: 1714
title: Reconsider top bar product identity
status: research
priority: important
created: 2026-05-21T23:24:05.487044+02:00
updated: 2026-05-21T23:24:05.487044+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - top-bar
  - identity
parent:
depends_on: []
ac:
  - Audit whether the Porsche logo is required for Cockpit or incidental visual
    treatment.
  - Compare top-bar identity alternatives such as OwlBear Dashboard/Cockpit.
  - Decide and implement an identity treatment that fits the product and
    constraints.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Is the Porsche logo a requirement on the top bar? Can it be replaced with `OwlBear dashboard` or something more fitting?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically. This likely needs a product/brand decision before implementation.

## Evaluation Notes
- Classification: user-observed brand/product-fit question.
- Value question: top identity should clarify the tool and feel fitting; Porsche Design System usage does not automatically mean the Porsche logo is the right product identity.
- Impact: could hurt Cockpit now by making the app feel like a Porsche-branded demo rather than OwlBear cockpit; brand requirements are unknown and should be verified before removal.
- Screenshot target: top bar desktop/mobile with Porsche logo, possible OwlBear/dashboard identity alternatives.

## Acceptance Criteria
- Determine whether Porsche logo is a requirement or only inherited from PDS styling.
- Compare product identity alternatives for clarity and fit.
- Choose top-bar identity treatment that supports OwlBear Cockpit without violating brand constraints.