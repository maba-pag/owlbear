# CleanupPanel / RepairPanel Confirm-Overlay PModal Migration

> **Owning task:** #1635 — P2-13: Migrate CleanupPanel/RepairPanel confirm-overlay dialogs to PModal
> **Date:** 2026-05-17 **Status:** Complete

## 1. Context and Question

Task #1608 (component complexity inventory) identified two unowned raw `div[role="dialog"]` confirm overlays classified as "complex integration" — in CleanupPanel.tsx:92 and RepairPanel.tsx:72. Three other modals (ConfirmDialog, ResolveModal, ArchivalModal) were already migrated to PModal in #1618. This research determines the correct migration approach for these two remaining dialog surfaces.

## 2. Sources Studied

| # | Source | URL/Path | Relevance |
|---|--------|----------|-----------|
| 1 | CleanupPanel.tsx current impl | `serve/cockpit/web/src/components/CleanupPanel.tsx` | 1.0 |
| 2 | RepairPanel.tsx current impl | `serve/cockpit/web/src/components/RepairPanel.tsx` | 1.0 |
| 3 | ConfirmDialog.tsx (migrated) | `serve/cockpit/web/src/components/ConfirmDialog.tsx` | 0.9 |
| 4 | PModal.migration.test.tsx | `serve/cockpit/web/src/__tests__/PModal.migration.test.tsx` | 0.9 |
| 5 | PDS Modal configurator docs | designsystem.porsche.com/v3/components/modal/configurator/ | 0.8 |
| 6 | PDS Modal accessibility docs | designsystem.porsche.com/v3/components/modal/accessibility/ | 0.8 |
| 7 | PModal React wrapper types | `@porsche-design-system/components-react/esm/lib/components/modal.wrapper.d.ts` | 0.7 |
| 8 | #1608 inventory research doc | `.owlbear/research/1608-component-complexity-inventory.md` | 0.7 |

## 3. Analysis

### 3.1 Current State Comparison

| Aspect | CleanupPanel | RepairPanel |
|--------|-------------|-------------|
| Confirm content | Single text paragraph | Multi-sentence + optional file list |
| Inline positioning | `position:fixed; zIndex:1000` | Same (via `OVERLAY_STYLE` const) |
| Focus trap | Element-level Tab/Shift-Tab wrapping | None (relies on document Escape) |
| Escape handling | `onKeyDown` on dialog element only | Document-level listener + `onKeyDown` on element |
| Focus restore | `previousFocusRef` in `useEffect` | Same pattern |
| Non-dialog phases | Plain divs (no overlay style) | `OVERLAY_STYLE` on repairing/done/error phases |
| Test files | 4 (unit, integration, overlay, wiring) | 4 (unit, focus, sidecar, healthbadge) |

### 3.2 PModal Behavior in This Codebase

Codebase evidence shows PModal is a **container primitive**, not a complete behavior replacement. All three existing PModal components (ConfirmDialog, ResolveModal, ArchivalModal) retain custom focus-trap, Tab wrapping, and Escape handling code alongside PModal. PModal provides: backdrop, top-layer z-index, scroll-lock, `onDismiss` event, and native `<dialog>` element.

### 3.3 Role Semantics

| Option | Pros | Cons | Confidence |
|--------|------|------|-----------|
| `dialog` (PModal default) | Preserves existing test assertions (`role="dialog"`); appropriate for review-before-action | Requires explicit `disableBackdropClick` | 0.85 |
| `alertdialog` (ConfirmDialog pattern) | Semantic match for destructive actions | Breaks existing tests asserting `role="dialog"`; RepairPanel is review-oriented | 0.55 |

**(rec:)** Use `dialog` role. Both panels present information for user review before confirmation, not urgent alerts requiring immediate response.

### 3.4 Dismiss Policy

Both panels gate destructive operations (cleanup releases claims/archives tasks; repair is explicitly "irreversible"). The migration must use `disableBackdropClick={true}` and `dismissButton={false}` to prevent accidental dismissal — matching ConfirmDialog's pattern for destructive confirms.

### 3.5 Migration Scope

Only the **confirming phase** `div[role="dialog"]` is in scope per the task title. RepairPanel's `OVERLAY_STYLE` on repairing/done/error phases are not dialog surfaces and are out of scope.

### 3.6 Test Impact

| Test file | Impact | Changes needed |
|-----------|--------|----------------|
| OverlayAnchoring.test.tsx | HIGH | `div[role="dialog"]` → `p-modal`; aria-modal/role assertions adapt to PModal |
| RepairPanel.test.tsx (AC12) | MEDIUM | `role="dialog"` assertion on `repair-confirm-dialog` adapts to PModal |
| RepairPanelFocusMgmt.test.tsx | HIGH | Focus management assertions adapt to PModal container pattern |
| CleanupPanel.test.tsx | LOW | `cleanup-confirm-dialog` testid preserved on PModal; no role assertions |
| CleanupPanel.integration.test.tsx | LOW | Same testid-based queries; dialog container changes transparently |
| HealthBadgeRepair.test.tsx | LOW | Tests PDS usage and exact copy text; unaffected by container change |
| SidecarUX.test.tsx (AC6) | LOW | Tests text content and file list; unaffected by container change |

## 4. Recommendation

**Confidence: 0.82**

Migrate both confirm overlays to PModal following the established ConfirmDialog pattern with `dialog` role:

1. Replace `div[role="dialog"]` with `<PModal open onDismiss={cancel} disableBackdropClick dismissButton={false} aria={{ 'aria-label': '...' }}>`
2. Remove inline positioning styles (PModal uses native top-layer)
3. Adapt focus management to PModal container (follow ConfirmDialog's MutationObserver + manual handler pattern — don't delete focus code entirely)
4. Preserve `data-testid` attributes for test continuity
5. Update affected test assertions to target `p-modal` element

Challenge: proceed — confidence in original revised from 0.88 to 0.82 after challenger identified: (1) PModal is a container primitive, not a full behavior replacement — custom focus code cannot be deleted wholesale, (2) `dialog` role is more appropriate than `alertdialog` for review-before-action surfaces, (3) test impact was understated — 7 test files affected not 2, (4) RepairPanel non-dialog phases are out of scope. All four challenges accepted and incorporated.

## 5. Follow-up Tasks

1. Implementation task: Migrate CleanupPanel and RepairPanel confirm-overlay `div[role="dialog"]` to PModal — depends on this research completing.
