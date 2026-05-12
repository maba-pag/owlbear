# Cockpit: Decompose DetailTab.tsx into Focused Components

> **Owning task:** #1492 — Cockpit: Decompose DetailTab.tsx into 4 components
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

DetailTab.tsx is 604 lines — the largest component in the Cockpit frontend. It handles:
- Form field editing (title, priority, body, deps, parent, block_reason)
- OCC conflict detection, draft preservation, merge UI
- Task actions (unclaim, unblock, move backward) with confirm dialogs
- History subtab toggle
- Raw `fetch()` mutation with error/conflict handling

**Question:** What decomposition approach minimizes coupling while staying under ~80 LOC for the container, and how should it sequence with the #1493 API client dependency?

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| DetailTab.tsx (604 LOC, current) | In-repo | 1.0 |
| useCleanupFlow.ts, useRepairFlow.ts | In-repo hook patterns | 0.9 |
| ConfirmDialog.tsx (already extracted) | In-repo extraction precedent | 0.8 |
| repair.ts, cleanup.ts (api/ modules) | In-repo API pattern | 0.8 |
| #1493 research (cockpit-api-client-centralization.md) | In-repo | 0.9 |
| React docs: composition model, custom hooks | External reference | 0.7 |

## 3. Analysis

### 3.1 Structural Zones in Current File

| Zone | Lines | LOC | Concern |
|------|-------|-----|---------|
| Types/interfaces | 16–56 | 40 | TaskDetail, DetailTabProps, ConflictLocalDraft |
| State + effects | 58–107 | 50 | 15 useState, 3 useEffect |
| Parsing utils | 128–168 | 40 | parseDependsOn, parseParent (pure functions) |
| Computed values | 170–204 | 35 | isDirty, conflict field diff, backwardTarget |
| runMutation | 206–280 | 75 | OCC mutation, conflict detection, error routing |
| Action handlers | 282–395 | 115 | handleSave/ForceSave/Confirm + openConfirm |
| Utility fns | 399–420 | 22 | readControlValue, setHideLabelAttr |
| JSX | 422–603 | 180 | Full render output |

### 3.2 Coupling Map

`runMutation` is the central bottleneck — used by both save (edit) and action (unclaim/unblock/move) flows. It reads/writes conflict state, server validation, and fires callbacks.

Field state (`title`, `priority`, `body`, `dependsOn`, `parent`, `blockReason`) is consumed by: (a) input bindings, (b) isDirty computation, (c) conflict draft construction, (d) save payload.

### 3.3 Decomposition Options

| Criterion | A: Props-drilling | B: Custom hooks | C: Context |
|-----------|-------------------|-----------------|------------|
| Interface clarity | Verbose prop types | Clean hook returns | Implicit |
| Testability | Component-only | Hook + component | Provider setup |
| Matches codebase | Partial (ConfirmDialog) | Yes (useCleanupFlow etc.) | No precedent |
| Container LOC ~80 | Possible | Achievable | Achievable |
| Complexity | Low | Medium | Overkill (4 consumers) |
| **Score** | **0.65** | **0.85** | **0.50** |

**Recommendation: Option B (Custom hooks + components)** — confidence 0.85.

### 3.4 Proposed Component/Hook Map

| Artifact | ~LOC | Responsibility |
|----------|------|----------------|
| `useConflictDraft.ts` | 60 | conflictLocalDraft, conflictRemoteTask, showConflict/Overwrite, changedFields |
| `useTaskMutation.ts` | 80 | runMutation wrapper, serverValidationMessage, previousStatus |
| `TaskFieldsEditor.tsx` | 180 | Field inputs + parsers + isDirty + readControlValue + body toggle |
| `ConflictBanner.tsx` | 60 | Conflict diff display, acknowledge/discard/force save buttons |
| `TaskActions.tsx` | 50 | Unclaim/unblock/move-backward buttons + ConfirmDialog wiring |
| `DetailTab.tsx` (container) | 80 | Wire hooks → components, history toggle, type re-exports |

Total: ~510 LOC across 6 files vs 604 LOC in 1 file. Net reduction ~15% through dead-code-adjacent cleanup.

### 3.5 Sequencing with #1493

#1492 depends on #1493 (centralize API client). Order matters:

1. **#1493 first:** Creates `api/tasks.ts` with `editTask()`, `moveTask()`, `releaseTask()`, `getTask()`
2. **#1492 second:** `useTaskMutation` wraps the centralized API instead of raw `fetch()`

Doing #1493 first avoids double-refactoring the fetch calls. The decomposition shape is identical either way, but the mutation hook is cleaner when it delegates to typed API functions.

### 3.6 Test Impact

7 test files import `DetailTab` and/or `TaskDetail`:

| Test file | Imports | Impact |
|-----------|---------|--------|
| DetailTab.test.tsx | default + TaskDetail | Re-export from container |
| DetailTab.conflict-resolution.test.tsx | default + TaskDetail | Re-export |
| DetailTab.conflict-nonregression.test.tsx | default + TaskDetail | Re-export |
| DetailTab.valid-edits.test.tsx | default + TaskDetail | Re-export |
| DetailTab.edit-payload.test.tsx | default + TaskDetail | Re-export |
| DetailTab.invalid-parent.test.tsx | default + TaskDetail | Re-export |
| DetailTab.gfm-plugins.test.tsx | default + TaskDetail | Re-export |

**Mitigation:** DetailTab.tsx re-exports `TaskDetail` type and remains the default export. Zero import changes needed in tests or Shell.tsx.

### 3.7 Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Test breakage from moved types | Low | Re-export from DetailTab.tsx |
| Over-extraction (too many hooks) | Low | 2 hooks is proportional to 604 LOC |
| Conflict logic split incorrectly | Medium | useConflictDraft keeps all conflict state atomic |
| Sequencing churn if #1493 not done first | Medium | Enforce dependency ordering |

## 4. Recommendation

Extract DetailTab using **custom hooks + focused components** (Option B), sequenced after #1493 completion. Confidence: **0.85**.

**Challenge:** skipped — T1 pure refactoring with no architectural change, following established codebase patterns.

## 5. Follow-up Tasks

Decomposition tasks to be created at `research` status via planner, all parented under #1492.
