# Cockpit: Wire PBanner Mutation Error Feedback in Shell

> **Owning task:** #1498 — Cockpit: Wire PBanner mutation error feedback in Shell
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

Task #1498 (child of #1494) wires `PBanner` into Shell for mutation errors from KanbanBoard moves and DetailTab edits. Parent research (`.owlbear/research/cockpit-mutation-error-banner.md`) selected the dual-layer approach: PBanner at Shell level, PInlineNotification in modals (#1499). This doc validates the parent recommendation against current codebase state and specifies the implementation contract.

**Question:** What is the exact wiring needed — props, state shape, callback flow, and edge cases?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | PDS PBanner API (v3 type defs, `@porsche-design-system/components-react` ^4.1.0) | 0.95 |
| S2 | PDS Banner examples (designsystem.porsche.com/v3/components/banner/examples/) | 0.85 |
| S3 | Shell.tsx — current lifted state, callback patterns | 1.00 |
| S4 | KanbanBoard.tsx — `moveError` local state, `handleDrop`/`handleTransitionClick` | 1.00 |
| S5 | DetailTab.tsx — `serverValidationMessage`, `runMutation` error paths | 1.00 |
| S6 | Parent research doc (task #1494) | 0.90 |

## 3. Analysis

### 3a. PBanner API (confirmed from type defs)

| Prop | Type | Default | Notes |
|------|------|---------|-------|
| `open` | `boolean` | `false` | Required — controls visibility |
| `heading` | `string` | `''` | Error source label |
| `description` | `string` | `''` | Error detail |
| `state` | `'info'\|'success'\|'warning'\|'error'` | `'info'` | AC maps: 409/500/network→error, 422→warning |
| `dismissButton` | `boolean` | `true` | Enabled by default — matches AC |
| `onDismiss` | `(e: CustomEvent<void>) => void` | — | Clears `bannerError` |
| `position` | responsive | `{base:'bottom',s:'top'}` | Overlay in `#top-layer` |

### 3b. Current Error Patterns (to replace)

| Component | Current State | Current Rendering | Replacement |
|-----------|--------------|-------------------|-------------|
| KanbanBoard | `moveError: string\|null` (local) | `<div data-testid="move-error" role="alert">` | Call Shell callback; remove local div |
| DetailTab | `serverValidationMessage: string\|null` (local) | Flows to Shell `detailValidationMessage` → `<div data-testid="validation-message">` | Call Shell callback; remove Shell div |
| Shell | `selectedTaskError` | `<div data-testid="task-fetch-error">` | **Keep** — this is a fetch error, not mutation |

### 3c. State Shape and Callback Contract

```typescript
// Shell state
type BannerError = { heading: string; description: string; state: 'error' | 'warning' } | null

// Callback props (added to KanbanBoardProps and DetailTabProps)
onMutationError?: (heading: string, description: string, state: 'error' | 'warning') => void
onMutationSuccess?: () => void  // auto-clear banner
```

### 3d. Error Path Mapping

| Source | HTTP Status | Banner `heading` | Banner `state` |
|--------|------------|-------------------|----------------|
| KanbanBoard handleDrop | 409 | 'Move failed' | 'error' |
| KanbanBoard handleDrop | other / network | 'Move failed' | 'error' |
| KanbanBoard handleTransitionClick | 409 / other / network | 'Move failed' | 'error' |
| DetailTab runMutation | 422 | 'Edit failed' | 'warning' |
| DetailTab runMutation | 500+ / network | 'Edit failed' | 'error' |

### 3e. Design Tension: DetailTab 409 Conflict

DetailTab 409 triggers the conflict resolution UI (local draft vs remote comparison + overwrite). This is a rich interactive flow, not a simple error notification. Options:

| Approach | Pros | Cons |
|----------|------|------|
| Show banner AND conflict UI | Matches AC literally (409→error) | Redundant — conflict UI already communicates the problem |
| Conflict UI only, no banner | Clean UX | Doesn't match AC "409→error" literally |
| **Banner only if conflict refetch fails** | Banner for true errors; conflict UI for recoverable conflicts | Nuanced — requires builder to distinguish sub-cases |

**Recommendation:** Let the builder decide. The AC says "409→error" but DetailTab 409 already has purpose-built conflict UX. Note this as a builder judgment call — both interpretations are defensible.

### 3f. Auto-Clear Mechanism

- **KanbanBoard:** Add `onMutationSuccess?.()` call after successful `refetchTasks()` in `handleDrop`/`handleTransitionClick`.
- **DetailTab:** Existing `onTaskUpdated?.(updatedTask)` call path already reaches Shell. Shell can clear `bannerError` in the same handler that processes `onTaskUpdated`.

### 3g. Persistence Verification

Shell state is component-level (`useState`). It is NOT reset by:
- Task selection changes (`setSelectedTaskId`) — confirmed, no `setBannerError(null)` needed
- Sidecar tab switches (tab change handler only toggles `aria-hidden`) — confirmed

## 4. Recommendation (confidence: 0.82)

Follow the parent research's Shell-lifted state approach with these specifics:

1. Add `bannerError` state to Shell + render `<PBanner>` at top of `shell__workspace` or as sibling to main layout
2. Add `onMutationError`/`onMutationSuccess` callbacks to `KanbanBoardProps` and `DetailTabProps`
3. KanbanBoard: replace `setMoveError(msg)` calls with `onMutationError?.('Move failed', msg, 'error')`; call `onMutationSuccess?.()` on successful moves; remove `<div data-testid="move-error">`
4. DetailTab: call `onMutationError?.('Edit failed', msg, state)` for 422/500/network; call auto-clear via `onMutationSuccess?.()` on success; leave 409 conflict UI as-is (builder decides banner overlay)
5. Shell: clear `bannerError` on `onMutationSuccess` and in `onTaskUpdated` handler

**Challenge: SKIP — parent already challenged; this is implementation-detail validation of approved approach.**

## 5. Follow-up Tasks

No new follow-ups needed. Siblings #1499 (modal PInlineNotification) and #1500 (tests) cover remaining scope. This task is ready to advance to backlog.
