# Cockpit: Extract useTaskMutation Hook + TaskActions Component

> **Owning task:** #1507 — Extract useTaskMutation hook + TaskActions component from DetailTab
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

DetailTab.tsx (634 LOC) contains ~130 LOC of mutation orchestration (`runMutation`, `previousStatus`, `serverValidationMessage` state) and ~60 LOC of action button logic (`confirmType` state, focus management, unclaim/unblock/move-backward buttons, ConfirmDialog wiring). Task #1507 is the second extraction in the #1492 decomposition sequence, after #1506 (conflict hook + banner).

**Question:** What are the precise extraction boundaries, hook/component interfaces, and coupling points with `useConflictDraft` (from #1506) that allow all 7 existing test files to pass unchanged?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| DetailTab.tsx (634 LOC) — mutation zones L69, L212–310, L370–415, JSX L562–634 | In-repo | 1.0 |
| useRepairFlow.ts (92 LOC) — established hook pattern | In-repo | 0.9 |
| useCleanupFlow.ts (69 LOC) — established hook pattern | In-repo | 0.9 |
| ConfirmDialog.tsx — already-extracted component | In-repo | 0.8 |
| cockpit-conflict-hook-extraction.md — #1506 research (coupling analysis) | In-repo | 0.9 |
| cockpit-detailtab-decomposition.md — #1492 parent research | In-repo | 0.8 |

## 3. Analysis

### 3.1 Mutation Code Zones in DetailTab.tsx

| Zone | Lines | LOC | What |
|------|-------|-----|------|
| `serverValidationMessage` state | 69 | 1 | `useState<string \| null>(null)` |
| `confirmType` state | 74 | 1 | `useState<null \| 'move-backward' \| 'unblock' \| 'unclaim'>(null)` |
| `pendingFocusRestore` + `confirmTriggerRef` | 75–76 | 2 | Focus management for ConfirmDialog |
| Focus restore useEffect | 112–119 | 8 | Restores focus after confirm dismiss |
| `previousStatus()` | 212–226 | 15 | Computes backward target from board transitions |
| `runMutation()` | 228–310 | 83 | OCC mutation with 200/409/404/422/error handling |
| `handleConfirm()` | 370–395 | 26 | Dispatches runMutation for each confirm type |
| `handleConfirmCancel()` | 397–403 | 7 | Focus save + dismiss |
| `openConfirm()` | 405–415 | 11 | Trigger ref capture + set confirmType |
| Action buttons JSX | 562–590 | 29 | move-backward, unclaim, unblock buttons |
| ConfirmDialog JSX | 627–634 | 8 | ConfirmDialog component rendering |
| **Total** | — | **~191** | Across 11 zones |

### 3.2 Coupling with useConflictDraft (#1506)

`runMutation` writes conflict state in three paths (per #1506 research §3.2):

| Path | Conflict action needed |
|------|----------------------|
| Success (200) | `clearConflict()` — clears all 4 conflict state vars |
| Conflict (409, refetch OK) | `setConflictDetected(draft, remoteTask)` |
| Conflict (409, refetch non-404 fail) | `setConflictDetectedNoRefetch(draft)` |
| Conflict (409, refetch 404) | `clearConflict()` + `onTaskCleared()` |

**Interface:** `useTaskMutation` accepts conflict action callbacks as options. It does not import or depend on `useConflictDraft` directly — DetailTab wires the connection.

### 3.3 Proposed Interfaces

**useTaskMutation hook:**

```typescript
interface UseTaskMutationOptions {
  taskId: number
  taskUpdated: string
  board?: Board | null
  conflictActions: {
    clearConflict: () => void
    setConflictDetected: (draft: ConflictLocalDraft | null, remoteTask: TaskDetail) => void
    setConflictDetectedNoRefetch: (draft: ConflictLocalDraft | null) => void
  }
  onTaskUpdated?: (task: TaskDetail) => void
  onTaskCleared?: (message?: string) => void
  onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
}

interface UseTaskMutationResult {
  serverValidationMessage: string | null
  setServerValidationMessage: (msg: string | null) => void
  previousStatus: (current: string) => string | null
  runMutation: (url: string, payload: Record<string, unknown>, options: MutationOptions) => Promise<void>
}
```

~80 LOC. Owns `serverValidationMessage` state and the `runMutation` function. Exposes `previousStatus` as a function (not a computed value) because DetailTab uses it to compute `backwardTarget` and TaskActions uses it indirectly via the `backwardTarget` prop.

**TaskActions component:**

```typescript
interface TaskActionsProps {
  task: TaskDetail
  backwardTarget: string | null
  runMutation: (url: string, payload: Record<string, unknown>, options: MutationOptions) => Promise<void>
}
```

~80 LOC. Owns `confirmType` state, `pendingFocusRestore` state, `confirmTriggerRef`, focus-restore useEffect, all three action handlers, all three action buttons, and ConfirmDialog rendering.

### 3.4 Data Flow After Extraction

```
DetailTab (container, ~80 LOC after #1508)
  ├── useConflictDraft() → conflict state + actions (#1506)
  ├── useTaskMutation({ conflictActions, ... }) → runMutation, serverValidationMessage
  ├── TaskActions({ task, backwardTarget, runMutation })
  │     └── ConfirmDialog (already extracted)
  ├── ConflictBanner({ ... }) (#1506)
  └── Field inputs, save button, etc. (→ #1508 TaskFieldsEditor)
```

### 3.5 Test Impact

All 7 test files import `DetailTab` (default) and `TaskDetail` (named). Both remain exported from DetailTab.tsx. TaskActions is rendered internally by DetailTab — no test import changes needed.

| Risk | Severity | Mitigation |
|------|----------|------------|
| `handleConfirm` calls `runMutation` incorrectly | Low | Tests already cover confirm flows via DetailTab integration tests |
| Focus management breaks | Low | Confirm dialog tests exercise open/cancel/confirm cycles |
| `previousStatus` returns wrong target | Low | Move-backward tests verify backward button visibility and target |
| Circular import between hook and component | None | Hook returns function, component receives via props — no circular dependency |

### 3.6 Implementation Sequencing

#1507 depends on both #1493 (API centralization) and #1506 (conflict hook). When #1507 reaches the builder:

- **If #1506 is done:** `useTaskMutation` receives conflict actions from the extracted `useConflictDraft` hook. Clean.
- **If #1506 is not done:** `useTaskMutation` receives conflict actions as raw setter wrappers built inline in DetailTab. Still works, just less clean. The builder should check #1506's state.
- **If #1493 is done:** `runMutation` wraps centralized API functions instead of raw `fetch()`. Cleaner error handling.
- **If #1493 is not done:** `runMutation` wraps raw `fetch()` as it does today. The extraction boundary is identical either way.

## 4. Recommendation

Extract using the interfaces defined in §3.3, matching the established `useRepairFlow`/`useCleanupFlow` hook pattern and `ConfirmDialog` component precedent. Confidence: **0.88**.

T1 classification — pure refactoring, no architectural change, no new capabilities.

Challenge: skipped — T1 pure refactoring following established in-repo patterns, no option selection needed.

## 5. Follow-up Tasks

No new follow-up tasks needed. #1507 is itself the implementation task; siblings #1508 exists for the next extraction step.
