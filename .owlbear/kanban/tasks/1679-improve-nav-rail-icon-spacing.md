---
id: 1679
title: Improve nav rail icon spacing
status: done
priority: important
created: 2026-05-21T19:51:24.066039+02:00
updated: 2026-05-23T01:27:54+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - nav-rail
parent:
depends_on: []
ac:
  - Audit current nav icon spacing and hit targets in desktop screenshots.
  - Tune spacing so the nav rail reads as deliberate rather than cramped.
  - Preserve badge visibility and active route clarity.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The left menu icons are too close to each other; there is no spacing.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current UI issue.
- Value question: how much spacing preserves compact cockpit navigation while feeling deliberate and premium?
- Screenshot target: nav rail at desktop widths with all route badges visible.

## Acceptance Criteria
- Measure current hit targets, visual gaps, badge placement, and hover/focus state.
- Adjust spacing if the dock reads as cramped or accidental.
- Preserve efficient workspace switching and badge legibility.

[[2026-05-21T20:03:03+02:00]]
## Implementation Evidence
- Classification: confirmed current UI issue. The screenshot crop showed the icon group still read as stacked too tightly after removing the heavy shadow.
- Change: increased the dock item gap from `gap-static-xs` to `gap-static-sm`, keeping 40px icon targets and the compact vertical rail footprint.
- Screenshot proof: `.owlbear/scratch/1672-nav-dock-audit/root-1440x1000-nav-dock.png` shows clearer separation between controls while preserving badges and active state.
- Verification: focused Shell/PDS tests passed 94 tests / 3 skipped; focused shell-layout browser tests passed 2.

[[2026-05-23T01:27:54+02:00]]
## Status Reconciliation
- Re-audit: this task already had implementation evidence and verification but was still marked `research`.
- Current classification: done. No additional product change was needed before continuing with the newer Cockpit polish feedback.
