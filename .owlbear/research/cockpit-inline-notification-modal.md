# Cockpit: Replace Modal Error Display with PInlineNotification

> **Owning task:** #1499 — Cockpit: Replace modal error display with PInlineNotification
> **Date:** 2026-05-12 **Status:** Complete

## 1. Context and Question

ArchivalModal and ResolveModal display mutation errors via `<PText data-testid="*-error">`. The parent research (#1494, `.owlbear/research/cockpit-mutation-error-banner.md`) recommended PInlineNotification for modal-scoped errors with retry action. This task researches the implementation details: API mapping, error categorization, state shape, and test migration.

**Question:** How should PInlineNotification replace PText for error display, and what are the testing implications of the PDS React wrapper's property-based rendering?

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| S1 | PDS Inline Notification API (v3) — designsystem.porsche.com | 0.95 |
| S2 | PDS Inline Notification Examples (v3) — designsystem.porsche.com | 0.90 |
| S3 | PDS React wrapper source (`inline-notification.wrapper.cjs`) — local node_modules | 1.00 |
| S4 | ArchivalModal.tsx, ResolveModal.tsx — local codebase | 1.00 |
| S5 | Test files: ArchivalModal.error-body.test.tsx, ErrorContract.test.tsx, ResolveModal.test.tsx | 1.00 |
| S6 | Parent research: .owlbear/research/cockpit-mutation-error-banner.md (#1494) | 0.90 |

## 3. Analysis

### 3a. PInlineNotification API Mapping

| PDS Prop | Type | Usage in Modal Error |
|----------|------|---------------------|
| `state` | `'error'` | Always `'error'` |
| `heading` | string | Error category: "Archival failed", "Validation error", "Network error" |
| `description` | string | Error detail message (from `getResponseErrorMessage` or catch) |
| `actionLabel` | string | `'Retry'` for retryable errors; omitted for non-retryable |
| `actionIcon` | IconName | `'reset'` for retry |
| `actionLoading` | boolean | `true` while retry in progress (`isSubmitting` state) |
| `onAction` | handler | Re-calls `handleSubmit()` |
| `onDismiss` | handler | `() => setError(null)` |
| `dismissButton` | boolean | `true` (always dismissible) |
| `headingTag` | string | `'h5'` (default, inside modal h3 context) |

PDS ^4.1.0 already installed — no dependency changes needed (S3).

### 3b. Error Categorization

| Error Type | Status | Retryable | Action Button | Notes |
|------------|--------|-----------|---------------|-------|
| Stale conflict | 409 | Yes (AC) | Retry | **Risk:** `expectedUpdated` prop is stale; retry needs fresh value — see §3d |
| Validation | 422 | No | None | User must fix input first |
| Server error | 500+ | Yes | Retry | Same request may succeed on retry |
| Network | catch | Yes | Retry | Transient; retry likely to succeed |
| Client validation | N/A | No | None | ArchivalModal only (invalid refs input) |

### 3c. Error State Shape

| Approach | Complexity | Trade-off |
|----------|-----------|-----------|
| **A: `{ message, retryable } \| null`** | Low | Single state, clear semantics. Recommended. |
| B: Separate `error` + `isRetryable` | Low | More state variables, easy to desync |
| C: Derive retryable from message string | Fragile | Pattern matching on error text — brittle |

**Recommendation: Option A.** Replace `useState<string | null>` with `useState<{ message: string; retryable: boolean } | null>`. Each error site sets `retryable` explicitly.

### 3d. 409 Retry Risk

ArchivalModal's 409 handler calls `onRefresh()` but keeps the modal open with the original `expectedUpdated` prop. A retry from PInlineNotification would re-submit with the stale timestamp → 409 again.

**Mitigation options:**

| Option | Impact | Recommended |
|--------|--------|-------------|
| Pass `expectedUpdated` via ref/callback so parent can update it post-refresh | ~5 LOC parent change | Yes |
| Retry button closes modal, calls `onRefresh()`, parent re-opens | UX disruption | No |
| Accept 409 retry may fail; user sees error again | Suboptimal UX | Fallback |

### 3e. Testing: PDS React Wrapper Property Rendering

**Critical finding (S3):** The PDS React wrapper sets `heading`, `description`, `state`, etc. as **JavaScript properties** on the `<p-inline-notification>` custom element — not HTML attributes. In jsdom (Vitest):

- `element.textContent` → **empty** (no Shadow DOM rendering)
- `element.getAttribute('heading')` → **null** (not set as attribute)
- `(element as any).description` → **works** (JS property on DOM element)

**Current test pattern (breaks):**
```ts
const errEl = container.querySelector('[data-testid="archival-error"]')
expect(errEl!.textContent).toContain('some error')
```

**New test pattern (required):**
```ts
const errEl = container.querySelector('[data-testid="archival-error"]')
expect((errEl as any).description).toContain('some error')
expect((errEl as any).state).toBe('error')
expect((errEl as any).actionLabel).toBe('Retry') // or undefined
```

**Affected test files (5 total, per challenger review):**

| File | Assertions affected |
|------|-------------------|
| ArchivalModal.test.tsx | 6 `querySelector('[data-testid="archival-error"]')` + `.textContent` checks |
| ArchivalModal.error-body.test.tsx | 6 `.textContent` assertions on error element |
| ErrorContract.test.tsx | 3 `[data-testid="resolve-error"]` + `.textContent` checks |
| ResolveModal.test.tsx | 2 `querySelector('[data-testid="resolve-error"]')` existence checks |
| PdsMigration.test.tsx | 2 assertions checking `p-text[data-testid="archival-error"]` tag name |

PdsMigration.test.tsx assertions must change from `p-text[data-testid="archival-error"]` to `p-inline-notification[data-testid="archival-error"]`.

### 3f. Focus Trap Impact (challenger blind spot)

ArchivalModal's `getFocusableElements()` selector includes `p-button`, `p-input-text`, `p-select`, `p-textarea` but NOT `p-inline-notification`. PInlineNotification renders internal dismiss/action buttons. These buttons live inside the web component's Shadow DOM and are not queryable from the light DOM focus trap logic.

**Mitigation:** Add `p-inline-notification` to `getFocusableElements()` selector list. The web component itself should be focusable; internal button focus is handled by the component's own focus management.

### 3g. ResolveModal Error Differentiation

ResolveModal currently treats all `!res.ok` responses identically. To satisfy the retryable/non-retryable AC, it needs status-code-based branching (like ArchivalModal already has). Add 422 → non-retryable, others → retryable.

## 4. Recommendation (confidence: 0.72)

**Component swap with structured error state, scoped to two modals.**

1. Replace `useState<string | null>` with `useState<{ message: string; retryable: boolean } | null>` in both modals.
2. Replace `<PText data-testid="*-error">` with `<PInlineNotification>` using prop mapping from §3a.
3. Add status-code branching to ResolveModal (mirrors ArchivalModal pattern).
4. Update 5 test files: migrate from `.textContent` to JS property access; update PdsMigration tag assertions.
5. Add `p-inline-notification` to ArchivalModal's focus trap selector.
6. Address 409 retry: pass updatable `expectedUpdated` via callback (preferred) or accept retry-fails-again as known limitation.

**Challenge: reconsider → revised to proceed with risks noted.**

Challenger confidence in original: 0.43. Key challenges accepted:
- **409 retry gap:** Research identified the issue (§3d) but didn't close the loop. Builder must choose mitigation from §3d table.
- **Test blast radius understated:** 5 files not 3; PdsMigration.test.tsx was missed. Updated in §3e.
- **Focus trap blind spot:** Added §3f — `getFocusableElements()` needs PInlineNotification in selector.
- **ResolveModal is a state-machine change, not just a swap:** Fair — adding `isSubmitting` state + status-code branching is new behavior. Research noted in §3g but AC covers this scope.

Researcher response: accepted all challenger points; revised confidence from 0.82 → 0.72. Proceed with explicit risk documentation.

## 5. Follow-up Tasks

Single implementation task — this task (#1499) itself. No additional decomposition needed; AC is already concrete and scoped.
