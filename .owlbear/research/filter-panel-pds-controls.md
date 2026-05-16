# Filter Panel PDS Controls — Component Audit & Implementation Plan

> **Owning task:** #1617 — P2-09: Filter panel PDS controls
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

Task #1617 requires migrating filter panel controls to PDS form components and establishing a coherent layout. The two ACs are:

1. Filter inputs use PDS form components (`PSelect`, `PTextFieldWrapper`, `PCheckboxWrapper` as appropriate)
2. Filter panel has coherent layout (horizontal bar or collapsible sidebar)

**Key finding up front:** the AC references deprecated component names. `PCheckboxWrapper` and `PTextFieldWrapper` are deprecated (🚫) in PDS v3+/v4 — the correct v4 equivalents are `PCheckbox` and `PInputSearch`/`PInputText`. The existing code already uses most of the correct components.

## 2. Sources Studied

| # | Source | URL | Relevance |
|---|--------|-----|-----------|
| S1 | PDS v3 component nav + deprecation markers | designsystem.porsche.com/v3/components/ | 0.9 — confirms Wrapper components deprecated |
| S2 | PDS GitHub — CheckboxExampleControlled.tsx | github.com/porsche-design-system/…/CheckboxExampleControlled.tsx | 1.0 — canonical React controlled pattern |
| S3 | PDS GitHub — CheckboxExampleForm.tsx | github.com/porsche-design-system/…/CheckboxExampleForm.tsx | 0.9 — form integration with onChange |
| S4 | PDS GitHub — checkbox.tsx (Stencil source) | github.com/porsche-design-system/…/checkbox.tsx | 0.8 — props, events, internals API |
| S5 | PDS v3 migration guide (v2→v3) | designsystem.porsche.com/v3/news/migration-guide/ | 0.7 — deprecation rationale |
| S6 | Codebase: FilterPanel.tsx | serve/cockpit/web/src/components/FilterPanel.tsx | 1.0 — current implementation |
| S7 | Codebase: FilterPanel.test.tsx | serve/cockpit/web/src/__tests__/FilterPanel.test.tsx | 0.9 — test surface + selectors |

## 3. Analysis

### Current PDS Compliance (FilterPanel.tsx)

| Control | Current Component | Target PDS v4 | Status | Migration Effort |
|---------|------------------|---------------|--------|-----------------|
| Search text | `PInputSearch` | `PInputSearch` | ✅ Done | None |
| Priority | `PSelect` + `<option>` | `PSelect` | ✅ Done | None |
| Tags | `PMultiSelect` + `PMultiSelectOption` | `PMultiSelect` | ✅ Done | None |
| Blocked toggle | `<p-checkbox>` (raw WC) | `PCheckbox` (React wrapper) | ❌ Needs migration | Low (~15 LOC) |
| Clear button | `PButton` | `PButton` | ✅ Done | None |

**4 of 5 controls are already PDS-compliant.** Only the blocked checkbox needs migration.

### AC Name Correction

| AC Name | PDS Status | Correct v4 Component | Already Used? |
|---------|-----------|---------------------|---------------|
| `PTextFieldWrapper` | 🚫 Deprecated | `PInputSearch` | ✅ Yes |
| `PCheckboxWrapper` | 🚫 Deprecated | `PCheckbox` | ❌ Uses raw WC |
| `PSelect` | ✅ Current | `PSelect` | ✅ Yes |

### PCheckbox React API (from S2, S3, S4)

```tsx
import { PCheckbox, CheckboxChangeEventDetail } from '@porsche-design-system/components-react'

<PCheckbox
  name="blocked-filter"
  label="Show only blocked tasks"
  checked={filter.blocked}
  onChange={(e: CustomEvent<CheckboxChangeEventDetail>) => {
    const { checked } = e.target as HTMLInputElement
    onFilterChange({ ...filter, blocked: checked })
  }}
/>
```

Key differences from current `<p-checkbox>`:
- Uses `onChange` prop (not `onClick` event handler)
- Gets `CheckboxChangeEventDetail` with typed event
- `label` as prop (not child text)
- `checked` as prop (not `aria-checked`)

### Layout Options

| Option | Approach | Pros | Cons | Confidence |
|--------|----------|------|------|------------|
| **A: Horizontal flex bar** | `display:flex; flex-wrap:wrap; gap:var(--p-spacing-sm); align-items:flex-end` | Simple, fits 4 controls, standard filter UX | Wraps on narrow viewports (acceptable) | 0.85 |
| B: CSS Grid 2-col | `grid-template-columns: 1fr 1fr` with responsive | Structured alignment | Over-engineered for 4 controls | 0.40 |
| C: Collapsible sidebar | Separate sidebar panel with `PFlyout` or absolute positioning | Good for many filters | Only 4 controls — YAGNI | 0.25 |

**Recommendation: Option A (horizontal flex bar).** With 4 controls + conditional clear button, a wrapping flex row is the simplest coherent layout. The panel is already collapsible via `open` prop.

### Test Impact

- `getBlockedControl()` in tests queries `p-checkbox` first — no selector change needed
- Test AC6 (interaction fires `onFilterChange`) will need the `onChange` event path instead of `onClick`
- No new test file needed; existing `FilterPanel.test.tsx` covers all 7 ACs

## 4. Recommendation

**Migrate blocked checkbox to `PCheckbox` React wrapper and add flex layout.** Confidence: **0.85**

This is a minimal migration — 1 component swap + CSS layout addition. The other 4 controls are already PDS v4 compliant.

Challenge: FALLBACK — trivial migration scope (1 component + layout CSS); challenger not cost-justified.

## 5. Follow-up Tasks

Task #1617 itself is the implementation task. No additional follow-up tasks needed — the scope is self-contained and the test task (#1612) was archived in favor of the existing test coverage.
