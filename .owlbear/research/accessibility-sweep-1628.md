# Accessibility Sweep — Research

> **Owning task:** #1628 — P3-10: Accessibility sweep
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1628 is the Batch 3 accessibility verification sweep for the cockpit visual redesign (#1590). Per brief constraint #8, accessibility is cross-cutting — earlier batches preserve/improve ARIA, focus, and keyboard navigation, while this B3 task is **verification, not greenfield implementation**.

Questions: (a) What existing a11y test coverage exists? (b) What tooling and configuration does the sweep need? (c) What gaps remain between existing tests and the three ACs? (d) What is the likely fix surface?

## 2. Sources Studied

| Source | URL / Path | What | Score |
|--------|-----------|------|-------|
| Playwright a11y docs | playwright.dev/docs/accessibility-testing | @axe-core/playwright API, withTags for WCAG scope, fixture pattern, exclude/disableRules | 0.95 |
| PDS v4 component a11y | designsystem.porsche.com (component /accessibility pages) | PDS tests against axe-core WCAG 2.2 AA + best-practice; components ship accessible | 0.85 |
| Existing E2E: accessibility-1395.spec.ts | serve/cockpit/web/e2e/ | Full-page axe scans on 4 views (board, detail, DR resolution, repair) at 1024px; keyboard tab-reachability + landmark checks at 4 viewports | 0.95 |
| Existing E2E: column-body-a11y-1574.spec.ts | serve/cockpit/web/e2e/ | Scoped axe scan for scrollable-region-focusable on column bodies | 0.90 |
| Codebase component ARIA audit | serve/cockpit/web/src/components/*.tsx, Shell.tsx | 42 aria-* matches across components; semantic HTML landmarks in Shell | 0.95 |
| PdsMigration.test.tsx | serve/cockpit/web/src/__tests__/ | Verifies zero raw button/input/select/textarea — all migrated to PDS | 0.90 |
| axe-core rule tags | deque.com/axe/core-documentation/api-documentation | wcag2a, wcag2aa, wcag21a, wcag21aa tag mapping | 0.90 |

## 3. Analysis

### Existing Coverage Matrix

| AC | What's needed | Existing coverage | Gap |
|----|---------------|-------------------|-----|
| AC1: axe-core scan → 0 WCAG 2.1 AA violations | Full-page scan with WCAG 2.1 AA tags | `accessibility-1395.spec.ts` runs bare `.analyze()` (all rules, incl. best-practice) on 4 views | **Configuration gap only**: existing scans use all rules, not `withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa'])`. Tightening to WCAG-only is optional — existing scope is already a superset. |
| AC2: Interactive elements have accessible names | No empty `aria-label` or missing labels | axe-core `button-name`, `label`, `link-name` rules catch this automatically; components already have aria-labels | **Likely zero gap**: codebase audit shows all interactive elements (Card, buttons, inputs, dialogs, popovers) have accessible names. axe scan is the verification. |
| AC3: Color contrast 4.5:1 normal / 3:1 large | Automated color-contrast check | axe-core `color-contrast` rule (WCAG 2.1 SC 1.4.3 + 1.4.11) runs by default | **Zero gap in tooling**: contrast check is automatic in every axe scan. Potential violations depend on PDS token colors post-migration. |

### ARIA Audit Summary

Components with ARIA attributes (verified in source):

| Component | ARIA / Semantic | Notes |
|-----------|----------------|-------|
| Shell | `<header>`, `<nav>`, `<main>`, `<aside>`; `aria-current`, `aria-label`, `aria-expanded`, `aria-controls`, `aria-hidden`, `aria-live` | Full semantic landmark structure |
| Card | `role="button"`, `tabIndex={0}`, `aria-haspopup="menu"`, `aria-label` on chips | Keyboard accessible with Enter/Space/Shift+F10 |
| Column | Dynamic `tabIndex` on scrollable body via ResizeObserver | Satisfies scrollable-region-focusable |
| FilterPanel | `role="region"`, `aria-label`, labels on inputs | PDS form controls provide native a11y |
| ArchivalModal | `role="dialog"`, `aria-labelledby` | Focus trap pattern |
| ResolveModal | `role="dialog"`, `aria-label` | Focus trap pattern |
| ConfirmDialog | `role="dialog"`, `aria-label` | Focus management |
| CleanupPanel | `role="dialog"`, `aria-label`, `aria-live="polite"` | Loading state announced |
| RepairPanel | `role="dialog"`, `aria-label`, `aria-live="polite"` | Loading state announced |
| HealthBadge | `aria-label`, `role="dialog"` on popover | Popover with a11y |
| DRStatusIndicator | `aria-label`, `role="dialog"` | DR popover with a11y |
| ThemeToggle | `aria-label` | Toggle button |
| ActivityTab | `role="toolbar"`, `aria-label`, session `aria-label` | Toolbar pattern |
| ErrorBoundary | `role="alert"` | Error announcement |
| DecisionViewport | `role="alert"`, `role="button"` | Error + interaction |

### Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PDS shadow DOM elements fail axe color-contrast check | Medium | Low — PDS guarantees compliance; axe may report false positives on shadow DOM | Exclude PDS shadow roots if needed (`AxeBuilder.exclude()`) |
| Undiscovered violations from B2 component migration | Low-Medium | Medium — could require component fixes | Run axe scan early, fix iteratively |
| Third-party markdown rendering (react-markdown) produces inaccessible output | Low | Low — limited surface (body preview only) | Scoped exclude if confirmed |

### axe-core Tag Recommendation

The AC says "WCAG 2.1 AA". Two options:

| Option | Tags | What's included | Pros | Cons |
|--------|------|----------------|------|------|
| **A: WCAG-scoped** | `['wcag2a','wcag2aa','wcag21a','wcag21aa']` | Only WCAG 2.1 A+AA criteria | Precise match to AC; fewer false positives | Misses best-practice rules that improve real-world a11y |
| **B: Default (no withTags)** | All rules | WCAG 2.0/2.1/2.2 A+AA + best-practice | Strictest; catches more issues | May flag best-practice items outside AC scope |

**Recommendation: Option A** (confidence: 0.80). Match the AC precisely. Existing tests already use default scope as a regression net. The sweep test should use `.withTags()` for clear AC traceability. The existing `accessibility-1395.spec.ts` can remain with default scope as a stricter regression gate.

### Playwright Fixture Pattern

Per Playwright docs, a shared fixture avoids boilerplate:

```typescript
// e2e/axe-test.ts
import { test as base } from '@playwright/test'
import AxeBuilder from '@axe-core/playwright'
export const test = base.extend<{ makeAxeBuilder: () => AxeBuilder }>({
  makeAxeBuilder: async ({ page }, use) => {
    await use(() => new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa']))
  },
})
export { expect } from '@playwright/test'
```

**Recommendation: Skip fixture** (confidence: 0.75). Only 1 new test file uses this; a shared fixture adds indirection for minimal reuse. Inline the configuration.

## 4. Recommendation

**Proceed as T1 (Autonomous).** Confidence: 0.85.

The existing accessibility infrastructure is comprehensive. The sweep task requires:

1. **Run existing `accessibility-1395.spec.ts` E2E tests** after B2 completion to identify any violations introduced by component migration.
2. **Fix violations found** — likely 0–3 issues given the thorough ARIA work in B0–B2.
3. **Write a new or extend existing E2E test** with explicit WCAG 2.1 AA tag scope (`.withTags()`), covering:
   - Board view (full-page scan)
   - Sidecar detail view
   - All overlay surfaces (ArchivalModal, ResolveModal, DR popover, HealthBadge popover)
4. **Verify accessible names** — axe `button-name` / `label` / `link-name` rules handle this.
5. **Verify color contrast** — axe `color-contrast` rule handles this automatically.
6. **Keyboard navigation** — already covered by `accessibility-1395.spec.ts` (AC5 viewport tests). No additional work unless new violations found.

Challenge: FALLBACK — challenger skipped (verification-only task, low ambiguity).

## 5. Follow-up Tasks

No follow-ups needed beyond the implementation task itself (#1628 already at correct status). The test-writer task #1623 was archived and merged into #1628.
