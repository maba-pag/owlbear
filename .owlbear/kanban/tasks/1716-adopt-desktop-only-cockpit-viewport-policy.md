---
id: 1716
title: Adopt desktop-only Cockpit viewport policy
status: todo
priority: important
created: 2026-05-22T00:56:41.749806+02:00
updated: 2026-05-22T00:56:44.499137+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - screenshots
  - testing
parent:
depends_on: []
ac:
  - Update Cockpit visual-audit and screenshot helpers used for polish work to
    capture desktop widths >= 1200px only.
  - Revisit Playwright coverage that exists solely for mobile/narrow route
    screenshots and either retarget it to desktop or document why it remains as
    legacy regression coverage.
  - Prefer at least one wide-desktop screenshot near 2560px for major layout
    decisions when practical.
  - Update task evidence language to avoid claiming mobile screenshots as
    product proof for new Cockpit polish tasks.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Cockpit only develops for desktop. Test and screenshot resolution width should be no less than 1200px; the user's display is 2560px.

## Evaluation Notes
- Classification: user-stated product/platform constraint, not theoretical.
- Impact: hurts the plan if polish work optimizes mobile/narrow layouts or uses mobile screenshots as proof for a desktop-only cockpit.

## Acceptance Criteria
- Update Cockpit visual-audit and screenshot helpers used for polish work to capture desktop widths >= 1200px only.
- Revisit Playwright coverage that exists solely for mobile/narrow route screenshots and either retarget it to desktop or document why it remains as legacy regression coverage.
- Prefer at least one wide-desktop screenshot near 2560px for major layout decisions when practical.
- Update task evidence language to avoid claiming mobile screenshots as product proof for new Cockpit polish tasks.