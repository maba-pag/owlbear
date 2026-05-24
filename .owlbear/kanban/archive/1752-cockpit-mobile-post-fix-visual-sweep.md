---
id: 1752
title: Cockpit mobile post-fix visual sweep
status: archived
priority: important
created: 2026-05-23T11:43:17+0200
updated: 2026-05-24T10:50:01.985562+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - responsive
  - visual-proof
parent:
depends_on:
  - 1751
ac:
  - Capture current 390x844 mobile Cockpit states after the
  - Inspect intended functionality for primary tabs and interaction states
    without mutating persisted project data.
  - Use screenshot and geometry metrics, not visual memory alone, to identify
    issues.
  - Classify each finding as observed or theoretical, current harm or
    future/possible harm, and product value.
  - Record screenshots/metrics under `.owlbear/scratch/1716-wide-cockpit/`.
  - Create a follow-up task before any code fix work if a material issue is
    observed.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Purpose
Run a fresh mobile visual and interaction sweep after the recent Ideas, Decisions resolver, and Memory edit action reachability fixes. Use live evidence to pick the next highest-value Cockpit polish issue.

## Method
- Use the built Cockpit frontend served by the local backend at `http://127.0.0.1:8426`.
- Prefer browser-side metrics for overflow, clipped actions, scroll ownership, and console/request errors.
- Avoid save/approve/delete/release actions during proof capture.

## Evidence Captured
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1752-mobile-postfix-sweep-metrics.json`.
- Summary: `.owlbear/scratch/1716-wide-cockpit/1752-mobile-postfix-summary.json`.
- Screenshots: `.owlbear/scratch/1716-wide-cockpit/1752-mobile-*.png` covering Kanban, Decisions, Memory, Ideas, task detail/edit, resolver, dirty Ideas editor/preview, and Memory edit.

## Findings
- #1747-#1751 fixes held: Ideas dirty editor actions, Ideas preview scroll cue, Decisions resolver cue/actions, and Memory edit Save/Cancel were visible in their mobile interaction captures with no document-level overflow and no console/request errors.
- Observed current issue: mobile Kanban opens with the empty Todo column dominating the viewport while the only current In Progress task is a clipped sliver. Current harm is moderate because the primary board route hides the actionable lane on first view. Product value is high because Kanban is the first screen and should surface active work immediately.
- Theoretical/false alarm investigated: Ideas notebook/status content looked clipped in screenshots, but child-level geometry in `.owlbear/scratch/1716-wide-cockpit/1752-ideas-mobile-clipping-probe.json` showed the toolbar, state rows, and metrics values within their parent boxes. No follow-up created for that without stronger evidence.

## Follow-up
- Created #1753 to keep the first active Kanban lane fully visible on narrow mobile viewports while preserving the desktop/tablet context-column behavior when it fits.
