---
id: 1507
title: 'Cockpit: Extract useTaskMutation hook + TaskActions component from DetailTab'
status: in-progress
priority: needed
created: 2026-05-12T03:04:44.023243+00:00
updated: 2026-05-12T09:41:31.815193+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1492
depends_on:
  - 1506
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Extract mutation orchestration and action buttons from DetailTab.tsx into two focused modules (~130 LOC total).

## Scope
- **useTaskMutation.ts** (hooks/): wraps runMutation + previousStatus + serverValidationMessage management
- **TaskActions.tsx** (components/): unclaim/unblock/move-backward buttons + ConfirmDialog wiring

Parent: #1492 — DetailTab decomposition

## Acceptance Criteria
- [ ] `useTaskMutation.ts` exists in `hooks/` and exports the hook
- [ ] `TaskActions.tsx` exists in `components/` and renders action buttons with ConfirmDialog
- [ ] `DetailTab.tsx` imports and delegates to both new modules
- [ ] All 7 existing DetailTab test files pass unchanged
- [ ] No new lint warnings from ESLint or Stylelint
2026-05-12T08:56:35+00:00
## Research
- Research doc: .owlbear/research/cockpit-mutation-hook-extraction.md
- Sources: 6 studied, 4 high-relevance (DetailTab.tsx, useRepairFlow/useCleanupFlow patterns, #1506 research, ConfirmDialog)
- Recommendation: Extract using action-callback pattern for conflict coupling, matching useRepairFlow/useCleanupFlow precedent — confidence 0.88
- T1 classification — pure refactoring, no architectural change
- Follow-up tasks: none needed — #1507 is the implementation task, sibling #1508 exists
- Decision requests: none

## Challenge Results
- Challenge: skipped — T1 pure refactoring, no option selection, established in-repo patterns
- Key findings: runMutation couples to conflict state via 3 action callbacks (clearConflict, setConflictDetected, setConflictDetectedNoRefetch); TaskActions owns confirmType state + focus management + ConfirmDialog wiring; ~80 LOC each
2026-05-12T08:56:42+00:00
Research complete. Identified precise extraction boundaries for useTaskMutation hook (~80 LOC: serverValidationMessage state, previousStatus function, runMutation with conflict action callbacks) and TaskActions component (~80 LOC: confirmType state, focus management, 3 action buttons, ConfirmDialog wiring). T1 pure refactoring following established patterns. Confidence 0.88. Doc: .owlbear/research/cockpit-mutation-hook-extraction.md
2026-05-12T09:39:09+00:00


## Refined Acceptance Criteria
_Supersedes original AC section._

- AC-1 (B1): `hooks/useTaskMutation.ts` exports `useTaskMutation` hook accepting `UseTaskMutationOptions` (taskId, taskUpdated, board, conflictActions: {clearConflict, setConflictDetected, setConflictDetectedNoRefetch}, onTaskUpdated, onTaskCleared, onMutationError). Returns `UseTaskMutationResult`: `serverValidationMessage`, `setServerValidationMessage`, `previousStatus(current: string) → string | null`, `runMutation(url, payload, options) → Promise<void>`.
- AC-2 (B1): `components/TaskActions.tsx` exports `TaskActions` component accepting `TaskActionsProps` (task, backwardTarget, runMutation). Renders conditionally: move-backward button (`data-testid="move-backward"`) when `backwardTarget` is non-null, unclaim button (`data-testid="unclaim-action"`) when `task.claimed !== false`, unblock button (`data-testid="unblock-action"`) when `task.blocked`. Owns `confirmType` state, focus management (`pendingFocusRestore`, `confirmTriggerRef`), focus-restore useEffect, and renders `ConfirmDialog`.
- AC-3 (B1): `DetailTab.tsx` imports `useTaskMutation` from `hooks/useTaskMutation` and renders `<TaskActions>` from `components/TaskActions`. DetailTab no longer contains inline definitions of: `serverValidationMessage` state, `confirmType` state, `pendingFocusRestore`/`confirmTriggerRef` refs, focus-restore useEffect, `previousStatus` function, `runMutation` function, `handleConfirm`/`handleConfirmCancel`/`openConfirm` handlers, action button JSX, or ConfirmDialog JSX.
- AC-4 (B2): Full Vitest suite passes without modification — verified by `npm test` in `serve/cockpit/web/`.
- AC-5: No new warnings from ESLint (`npx eslint src/`) or Stylelint (`npm run lint:css`) in `serve/cockpit/web/`.

Proof bundle: existing
Existing proof scope: Full Vitest suite (`npm test` in `serve/cockpit/web/`)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extracts one concern (mutation orchestration + action UI) into two focused modules |
| Interface clarity | PASS | Hook return type and component props specified in AC-1/AC-2; data-testid attrs and visibility conditions enumerated |
| Dependency correctness | PASS | Removed #1493 dep (see notes below); retains #1506 for sequential extraction |
| Module layering | PASS | hooks/ and components/ follow established useRepairFlow/useCleanupFlow and RepairPanel/CleanupPanel patterns; hook returns functions, component receives via props — no circular deps |
| TDD compliance | PASS | Full Vitest suite serves as regression gate via `existing` proof bundle |
| KISS/YAGNI | PASS | Pure extraction, no new abstractions or features |
| Premise challenge | PASS | 634-LOC monolith with ~191 LOC across 11 mutation/action zones — extraction follows established useRepairFlow/useCleanupFlow precedent |
| Pattern consistency | PASS | Action-function pattern matches useRepairFlow (88 LOC) and useCleanupFlow (51 LOC); TaskActions follows ConfirmDialog/RepairPanel component patterns |
| Security surface | N/A | No new system boundaries; same fetch calls and error handling move unchanged |
| Single domain | PASS | Frontend component domain |

### Dependency Override: #1493 Removed
Original planning sequenced #1493 (API centralization) before extraction tasks to avoid double-refactoring churn. Analysis: `useTaskMutation` wraps `runMutation` which contains raw `fetch()`. The extraction boundary is identical whether fetch is raw or centralized — same code moves to a new file unchanged. When #1503 eventually migrates consumers, it updates `useTaskMutation.ts` instead of `DetailTab.tsx` — same work, different file, zero churn. Same reasoning applied when #1506 removed its #1493 dependency. Sibling #1508 retains #1493 dependency as the final composition step.

### Proof-Bundle Validation
- Planner assignment: none (research classified as T1)
- Final bundle: existing
- Existing proof scope: Full Vitest suite (`npm test` in `serve/cockpit/web/`) — widened from 8 DetailTab tests per challenger finding that PdsMigration, ErrorContract, and KeyboardA11y suites also exercise extracted zones
- Test-writer: SKIP (bundle `existing`)

### Challenge Results
- Challenger: reconsider (0.58)
- Findings: (1) ac-quality: AC-1/AC-2 fail B2 — rebutted: behavior-preserving extraction verified by full test suite, adding behavioral AC duplicates test coverage; (2) ac-quality: AC-2 missing visibility conditions — accepted, added conditional rendering rules; (3) ac-quality: AC-3 implementation-diff — accepted, reframed as structural absence verification; (4) ac-quality: AC-4 proof scope too narrow — accepted, widened to full Vitest suite; (5) ac-quality: AC-5 wrong lint command — accepted, corrected to `npx eslint src/` and `npm run lint:css`; (6) consolidation-test-gap — rebutted: sequential chain + full-suite gate on each child + #1508 as final verifier + parent #1492 tracker = sufficient coverage; (7) reasoning-gap: dependency removal — documented above, structural code motion not interface creation; (8) blind spots: task-change reset behavior and focus ownership — accepted, added implementation guidance below
- Architect response: accepted items 2/3/4/5/8, rebutted 1/6, documented reasoning for 7

### Design Diverge
- Trigger: skipped — single valid approach (action-callback pattern matching useRepairFlow/useCleanupFlow precedent), no competing designs

### Implementation Guidance
- **Task-change reset split:** The useEffect at L86-109 mixes field-restore logic (stays in DetailTab — reads conflict state for field restoration) and mutation-state resets (`setServerValidationMessage(null)`, `setConfirmType(null)`). The hook should handle its own reset (clear serverValidationMessage on taskId/updated changes) and TaskActions should reset confirmType via a prop-driven effect or the hook can expose a resetMutationState action that DetailTab calls.
- **Focus ownership:** TaskActions owns `confirmType` state, `pendingFocusRestore` state, `confirmTriggerRef`, and focus-restore useEffect. ConfirmDialog has its own internal focus management (captures/restores on mount/unmount). These are two separate layers — TaskActions handles the trigger→restore cycle, ConfirmDialog handles trap→release.
- **ConflictBanner** rendering stays at same DOM position in DetailTab (from #1506 scope), not moved to TaskActions.

### Verdict: APPROVE
### Action Taken: Refined AC (numbered per h-ac-quality, added visibility conditions, corrected lint commands, widened proof scope to full Vitest suite), removed #1493 dependency with documented reasoning, assigned proof bundle `existing`, added implementation guidance for reset/focus ownership. Advanced to todo.
2026-05-12T09:39:16+00:00
Architecture review complete. REFINE + APPROVE: Refined AC (numbered per h-ac-quality, added button visibility conditions in AC-2, reframed AC-3 as structural absence check, widened proof scope from 8 DetailTab tests to full Vitest suite per challenger finding, corrected lint commands in AC-5). Removed #1493 dependency — extraction is structural code motion, boundary identical whether fetch is raw or centralized. Proof bundle: existing (full Vitest suite). Challenger: reconsider (0.58) — accepted 5 of 8 findings (visibility conditions, structural AC reframe, proof scope widening, lint command fix, implementation guidance for reset/focus split), rebutted behavioral-lock gap and consolidation-test gap. Test-writer: SKIP.
2026-05-12T09:41:31+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: Full Vitest suite (`npm test` in `serve/cockpit/web/`) covers all extracted zones (DetailTab, PdsMigration, ErrorContract, KeyboardA11y suites).
- Passing through to builder.