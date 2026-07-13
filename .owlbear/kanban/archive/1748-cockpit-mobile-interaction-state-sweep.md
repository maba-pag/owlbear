---
id: 1748
title: Cockpit mobile interaction-state sweep
status: archived
priority: medium
created: 2026-05-23T11:10:19+0200
updated: 2026-05-24T10:50:01.931913+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-sweep
  - responsive
parent:
depends_on:
  - 1747
ac:
  - Capture current narrow-viewport runtime evidence for key mobile interaction
    states after
  - Include at least Decisions resolver and Ideas dirty/edit states; include
    Memory edit or task detail when reachable without mutating persistent data.
  - Record geometry metrics for action reachability, bounded scroll surfaces,
    document overflow, horizontal overflow, and console/page errors.
  - Classify each finding as observed/theoretical and current/future harm with
    product value.
  - Create a follow-up fix task before editing any newly discovered issue.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Problem
Mobile resting pages are bounded, and the Ideas preview now has a continuation cue. Mobile modal/edit interaction states still need current browser evidence because cramped controls and sticky actions can fail differently on narrow viewports.

## Evidence Plan
- Capture the mobile Decisions resolver with its response controls and action buttons.
- Capture the mobile Ideas dirty/edit state with Save, Preview, textarea, and scroll cue behavior measured.
- Capture Memory edit or task detail mobile state if it can be opened without committing data changes.
- Classify any observed issue before creating a fix task.

## Evidence
- Screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1748-mobile-decisions-resolver.png`
  - `.owlbear/scratch/1716-wide-cockpit/1748-mobile-ideas-dirty-editor.png`
  - `.owlbear/scratch/1716-wide-cockpit/1748-mobile-memory-edit.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1748-mobile-interaction-metrics.json`.
- Browser proof reported no console, page, or request errors.

## Findings
- Ideas dirty editor: observed current usability issue. Raw button coordinates are in the viewport, but the screenshot shows the editor toolbar/actions are clipped out of the visible editor shell after the textarea receives focus. Metrics explain the cause: the shell has `clientHeight: 368` and `scrollTop: 174`, while the textarea is `min-height` constrained to 420px and overflows its hidden parent. Current harm is real: mobile users lose the Save/Preview controls while editing. Product value is high because Ideas is an editing surface and dirty-state actions must stay reachable.
- Decisions resolver: observed current usability issue. The resolver action buttons are visible, but the response section and notes extend below the modal body (`responseSelector.bottom: 974`, `resolveNotes.top: 1042`) while the modal footer remains visible. Current harm is mild-to-moderate: users can scroll the modal body, but there is no continuation cue and the disabled Submit button appears before the hidden response choices are obvious. Product value is high for decision workflow clarity. Follow-up task should add a resolver body continuation affordance.
- Memory edit: observed current mobile issue. The edit form is opened near the bottom of the list shell, with sticky edit actions around the viewport bottom (`memoryEditSave.bottom: 854` on an 844px viewport). Current harm is moderate: Save/Cancel are barely/cut-off until the user scrolls the list. Product value is high for memory editing, but Ideas edit toolbar loss is the first fix because it affects the active text editor shell itself.

## Follow-up
- Created #1749 Keep Ideas mobile edit actions visible before editing.
- Additional follow-up candidates: mobile resolver body continuation cue; mobile Memory edit auto-positioning.
