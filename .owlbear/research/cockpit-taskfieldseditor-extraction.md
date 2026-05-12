# Cockpit: TaskFieldsEditor Extraction — Technical Validation

> **Owning task:** #1508 — Cockpit: Extract TaskFieldsEditor + reduce DetailTab to container
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

After #1506 (conflict hook+banner) and #1507 (mutation hook+actions) complete their extractions, #1508 must extract the remaining field editing UI into `TaskFieldsEditor.tsx` and reduce `DetailTab.tsx` to a ~80 LOC container.

**Questions:** (a) What are the exact extraction boundaries after predecessors complete? (b) How to handle the `handleSave`/`handleForceSave` coupling between field state and mutation hook? (c) Is the `TaskDetail` type discrepancy between `api/tasks.ts` and `DetailTab.tsx` a blocker?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| DetailTab.tsx (634 LOC, current state) | In-repo | 1.0 |
| api/tasks.ts (#1501 output) | In-repo | 0.9 |
| cockpit-detailtab-decomposition.md (parent research) | In-repo | 0.9 |
| useCleanupFlow.ts + CleanupPanel.tsx | In-repo pattern | 0.8 |
| Shell.tsx import pattern | In-repo | 0.7 |
| 8 DetailTab test files (import patterns) | In-repo | 0.8 |

## 3. Analysis

### 3.1 Current Dependency State

| Dep | Status | Impact on #1508 |
|-----|--------|-----------------|
| #1493 (API centralization) | todo (children in-progress) | DetailTab still uses raw `fetch()` |
| #1506 (conflict hook+banner) | in-progress | Not yet extracted |
| #1507 (mutation hook+actions) | in-progress | Not yet extracted |

#1508 works on the **post-extraction** file. Builder must implement against the state left by #1506 and #1507.

### 3.2 What TaskFieldsEditor.tsx Gets (after #1506/#1507 extract their pieces)

| Category | Lines (approx) | Items |
|----------|----------------|-------|
| Field state | ~20 | title, priority, body, dependsOn, parent, blockReason, editBody |
| Parsers | ~40 | parseDependsOn, parseParent (pure functions) |
| Computed | ~15 | isDirty, clientValidationMessage, parsedParent, parsedDependsOn |
| Utilities | ~25 | readControlValue, setHideLabelAttr |
| handleSave | ~20 | Constructs payload + conflictDraft, calls mutation |
| Field JSX | ~100 | All PInputText/PSelect/PTextarea + save button + dirty indicator + body toggle |
| **Total** | **~220** | |

### 3.3 Coupling Resolution: handleSave + handleForceSave

**handleSave** constructs payload from field state and calls mutation. Since field state lives inside TaskFieldsEditor, handleSave naturally belongs there too.

**handleForceSave** is triggered from ConflictBanner (#1506's component). It reads `conflictLocalDraft` (from useConflictDraft) and falls back to current field state. Resolution:

| Option | Approach | Score |
|--------|----------|-------|
| A | handleForceSave in container; expose parsers as exports | **0.80** |
| B | handleForceSave in TaskFieldsEditor via prop trigger | 0.65 |
| C | Both in TaskFieldsEditor; ConflictBanner trigger bubbles through container | 0.55 |

**Recommendation: Option A** — handleForceSave remains in the container (it primarily uses `conflictLocalDraft` which the container already has). Export `parseDependsOn`/`parseParent` from TaskFieldsEditor for the container to reuse. The fallback to raw field state can use an imperative ref or the container can just use the draft (always set when force-save is invoked).

### 3.4 TaskFieldsEditor Interface (proposed)

```typescript
interface TaskFieldsEditorProps {
  task: TaskDetail
  onSave: (payload: EditRequest, draft: ConflictLocalDraft) => Promise<void>
  validationMessage: string | null
  conflictLocalDraft: ConflictLocalDraft | null  // restore on conflict
  conflictRemoteTask: TaskDetail | null          // sync effect dependency
}
```

### 3.5 Container Shape (~80 LOC)

```
- Imports (10)
- Hook wiring: useConflictDraft, useTaskMutation (10)
- handleForceSave + history logic (20)
- JSX: TaskFieldsEditor + ConflictBanner + TaskActions + HistorySubtab (30)
- Re-exports: TaskDetail, DetailTabProps (5)
```

### 3.6 TaskDetail Type Discrepancy

- `api/tasks.ts`: `body: string | null`
- `DetailTab.tsx`: `body: string`

Not a blocker. #1503 (migrate components to centralized API) will reconcile types. For #1508, keep the existing DetailTab `TaskDetail` type and re-export it unchanged. Type unification is out of scope.

### 3.7 Test File Count Correction

8 test files (not 7 as in AC):
1. DetailTab.test.tsx
2. DetailTab.conflict-resolution.test.tsx
3. DetailTab.conflict-nonregression.test.tsx
4. DetailTab.valid-edits.test.tsx
5. DetailTab.edit-payload.test.tsx
6. DetailTab.invalid-parent.test.tsx
7. DetailTab.gfm-plugins.test.tsx
8. DetailTab.pbanner-1498.test.tsx (added after AC was written)

All import: `import DetailTab, { type TaskDetail } from '../components/DetailTab'`. One (#8) also imports `DetailTabProps`. Re-exporting both from DetailTab.tsx maintains backward compat.

## 4. Recommendation

Proceed with extraction using **Option A** (handleForceSave in container, exported parsers). Confidence: **0.85**.

Key implementation details for builder:
1. Export `parseDependsOn`, `parseParent` from TaskFieldsEditor for container reuse
2. TaskFieldsEditor receives `onSave` callback (container wraps with runMutation + conflictDraft options)
3. Container re-exports `TaskDetail` and `DetailTabProps` types from DetailTab.tsx
4. 8 test files must pass unchanged (not 7 — AC needs minor correction)

Challenge: skipped — T1 pure refactoring, no trade-off ambiguity, follows validated parent research.

## 5. Follow-up Tasks

No additional follow-up tasks needed — #1508 is already the final task in the decomposition chain. AC correction (7→8 test files) is a minor note for the builder, not a separate task.
