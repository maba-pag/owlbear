---
id: 1712
title: Shrink top bar theme switcher
status: todo
priority: important
created: 2026-05-21T23:23:43.267289+02:00
updated: 2026-05-22T00:47:04.722393+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - top-bar
  - theme
parent:
depends_on: []
ac:
  - Audit top-bar ThemeToggle size and dominance in screenshots.
  - Design a smaller light/dark/auto state control if it improves chrome
    balance.
  - Preserve accessible labels and keyboard interaction.
  - Explore a clearer compact theme-state treatment where automatic mode is
    visibly distinct without a cryptic bare letter.
  - Discuss the preferred theme-switcher direction with the user before
    implementation.
  - Validate the chosen theme control in light, dark, and automatic states on
    desktop screenshots >= 1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The top bar theme switcher could be smaller, maybe just the icon in light/dark plus an A or glowing A for auto.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current visual-weight issue.
- Value question: theme mode is useful, but persistent text should not dominate top chrome if compact icon states remain clear.
- Impact: hurts Cockpit now if utility controls compete with route content and status.
- Screenshot target: top bar desktop/mobile in light/dark/auto states.

## Acceptance Criteria
- Audit ThemeToggle visual weight and discoverability.
- Design compact mode-state representation for light/dark/auto.
- Preserve accessible labels, keyboard operation, and clear current mode.

[[2026-05-21T23:58:48+02:00]]
## Builder Evidence
- Classification: observed current visual-weight issue, not theoretical. Screenshots showed the full `Auto` label adding another text control to the top-right chrome next to `Workspace OK`.
- Impact: hurt Cockpit now by letting a utility preference compete with route content; hurt the plan for a premium, quiet cockpit because the top strip read like controls instead of state.
- Decision: keep the PDS `PButtonPure` theme control but render it compact in Shell: theme icon plus one-character mode indicator (`L`, `D`, `A`) and sr-only full mode text.
- Implementation: ThemeToggle compact mode now exposes a mode indicator, keeps `aria-label` and `title` for the full state, and preserves the same click/keyboard toggle behavior. Shell now uses compact ThemeToggle.
- Screenshot evidence: `.owlbear/scratch/1680-route-kanban-desktop.png` and `.owlbear/scratch/1680-route-kanban-mobile.png` show the compact top-right theme icon plus `A` state.
- Validation: focused Vitest passed (6 files, 97 tests); `npm run build` passed with existing Vite chunk-size warning; E2E passed for board view + workspace status popover accessibility, HealthBadge popover no-reflow, and status-bar control names (4 tests); eslint and diagnostics passed.


## Reopened User Feedback - 2026-05-22
- The compact theme treatment was not what the user meant: a bare letter after the icon is not meaningful enough, but the old full text may be too long.
- Automatic mode needs a visibly distinct state, and the solution should be discussed before implementation.
- Classification: user-observed delivered-work gap, not theoretical.
- Impact: hurts Cockpit now because the current compact control is ambiguous.
