# Token Architecture Implementation Approach

> **Owning task:** #1543 — P1-02: impl — token architecture: agnostic rename + expansion + dark overrides
> **Date:** 2026-05-14 **Status:** Complete

## 1. Context and Question

Task #1543 restructures `tokens.css` from 19 light-only `--pds-theme-light-*` vars to agnostic `--pds-*` names with dark overrides and non-color token expansion. Three ACs: rename, dark fallback, shadow/radius/spacing. The TDD RED suite exists at `TokenArchitecture_1535.test.ts`. Question: what values, selector patterns, and risks should the builder know?

## 2. Sources Studied

| Source | URL / Path | Relevance |
|--------|-----------|-----------|
| PDS v4 `themeDark` export | `@porsche-design-system/components-react/styles` | 1.0 — authoritative dark HSL values |
| PDS v4 `themeLight` export | same package | 1.0 — authoritative light HSL values (matches current) |
| PDS v4 `shadow*`, `radius*`, `spacingStatic*` | same package | 1.0 — non-color reference values |
| PDS v4 `colorSchemeStyles` | same package (fallback CSS structure) | 0.8 — confirms dark values match |
| MDN `prefers-color-scheme` | developer.mozilla.org | 0.7 — CSS spec reference |
| Codebase: `tokens.css` | `serve/cockpit/web/src/tokens.css` | 1.0 — current 19-var, 37-line file |
| Codebase: `TokenArchitecture_1535.test.ts` | `serve/cockpit/web/src/__tests__/` | 1.0 — TDD RED contract |
| Codebase: `useTheme.ts` | `serve/cockpit/web/src/hooks/useTheme.ts` | 0.9 — theme resolution logic |
| #1535 research doc | `.owlbear/research/1535-token-architecture-test-approach.md` | 0.9 — token inventory analysis |

Note: `themeDark`/`themeLight` are exported via a deprecated path in PDS v4 internals, but the values are consistent with PDS's current `colorSchemeStyles` fallback CSS. Treat as stable for value extraction; don't depend on the export path long-term.

## 3. Analysis

### 3.1 Implementation: Single-File CSS Edit

The entire deliverable is a restructured `tokens.css` (~90 lines replacing ~37):

| Block | Selector | Content |
|-------|----------|---------|
| Light defaults | `:root` | 19 color tokens (`--pds-*`) + 13 non-color tokens |
| Dark overrides | `[data-theme="dark"]` | 19 color tokens with dark values |
| Auto fallback | `@media (prefers-color-scheme: dark) { :root:not([data-theme]) { ... } }` | Same 19 dark overrides |

### 3.2 Value Reference Table (Dark vs Light)

| Token | Light (`:root`) | Dark |
|-------|----------------|------|
| `--pds-primary` | `hsl(225 66.7% 1.2%)` | `hsl(225 100% 99%)` |
| `--pds-background-base` | `#fff` | `hsl(225 66.7% 1.2%)` |
| `--pds-background-surface` | `hsl(240 10% 95%)` | `hsl(240 2% 10%)` |
| `--pds-background-shading` | `hsl(240 5.3% 14.9% / 0.5)` | `hsl(240 5.3% 14.9% / 0.5)` |
| `--pds-state-focus` | `#1A44EA` | `#1A44EA` |
| *(14 others)* | *(differ between themes)* | |

### 3.3 Non-Color Token Values (Theme-Independent)

| Token | PDS Source | Value |
|-------|-----------|-------|
| `--pds-shadow-sm` | `shadowSm` | `0px 3px 8px rgba(0,0,0,.16)` |
| `--pds-shadow-md` | `shadowMd` | `0px 4px 16px rgba(0,0,0,.16)` |
| `--pds-shadow-lg` | `shadowLg` | `0px 8px 40px rgba(0,0,0,.16)` |
| `--pds-radius-sm` | `radiusSm` | `4px` |
| `--pds-radius-md` | `radiusMd` | `6px` |
| `--pds-radius-lg` | `radiusLg` | `8px` |
| `--pds-radius-xl` | `radiusXl` | `12px` |
| `--pds-spacing-xs` | `spacingStaticXs` | `4px` |
| `--pds-spacing-sm` | `spacingStaticSm` | `8px` |
| `--pds-spacing-md` | `spacingStaticMd` | `16px` |
| `--pds-spacing-lg` | `spacingStaticLg` | `32px` |
| `--pds-spacing-xl` | `spacingStaticXl` | `48px` |
| `--pds-spacing-2xl` | `spacingStatic2Xl` | `80px` |

### 3.4 Critical Test Defect: `--pds-state-focus`

**PDS defines identical focus color for both themes: `#1A44EA`.** The RED test asserts `darkValue !== rootValue` for ALL 19 tokens. This will fail for `--pds-state-focus` with a correct implementation. Same for `--pds-background-shading` (both `hsl(240 5.3% 14.9% / 0.5)`).

Builder must either flag the test defect for test-writer correction or note the issue and proceed with the understanding that the test's difference assertion is over-strict.

### 3.5 Media Fallback: Primary Dark Path (Not Just Edge Case)

`applyTheme()` is not called in `main.tsx` yet (wired by #1545). Until that task lands, the `@media (prefers-color-scheme: dark)` block is the **only** production dark-mode path. The `:root:not([data-theme])` selector correctly limits to "no JS bootstrap yet" — which is the entire current app.

### 3.6 Downstream Breakage (By Design)

Files using legacy `--pds-theme-light-*` names that will break:

| File | Legacy Tokens Used | Updated By Task |
|------|-------------------|----------------|
| `Shell.css` | 4 tokens | #1550 |
| `Card.css` | 7 tokens | #1546 |
| `Card.tsx` (inline) | priority color vars | #1546 |
| `utils/styles.ts` | 5 tokens | #1546 |
| `ErrorBoundary.tsx` | 1 token (inline) | #1550 |
| `ResponsiveLayout_1391.test.tsx` | assertion strings | #1552 (grep gate) |

Migration grep gate #1552 catches any stragglers after all impl tasks complete.

## 4. Recommendation

**Proceed** (confidence: 0.82, revised from initial 0.90 after challenger).

The implementation is a straightforward CSS restructure with authoritative PDS values. One blocker: the RED test has 2 over-strict assertions (`state-focus` and `background-shading` identical across themes). Builder should flag this for test-writer correction before or during implementation.

Challenge: reconsider → revised to proceed. Key challenges accepted: focus/shading token identity (real defect in test, not in approach), media fallback is primary dark path (reframed), deprecation of PDS export path (acknowledged). Rebutted: over-strict "reconsider" verdict — the test defect is fixable and doesn't invalidate the architecture.

## 5. Follow-up Tasks

No new tasks needed. The test defect is noted in task body for the test-writer/builder to handle within the existing #1535/#1543 pipeline. All downstream consumer updates are already decomposed (#1546–#1550, #1552).
