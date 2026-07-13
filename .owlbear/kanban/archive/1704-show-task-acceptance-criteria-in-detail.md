---
id: 1704
title: Show task acceptance criteria in detail
status: archived
priority: medium
created: 2026-05-21T20:23:32.985106+02:00
updated: 2026-05-24T10:50:01.299317+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - acceptance-criteria
parent:
depends_on: []
ac:
  - Verify task detail payload includes acceptance criteria when tasks have
    them.
  - Render acceptance criteria in task detail when present.
  - Use a clear absent state when no AC exist rather than leaving the user
    guessing.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Where are the AC of this task? Current tasks should have some, or the view may be missing them.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current information gap, pending data check.
- Value question: AC are core task context; task detail should show them when present and clearly show absence when not.
- Screenshot target: task detail for a task with AC and one without AC.

## Acceptance Criteria
- Verify whether acceptance criteria are present in the task detail API payload for current tasks.
- Render AC prominently enough for review/build work when present.
- Provide a useful empty/absent state when a task has no AC.

## Builder Evidence
- Observed backend detail payload for task #1704 includes canonical `ac` with 3 items.
- Preserved `ac` on the Cockpit frontend `TaskDetail` API type.
- Rendered a dedicated Acceptance Criteria section in task detail: `task-ac-list` for populated AC and `task-ac-empty-state` when no usable AC items exist.
- Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/task-detail-ac-1704.png` at 2560x1440, with 3 rendered AC items and 0 console/page/request/response diagnostics.

## Verification
- Red proof: `npx vitest run src/__tests__/DetailTab.test.tsx --testNamePattern="acceptance criteria" --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1704-red-detail-ac.json` failed before implementation because the AC section/list/empty state did not exist.
- Focused green: `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/tasks.test.ts --testNamePattern="acceptance criteria|TaskDetail: ac" --reporter=json --outputFile=.owlbear/scratch/1704-focused-detail-ac.json` passed 3 tests.
- Broader regression: `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/tasks.test.ts src/__tests__/TaskDetailModel.test.tsx --reporter=json --outputFile=.owlbear/scratch/1704-vitest-detail-ac.json` passed 157 tests, 1 existing skipped.
- Lint: `npx eslint src/api/tasks.ts src/components/DetailTab.tsx src/__tests__/DetailTab.test.tsx src/__tests__/tasks.test.ts` passed.
- Build: `npm run build` passed; only the existing Vite chunk-size warning appeared.