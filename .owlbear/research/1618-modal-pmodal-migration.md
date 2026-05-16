# Complex Integrations — Modals → PModal Migration

> **Owning task:** #1618 — P2-11: Complex integrations — modals → PModal
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Three custom modal components (ConfirmDialog, ResolveModal, ArchivalModal) use hand-rolled focus trap, Escape handling, focus return, and `position: fixed` + z-index overlay. The task is to migrate them to PDS v4 `PModal`, which uses the native `<dialog>` element internally. Key questions: Does PModal fully replace the existing a11y behavior? What per-modal dismiss policy is needed? What is the test regression surface?

## 2. Sources Studied

| # | Source | Rel. | What |
|---|--------|:----:|------|
| S1 | PDS v4 modal source (`modal.tsx` on GitHub) | 1.0 | Props: `open`, `dismissButton`, `disableBackdropClick`, `backdrop`, `background`, `fullscreen`, `aria`. Slots: `header`, default, `footer`. Event: `dismiss`. Uses `showModal()` internally. |
| S2 | PDS v4 modal configurator page | .90 | Alert dialog pattern: `aria={{ role: 'alertdialog' }}` + `disableBackdropClick={true}` |
| S3 | MDN `<dialog>` element reference | 1.0 | Native `showModal()` provides: focus trap, Escape dismiss, `::backdrop`, top-layer rendering, automatic focus return on `close()` |
| S4 | Stefan Judis blog — dialog super powers | .85 | Confirms: "focus will be moved back to the previously focused element if you close the modal" |
| S5 | Sam Hermes blog — dialog element | .85 | Confirms: "when the dialog is closed, focus will be returned to the element used to open the dialog" |
| S6 | PDS React examples (GitHub) | .95 | Canonical pattern: `<PModal open={isOpen} onDismiss={onDismiss}>` with `useCallback` handlers |
| S7 | Existing overlay E2E tests (`overlay-behavior-1563.spec.ts`) | 1.0 | Already tests focus trap and focus return for all 3 modals — test surface that needs updating |

## 3. Analysis

### 3.1 Current State — Duplicated A11y Code

All three modals duplicate ~30 lines of identical focus-management code:

| Pattern | ConfirmDialog | ResolveModal | ArchivalModal |
|---------|:---:|:---:|:---:|
| `getFocusableElements()` query | ✓ | ✓ | ✓ |
| `handleKeyDown` Tab cycling | ✓ | ✓ | ✓ |
| Escape → close | ✓ (component-level) | ✓ (document + component) | ✓ (component-level) |
| `previousFocusRef` + focus return | ✓ (+ parent in TaskActions) | ✓ (self-managed) | ✓ (explicit `returnFocusTo` prop) |
| Backdrop overlay | **None** | **None** | **None** |
| `position: fixed` + z-index | ✓ | ✓ | ✓ |

### 3.2 What PModal Provides (Native `<dialog>`)

| Capability | PModal behavior | Source |
|------------|----------------|--------|
| Focus trap | Built-in via `showModal()` — inert rest of page | S3 |
| Focus return on close | Automatic — returns to element focused before `showModal()` | S3, S4, S5 |
| Escape dismiss | Built-in, fires `dismiss` event | S1, S3 |
| Backdrop click dismiss | Default enabled; `disableBackdropClick={true}` to disable | S1 |
| Backdrop visual | Built-in `::backdrop` with `blur` (default) or `shading` | S1 |
| Top-layer rendering | `<dialog>` renders on `#top-layer` — z-index irrelevant | S3 |
| Dismiss button (X) | `dismissButton={true}` (default); set `false` to suppress | S1 |
| ARIA | `aria-modal="true"` auto-set; custom `aria` prop for role/label | S1 |
| Slots | `header`, default (content), `footer` (sticky) | S1 |

### 3.3 Per-Modal Migration Map

| Modal | PModal config | Dismiss policy | Focus return change |
|-------|--------------|----------------|---------------------|
| **ConfirmDialog** | `disableBackdropClick={true}`, `aria={{ role: 'alertdialog' }}`, `dismissButton={false}` | Escape + Cancel/Confirm buttons only (alert dialog pattern per S2) | Remove `previousFocusRef` and parent `pendingFocusRestore` in TaskActions — native dialog handles it |
| **ResolveModal** | Default `disableBackdropClick={false}`, `dismissButton={true}` | Escape + backdrop click + X + Cancel button | Remove `previousFocusRef`, remove document-level keydown handler |
| **ArchivalModal** | Default `disableBackdropClick={false}`, `dismissButton={true}` | Escape + backdrop click + X + Cancel button | Remove `previousFocusRef`, remove `returnFocusTo` prop — native dialog handles it |

### 3.4 Code Removal Per Component

| Component | Lines removed | What's removed |
|-----------|:---:|----------------|
| ConfirmDialog | ~35 | `getFocusableElements`, `handleKeyDown`, `previousFocusRef`, `useEffect` focus hooks, inline positioning styles |
| ResolveModal | ~45 | Same + document-level Escape listener |
| ArchivalModal | ~40 | Same + `returnFocusTo` prop, `previousFocusRef` wiring |
| TaskActions | ~15 | `pendingFocusRestore` state, `confirmTriggerRef`, `useEffect` focus-restore hook |

### 3.5 Risk: Test Regression Surface

Existing tests that will need updating:

| Test file | Impact |
|-----------|--------|
| `overlay-behavior-1563.spec.ts` (E2E) | DOM selectors change: modals render inside PModal shadow DOM; focus-trap tests may need PDS-aware selectors |
| `KeyboardA11y_1395.test.tsx` | ConfirmDialog tests query `role="dialog"` on wrapper div — now it's inside PModal |
| `ResolveModalUX.test.tsx` | Escape key and dismiss tests — PModal handles dismiss event differently |
| `ArchivalModal.test.tsx` | Similar DOM structure changes |
| `KanbanBoard.filter-integration.test.tsx` | Mocks ArchivalModal — mock may need updating |

### 3.6 Risk: Shadow DOM and Test Selectors

PModal uses Shadow DOM (`shadow: true` in source). The `data-testid` attributes currently on the wrapper `<div>` must be placed on PModal or an inner element. Vitest/Testing Library may need `shadowDomQueries` or PDS test utilities. Playwright accesses shadow DOM by default.

## 4. Recommendation

**Proceed with PModal migration.** Confidence: 0.75.

The migration eliminates ~135 lines of duplicated focus-management code across 4 files, adds proper backdrop overlays (currently missing), and shifts a11y to platform-native `<dialog>` behavior. The per-modal dismiss policy must be explicit: ConfirmDialog uses alert dialog pattern (no backdrop dismiss, no X button), while ResolveModal and ArchivalModal allow all dismiss methods.

**Challenge: reconsider** — confidence in original: 0.75. Challenger identified 7 issues: AC-3 backdrop contradiction (accepted — addressed via per-modal dismiss map), focus-return evidence gap (rebutted — MDN + 2 sources confirm native `<dialog>` focus return), regression surface (accepted — noted in risk section), dismiss button default (accepted — ConfirmDialog uses `dismissButton={false}`). Revised from .85 to .75 due to legitimate test-surface and shadow DOM concerns.

## 5. Follow-up Tasks

1. Task #1613 (already exists): P2-10 Tests — must be written against PModal API, not current wrapper div structure
2. Implementation (#1618): Use per-modal config from §3.3; remove code per §3.4; update existing test selectors per §3.5
