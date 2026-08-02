---
id: 1494
title: 'Cockpit: Add PDS banner for mutation error feedback'
status: archived
priority: medium
created: 2026-05-11T23:15:34.497443+00:00
updated: 2026-05-12T16:28:05.495397+00:00
tags:
  - cockpit
  - frontend
  - ux
  - quality
parent:
depends_on:
  - 1498
  - 1499
  - 1500
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Objective
Use PDS banner component for persistent mutation error feedback. Keep inline validation for field-level errors.

## Acceptance Criteria
- Mutation errors (move, edit, archive, resolve) show PDS p-banner (or equivalent)
- Errors persist until dismissed or action succeeds
- Field-level validation stays inline
- Errors survive tab/task navigation

## Source
Cockpit audit 2026-05-11, Finding F15
2026-05-12T02:39:31+00:00
## Research
- Research doc: .owlbear/research/cockpit-mutation-error-banner.md
- Sources: 6 studied, 5 high-relevance (PDS API docs, notification patterns, decision tree, codebase)
- Recommendation: Dual-layer — PBanner at Shell level for board/detail errors; PInlineNotification inside modals for archive/resolve with retry action (confidence: 0.75)
- Challenge: proceed — original confidence 0.34 raised to 0.75 after addressing modal scope carve-out and overlay stacking concerns
- Follow-up tasks: #1498 (wire PBanner in Shell), #1499 (replace modal errors with PInlineNotification), #1500 (tests)


## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Umbrella correctly decomposed into 3 focused children (#1498, #1499, #1500) |
| Interface clarity | PASS (refined) | Original AC is feature-level; refined below to P2/B1 verifiable criteria |
| Dependency correctness | PASS (fixed) | Added depends_on [#1498, #1499, #1500] |
| Module layering | PASS | PBanner→Shell level, PInlineNotification→modal level; no upward imports |
| TDD compliance | N/A | Umbrella task — children have own TDD cycles |
| KISS/YAGNI | PASS | Dual-layer justified by PDS modal stacking constraints (PBanner overlay competes with modal focus) |
| Premise challenge | PASS | Confirmed current state: KanbanBoard uses plain div, DetailTab uses plain div, modals use PText — PBanner/PInlineNotification available but unused |
| Pattern consistency | PASS | Shell-lifted state follows existing Shell.tsx pattern (selectedTaskId, refreshKey already lifted) |
| Security surface | PASS | No new system boundaries — error display is UI-only |
| Single domain | PASS | Frontend/UX only |

### AC Refinement

Original AC lines are feature-level. For pipeline verifiability, the following refined AC applies:

- AC-1 (P2): Child tasks #1498 (Shell PBanner), #1499 (modal PInlineNotification), #1500 (tests) reach `done` — verified by stage-transition audit of child statuses
- AC-2 (B1): Cockpit mutation errors surface via `PBanner` (Shell-level) and `PInlineNotification` (modal-level) instead of plain `<div>`/`<PText>` — verified by artifact inspection of component imports in Shell.tsx, KanbanBoard.tsx, ArchivalModal.tsx, ResolveModal.tsx

### Design Diverge

- Trigger: skipped — research doc evaluated 3 approaches (A: PBanner-only, B: PInlineNotification-only, C: dual-layer) and selected C with 0.75 confidence after challenger raised valid modal stacking concern

### Challenge Results

- Challenger: SKIPPED — proof bundle `skip`

### Proof-Bundle Validation

- Planner assignment: (none)
- Final bundle: skip
- Test-writer: SKIP

### Children Structure Notes

- #1498 and #1499 are independent implementation tasks — no cross-dependency needed
- #1500 (tests) Vitest unit-test AC overlaps with standard TDD RED phases of #1498/#1499; when children reach backlog, consider restructuring #1500 to E2E/consolidation scope only
- Recommend adding depends_on [#1498, #1499] to #1500 when reviewed

### Verdict: APPROVE
### Action Taken: Refined AC to P2/B1 verifiable criteria, added depends_on [1498, 1499, 1500], tagged `quality` for pass-through, advanced backlog → todo
2026-05-12T03:18:40+00:00
Architecture review complete. Umbrella task for PDS mutation error feedback feature. Refined broad feature-level AC to verifiable P2/B1 criteria. Added depends_on [#1498, #1499, #1500]. Tagged `quality` for pass-through. Proof bundle: skip. Challenger: skipped (bundle skip). Children structure note: #1500 Vitest AC overlaps TDD RED phases — flag for restructuring at children's review.
2026-05-12T03:25:10+00:00
## Test-Writer Notes
- Proof bundle: skip — no new test writing required.
- Also tagged `quality` (non-implementation umbrella task).
- Children #1498, #1499, #1500 carry their own TDD cycles.
- Passing through to builder.
2026-05-12T03:39:49+00:00
## Builder Notes
- Implementation: none (umbrella parent task)
- Tests: skipped per `Proof bundle: skip` and explicit Test-Writer pass-through note
- Coverage: N/A (no code changes)
- ruff: N/A (no code changes)
- Evidence summary: Task #1494 AC is orchestration-level (child-task completion + component-level adoption checks) and already decomposed into implementation children #1498, #1499, #1500. Parent body includes `Proof bundle: skip` and `Test-Writer Notes` marking this as non-implementation pass-through.
- Routing decision: Advanced parent task without code changes; implementation and GREEN verification remain on child tasks.
2026-05-12T04:06:27+00:00
## Review Evidence
- Verdict: FAIL
- Blocking findings:

| # | AC Line | Finding | Evidence | Route |
|---|---------|---------|----------|-------|
| 1 | AC-1 (P2) | Parent was advanced before its own completion gate. The refined contract requires child tasks #1498, #1499, and #1500 to reach `done`, but the board still shows `in-progress`, `research`, and `research`. Builder notes also state implementation and GREEN verification remain on child tasks. | `.owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md:61`, `.owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md:100`, `.owlbear/kanban/tasks/1498-cockpit-wire-pbanner-mutation-error-feedback-in-shell.md:4`, `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md:4`, `.owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md:4` | in-progress |
| 2 | AC-2 (B1) | Artifact inspection still shows legacy error surfaces instead of the required PDS notification components. Shell still renders plain `<div>` feedback, KanbanBoard still renders `data-testid="move-error"` in a div, and both modals still render `PText` errors. | `.owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md:62`, `serve/cockpit/web/src/Shell.tsx:225`, `serve/cockpit/web/src/Shell.tsx:230`, `serve/cockpit/web/src/KanbanBoard.tsx:333`, `serve/cockpit/web/src/components/ArchivalModal.tsx:282`, `serve/cockpit/web/src/components/ResolveModal.tsx:201` | in-progress |

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Return parent #1494 to review only after child tasks #1498, #1499, and #1500 have reached `done` and the parent AC-1 gate is actually satisfied. | `.owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md`, `.owlbear/kanban/tasks/1498-cockpit-wire-pbanner-mutation-error-feedback-in-shell.md`, `.owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md`, `.owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md` | AC-1 at `1494:61`; child statuses at `1498:4`, `1499:4`, `1500:4` |
| 2 | builder | Do not claim AC-2 complete on the parent while the UI still renders the legacy `div`/`PText` error surfaces; re-advance the parent only after child implementation lands and artifact inspection reflects `PBanner`/`PInlineNotification` adoption. | `serve/cockpit/web/src/Shell.tsx`, `serve/cockpit/web/src/KanbanBoard.tsx`, `serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx` | `1494:62`; `Shell.tsx:225`, `Shell.tsx:230`, `KanbanBoard.tsx:333`, `ArchivalModal.tsx:282`, `ResolveModal.tsx:201` |

## Observations
- Proof bundle `skip` is not the issue by itself. The blocker is that the parent's architect-refined contract explicitly ties completion to downstream task completion and artifact adoption, and the builder notes acknowledge those remain outstanding.
- No independent `quality-runner` rerun was needed because the builder evidence and direct board/code inspection already prove the parent contract is unmet.
2026-05-12T04:24:58+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (no code paths to verify at parent level)
- Coverage: N/A
- ruff: N/A
- Evidence summary: AC-1 requires child tasks #1498, #1499, #1500 to reach `done` before parent completion. Current statuses are #1498=`review`, #1499=`research`, #1500=`research`, so parent gate is structurally unreachable from builder scope.
- Routing decision: Released claim and kept parent in `in-progress` pending child completion through normal pipeline.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | reviewer | Complete review routing for child task #1498 so it can progress toward `done`. | .owlbear/kanban/tasks/1498-cockpit-wire-pbanner-mutation-error-feedback-in-shell.md | Child status currently `review` (kanban list ids [1498,1499,1500]). |
| 2 | researcher | Advance child task #1499 from `research` with concrete AC and follow-up routing through test-writer/builder pipeline. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Child status currently `research` (kanban list ids [1498,1499,1500]). |
| 3 | researcher | Advance child task #1500 from `research` with concrete AC and follow-up routing through test-writer/builder pipeline. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Child status currently `research` (kanban list ids [1498,1499,1500]). |
2026-05-12T04:41:09+00:00
## Builder Notes
- Implementation: none in this cycle (parent umbrella task)
- Tests: skipped (`Proof bundle: skip`)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current child statuses are #1498=`todo`, #1499=`research`, #1500=`research`, so the parent completion gate is structurally unreachable in builder scope.
- Verification snapshot: Artifact check confirms Shell-level `PBanner` wiring exists in `serve/cockpit/web/src/Shell.tsx`, but parent gate still depends on child task lifecycle completion per AC-1.
- Routing decision: Kept #1494 in `in-progress` and released claim.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Complete dispatch preparation and advancement for child task #1498 so it can proceed through builder/review to `done`. | .owlbear/kanban/tasks/1498-cockpit-wire-pbanner-mutation-error-feedback-in-shell.md | Child status is `todo`; AC-1 requires done-state completion of all children. |
| 2 | researcher | Advance child task #1499 from `research` with finalized AC and routing into test-writer/builder pipeline. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Child status is `research`; AC-1 dependency unmet. |
| 3 | researcher | Advance child task #1500 from `research` with finalized AC and routing into test-writer/builder pipeline. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Child status is `research`; AC-1 dependency unmet. |
2026-05-12T04:54:31+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: skipped (`Proof bundle: skip` on parent)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance.
- Current dependency snapshot: #1498=`review`, #1499=`research`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with status unchanged (`in-progress`) pending child lifecycle completion.
2026-05-12T05:05:25+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (no parent-level executable scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current board snapshot: #1498=`backlog`, #1499=`research`, #1500=`research`.
- Routing decision: Completion gate is structurally unreachable in builder scope. Released claim with FAIL routing so prerequisite child tasks can proceed first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect | Advance child task #1498 from `backlog` into actionable pipeline flow (todo -> test-writer -> builder -> review -> done). | .owlbear/kanban/tasks/1498-cockpit-wire-pbanner-mutation-error-feedback-in-shell.md | Board state snapshot: #1498 status is `backlog`; parent AC-1 requires child `done`. |
| 2 | researcher | Advance child task #1499 from `research` with finalized AC and routing into implementation pipeline. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Board state snapshot: #1499 status is `research`; parent AC-1 dependency unmet. |
| 3 | researcher | Advance child task #1500 from `research` with finalized AC and routing into implementation pipeline. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Board state snapshot: #1500 status is `research`; parent AC-1 dependency unmet. |
2026-05-12T05:10:16+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (no parent-level executable scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current board snapshot: #1498=`todo`, #1499=`research`, #1500=`research`.
- Routing decision: Completion gate is structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can proceed first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Advance child task #1498 from `todo` through RED/TDD dispatch into builder and review until it reaches `done`. | .owlbear/kanban/tasks/1498-cockpit-wire-pbanner-mutation-error-feedback-in-shell.md | Board state snapshot: #1498 status is `todo`; parent AC-1 requires child `done`. |
| 2 | researcher | Advance child task #1499 from `research` with finalized AC and routing into implementation pipeline. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Board state snapshot: #1499 status is `research`; parent AC-1 dependency unmet. |
| 3 | researcher | Advance child task #1500 from `research` with finalized AC and routing into implementation pipeline. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Board state snapshot: #1500 status is `research`; parent AC-1 dependency unmet. |
2026-05-12T05:13:59+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (no parent-level executable scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance.
- Current dependency snapshot: #1498=`review`, #1499=`research`, #1500=`research`.
- Routing decision: Completion gate is structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can proceed first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | reviewer | Complete review routing for child task #1498 so it can progress toward `done`. | .owlbear/kanban/tasks/1498-cockpit-wire-pbanner-mutation-error-feedback-in-shell.md | Board state snapshot: #1498 status is `review`; parent AC-1 requires child `done`. |
| 2 | researcher | Advance child task #1499 from `research` with finalized AC and routing into implementation pipeline. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Board state snapshot: #1499 status is `research`; AC-1 dependency unmet. |
| 3 | researcher | Advance child task #1500 from `research` with finalized AC and routing into implementation pipeline. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Board state snapshot: #1500 status is `research`; AC-1 dependency unmet. |
2026-05-12T05:26:59+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (no parent-level executable scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current board snapshot: #1498=`docs`, #1499=`research`, #1500=`research`.
- Routing decision: Completion gate is structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | doc-writer/auditor | Complete child task #1498 lifecycle from `docs` to `done`/`archived` (or equivalent terminal completion state accepted by AC governance). | .owlbear/kanban/tasks/1498-cockpit-wire-pbanner-mutation-error-feedback-in-shell.md | Parent AC-1 dependency requires child completion; current status is `docs`. |
| 2 | researcher | Advance child task #1499 from `research` with finalized AC and routing into implementation pipeline. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency unmet while status remains `research`. |
| 3 | researcher | Advance child task #1500 from `research` with finalized AC and routing into implementation pipeline. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency unmet while status remains `research`. |
2026-05-12T05:30:26+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (no parent-level executable scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`done`, #1499=`research`, #1500=`research`.
- Routing decision: Completion gate is structurally unreachable in builder scope. Released claim with FAIL routing so prerequisite child tasks can proceed first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | researcher | Advance child task #1499 from `research` with finalized AC and routing into implementation pipeline (test-writer -> builder -> review -> docs -> done). | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency unmet while #1499 remains `research`. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and routing into implementation pipeline (test-writer -> builder -> review -> docs -> done). | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency unmet while #1500 remains `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion check only after #1499 and #1500 reach `done`; then confirm AC-2 artifact adoption remains satisfied. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard done-state gate for all three children. |
2026-05-12T05:41:25+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (no parent-level executable scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance.
- Current dependency snapshot: #1498=`archived`, #1499=`research`, #1500=`research`.
- Routing decision: Completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can progress first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | researcher | Advance child task #1499 from `research` with finalized AC and route into implementation pipeline (test-writer -> builder -> review -> docs -> done). | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is `research`. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline (test-writer -> builder -> review -> docs -> done). | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 is a hard child-completion gate in parent refined AC. |
2026-05-12T05:54:22+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (no parent-level executable scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance.
- Current dependency snapshot: #1498=`archived` (completed), #1499=`backlog`, #1500=`research`.
- Routing decision: Completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can progress first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect/test-writer/builder pipeline | Advance child task #1499 from `backlog` through implementation lifecycle to terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency unmet while #1499 is not terminal-complete. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency unmet while #1500 remains `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 is a hard child-completion gate in parent refined AC. |
2026-05-12T06:11:10+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current child snapshot is #1498=`archived` (complete), #1499=`todo`, #1500=`research`.
- Routing decision: Parent completion gate is structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can proceed first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer/builder pipeline | Advance child task #1499 from `todo` through implementation lifecycle to terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency unmet while #1499 is not terminal-complete. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency unmet while #1500 remains `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 is a hard child-completion gate in parent refined AC. |
2026-05-12T06:22:43+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (complete), #1499=`in-progress`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder | Complete child task #1499 implementation and hand off through review/docs/auditor until terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is `in-progress`. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is `research`. |
| 3 | builder | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T06:33:28+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance.
- Current dependency snapshot: #1498=`archived` (completed), #1499=`todo`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer/builder pipeline | Advance child task #1499 from `todo` through implementation lifecycle to terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is `todo`. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T06:39:59+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current child snapshot: #1498=`archived` (completed), #1499=`in-progress`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder/reviewer/docs/auditor pipeline | Complete child task #1499 from `in-progress` through `review` and terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is `in-progress`. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is `research`. |
| 3 | builder | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T06:47:25+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip`)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`review`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | reviewer/docs/auditor pipeline | Complete child task #1499 from `review` through terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is not terminal-complete. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T07:06:46+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`in-progress`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder/reviewer/docs/auditor pipeline | Complete child task #1499 from `in-progress` through `review` and terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is not terminal-complete. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T07:10:45+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`review`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | reviewer/docs/auditor pipeline | Complete child task #1499 from `review` through terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is not terminal-complete. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T07:22:35+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`backlog`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect/test-writer/builder pipeline | Advance child task #1499 from `backlog` through implementation lifecycle to terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is not terminal-complete. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 remains `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T07:35:02+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`todo`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer/builder/reviewer/docs/auditor pipeline | Advance child task #1499 from `todo` through implementation lifecycle to terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is not terminal-complete. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 remains `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T08:19:46+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`review`, #1500=`research`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | reviewer/docs/auditor pipeline | Complete child task #1499 from `review` through terminal completion. | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is not terminal-complete. |
| 2 | researcher | Advance child task #1500 from `research` with finalized AC and route into implementation pipeline to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 remains `research`. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T09:12:29+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`docs`, #1500=`backlog`.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child tasks can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | doc-writer/auditor pipeline | Complete child task #1499 from `docs` through terminal completion (`done`/`archived` per board policy). | .owlbear/kanban/tasks/1499-cockpit-replace-modal-error-display-with-pinlinenotification.md | Parent AC-1 dependency remains unmet while #1499 is not terminal-complete. |
| 2 | architect/test-writer/builder pipeline | Advance child task #1500 from `backlog` through implementation/test lifecycle to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is not terminal-complete. |
| 3 | builder/reviewer | Re-run parent #1494 completion gate only after #1499 and #1500 are terminal-complete and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate. |
2026-05-12T09:40:28+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`done` (completed), #1500=`todo` (not complete).
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so the remaining prerequisite child task can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer/builder/reviewer/docs/auditor pipeline | Advance child task #1500 from `todo` through implementation/test lifecycle to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is not terminal-complete. |
| 2 | builder/reviewer | Re-run parent #1494 completion gate only after #1500 reaches terminal completion and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate; #1498/#1499 are already complete. |
2026-05-12T10:01:54+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`archived` (completed), #1500=`in-progress` (not complete).
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child task #1500 can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder/reviewer/docs/auditor pipeline | Complete child task #1500 from `in-progress` through terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is not terminal-complete. |
| 2 | builder/reviewer | Re-run parent #1494 completion gate only after #1500 reaches terminal completion and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate; #1498/#1499 are already complete. |
2026-05-12T10:46:15+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`archived` (completed), #1500=`review` (not terminal-complete).
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child task #1500 can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | reviewer/docs/auditor pipeline | Complete child task #1500 from `review` through terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is not terminal-complete. |
| 2 | builder/reviewer | Re-run parent #1494 completion gate only after #1500 reaches terminal completion and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate; #1498/#1499 are already complete. |
2026-05-12T11:25:59+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`archived` (completed), #1500=`backlog` (not terminal-complete).
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child task #1500 can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | architect/test-writer/builder/reviewer/docs/auditor pipeline | Advance child task #1500 from `backlog` through implementation/test lifecycle to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is not terminal-complete. |
| 2 | builder/reviewer | Re-run parent #1494 completion gate only after #1500 reaches terminal completion and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate; #1498/#1499 are already complete. |
2026-05-12T11:53:15+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`archived` (completed), #1500=`todo` (not terminal-complete).
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child task #1500 can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer/builder/reviewer/docs/auditor pipeline | Advance child task #1500 from `todo` through implementation/test lifecycle to terminal completion. | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is not terminal-complete. |
| 2 | builder/reviewer | Re-run parent #1494 completion gate only after #1500 reaches terminal completion and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate; #1498/#1499 are already complete. |
2026-05-12T12:33:47+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`archived` (completed), #1500=`in-progress` (not terminal-complete).
- Artifact verification: AC-2 adoption remains satisfied in code — Shell renders `PBanner` for mutation errors (`serve/cockpit/web/src/Shell.tsx`), and modal-level errors use `PInlineNotification` (`serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`).
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child task #1500 can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | builder/reviewer/docs/auditor pipeline | Complete child task #1500 from `in-progress` through terminal completion (`done`/`archived` per board policy). | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is not terminal-complete. |
| 2 | builder/reviewer | Re-run parent #1494 completion gate only after #1500 reaches terminal completion; reconfirm AC-2 artifact adoption before advancing. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate; AC-2 artifacts verified in current source files. |
2026-05-12T13:06:17+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot: #1498=`archived` (completed), #1499=`archived` (completed), #1500=`review` (not terminal-complete).
- Artifact verification: AC-2 adoption remains satisfied in code — Shell renders `PBanner` for mutation errors (`serve/cockpit/web/src/Shell.tsx`), and modal-level errors use `PInlineNotification` (`serve/cockpit/web/src/components/ArchivalModal.tsx`, `serve/cockpit/web/src/components/ResolveModal.tsx`).
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child task #1500 can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | reviewer/docs/auditor pipeline | Complete child task #1500 from `review` through terminal completion (`done`/`archived` per board policy). | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is not terminal-complete. |
| 2 | builder/reviewer | Re-run parent #1494 completion gate only after #1500 reaches terminal completion and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate; AC-2 artifacts are currently satisfied in source files. |
2026-05-12T13:37:25+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip` does not bypass AC-1 child-completion gate)
- Coverage: N/A
- ruff: N/A
- Evidence summary: Parent AC-1 requires child tasks #1498, #1499, and #1500 to reach `done` before #1494 can advance. Current dependency snapshot from kanban list: #1498=`archived` (completed), #1499=`archived` (completed), #1500=`docs` (not terminal-complete and not `done`).
- Artifact verification: AC-2 adoption remains satisfied in source (Shell-level `PBanner` and modal-level `PInlineNotification` already present), but AC-1 remains unmet.
- Routing decision: Parent completion gate remains structurally unreachable in builder scope; released claim with fail routing so prerequisite child task #1500 can complete first.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | doc-writer/auditor pipeline | Complete child task #1500 from `docs` through terminal completion (`done`/`archived` per board policy). | .owlbear/kanban/tasks/1500-cockpit-tests-for-mutation-error-banner-and-inline-notification.md | Parent AC-1 dependency remains unmet while #1500 is `docs`. |
| 2 | builder/reviewer | Re-run parent #1494 completion gate only after #1500 reaches terminal completion and AC-2 artifact checks are reconfirmed. | .owlbear/kanban/tasks/1494-cockpit-add-pds-banner-for-mutation-error-feedback.md | AC-1 in parent body is a hard child-completion gate; #1498/#1499 are already complete. |
2026-05-12T14:33:44+00:00
## Builder Notes
- Implementation: none (umbrella parent task; no direct source changes)
- Tests: not run (parent-level non-implementation scope; `Proof bundle: skip`)
- Coverage: N/A
- ruff: N/A
- Evidence summary:
  - AC-1 child-completion gate is now satisfied by board state: #1498=`archived` (completed), #1499=`archived` (completed), #1500=`done` (completed).
  - AC-2 artifact adoption remains satisfied in source:
    - Shell-level mutation feedback uses `PBanner` in `serve/cockpit/web/src/Shell.tsx`.
    - Modal-level mutation feedback uses `PInlineNotification` in `serve/cockpit/web/src/components/ArchivalModal.tsx` and `serve/cockpit/web/src/components/ResolveModal.tsx`.
- Routing decision: Parent #1494 completion gate is now reachable and satisfied; advanced to review.
2026-05-12T15:05:12+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1494 to docs | AC mapped to code and evidence sufficient.
- AC evidence map:

| AC Line | Code / Board Evidence | Test / Proof Evidence | Status |
|---|---|---|---|
| AC-1 (P2) | Current kanban snapshot for child tasks 1498, 1499, and 1500 shows all three in archived status with archival_reason `completed`, which is terminal completion beyond the parent gate. | Parent proof bundle is `skip`; the parent contract uses child lifecycle completion as its proof surface. | PASS |
| AC-2 (B1) | `PBanner` is rendered in `serve/cockpit/web/src/Shell.tsx:232`; `PInlineNotification` is rendered in `serve/cockpit/web/src/components/ArchivalModal.tsx:310` and `serve/cockpit/web/src/components/ResolveModal.tsx:237`. | Direct artifact inspection of the current source matches the architect-refined component-adoption contract. | PASS |
- Blocking findings: none.

## Observations
- The builder snapshot recorded child task 1500 at `done`; current board state has since advanced it to `archived` with archival_reason `completed`, so the gate is now strictly stronger than the builder snapshot and still satisfied.
- No independent quality-runner rerun was needed. The parent task has `Proof bundle: skip`, no parent-level code changes, and the builder evidence became sufficient after direct board and source verification.
2026-05-12T15:53:26+00:00
## Docs Gate

### Checklist

**Item 1: README Verification**
N/A — umbrella parent task; all builder notes confirm "Implementation: none (umbrella parent task; no direct source changes)". Code changes were made entirely in child tasks #1498, #1499, #1500 through their own pipeline stages including individual docs gates. `serve/cockpit/README.md` describes stack/launch/API surface — no implementation-level error-display detail belongs there; no update needed.

**Item 2: External Attribution**
PASS — `.owlbear/sources/overview.md` already contains 4 entries for external PDS sources (PDS Banner API, PDS Inline Notification API, PDS Notification Patterns, PDS Notification Decision Tree) all linked to `.owlbear/research/cockpit-mutation-error-banner.md`. Local sources (codebase, node_modules) require no external attribution.

**Item 3: Research Doc**
PASS — Research doc `.owlbear/research/cockpit-mutation-error-banner.md` exists and is explicitly linked in the task body ("Research doc: .owlbear/research/cockpit-mutation-error-banner.md").

**Item 4: Deletion Detection**
N/A — No file deletions at parent task level; umbrella task had no direct source changes.

### Files Updated
None — no docs impact from parent-level task scope.

### Scratch Cleanup
No `1494-*` scratch files found.
2026-05-12T16:28:05+00:00
## Audit\n### Regression Detection\n- quality-runner mode full: pytest 4418 passed / 208 failed, vitest 1375 passed / 138 failed, ruff clean, eslint 1 violation\n- All failures are pre-existing background debt — umbrella parent task made zero direct code changes; all three children (#1498, #1499, #1500) passed their own full pipeline audits before archival\n- ESLint violation (`selectedDRId` unused in Shell.tsx) belongs to a separate DR feature, not this task scope\n- regression verdict: PASS (no task-attributed regressions)\n\n### Intent Verification\n- scope alignment: PASS (umbrella parent correctly delegates implementation to children; no extraneous scope)\n- purpose match: PASS (AC-1 child-completion gate verified: #1498=archived/completed, #1499=archived/completed, #1500=archived/completed; AC-2 artifact adoption verified: PBanner in Shell.tsx, PInlineNotification in ArchivalModal.tsx and ResolveModal.tsx)\n- extraneous scope: none\n- boundary check: function-level behavior verification deferred to reviewer\n\n### Architect Quality: 4/5\n- Original AC was feature-level and needed refinement, but the architect cleanly refined to P2/B1 verifiable criteria and decomposed into 3 focused children with appropriate parent/child structure\n- Challenge: confirmed PDS modal stacking concern justified dual-layer approach\n- Minor gap: original AC could have been written at P2/B1 level from the start, requiring fewer pipeline round-trips\n\n### Commit Integrity\n- upstream commit presence: PASS (#1498: 374bef91, 51fbd12e, e691ffd3; #1499: 253b3d2a, 09110656, 48fa5e8d; #1500: 08f14137; archival commits: 761c8ab0, 52f8c84e, 7f678dee)\n- kanban commit packaging: pending (this audit cycle)\n\n### Deduction Breakdown\nNo deductions applied.\n- Regression: 0 (no task-attributed regressions)\n- Intent mismatch: 0\n- Evidence integrity: 0\n- Lint violations: 0 (not attributable to task scope)\n- AC quality ≤3: not applicable (score=4)\n- Missing reviewer evidence: 0 (present and detailed)\n\n### Confidence: 1.00\n### Action: archive