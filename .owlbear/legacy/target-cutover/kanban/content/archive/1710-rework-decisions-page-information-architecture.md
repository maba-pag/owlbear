---
id: 1710
title: Rework decisions page information architecture
status: archived
priority: medium
created: 2026-05-21T23:23:24.567462+02:00
updated: 2026-05-24T10:50:01.374220+02:00
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
  - Validate Decisions IA with desktop screenshots at widths >= 1200px, not
    mobile/narrow screenshots.
  - Sort pending decisions oldest first by creation date.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
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


## Additional User Feedback - 2026-05-22
- Decisions must be validated with desktop screenshots only; Cockpit development target is desktop, with screenshot/test widths no less than 1200px and wide-display review encouraged.
- Pending decisions should sort oldest first by creation date so the queue behaves like a real decision backlog.


## Evidence - 2026-05-22
- Classification: user-observed current Decisions workflow deficiency, not theoretical. The route used duplicated title/body content, route-level response chips that did not actually resolve anything, and an oversized resolver heading/body-first layout.
- Impact: hurt Cockpit now because `/decisions` is the primary route-owned human resolution surface; it also hurt the Decisions plan by making the workflow read like a preview table instead of a decision queue.
- Implementation: extracted shared decision-brief parsing into `src/utils/decisionBrief.ts`; Decisions cards now render title, context, options, recommendation, impact, and a single `Open resolver` path. The fake route-level `Approve / Needs info / Reject` chips were removed. Pending decisions sort oldest-first by `created` timestamp.
- Resolver: `ResolveModal` now opens with a compact decision summary, response choices, notes, and a collapsed `Full request` disclosure. The DR title is no longer repeated as the markdown body, and the heading scale is reduced.
- Test update: corrected a stale snapshot test to assert the open modal keeps its original DR title while allowing the background Decisions list to refresh after SSE.
- Screenshot proof: `.owlbear/scratch/1710-decisions-1440-light.png`, `.owlbear/scratch/1710-decisions-modal-1440-light.png`, `.owlbear/scratch/1710-decisions-modal-1440-dark.png`, and `.owlbear/scratch/1710-decisions-2560-light.png`. All are desktop widths >= 1200px; the 2560px capture matches the user's display class.
- Browser metrics: screenshot capture confirmed item order `dr-oldest-1710`, then `dr-newer-1710`, and the resolver stayed inside the viewport at 920px wide on 1440px and 2560px desktops.
- Validation: focused Vitest passed 6 files / 145 tests / 3 skipped. `npm run build` passed with the existing Vite chunk-size warning. Focused Playwright passed 5 tests for Decisions route composition, modal open flow, Decisions axe scan, and resolver axe scan. ESLint on touched source/tests passed. VS Code diagnostics found no errors in touched files.
