---
id: 1703
title: Include task creation in history
status: done
priority: important
created: 2026-05-21T20:23:20.827522+02:00
updated: 2026-05-22T16:02:24+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - history
parent:
depends_on: []
ac:
  - Verify availability of task creation timestamp in task detail data.
  - Show task creation in History when available.
  - Use consistent readable timestamp formatting for history events.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Task detail History misses the creation event. It should have a usable timestamp that can be used there, shouldn't it?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current history completeness gap.
- Value question: creation is foundational audit context and should be visible if the backend/task model provides `created`.
- Screenshot target: task detail History with task created timestamp and subsequent events.

## Acceptance Criteria
- Confirm whether task creation timestamp is available in the task detail payload.
- Add creation as the first history event when available.
- Format timestamp consistently and usefully for cockpit review.

## Builder Evidence
- Confirmed task detail payloads already include `created`; task #1703 returned `2026-05-21T20:23:20.827522+02:00`.
- Added a synthetic `Task created` history event from the task detail `created` field, rendered before matching work-session rows.
- Added readable timestamp rendering for creation and session rows, preserving raw timestamps in `data-timestamp` for testability.
- Kept creation rows distinct from work-session rows (`history-created-row` vs `history-session-row`) so existing session click/filter semantics remain stable.
- Opening History now scrolls the event list into view when the modal content is lower than the desktop viewport.
- Rounded fractional session durations into human audit labels (`10m`, `13m`) instead of leaking raw decimal seconds.
- Screenshot proof: `.owlbear/scratch/1716-wide-cockpit/task-history-created-1703.png` at 2560x1440. The screenshot uses real task #1677 because it has both a `created` timestamp and 2 matching sessions; #1703 itself had `created` but no matching session rows yet. Browser diagnostics were 0 console/page/request/response errors.

## Verification
- Red proof: `npx vitest run src/__tests__/DetailTab.test.tsx --testNamePattern="history includes task creation|history session row shows a readable" --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1703-red-history-created.json` failed before implementation because History only showed session rows and no readable timestamp field.
- Focused green: `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/ActivityTab.fetch-filter.test.tsx src/__tests__/ActivityTab.test.tsx src/__tests__/SidecarUX.test.tsx --testNamePattern="history includes task creation|history session row shows a readable|history shows only sessions|HistorySubtab formats fractional seconds|HistorySubtab duration 120|ActivityTab session row with duration 120" --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1703-focused-history-created.json` passed 8 tests.
- Affected regression: `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/ActivityTab.fetch-filter.test.tsx src/__tests__/ActivityTab.test.tsx --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1703-vitest-history-created.json` passed 124 tests, 1 existing skipped.
- Broader exploratory run including `src/__tests__/SidecarUX.test.tsx` passed all History/Activity assertions but still exposed an unrelated existing RepairPanel quarantine-copy failure.
- Lint/build: `npx eslint src/components/ActivityTab.tsx src/components/DetailTab.tsx src/components/HistorySubtab.tsx src/__tests__/ActivityTab.fetch-filter.test.tsx src/__tests__/DetailTab.test.tsx && npm run lint:css && npm run build` passed; build emitted only the existing Vite chunk-size warning.