---
id: 1712
title: Shrink top bar theme switcher
status: research
priority: important
created: 2026-05-21T23:23:43.267289+02:00
updated: 2026-05-21T23:23:43.267289+02:00
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