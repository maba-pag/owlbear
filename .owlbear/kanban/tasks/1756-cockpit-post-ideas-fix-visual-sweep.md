---
id: 1756
title: Cockpit post Ideas fix visual sweep
status: done
priority: important
created: 2026-05-23T15:49:12+0200
updated: 2026-05-23T15:54:30+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-proof
  - sweep
parent:
depends_on: [1755]
ac:
  - Capture current desktop and mobile Cockpit states after the #1755 Ideas mobile panel fix.
  - Include the core workspace routes and non-mutating interaction states likely to reveal layout regressions.
  - Confirm the Ideas fix remains visible in full-route screenshots.
  - Classify any new finding as observed current harm, plan risk, or theoretical before creating a fix task.
  - Record screenshot and metric evidence under `.owlbear/scratch/1716-wide-cockpit/`.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Purpose
Run the next current-state visual pass after #1755. The previous sweep found a real mobile issue only in screenshot review, so this pass checks the complete Cockpit work surface again before choosing the next fix.

## Evaluation Frame
- Prefer observed UI harm over speculative polish.
- Keep route surfaces bounded, readable, and action-reachable.
- Treat screenshots as product evidence and tests as supporting build artifacts.

## Evidence
- Screenshots captured under `.owlbear/scratch/1716-wide-cockpit/1756-*.png` for desktop/mobile routes and key interaction states.
- Metrics captured in `.owlbear/scratch/1716-wide-cockpit/1756-post-ideas-sweep-metrics.json` with 18 records.
- Summary: no document-level horizontal or vertical overflow, no console messages, and no request failures.
- The #1755 Ideas mobile panel fix remains visible in `1756-mobile-ideas.png` and `1756-mobile-ideas-edit.png`.

## Finding
- Observed current harm: mobile Memory filter controls are clipped at the right edge, including PDS dropdown affordances. Follow-up created as #1757.
- Non-issues: Kanban offscreen columns are expected inside the horizontal strip; decision summary truncation is intentional preview behavior; Ideas edit textarea scroll is expected for editor content.
