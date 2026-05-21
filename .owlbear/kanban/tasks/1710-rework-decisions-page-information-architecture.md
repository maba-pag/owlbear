---
id: 1710
title: Rework decisions page information architecture
status: research
priority: important
created: 2026-05-21T23:23:24.567462+02:00
updated: 2026-05-21T23:23:24.567462+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - decisions
  - information-architecture
parent:
depends_on: []
ac:
  - Audit the current Decisions page hierarchy against real decision workflow
    value.
  - Fix duplicated title/body preview behavior and oversized text hierarchy.
  - Rework options and response controls so they support decision-making instead
    of decorative layout.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The Decisions page is still a mess overall: decision choices appear as bullets on the side for no clear reason, text opens in giant letters, and the decision body is used as both title and body in the preview table.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically. This supersedes the idea that the first Decisions redesign was enough.

## Evaluation Notes
- Classification: user-observed current page-level product deficiency, not theoretical.
- Value question: the Decisions route must help users understand requests and choose responses without chaotic hierarchy or duplicated body/title content.
- Impact: hurts Cockpit now and hurts the route-owned Decisions plan because `/decisions` is the primary resolution surface.
- Screenshot target: Decisions route list/preview, ResolveModal, body/title handling, choices layout.

## Acceptance Criteria
- Re-audit Decisions page information hierarchy with realistic DR bodies.
- Separate title, summary, body, options, recommendation, and response controls cleanly.
- Remove side bullets/giant typography/duplicated body-title patterns that do not support deciding.