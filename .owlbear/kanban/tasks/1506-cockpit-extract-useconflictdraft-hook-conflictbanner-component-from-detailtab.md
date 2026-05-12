---
id: 1506
title: 'Cockpit: Extract useConflictDraft hook + ConflictBanner component from DetailTab'
status: in-progress
priority: needed
created: 2026-05-12T03:04:43.984524+00:00
updated: 2026-05-12T09:40:13.229648+00:00
tags:
  - cockpit
  - frontend
  - refactor
parent: 1492
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Extract conflict-detection state and UI from DetailTab.tsx into two focused modules (~120 LOC total).

## Scope
- **useConflictDraft.ts** (hooks/): manages conflictLocalDraft, conflictRemoteTask, showConflict, showConflictOverwrite, conflictChangedFields, conflictRemoteValues/conflictLocalValues
- **ConflictBanner.tsx** (components/): conflict diff display, acknowledge/discard/force-save buttons

Parent: #1492 — DetailTab decomposition

## Acceptance Criteria
- [ ] `useConflictDraft.ts` exists in `hooks/` and exports the hook
- [ ] `ConflictBanner.tsx` exists in `components/` and renders conflict diff + action buttons
- [ ] `DetailTab.tsx` imports and delegates to both new modules
- [ ] All 7 existing DetailTab test files pass unchanged
- [ ] No new lint warnings from ESLint or Stylelint
2026-05-12T08:28:18+00:00
## Research
- Research doc: .owlbear/research/cockpit-conflict-hook-extraction.md
- Sources: 6 studied, 4 high-relevance (DetailTab.tsx, useRepairFlow/useCleanupFlow patterns, conflict test files)
- Recommendation: Extract using action-function pattern (not raw setters), matching useRepairFlow/useCleanupFlow precedent — confidence 0.88
- T1 classification — pure refactoring, no architectural change
- Follow-up tasks: none needed — #1506 is the implementation task, siblings #1507/#1508 exist
- Decision requests: none

## Challenge Results
- Challenge: skipped — T1 pure refactoring, no option selection, established in-repo patterns
- Key findings: useEffect boundary split (field-restore vs conflict-cleanup) is the main implementation subtlety; hook exposes clearConflictIfTaskChanged(taskId) action for DetailTab's effect to call; ConflictBanner preserves all data-testid attributes for zero test impact
2026-05-12T09:26:37+00:00

## Refined Acceptance Criteria
_Supersedes original AC section._

- AC-1 (B1): `hooks/useConflictDraft.ts` exports `useConflictDraft` hook returning conflict state (`showConflict`, `showConflictOverwrite`, `conflictLocalDraft`, `conflictRemoteTask`, `conflictChangedFields`, `conflictRemoteValues`, `conflictLocalValues`) and action functions (`setConflictDetected`, `clearConflict`, `acknowledgeOverwrite`, `dismissConflict`, `clearConflictIfTaskChanged`). `ConflictLocalDraft` interface defined in or re-exported from the hook module.
- AC-2 (B1): `components/ConflictBanner.tsx` accepts conflict state via props and renders conflict diff display with action buttons. Preserves data-testid attributes: `conflict-modal`, `conflict-acknowledge`, `conflict-refresh`, `conflict-overwrite`, and per-field pairs `conflict-remote-{f}` / `conflict-local-{f}` for fields `title`, `priority`, `body`, `depends_on`, `parent`, `block_reason`.
- AC-3 (B1): `DetailTab.tsx` imports `useConflictDraft` from `hooks/useConflictDraft` and renders `ConflictBanner` from `components/ConflictBanner`, replacing inline conflict state declarations, computed values, and conflict JSX.
- AC-4 (B2): 8 existing DetailTab test files pass without modification: `DetailTab.test.tsx`, `DetailTab.valid-edits.test.tsx`, `DetailTab.invalid-parent.test.tsx`, `DetailTab.edit-payload.test.tsx`, `DetailTab.conflict-resolution.test.tsx`, `DetailTab.conflict-nonregression.test.tsx`, `DetailTab.pbanner-1498.test.tsx`, `DetailTab.gfm-plugins.test.tsx`.
- AC-5: No new ESLint or Stylelint warnings — verified by `npm run lint` and `npm run lint:css` in `serve/cockpit/web/`.

Proof bundle: existing
Existing proof scope: `serve/cockpit/web/src/__tests__/DetailTab*.test.tsx` (8 files enumerated in AC-4)

## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Extracts one concern (conflict state + UI) into two modules |
| Interface clarity | PASS | Hook return type and component props specified in AC-1/AC-2; data-testid attrs enumerated |
| Dependency correctness | PASS | Removed #1493 dep (see notes below); siblings #1507/#1508 retain it |
| Module layering | PASS | hooks/ and components/ follow established useRepairFlow/useCleanupFlow and RepairPanel/CleanupPanel patterns |
| TDD compliance | PASS | 8 existing test files serve as regression gate via `existing` proof bundle |
| KISS/YAGNI | PASS | Pure extraction, no new abstractions or features |
| Premise challenge | PASS | 634-LOC monolith with 5 scattered conflict zones (~94 LOC) — extraction justified |
| Pattern consistency | PASS | Action-function pattern matches useRepairFlow (92 LOC) and useCleanupFlow (69 LOC) |
| Security surface | N/A | No new system boundaries |
| Single domain | PASS | Frontend component domain |

### Dependency Override: #1493 Removed
Original planning sequenced #1493 (API centralization) before all three extraction tasks to avoid double-refactoring churn. Analysis shows this concern applies to #1507 (wraps `runMutation` which contains fetch calls) and #1508 (container reduction touching mutation paths), but NOT to #1506: the conflict hook manages `useState`/`useMemo` state only — zero fetch calls, zero API surface. Removing the dependency unblocks #1506 while #1493's children (#1501-#1503) complete their pipeline. Siblings #1507 and #1508 retain their #1493 dependency.

### Proof-Bundle Validation
- Planner assignment: none (research classified as T1)
- Final bundle: existing
- Existing proof scope: `serve/cockpit/web/src/__tests__/DetailTab*.test.tsx` (8 files)
- Test-writer: SKIP (bundle `existing`)

### Challenge Results
- Challenger: reconsider (0.67)
- Findings: (1) ac-quality: behavioral lock gaps — rebutted: AC-4 gates on 8 tests that already cover async-gap, dismiss-preservation, 409→404 paths; (2) ac-quality: field enumeration — accepted, AC-2 refined with exact 6 fields; (3) proof-scope: 7→8 drift — accepted, corrected; (4) dependency: planning override — accepted, documented reasoning above; (5) consolidation-test-gap: no explicit consolidation task — noted: sequential chain + identical 8-test gate on each child + #1508 as final composition verifier + parent #1492 tracker provides sufficient coverage
- Architect response: accepted items 2/3, rebutted 1, documented override reasoning for 4, justified coverage for 5

### Design Diverge
- Trigger: skipped — single valid approach (action-function pattern matching useRepairFlow/useCleanupFlow precedent), no competing designs

### Implementation Guidance
- useEffect at L89-109 mixes field-restore (stays in DetailTab) and conflict-cleanup (moves to hook). Hook exposes `clearConflictIfTaskChanged(taskId)` action; DetailTab's effect reads `conflictLocalDraft` for field restoration, then delegates cleanup to the hook action.
- `runMutation` coupling: hook exposes focused action functions, not raw setters. `runMutation` stays in DetailTab (moves to #1507 scope).
- ConflictBanner must render at the same DOM position to preserve test selectors.

### Verdict: APPROVE
### Action Taken: Refined AC (enumerated fields, corrected test count 7→8, added verification method for lint, numbered AC lines), removed #1493 dependency with documented reasoning, assigned proof bundle `existing` with 8-file scope, advanced to todo.

2026-05-12T09:26:43+00:00
Architecture review complete. REFINE + APPROVE: Refined AC (corrected test count 7→8, enumerated 6 conflict fields in AC-2, added lint verification method in AC-5, numbered AC lines per h-ac-quality). Removed #1493 dependency — conflict hook has zero API surface; churn concern applies to siblings #1507/#1508 only. Proof bundle: existing (8 DetailTab*.test.tsx files). Challenger: reconsider (0.67) — accepted field enumeration + proof-scope corrections, rebutted behavioral-lock gap (AC-4 gates on tests that already cover those paths), documented dependency override. Test-writer: SKIP.
2026-05-12T09:40:13+00:00
## Test-Writer Notes
- Proof bundle: existing — no new test writing required.
- Existing proof scope: `serve/cockpit/web/src/__tests__/DetailTab*.test.tsx` (8 files per AC-4).
- Passing through to builder.