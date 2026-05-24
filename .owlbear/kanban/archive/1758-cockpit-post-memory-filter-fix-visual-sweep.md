---
id: 1758
title: Cockpit post Memory filter fix visual sweep
status: archived
priority: important
created: 2026-05-23T16:10:51+0200
updated: 2026-05-24T10:50:02.068490+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-proof
  - sweep
parent:
depends_on:
  - 1757
ac:
  - Capture current desktop and mobile Cockpit states after the
  - Include the core workspace routes and non-mutating interaction states likely
    to reveal layout regressions.
  - Confirm the Memory filter fix remains visible in full-route screenshots.
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
Run the next current-state visual pass after #1757. The previous fix removed mobile Memory filter clipping; this sweep checks the complete Cockpit work surface again before choosing the next fix.

## Evaluation Frame
- Prefer observed UI harm over speculative polish.
- Treat screenshots as product evidence and metrics/tests as support.
- Keep route surfaces bounded, readable, and action-reachable across mobile and desktop.

## Evidence
- Screenshots captured under `.owlbear/scratch/1716-wide-cockpit/1758-*.png` for desktop/mobile routes and key interaction states.
- Metrics captured in `.owlbear/scratch/1716-wide-cockpit/1758-post-memory-filter-sweep-metrics.json` with 20 records.
- Contact sheets captured as `.owlbear/scratch/1716-wide-cockpit/1758-desktop-contact-sheet.png` and `.owlbear/scratch/1716-wide-cockpit/1758-mobile-contact-sheet.png` for review triage.
- Summary: no document-level horizontal or vertical overflow, no console messages, and no request failures.
- The #1757 Memory mobile filter fix remains visible in `1758-mobile-memory-rest.png`; the state, category, agent, and search controls fit the route surface.

## Finding
- Observed current harm: mobile Ideas dirty preview toolbar clips the right side of the `Save` action in `1758-mobile-ideas-dirty-preview.png`. Follow-up created as #1759.
- Plan risk to revisit after #1759: `1758-mobile-memory-edit.png` shows a suspicious left-edge crop while the edit form is open, but the raw metric set is noisy around expected scroll containers and PDS internals. Recheck in the next sweep before classifying as a source-code defect.