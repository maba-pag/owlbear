---
id: 1724
title: Fix theme switcher focus ring artifact
status: archived
priority: medium
created: 2026-05-23T02:07:23+0200
updated: 2026-05-24T10:50:01.592271+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - top-bar
  - theme
  - focus
parent:
depends_on: []
ac:
  - Reproduce the blue border/focus artifact after selecting and reopening the
    theme switcher.
  - Distinguish acceptable keyboard focus visibility from a persistent visual
    artifact after pointer selection.
  - Preserve accessible focus indication for keyboard users.
  - Validate with focused checks and desktop screenshot evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
After selecting a theme, the theme selector bubble has a blue border; reopening the dropdown also shows a strange blue border. This should be investigated and polished without removing necessary accessibility affordances.

## Evaluation Notes
- Classification: user-observed current visual issue.
- Product value: the top bar is visible everywhere; a persistent or odd focus artifact makes the otherwise compact theme control feel unfinished.
- Do after the markdown preview task unless screenshots show it is more severe.

## Evidence
- Reproduced the artifact after pointer-selecting a theme: `.owlbear/scratch/1716-wide-cockpit/1724-theme-focus-before-fix-after-select.png` showed the trigger retaining a blue ring.
- Fixed compact theme option activation so pointer clicks close the menu without refocusing the trigger, while keyboard activation still restores trigger focus.
- Focused Vitest passed: `ThemeToggle.test.tsx` 1 file, 7 tests.
- ESLint passed for `ThemeToggle.tsx` and `ThemeToggle.test.tsx`.
- `npm run build` passed with the existing Vite chunk-size warning.
- After-fix pointer screenshot: `.owlbear/scratch/1716-wide-cockpit/1724-theme-focus-after-fix-after-select.png`.
- After-fix reopen screenshot: `.owlbear/scratch/1716-wide-cockpit/1724-theme-focus-after-fix-reopen.png`.
- Keyboard proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1724-theme-focus-after-fix-keyboard.png`.
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1724-theme-focus-after-fix-metrics.json` and `.owlbear/scratch/1716-wide-cockpit/1724-theme-focus-keyboard-metrics.json`.
