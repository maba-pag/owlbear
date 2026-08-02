---
id: 1795
title: Make task reference chips navigable
status: archived
priority: medium
created: 2026-05-24T03:09:50.740084+02:00
updated: 2026-05-24T10:50:02.561948+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - references
  - discussion
parent: 1773
depends_on: []
ac:
  - Parent and dependency references in task detail are rendered as intentional
    chips/tags, not inert plain text.
  - Clicking a valid task reference opens the referenced task detail through
    Cockpit navigation/API, not direct filesystem access.
  - Missing or archived references are represented safely and clearly.
  - No implementation begins until the user approves this task.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
While discussing #1789, user noted that dependencies and parent are both task references and should probably be clickable PTags/bubbles that open the respective task details. This is related but broader than edit-input structure because it affects read-mode navigation too.

## Current Interpretation
Observed workflow improvement candidate. Task references should behave like references, not inert numbers/text, especially inside task detail where jumping between related tasks is a natural workflow.

## Value
Clickable parent/dependency chips let users inspect related tasks without copying IDs or going back to the board/search. This improves dependency tracing and task navigation.

## Discussion Questions
- Should reference chips open the referenced task in the same modal, preserving a back stack?
- Should broken/missing references render differently and explain the issue?
- Should chips show only `#id`, or also title/status when available?

[[2026-05-24T03:26:45+02:00]]

## Discussion Decision
Use same-modal navigation with a local back stack for task reference chips. Valid parent/dependency chips should open the referenced task detail in place, and the user should be able to return to the previously viewed task. Prefer chips that include `#id`, title, and status when available; missing or inaccessible references should render safely.

[[2026-05-24T05:04:34+02:00]]
## Implementation Start
Working on the approved same-modal reference navigation approach: inspect current parent/dependency rendering, task-detail selection flow, and available task metadata before editing.

## Implementation Proof
- Rendered task detail parent and dependency IDs as intentional task-reference chips instead of inert text.
- Known references show `#id`, task title, and status; missing/inaccessible references render as unavailable chips without navigation.
- Clicking an available reference routes through the existing Cockpit task detail selection/API path and opens the task in the same modal.
- Added a modal-local Back action after reference navigation, with dirty-edit guard still handled by the existing Shell task detail action flow.

## Verification
- `npm test -- --run src/__tests__/DetailTab.test.tsx src/__tests__/Shell.callbacks.test.tsx src/__tests__/Shell.card-selection.integration.test.tsx src/__tests__/ActivityTab.fetch-filter.test.tsx src/__tests__/TaskDetailModel.test.tsx` — 160 passed, 1 skipped.
- `npx eslint src/components/TaskFieldsEditor.tsx src/components/DetailTab.tsx src/Shell.tsx src/__tests__/DetailTab.test.tsx src/__tests__/Shell.callbacks.test.tsx` — passed.
- `npm run build` — passed with the known Vite chunk-size warning.
- `git diff --check` for #1795 files — passed.

## Visual Proof
- `.owlbear/scratch/1716-wide-cockpit/1795-task-reference-chips-1024.png`
- `.owlbear/scratch/1716-wide-cockpit/1795-task-reference-back-1024.png`
- `.owlbear/scratch/1716-wide-cockpit/1795-task-reference-return-1024.png`

## Screenshot Metrics
- Initial detail selected task `42`; chips included dependency `#10 API contract review IN PROGRESS`, parent `#5 Parent planning lane BACKLOG`, and missing dependency `#404 UNAVAILABLE`.
- After clicking dependency `#10`, selected task changed to `10` and Back became visible.
- After clicking Back, selected task returned to `42` and Back was hidden again.

[[2026-05-24T05:18:01+02:00]]
Implemented same-modal task reference navigation: parent/dependency chips show id/title/status, unavailable refs render safely, valid refs open through Cockpit selection/API, and a local Back action returns to the previous task. Verified with focused tests, lint/build, diff check, and screenshots.
