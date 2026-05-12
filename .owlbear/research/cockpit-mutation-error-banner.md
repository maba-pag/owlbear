# Cockpit: PDS Notification Component for Mutation Error Feedback

> **Owning task:** #1494 — Cockpit: Add PDS banner for mutation error feedback
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

The Cockpit frontend currently surfaces mutation errors (move, edit, archive, resolve) using plain `<div>` elements or `<PText>` components. No PDS notification component is used. Error state is component-local (`useState<string|null>`), so errors vanish on task selection changes and tab switches.

**Question:** Which PDS notification component(s) should replace the current ad-hoc error display, and what state architecture keeps errors persistent across navigation?

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | PDS Banner API (v3) | designsystem.porsche.com/v3/components/banner/api | 0.95 |
| S2 | PDS Inline Notification API (v3) | designsystem.porsche.com/v3/components/inline-notification/api | 0.95 |
| S3 | PDS Notification Patterns | designsystem.porsche.com/v3/patterns/notifications/introduction | 0.90 |
| S4 | PDS Notification Decision Tree | designsystem.porsche.com/v3/patterns/notifications/decision-tree | 0.90 |
| S5 | Cockpit codebase: Shell.tsx, KanbanBoard.tsx, DetailTab.tsx, ArchivalModal.tsx, ResolveModal.tsx | local | 1.00 |
| S6 | PDS React exports (`@porsche-design-system/components-react` ^4.1.0) | local node_modules | 0.85 |

## 3. Analysis

### 3a. PDS Component Comparison

| Criterion | PBanner | PInlineNotification | PToast |
|-----------|---------|---------------------|--------|
| Criticality (PDS) | Medium/High | Medium | Low/Medium |
| Placement | Top overlay (`#top-layer`) | In-flow (before/after content) | Bottom-left overlay |
| Persist until dismissed | Yes | Yes | No (auto-dismiss 6s) |
| Action button (retry) | **No** — dismiss only | **Yes** — `actionLabel`, `actionIcon`, `onAction` | No |
| States | info, warning, error, neutral | success, info, warning, error, neutral | neutral, success |
| Modal stacking | Competes with modals for `#top-layer` / focus | No stacking issue (in-flow) | N/A |
| React export available | `PBanner` ✓ | `PInlineNotification` ✓ | `PToast` ✓ |

**PToast eliminated:** Auto-dismiss violates AC "persist until dismissed or action succeeds." Only supports neutral/success states — no error state.

### 3b. Dual-Layer vs. Single-Component

| Approach | Pros | Cons |
|----------|------|------|
| **A: PBanner everywhere** | Single pattern; task title aligns | No retry action; overlay conflicts with open modals; modal errors behind banner |
| **B: PInlineNotification everywhere** | Retry action; no stacking issues; consistent | In-flow only — could scroll out of view on long detail forms |
| **C: Dual-layer (recommended)** | PBanner for Shell-level (high visibility); PInlineNotification in modals (retry + no focus conflict) | Two patterns to implement |

### 3c. State Architecture

| Approach | Pros | Cons |
|----------|------|------|
| **MutationErrorContext (new provider)** | Decoupled from Shell; any descendant calls showError | Extra provider; mutation side-effects (409→refetch, 404→clear) can't live in context cleanly |
| **Shell-lifted state + callbacks (recommended)** | KISS; Shell is the only route; already holds lifted state (`selectedTaskId`, `refreshKey`); callbacks already flow down | Shell component grows ~15 lines |

## 4. Recommendation (confidence: 0.75)

**Dual-layer approach (C) with Shell-lifted state:**

1. **PBanner** at Shell level for board-level and detail-tab mutation errors (move, edit). Mounted once, controlled by Shell state. Survives task selection and tab switches.
2. **PInlineNotification** inside ArchivalModal and ResolveModal for modal-scoped errors. Provides built-in retry action button. No `#top-layer` focus conflict with the modal itself.
3. **Error state lifted to Shell** via callback props (not a new React context). Shell already owns `selectedTaskId`, `refreshKey`, and mutation callbacks — adding `bannerError: {message, state} | null` is minimal.
4. **Last-write-wins** for the global banner — concurrent failures from different sources are unlikely; most recent error is most actionable.
5. **Auto-clear** on next successful mutation from same component.

**Challenge: proceed — confidence in original: 0.34 → revised to 0.75 after addressing scope carve-out and modal stacking.**

The challenger's critical objections (modal carve-out violates AC scope; overlay focus conflicts) were valid and incorporated. Archive/resolve errors now use PInlineNotification with retry action instead of being excluded. The "(or equivalent)" clause in AC1 permits PInlineNotification for modal contexts.

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| PBanner overlay obscures board during drag-drop | Medium | Position at top; CSS `--p-banner-position-top: 0px`; dismiss button always visible |
| Modal + banner focus competition | Medium | Banner only shows for non-modal errors; modals use PInlineNotification |
| Two notification patterns to maintain | Low | Clear boundary: banner = Shell-level; inline = modal-level |
| Error source attribution lost in global banner | Low | Include source in heading: "Move failed" vs "Edit failed" |

## 5. Follow-up Tasks

Implementation tasks to be created at `research` status via planner:

1. **Add MutationErrorBanner to Shell** — Wire `PBanner` in Shell, add `bannerError` state, pass error callbacks to KanbanBoard and DetailTab. Replace plain `<div>` error displays with callback invocations.
2. **Replace modal error display with PInlineNotification** — Swap `<PText>` error rendering in ArchivalModal and ResolveModal for `<PInlineNotification>` with retry action button.
3. **Add tests for mutation error banner** — Vitest unit tests for banner visibility, dismiss, auto-clear, navigation persistence. Playwright E2E for banner appearing on simulated mutation failures.
