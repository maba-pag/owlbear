# PToast Success Feedback — Implementation Research

> **Owning task:** #1624 — P3-02: Success feedback — PToast notifications
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

The cockpit frontend currently has no positive feedback for successful mutations. Errors display via PBanner in Shell.tsx, but the success path (`onMutationSuccess`) only clears the error banner. Task scope (from body): "PToast for move/mutation success, inline confirmation for edits."

**Questions:** (1) How to integrate PDS PToast for move success notifications. (2) How to provide inline edit confirmation without conflating success and error paths. (3) How to avoid regressing existing error feedback.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| 1 | PDS Toast Configurator (v3 docs) | designsystem.porsche.com/v3/components/toast/configurator/ | 0.95 |
| 2 | PDS Toast API (v3 docs) | designsystem.porsche.com/v3/components/toast/api/ | 0.90 |
| 3 | PDS Toast Accessibility | designsystem.porsche.com/v3/components/toast/accessibility/ | 0.85 |
| 4 | PDS GitHub — ToastExample.tsx (React) | github.com/porsche-design-system/.../ToastExample.tsx | 0.95 |
| 5 | PDS GitHub — toast-manager.ts | github.com/porsche-design-system/.../toast-manager.ts | 0.90 |
| 6 | PDS GitHub — hooks.spec.tsx (useToastManager tests) | github.com/porsche-design-system/.../hooks.spec.tsx | 0.85 |
| 7 | PDS GitHub — toast.e2e.ts (Playwright tests) | github.com/porsche-design-system/.../toast.e2e.ts | 0.80 |
| 8 | Local: @porsche-design-system/components-react v4.1.0 types | node_modules/.../types.d.ts | 1.00 |

## 3. Analysis

### PDS PToast API Summary

| Aspect | Detail |
|--------|--------|
| React imports | `PToast`, `useToastManager` from `@porsche-design-system/components-react` |
| Mount | Singleton — one `<PToast />` per app. Warns if rendered twice. |
| Usage | `const { addMessage } = useToastManager(); addMessage({ text, state })` |
| ToastMessage | `{ text: string, state?: 'info' \| 'success' \| 'warning' \| 'error' }` |
| Auto-dismiss | 6 seconds (override via `--p-temporary-toast-timeout` CSS var in tests) |
| Accessibility | `role="status"` — ARIA live region, non-intrusive announcement |
| Position | Fixed bottom-right, `--p-toast-position-bottom` adjustable |
| Top-layer | Renders on `#top-layer` — z-index irrelevant |
| Queue | Latest message replaces current; if different text, dismisses current first |

### Current Mutation Success Flow

```
KanbanBoard.handleDrop()   → moveTask() → refetchTasks() → onMutationSuccess?.()
KanbanBoard.handleTransition() → moveTask() → refetchTasks() → onMutationSuccess?.()
Shell.onMutationSuccess    → setBannerError(null)  [clears error, no positive feedback]
DetailTab.handleSave()     → runMutation()          [no success callback at all]
```

### Integration Options

| Criterion | A: PToast in App.tsx + Context | B: PToast in Shell.tsx (revised) | C: PToast in App.tsx, no context |
|-----------|-------------------------------|-----------------------------------|----------------------------------|
| PToast mount | App.tsx (inside PDS provider) | Shell.tsx | App.tsx |
| Hook access | Custom ToastContext | useToastManager in Shell | useToastManager in Shell |
| Move toast | Context consumer in KanbanBoard | Callback from KanbanBoard | Callback from KanbanBoard |
| Edit toast | Context consumer in DetailTab | Callback via onMutationSuccess | Not applicable |
| Inline confirm | Separate mechanism | Separate mechanism | Separate mechanism |
| New files | ToastProvider.tsx | None | None |
| Complexity | High — new context layer | Low — extends existing callbacks | Low — extends callbacks |
| KISS score | 0.55 | 0.85 | 0.80 |

### Challenger Findings (Revised)

The challenger (confidence in original: 0.48) identified five issues:

1. **Inline save success detection (critical):** `runMutation` resolves on both success AND handled errors — a post-await flash would fire on 422/500. **Resolution:** Add explicit `onMutationSuccess` callback to `UseTaskMutationOptions`, called only at line 97 (the true success return). This gives a clean success-only signal.

2. **Proof target ambiguity:** `<PToast>` host is always mounted; AC1 tests the `p-toast-item` child that appears inside when `addMessage()` fires. **Resolution:** Test asserts `p-toast-item` visibility or text content, not `p-toast` host existence.

3. **Callback contract scope:** Changing `onMutationSuccess: () => void` to `(message?: string) => void` touches 2 interfaces, 2 call sites, and ~3 test files. **Resolution:** Optional param is backwards-compatible; old callers pass no args.

4. **Toast lifecycle:** `useToastManager` queries `document.body.querySelector('p-toast')` with no null guard. **Resolution:** Mount PToast in App.tsx (above Shell) — guaranteed present before any mutation.

5. **AC quality gap:** ACs are intentionally loose. **Resolution:** Research doc defines concrete DOM contracts for builder.

## 4. Recommendation (confidence: 0.82)

**Option B-revised:** PToast singleton in App.tsx, wired via Shell callbacks.

Challenge: **proceed** — confidence in original revised from 0.48 to 0.82 after addressing all five challenger concerns.

### Concrete Implementation Plan

**1. Mount PToast singleton in App.tsx:**
```tsx
<PorscheDesignSystemProvider>
  <PToast />          {/* singleton — renders on #top-layer */}
  <BrowserRouter>...</BrowserRouter>
</PorscheDesignSystemProvider>
```

**2. Enhance callbacks for move success:**
- `onMutationSuccess` signature: `(message?: string) => void`
- Shell handler: `useToastManager().addMessage({ text: message ?? 'Done', state: 'success' })`
- KanbanBoard call sites pass descriptive text: `onMutationSuccess?.('Task moved to review')`

**3. Add success signal to useTaskMutation:**
- New optional callback: `onMutationSuccess?: () => void` in `UseTaskMutationOptions`
- Called at line 97 (after `onTaskUpdated`, before return) — success-only path
- Not called in any catch branch

**4. Inline edit confirmation:**
- After successful edit mutation, set a brief `saved` state in TaskFieldsEditor
- Show "Saved" indicator near save button (data-testid="save-confirmed")
- Auto-reset after ~2s
- Does NOT use PToast — per task body "inline confirmation for edits"

**5. Error no-regression:**
- PBanner stays for errors — no changes to error paths
- PToast is additive (separate component, separate layer)

### DOM Contracts for Testing

| AC | Observable DOM target | Assertion |
|----|----------------------|-----------|
| AC1 (move toast) | `p-toast-item` inside `p-toast` shadow DOM | Text contains status name, appears within 500ms |
| AC2 (edit confirm) | `[data-testid="save-confirmed"]` or equivalent | Visible after edit save, not visible after error |
| AC3 (error no-regression) | `PBanner[open=true]` | Still shows on mutation errors |

## 5. Follow-Up Tasks

Follow-up tasks to be created via planner at `research` status:

1. **Implement PToast singleton + move success toasts** — mount PToast in App.tsx, enhance onMutationSuccess callback, wire KanbanBoard move handlers
2. **Implement inline edit confirmation** — add onMutationSuccess to useTaskMutation, add saved state to TaskFieldsEditor
3. **Error feedback no-regression verification** — ensure PBanner error paths are unmodified

Note: Since the predecessor test task (#1619) was archived as deprecated, tests should be written alongside implementation (TDD within the implementation tasks).
