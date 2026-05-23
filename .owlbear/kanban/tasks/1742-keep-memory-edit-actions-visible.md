---
id: 1742
title: Keep memory edit actions visible
status: done
priority: needed
created: 2026-05-23T10:28:21+0200
updated: 2026-05-23T10:40:45+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
  - edit-mode
parent:
depends_on: [1737]
ac:
  - Use the #1737 memory edit-mode screenshot and metrics as current evidence.
  - Keep Memory edit Save and Cancel controls reachable in the initial edit-mode viewport.
  - Preserve the bounded Memory workspace and vertical-only internal scrolling.
  - Preserve existing edit, save, cancel, approval-state, and validation behavior.
  - Add or update focused tests for the visible edit-action contract where practical.
  - Capture after-fix screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## User Feedback Context
The #1737 interaction sweep shows the Memory detail expansion remains usable in display mode, but editing the selected memory pushes the form and its primary actions below the visible workspace.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1737-memory-edit.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1737-interaction-sweep-metrics.json` reports the Memory detail box `top: 375`, `bottom: 1503` and edit form `top: 845`, `bottom: 1503` inside a 1000px viewport, while the workspace ends at `bottom: 976`.

## Evaluation Notes
- Classification: observed current interaction usability issue.
- Current harm: users can enter Memory edit mode from the first item but must scroll inside the Memory list to reach Save or Cancel.
- Product value: Memory curation is a core Cockpit workflow; edit completion controls should be continuously reachable like the task detail editor.

## Implementation
- Moved the Memory edit title, character counter, Save, and Cancel controls into a sticky edit header at the top of the inline edit form.
- Suppressed the generic Memory list scroll cue while edit mode is active so the edit header owns the visible action surface.
- Preserved the existing PDS edit inputs, save payload, cancel behavior, validation messages, and approval-state mutation behavior.
- Added focused tests for the sticky Memory edit actions and edit-mode cue suppression contract.

## Evidence After Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1742-memory-edit-actions.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1742-memory-edit-actions-metrics.json` reports workspace `bottom: 976`, Memory list `overflowX: hidden` / `overflowY: auto`, edit actions `position: sticky`, action row `top: 846` / `bottom: 899`, Cancel `top: 854` / `bottom: 890`, Save `top: 854` / `bottom: 890`, and `memoryListScrollCue: null`.
- Metrics flags: `horizontalOverflow: false`, `verticalDocumentOverflow: false`, `workspaceBottomWithinViewport: true`, `memoryListVerticalOnly: true`, `actionsVisibleInListViewport: true`, `cancelVisibleInListViewport: true`, `saveVisibleInListViewport: true`, and no console messages.
- Validation: `npx vitest run src/__tests__/MemoryTab_1672.test.tsx src/__tests__/MemoryTab_1671.test.tsx --reporter=verbose` passed; `npx eslint src/pages/MemoryTab.tsx src/__tests__/MemoryTab_1672.test.tsx` passed; `npm run build` passed with the existing Vite chunk-size warning.