---
id: 1500
title: 'Cockpit: Tests for mutation error banner and inline notification'
status: archived
priority: needed
created: 2026-05-12T02:38:27.742252+00:00
updated: 2026-05-12T14:45:28.171665+00:00
tags:
  - cockpit
  - frontend
  - testing
  - test
parent: 1494
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Objective
Add Vitest unit tests for the new PDS notification components.

## Acceptance Criteria
- AC-1: Vitest — `Shell.pbanner-1498.test.tsx` confirms PBanner appears on simulated move/edit failure, correct `state` prop, dismiss clears `bannerError`
- AC-2: Vitest — `Shell.pbanner-1498.test.tsx` confirms PBanner auto-clears on next successful mutation (`onMutationSuccess` / `onTaskUpdated`)
- AC-3: Vitest — `Shell.pbanner-1498.test.tsx` confirms PBanner survives `selectedTaskId` change (tab switch, task selection)
- AC-4: Vitest — `PInlineNotification.modal-1499.test.tsx` confirms PInlineNotification appears in ArchivalModal on failure, retry action works
- AC-5: Vitest — `PInlineNotification.modal-1499.test.tsx` confirms PInlineNotification appears in ResolveModal on failure

## Source
Research doc: .owlbear/research/cockpit-mutation-error-banner.md (task #1494)
Playwright E2E coverage extracted to #1509.

## Planning

Single follow-up task created (single-task shortcut — no TDD pair needed for a standalone E2E test task at research status).

| ID | Title | Status | Priority | Parent | Tags |
|----|-------|--------|----------|--------|------|
| #1509 | Cockpit: Playwright E2E test for mutation error banner | research | nice-to-have | #1494 | cockpit, frontend, testing |

All 5 Vitest AC items from #1500 are already covered by existing suites (56 tests passing). Only the Playwright E2E gap remains, captured in #1509.

## Research
- Research doc: .owlbear/research/cockpit-mutation-error-tests.md
- Sources: 7 studied, 5 high-relevance (all codebase)
- Recommendation: All Vitest ACs already covered (56 passing tests from #1498/#1499); one follow-up for Playwright E2E gap (confidence: 0.88)
- Follow-up: #1509 — Playwright E2E test for mutation error banner (at research, nice-to-have)

## Architecture Review (cycle 1)

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1: PBanner on move/edit failure, state prop, dismiss | PASS — covered by Shell.pbanner-1498.test.tsx | None |
| AC-2: PBanner auto-clears on success | PASS — covered by Shell.pbanner-1498.test.tsx AC-6/AC-7 | None |
| AC-3: PBanner survives selectedTaskId change | PASS — covered by Shell.pbanner-1498.test.tsx AC-8 | None |
| AC-4: PInlineNotification in ArchivalModal, retry | PASS — covered by PInlineNotification.modal-1499.test.tsx AC-1/AC-3 | None |
| AC-5: PInlineNotification in ResolveModal | PASS — covered by PInlineNotification.modal-1499.test.tsx AC-2 | None |
| AC-6: Playwright E2E banner test | SPLIT — extracted to #1509 | Excluded from scope |

### Verdict: APPROVE (cycle 1)

## Test-Writer Notes
- Non-implementation task (tagged `test`) — no tests applicable.
- Proof bundle: existing — no new test writing required.
- All 5 Vitest ACs pre-satisfied by #1498/#1499 TDD cycles (64 tests across 4 files: Shell.pbanner-1498.test.tsx, KanbanBoard.pbanner-1498.test.tsx, DetailTab.pbanner-1498.test.tsx, PInlineNotification.modal-1499.test.tsx).
- Playwright E2E gap correctly extracted to #1509.
- Passing through to builder.

## Builder Notes
- Implementation: none (non-implementation pass-through task; proof bundle existing)
- Files changed: none
- Tests: 64 passed, 0 failed, 0 skipped
- Coverage: not required/measured for this proof-bundle-existing pass-through
- Lint: clean (eslint scoped run)
- Evidence summary:
  - Ran required existing proof files via quality-runner:
    - serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx (13 passing)
    - serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx (9 passing)
    - serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx (8 passing)
    - serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx (34 passing)
  - Scoped lint over those tests and related sources (Shell.tsx, KanbanBoard.tsx, components/DetailTab.tsx): clean
- Approach: validated architect/test-writer "Proof bundle: existing" requirement directly through quality-runner and advanced without code edits.

## Review Evidence (cycle 1)
- Verdict: FAIL
- FAIL #1500 -> backlog | AC-6 still requires Playwright E2E proof, but the task was advanced as an existing-proof pass-through and the split follow-up #1509 remains only at research.
- Required follow-up: Reconcile #1500 AC with scope split — remove Playwright AC from #1500.

## Architecture Review (cycle 2)

### Reviewer Feedback Resolution
Reviewer correctly identified that AC-6 (Playwright E2E) was split to #1509 during cycle 1 but left in #1500's AC, creating an unsatisfiable contract. Fix: removed AC-6 from AC section; added cross-reference to #1509 in Source section.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1: PBanner on move/edit failure, state prop, dismiss | PASS — covered by Shell.pbanner-1498.test.tsx (6 tests) | None |
| AC-2: PBanner auto-clears on success | PASS — covered by Shell.pbanner-1498.test.tsx (2 tests) | None |
| AC-3: PBanner survives selectedTaskId change | PASS — covered by Shell.pbanner-1498.test.tsx (2 tests) | None |
| AC-4: PInlineNotification in ArchivalModal, retry | PASS — covered by PInlineNotification.modal-1499.test.tsx (~10 tests) | None |
| AC-5: PInlineNotification in ResolveModal | PASS — covered by PInlineNotification.modal-1499.test.tsx (6 tests) | None |

### Evaluation

| Criterion | Assessment |
|-----------|-----------|
| Single responsibility | PASS — Vitest verification only |
| Interface clarity | PASS — AC names components + test files + behaviors |
| Dependency correctness | PASS — #1498 (archived), #1499 near-terminal |
| TDD compliance | N/A — this IS the test task |
| KISS/YAGNI | PASS — no new code needed |
| Pattern consistency | PASS — existing tests use project patterns |
| Security surface | PASS — no new system boundaries |
| Single domain | PASS — frontend testing only |

### Proof-Bundle Validation
- Planner assignment: (none)
- Final bundle: `existing`
- Existing proof scope: `serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx`, `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`
- Test-writer: SKIP
- Challenger: SKIPPED (bundle `existing`)

### Verdict: APPROVE (cycle 2)
AC-6 removed (Playwright E2E extracted to #1509). Remaining 5 Vitest ACs have pre-existing proof from #1498/#1499 TDD cycles. Proof bundle: existing. Tagged `test` for pass-through.
2026-05-12T11:32:41+00:00
Architecture review cycle 2 complete. Removed AC-6 (Playwright E2E) from contract — correctly extracted to #1509. Remaining 5 Vitest ACs have existing proof from #1498/#1499 TDD cycles. Proof bundle: existing. Tagged `test` for pass-through.
2026-05-12T12:00:23+00:00
## Test-Writer Notes (cycle 2)
- Non-implementation task (tagged `test`) — no new tests applicable.
- Proof bundle: existing — AC-1 through AC-5 all pre-satisfied by #1498/#1499 TDD cycles.
- Retry cycle: reviewer's cycle 1 FAIL was a scope-contract gap (AC-6 Playwright E2E not properly extracted). Architect resolved in cycle 2 by removing AC-6 from the AC section. No test-writing gap identified.
- Existing proof files (64 tests passing):
  - `serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx` (13)
  - `serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx` (9)
  - `serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx` (8)
  - `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx` (34)
- Passing through to builder.
2026-05-12T12:41:06+00:00
## Builder Notes
- Implementation: none (non-implementation pass-through task; proof bundle `existing`)
- Files changed: none
- Tests: 64 passed, 0 failed, 0 skipped
  - `src/__tests__/Shell.pbanner-1498.test.tsx`: 13 passed
  - `src/__tests__/KanbanBoard.pbanner-1498.test.tsx`: 9 passed
  - `src/__tests__/DetailTab.pbanner-1498.test.tsx`: 8 passed
  - `src/__tests__/PInlineNotification.modal-1499.test.tsx`: 34 passed
- Coverage: not required/measured for this proof-bundle-existing pass-through
- Lint: clean (scoped eslint)
- Evidence summary:
  - Ran required existing proof files through quality-runner (Vitest): all green
  - Ran scoped eslint on proof files plus related sources (`Shell.tsx`, `KanbanBoard.tsx`, `components/DetailTab.tsx`, `components/ArchivalModal.tsx`, `components/ResolveModal.tsx`): clean
- Fixes applied: none required
2026-05-12T13:26:54+00:00
## Review Evidence
- Verdict: PASS
- PASS confirmation: PASS #1500 -> docs | AC mapped to code and existing-proof evidence sufficient.
- Builder evidence reviewed first: proof bundle `existing`; builder reported 64 passed / 0 failed / 0 skipped across `serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx`, `serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx`, `serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx`, and `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx`, with scoped eslint clean.

| AC Line | Code Evidence | Test Evidence | Status |
|---|---|---|---|
| AC-1 | `serve/cockpit/web/src/Shell.tsx:41,62-67,232-237` binds `bannerError` into `PBanner`; failure producers feed the callback from `serve/cockpit/web/src/KanbanBoard.tsx:165,219` and `serve/cockpit/web/src/hooks/useTaskMutation.ts:115,124` | `serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx:222,240,268,289` verifies render/state/dismiss; `serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx:153,196` and `serve/cockpit/web/src/__tests__/DetailTab.pbanner-1498.test.tsx:179,195` verify move/edit failure callbacks | PASS |
| AC-2 | `serve/cockpit/web/src/Shell.tsx:66-67,276,281` clears the banner on `onMutationSuccess` and `onTaskUpdated` | `serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx:319,341` verifies both clear paths; `serve/cockpit/web/src/__tests__/KanbanBoard.pbanner-1498.test.tsx:266` verifies successful move emits `onMutationSuccess` | PASS |
| AC-3 | `serve/cockpit/web/src/Shell.tsx:60,81-82,266,302` selection/tab-change paths do not clear `bannerError`; clear sites remain the explicit success/dismiss handlers | `serve/cockpit/web/src/__tests__/Shell.pbanner-1498.test.tsx:363,381` verifies banner persistence across task selection and tab switch | PASS |
| AC-4 | `serve/cockpit/web/src/components/ArchivalModal.tsx:218,224,237,243,319,322,324` records failure state, exposes retry, and renders retryable `PInlineNotification` | `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:193,292,417,612,707` verifies failure render, propagated detail, retry affordance/loading, and successful retry clear | PASS |
| AC-5 | `serve/cockpit/web/src/components/ResolveModal.tsx:69,86,246,249,251` records failure state, exposes retry when retryable, and renders `PInlineNotification` | `serve/cockpit/web/src/__tests__/PInlineNotification.modal-1499.test.tsx:314,389` verifies failure rendering across status cases and propagated detail | PASS |

- Safety & security: no new code or dependency changes in this task; reviewed UI error-handling paths only, with no new injection, credential, or storage risk introduced in scope.

## Observations
- Non-blocking: the `onTaskUpdated` half of AC-2 is proved at the Shell callback boundary, not by a separate successful DetailTab mutation test. That is adjacent coverage debt rather than a blocker for #1500 because this task's AC names Shell callback handling as the contract.
2026-05-12T13:44:07+00:00
## Docs Gate

**Verdict: PASS — no docs impact**

### Checklist

| Item | Result | Evidence |
|------|--------|----------|
| 1. README Verification | N/A | Builder changed no files (proof bundle: existing pass-through). No README target triggered. |
| 2. External Attribution | N/A | All 7 sources are codebase-internal. No external attribution needed. |
| 3. Research Doc | PASS | `.owlbear/research/cockpit-mutation-error-tests.md` exists and linked in task body under `## Research`. |
| 4. Deletion Detection | N/A | No files deleted. No orphaned references possible. |

### Files Updated
None — no docs changes required.

### Scratch Cleanup
No `.owlbear/scratch/1500-*` files found.
2026-05-12T14:45:28+00:00
## Audit
### Regression Detection
- quality-runner mode full: Vitest 0 failures (frontend domain — relevant); Python 202 pre-existing failures unrelated to this zero-change pass-through task; ruff clean; eslint clean
- regression verdict: PASS

### Intent Verification
- scope alignment: PASS (task verifies existing frontend tests from #1498/#1499 — no file changes, proof bundle existing)
- purpose match: PASS (all 5 Vitest ACs verified against existing test files in cockpit domain)
- extraneous scope: none
- boundary check: function-level behavior verification deferred to reviewer

### Architect Quality: 4/5
AC-1 through AC-5 well-specified (test file, behavior, component/prop). Cycle 1 left AC-6 (Playwright E2E) in scope despite being split to #1509 — caught by reviewer. Cycle 2 corrected properly. Minor gap, adequately resolved.

### Commit Integrity
- upstream commit presence: PASS (researcher: 08f14137 research doc; builder/test-writer: N/A — proof bundle existing, no new files)
- kanban commit packaging: pending (post-archival)

### Deduction Breakdown
No deductions applied.

### Confidence: 1.00
### Action: archive