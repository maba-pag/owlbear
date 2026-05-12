# Cockpit: Extract useConflictDraft Hook + ConflictBanner Component

> **Owning task:** #1506 — Extract useConflictDraft hook + ConflictBanner component from DetailTab
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

DetailTab.tsx (634 LOC) contains ~100 LOC of OCC conflict-detection state, computed values, and UI spread across four code zones. Task #1506 is the first extraction in the #1492 decomposition sequence. **Question:** What is the precise extraction boundary, hook interface, and component contract that allows all 7 existing test files to pass unchanged?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| DetailTab.tsx (634 LOC) — conflict zones at L46–53, L69–73, L89–109, L186–210, L586–620 | In-repo | 1.0 |
| useRepairFlow.ts (92 LOC) — established hook pattern | In-repo | 0.9 |
| useCleanupFlow.ts (69 LOC) — established hook pattern | In-repo | 0.9 |
| DetailTab.conflict-resolution.test.tsx — 23 tests, imports DetailTab + TaskDetail | In-repo | 1.0 |
| DetailTab.conflict-nonregression.test.tsx — 1 test, imports DetailTab + TaskDetail | In-repo | 0.9 |
| cockpit-detailtab-decomposition.md — parent research | In-repo | 0.8 |

## 3. Analysis

### 3.1 Conflict Code Zones in DetailTab.tsx

| Zone | Lines | LOC | What |
|------|-------|-----|------|
| `ConflictLocalDraft` interface | 46–53 | 8 | Type definition |
| State declarations | 69–73 | 5 | showConflict, showConflictOverwrite, conflictLocalDraft, conflictRemoteTask |
| useEffect draft restoration/cleanup | 89–109 | 21 | Restore fields from draft on re-render; clear conflict on task change |
| Computed conflict values | 186–210 | 25 | conflictRemoteValues, conflictLocalValues, conflictChangedFields |
| Conflict modal JSX | 586–620 | 35 | Diff display, acknowledge/discard/overwrite buttons |
| **Total** | — | **~94** | Across 5 zones |

### 3.2 Coupling Points with runMutation

`runMutation` (L230–295) writes conflict state in three places:
- **Success (L243–247):** clears all conflict state
- **409 branch (L253–280):** sets conflictLocalDraft, conflictRemoteTask, showConflict
- **404-during-409 (L261–267):** clears conflict state

`handleForceSave` (L345–370) reads conflictLocalDraft, calls `setShowConflict(false)`.

These mutation handlers must call hook-exposed actions. The hook cannot own runMutation — that also handles non-conflict concerns (validation, 404, 422).

### 3.3 useEffect Boundary Split

The effect at L89–109 mixes conflict and field-reset logic:
- **L89–97:** If conflictLocalDraft exists for current task → restore field values (writes title/priority/body state → stays in DetailTab)
- **L99–109:** Otherwise reset fields + clear conflict if task changed (conflict cleanup → hook owns via returned `shouldRestoreDraft` flag or `resetForTask(id)` callback)

**Recommended approach:** Hook exposes `conflictLocalDraft` and a `clearConflictIfTaskChanged(taskId)` action. DetailTab's useEffect reads the draft to restore fields, then delegates cleanup to the hook action. This keeps field state in DetailTab while the hook owns conflict lifecycle.

### 3.4 Proposed Interfaces

**useConflictDraft hook:**
```
Inputs: (none — pure state hook)
Returns: {
  showConflict, showConflictOverwrite,
  conflictLocalDraft, conflictRemoteTask,
  conflictRemoteValues, conflictLocalValues, conflictChangedFields,
  setConflictDetected(draft, remoteTask),  // for runMutation 409 path
  setConflictDetectedNoRefetch(draft),     // for runMutation 409 refetch-fail path
  clearConflict(),                         // for runMutation success + dismiss
  acknowledgeOverwrite(),                  // sets showConflictOverwrite=true
  dismissConflict(),                       // discard changes button
  clearConflictIfTaskChanged(taskId),      // for useEffect cleanup
}
```

**ConflictBanner component:**
```
Props: {
  changedFields: string[],
  remoteValues: Record<string, string>,
  localValues: Record<string, string>,
  showOverwrite: boolean,
  onAcknowledge: () => void,
  onRefresh: () => void,
  onForceSave: () => void,
}
```

### 3.5 LOC Estimates

| Artifact | Estimated LOC |
|----------|---------------|
| useConflictDraft.ts (interface + hook + actions + computed) | ~65 |
| ConflictBanner.tsx (props + component + JSX) | ~50 |
| DetailTab.tsx net change | −85 (replace inline code with hook calls + component) |

### 3.6 Test Compatibility

All 7 test files import `DetailTab` (default) and `TaskDetail` (named). None import conflict internals directly — they interact via rendered DOM (data-testid attributes like `conflict-modal`, `conflict-acknowledge`, `conflict-remote-*`, `conflict-local-*`, `conflict-overwrite`, `conflict-refresh`). **Zero test changes needed** as long as DetailTab re-exports TaskDetail and renders ConflictBanner at the same DOM position.

### 3.7 Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| useEffect field-restore/conflict-cleanup split | Medium | Hook returns draft; DetailTab's effect reads it for field restoration |
| runMutation coupling to conflict setters | Low | Hook exposes focused action fns, not raw setters |
| ConflictBanner data-testid regression | Low | Component preserves identical testid structure |
| Import path changes break tests | None | Tests import from DetailTab, which re-exports |

## 4. Recommendation

Extract using the interface contracts in §3.4, following the useRepairFlow/useCleanupFlow pattern (action functions, not raw setters). Confidence: **0.88**.

Challenge: skipped — T1 pure refactoring with no option selection, following established in-repo patterns (useRepairFlow, useCleanupFlow).

## 5. Follow-up Tasks

No additional tasks needed — #1506 itself is the implementation task. It moves to backlog for architecture review → TDD cycle. Sibling tasks #1507 and #1508 already exist for subsequent extractions.
