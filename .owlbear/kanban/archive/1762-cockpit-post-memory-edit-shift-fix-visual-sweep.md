---
id: 1762
title: Cockpit post Memory edit shift fix visual sweep
status: archived
priority: important
created: 2026-05-23T16:41:44+0200
updated: 2026-05-24T10:50:02.124138+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-proof
  - sweep
parent:
depends_on:
  - 1761
ac:
  - Capture current desktop and mobile Cockpit states after the
  - Include the core workspace routes and non-mutating interaction states likely
    to reveal layout regressions.
  - Confirm the Memory edit shift fix remains visible in full-route screenshots.
  - Confirm the
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
Run the next current-state visual pass after #1761. The previous fix removed the mobile Memory edit horizontal shift; this sweep checks the complete Cockpit work surface again before choosing the next fix.

## Evaluation Frame
- Prefer observed UI harm over speculative polish.
- Treat screenshots as product evidence and metrics/tests as support.
- Recheck route interactions after scroll-related changes.

## Evidence
- Screenshots captured under `.owlbear/scratch/1716-wide-cockpit/1762-*.png` for desktop/mobile routes and key interaction states.
- Contact sheets captured as `.owlbear/scratch/1716-wide-cockpit/1762-desktop-contact-sheet.png` and `.owlbear/scratch/1716-wide-cockpit/1762-mobile-contact-sheet.png`.
- Metrics captured in `.owlbear/scratch/1716-wide-cockpit/1762-post-memory-edit-sweep-metrics.json` with 20 records.
- Summary: no document-level horizontal or vertical overflow, no console messages, and no request failures.
- The #1761 Memory mobile edit fix remains visible in `1762-mobile-memory-edit.png`; the route starts inside the viewport and edit actions remain reachable.
- The #1759 Ideas dirty preview toolbar fix remains visible in `1762-mobile-ideas-dirty-preview.png`; `Save` is fully shown.

## Finding
- No new observed current harm requiring a source-code fix was identified in this sweep.
- Non-issue: Kanban mobile screenshots and metrics still show offscreen column/card content because the board is an intentional horizontal strip; the active visible lane and task detail modal remain usable.
- Non-issue: the task edit modal shows lower form content partially below the fold, but the sticky Save/Cancel actions are visible and the scroll body is the intended interaction model.