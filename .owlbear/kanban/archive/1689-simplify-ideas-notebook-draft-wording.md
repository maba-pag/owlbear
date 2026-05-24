---
id: 1689
title: Simplify ideas notebook draft wording
status: archived
priority: important
created: 2026-05-21T19:52:59.015387+02:00
updated: 2026-05-24T10:50:01.104633+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - ideas
parent:
depends_on: []
ac:
  - Audit all visible `draft` wording in the Ideas notebook.
  - Replace repeated or unclear labels with useful state/action language.
  - Align Ideas header with the shared route-header system.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Ideas notebook looks good apart from the headline not matching the shared design. The word `draft` appears in multiple places, and it is unclear what the word is supposed to communicate.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current copy/semantic noise.
- Value question: should the notebook communicate document state as saved/unsaved/conflict, not generic `draft` labels?
- Screenshot target: Ideas route header, editor toolbar, side status panel.

## Acceptance Criteria
- Inventory every visible `draft` label in Ideas.
- Remove or replace repeated wording with state language that helps the user act.
- Align the Ideas route header with the shared Cockpit header pattern.

## Outcome
- Audit: visible `draft` wording appeared in the editor toolbar (`Draft`) and side panel (`Draft`, `Draft Metrics`), but it did not tell the user whether the notebook was saved, unsaved, conflicted, or what action was available.
- Decision: reserve prime header/status language for save state (`Saved`, `Unsaved changes`, `Conflict`) and use concrete surface labels elsewhere: `Editor`, `Markdown preview`, `Notebook`, `Changes`, and `Writing metrics`.
- Implementation: Ideas now keeps the shared `WorkspaceHeader`, removes visible `draft` wording from the notebook surface, and uses local labels that describe what the user is looking at rather than repeating a generic document-stage term.

## Evidence
- Focused green: `npx vitest run src/__tests__/IdeasPage.test.tsx --testNamePattern="StatusWording|SaveFlow|PdsControls"` passed, 13 selected tests.
- Affected regression: `npx vitest run src/__tests__/IdeasPage.test.tsx src/__tests__/IdeasPage_1664.test.tsx` passed, 52 tests.
- Quality: `npx eslint src/pages/IdeasPage.tsx src/__tests__/IdeasPage.test.tsx` passed; `npm run build` passed with only the known Vite chunk-size warning.
- Editor diagnostics: VS Code reported no errors in `IdeasPage.tsx` or `IdeasPage.test.tsx`.
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/ideas-wording-1689-1690.png` at 2560x1440 shows the Ideas route with no visible `draft` wording, header state `Unsaved changes`, toolbar `Editor / 29 lines`, and side-panel `Writing metrics`; browser diagnostics were empty.