# Token Architecture Test Approach

> **Owning task:** #1535 — P1-01: test — token architecture: agnostic rename + expansion + dark overrides
> **Date:** 2026-05-13 **Status:** Complete

## 1. Context and Question

Task #1535 writes Vitest tests (RED phase) for the token architecture refactor defined in the board visual design brief (#1534). Three ACs: verify agnostic rename, dark overrides, and new non-color tokens. Question: what test approach and token inventory should the test-writer use?

## 2. Sources Studied

| Source | URL | Relevance |
|--------|-----|-----------|
| PDS v4 Migration Guide | designsystem.porsche.com/v4/news/migration-guide/ | 0.9 — documents PDS v4 theme system |
| PDS v4 CSS Variables | designsystem.porsche.com/v4/stylesheets/css-variables/introduction/ | 1.0 — full CSS variable reference |
| PDS v4 Token docs (shadow, border, spacing) | designsystem.porsche.com/v4/tokens/{shadow,border,spacing}/ | 0.8 — official token values |
| Codebase: tokens.css | serve/cockpit/web/src/tokens.css | 1.0 — current 19-var inventory |
| Codebase: PDSHexScan_1395.test.ts | serve/cockpit/web/src/__tests__/PDSHexScan_1395.test.ts | 0.7 — file-based test precedent |
| PDS v4 themeDark export | @porsche-design-system/components-react/styles | 0.9 — authoritative dark values |

## 3. Analysis

### 3.1 Token Count Discrepancy

The AC says "17 existing color tokens." Actual `tokens.css` declares **19** custom properties:

| Group | Tokens | Count |
|-------|--------|-------|
| Primary | primary | 1 |
| Background | base, surface, shading | 3 |
| Contrast | low, medium, high | 3 |
| Notification | success, success-soft, warning, warning-soft, error, error-soft, info, info-soft | 8 |
| State | hover, active, focus, disabled | 4 |
| **Total** | | **19** |

The "17" in the brief is likely a counting error. Tests should enumerate all 19.

### 3.2 Test Approach: File-Based CSS Parsing

| Approach | Pros | Cons | Fit |
|----------|------|------|-----|
| File-based regex | Simple, matches existing pattern (PDSHexScan), no jsdom CSS overhead | Not a full CSS parser | ✅ Best |
| CSSOM via jsdom | Tests runtime behavior | jsdom has limited CSS custom property support, complex setup | ❌ Over-engineered |
| PostCSS AST parse | Robust CSS parsing | New dependency, over-engineered for 35-line file | ❌ Over-engineered |

**Recommendation: file-based parsing** (confidence: 0.85). The tokens.css is hand-maintained, ~35 lines, predictable structure. Regex is adequate and consistent with codebase patterns.

### 3.3 PDS v4 Native vs Brief's Token Convention

| Dimension | PDS v4 Native | Brief's Design |
|-----------|---------------|----------------|
| Prefix | `--p-*` | `--pds-*` |
| Dark mechanism | `light-dark()` CSS function | `[data-theme="dark"]` override |
| Theme toggle | `color-scheme` + `scheme-*` classes | `data-theme` attribute on `<html>` |
| Color naming | `--p-color-primary` | `--pds-primary` |

The brief deliberately chose a **separate alias layer** (`--pds-*`) to shield Cockpit from upstream PDS churn. No naming collision with PDS v4's `--p-*` prefix. Tests protect the brief's contract, not PDS native.

### 3.4 Non-Color Token Inventory (AC-3)

| Token family | Brief spec | PDS v4 has | Test verifies |
|--------------|-----------|------------|---------------|
| Shadow | sm, md, lg | sm, md, lg | 3 tokens |
| Radius | sm..xl | xs..4xl, full (9) | 4 tokens: sm, md, lg, xl |
| Spacing | xs..2xl | static-2xs..2xl + fluid (13) | 6 tokens: xs, sm, md, lg, xl, 2xl |
| **Total** | | | **13** |

This is a deliberate Cockpit-scoped subset. PDS v4 values can seed the values.

### 3.5 Dark Value Verification (AC-2)

PDS v4 `themeDark` export provides authoritative dark HSL values for all 19 color tokens. Tests should verify both **presence** of dark overrides AND **value correctness** against the PDS export.

### 3.6 Downstream Impact

These tests will be RED (failing) until the implementation task lands. Existing tests referencing `--pds-theme-light-*` (`styles.test.ts`, `ResponsiveLayout_1391.test.tsx`) will break at implementation time — the builder handles those updates, not this test task.

## 4. Recommendation

**Proceed with file-based CSS parsing approach** (confidence: 0.77, revised from 0.85 after challenge).

Test structure per AC:
- **AC-1**: Read `tokens.css`, extract `:root` block, verify 19 `--pds-*` agnostic names present (no `--pds-theme-light-*`), verify token names match expected set
- **AC-2**: Verify `[data-theme="dark"]` block overrides all 19 color tokens with non-empty dark values matching PDS `themeDark`
- **AC-3**: Verify `:root` contains 13 non-color tokens: 3 shadow + 4 radius + 6 spacing

Challenge: proceed — confidence in original: 0.77. Key challenges accepted: 19-not-17 count, dark value exactness, subset scoping. Rejected: CSSOM approach (over-engineered), migration grep gate (separate task).

## 5. Follow-up Tasks

None needed beyond #1535 itself — the task is already correctly scoped for test-writing. The 19-vs-17 discrepancy should be noted in the task body for the test-writer.
