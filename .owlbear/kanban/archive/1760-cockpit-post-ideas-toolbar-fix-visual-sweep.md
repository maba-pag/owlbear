---
id: 1760
title: Cockpit post Ideas toolbar fix visual sweep
status: archived
priority: medium
created: 2026-05-23T16:22:31+0200
updated: 2026-05-24T10:50:02.095457+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-proof
  - sweep
parent:
depends_on:
  - 1759
ac:
  - Capture current desktop and mobile Cockpit states after the
  - Include the core workspace routes and non-mutating interaction states likely
    to reveal layout regressions.
  - Confirm the Ideas dirty preview toolbar fix remains visible in full-route
    screenshots.
  - Recheck the
  - Classify any new finding as observed current harm, plan risk, or theoretical
    before creating a fix task.
  - Record screenshot and metric evidence under
    `.owlbear/scratch/1716-wide-cockpit/`.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Purpose
Run the next current-state visual pass after #1759. The previous fix removed mobile Ideas dirty preview toolbar clipping; this sweep checks the complete Cockpit work surface again before choosing the next fix.

## Evaluation Frame
- Prefer observed UI harm over speculative polish.
- Treat screenshots as product evidence and metrics/tests as support.
- Recheck suspicious crops with focused evidence before creating source-code work.

## Evidence
- Screenshots captured under `.owlbear/scratch/1716-wide-cockpit/1760-*.png` for desktop/mobile route states plus focused Memory edit and Ideas dirty preview states.
- Metrics captured in `.owlbear/scratch/1716-wide-cockpit/1760-post-ideas-toolbar-sweep-metrics.json` with 12 records.
- Summary: no document-level horizontal or vertical overflow and no console messages.
- The #1759 Ideas dirty preview toolbar fix remains visible in `1760-mobile-ideas-dirty-preview.png`; `Save` is fully inside the toolbar and editor shell.
- One request failure was an aborted PDS `view` icon request after toggling Ideas from editor to preview; the rendered screenshot and toolbar containment checks were clean.

## Finding
- Observed current harm: mobile Memory edit mode shifts the workspace left, clipping the route surface at the viewport edge. The focused metric shows `workspace.left = -16`, `memoryTab.left = -16`, and `memoryFilterPanel.left = -8` in `1760-mobile-memory-edit.png`. Follow-up created as #1761.