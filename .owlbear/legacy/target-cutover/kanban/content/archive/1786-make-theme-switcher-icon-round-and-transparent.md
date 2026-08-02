---
id: 1786
title: Make theme switcher icon round and transparent
status: archived
priority: medium
created: 2026-05-24T01:57:03.588400+02:00
updated: 2026-05-24T10:50:02.440740+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - pds
  - discussion
parent: 1773
depends_on: []
ac:
  - Theme switcher rest state is round, not oval.
  - Theme switcher rest state has no gray fill/background.
  - Hover/focus/active states remain accessible and visible.
  - No implementation begins until the user approves this task.
  - Theme switcher visually aligns with the adjacent health-status trigger size
    and rest treatment.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User observed the theme switcher icon has a gray background and is oval rather than round. It should be a round icon control without a visible background color.

## Current Interpretation
Likely small visual polish issue in the global header/status controls. The current shape/background makes the theme toggle look heavier and less aligned with the health indicator/icon treatment.

## Value
The header is always visible, so small visual mismatches are high-frequency polish defects. A clean round transparent icon improves perceived fit with the rest of the Cockpit chrome.

## Discussion Questions
- Should the theme toggle match the health badge exact 44px transparent target?
- Should hover/focus still show a subtle background while rest state stays transparent?
- Should this be done with PDS button props/classes or a custom wrapper exception?

[[2026-05-24T02:47:27+02:00]]
## User Preference
User prefers a PDS-native `p-button-pure` icon trigger, roughly `<p-button-pure icon="theme" hideLabel>`, over a compact secondary `p-button` with style overrides. User is open to alternatives if there is a clear reason another approach is better.

[[2026-05-24T02:47:43+02:00]]
## Discussion Note
Local evidence supports the user's instinct: `PButtonPure` is already used for non-compact `ThemeToggle` and for compact icon-only `CleanupPanel`. It is the better first-choice because it stays PDS-native while avoiding the secondary `PButton` rest background/oval shape. A different approach would only be better if `PButtonPure` could not provide a reliable 44px target, focus state, or menu trigger semantics.

[[2026-05-24T02:48:56+02:00]]
## Decision
User locked the `PButtonPure` solution for the theme switcher. Health-status parity matters: the theme switcher should share the same apparent 44px transparent circular trigger signature as the adjacent health control.

## Health Badge Note
`HealthBadge` already uses a custom native button with `size-11`, `rounded-full`, and `bg-transparent` so it is closer to the intended signature. The theme toggle should be brought into alignment with that control; HealthBadge should only change if proof shows a mismatch after the theme fix.

[[2026-05-24T03:42:42+02:00]]

## Implementation Proof
Implemented in Cockpit web as part of the approved small polish package. Compact theme trigger now uses PDS `PButtonPure` instead of secondary `PButton`; proof metrics show `p-button-pure`, 44x44 target, transparent rest background, and menu semantics preserved.

Proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1786-theme-toggle-after.png`

[[2026-05-24T04:22:03+02:00]]

## Reopen Note
User review found the compact theme button still looks wrong: the round hit box appears too large, the icon is visually off-center as if hidden text still affects layout, and the adjacent health indicator hover/click area also feels too large. Fix direction: tighten and center the actual icon triggers visually, not just satisfy DOM size metrics.

[[2026-05-24T04:33:58+02:00]]
## Completion Note
- Replaced the compact theme trigger with a tightly sized 32px icon-only status-bar button using the PDS `PIcon` theme glyph, avoiding the hidden-label offset that made the icon appear left-weighted.
- Tightened the workspace health trigger from the oversized 44px hover target to the same 32px compact footprint and reduced the traffic-light halo.
- Verification: `npm test -- --run src/__tests__/IdeasPage.test.tsx src/__tests__/ThemeToggle.test.tsx src/__tests__/HealthBadge.test.tsx src/__tests__/BoardVisualDesign.test.tsx src/__tests__/Shell.test.tsx`; focused ESLint; `npm run build`.
- Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/1786-status-controls-theme-hover-updated.png` and `.owlbear/scratch/1716-wide-cockpit/1786-status-controls-health-hover-updated.png`; Playwright metrics show both controls at 32x32 and both icon/dot center deltas at `{dx: 0, dy: 0}`.

