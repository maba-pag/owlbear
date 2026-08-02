---
id: 1690
title: Clarify ideas notebook status pills
status: archived
priority: medium
created: 2026-05-21T19:53:07.237638+02:00
updated: 2026-05-24T10:50:01.118063+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - ideas
parent:
depends_on: []
ac:
  - Audit Ideas header pills and side-panel metrics for duplication and value.
  - Keep only actionable or high-value status in the header.
  - Move or remove static mode/word-count text if it is redundant.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Ideas notebook has status info in a corner bubble such as `Saved, Edit, 14 words`. Saved/edited might be worth it, but static `Edit` text and repeated word count are unclear.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current status-signal noise.
- Value question: what should be always visible: save state, conflict state, mode toggle, or writing metrics? Metrics may belong in the state panel, not header.
- Screenshot target: Ideas header and side panel in edit/preview/saved/dirty states.

## Acceptance Criteria
- Determine which Ideas state signals are actionable in the header.
- Remove repeated/static signals that do not change behavior or understanding.
- Keep writing metrics only where they help, without duplicating header status.

## Outcome
- Audit: the Ideas header summary mixed three signal types: save state (`Saved`/dirty/conflict), current mode (`Edit`/`Preview`), and writing metrics (`words`). Mode was already represented by the preview/edit command, and writing metrics were repeated in the side panel.
- Decision: the header should carry only the actionable persistence state: `Saved`, `Unsaved changes`, or `Conflict`. Mode remains an action button in the editor toolbar, and writing metrics live in the right-side state panel where they are useful but not top-level chrome.
- Implementation: removed the static mode pill and word-count metric from the header summary, expanded the dirty header label to `Unsaved changes`, and kept metrics in the `Writing metrics` panel.

## Evidence
- Focused green: `npx vitest run src/__tests__/IdeasPage.test.tsx --testNamePattern="StatusWording|SaveFlow|PdsControls"` passed, 13 selected tests, including assertions that the header summary has no mode or word metric and changes to `Unsaved changes` after editing.
- Affected regression: `npx vitest run src/__tests__/IdeasPage.test.tsx src/__tests__/IdeasPage_1664.test.tsx` passed, 52 tests.
- Quality: `npx eslint src/pages/IdeasPage.tsx src/__tests__/IdeasPage.test.tsx` passed; `npm run build` passed with only the known Vite chunk-size warning.
- Editor diagnostics: VS Code reported no errors in `IdeasPage.tsx` or `IdeasPage.test.tsx`.
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/ideas-wording-1689-1690.png` at 2560x1440 shows the Ideas header with only `Unsaved changes` in the summary, no header word-count metric, and metrics retained in the side panel; browser diagnostics were empty.