# Token Provenance Map — `--pds-*` Classification

> **Owning task:** #1597 — P1-01: Token provenance map
> **Date:** 2026-05-16 **Status:** Complete
> **Validation of:** `.owlbear/research/1603-token-migration-provenance.md` (verified current)

## 1. Context and Question

`tokens.css` declares 33 custom `--pds-*` properties mirroring PDS v4 values. Every `--pds-*` reference in `serve/cockpit/web/src/` must be classified into exactly one of four categories: PDS equivalent (`--p-*`), Tailwind utility, custom-keep, or dead-delete. This map is the prerequisite for atomic token migration (#1603).

## 2. Sources Studied

| Source | Type | Relevance |
|--------|------|-----------|
| PDS v4 `color-scheme.css` (node_modules) | Primary — 33 `--p-color-*` tokens | 1.0 |
| PDS v4 `variables.css` (node_modules) | Primary — spacing, radius, shadow tokens | 1.0 |
| `tokens.css` (authored, 33 definitions) | Primary — grep-verified source of truth | 1.0 |
| 8 consumer CSS/TSX source files | Primary — exhaustive `grep -rl` inventory | 1.0 |
| `.owlbear/research/1603-token-migration-provenance.md` | Prior research — validated against codebase | 0.9 |

## 3. Four-Way Classification

### 3a. PDS Equivalent (27 consumed tokens → replace with `--p-*`)

| `--pds-*` Token | PDS v4 `--p-*` Replacement | Consumer Files |
|---|---|---|
| `--pds-primary` | `--p-color-primary` | Shell.css (via alias) |
| `--pds-background-base` | `--p-color-canvas` | Shell.css, Card.css |
| `--pds-background-surface` | `--p-color-surface` | Shell.css, Card.css, Column.css, FilterPanel.css, KanbanBoard.css |
| `--pds-background-shading` | `--p-color-backdrop` | Column.css |
| `--pds-contrast-low` | `--p-color-contrast-low` | Shell.css, Column.css |
| `--pds-contrast-medium` | `--p-color-contrast-medium` | Card.css, ErrorBoundary.tsx |
| `--pds-notification-success` | `--p-color-success` | Card.css |
| `--pds-notification-success-soft` | `--p-color-success-frosted` | Card.css |
| `--pds-notification-warning` | `--p-color-warning` | Card.css, SessionRows.css |
| `--pds-notification-warning-soft` | `--p-color-warning-frosted` | SessionRows.css |
| `--pds-notification-error` | `--p-color-error` | Card.css, SessionRows.css |
| `--pds-notification-error-soft` | `--p-color-error-frosted` | SessionRows.css |
| `--pds-state-hover` | `--p-color-frosted` | Shell.css, Card.css, Column.css |
| `--pds-state-focus` | `--p-color-focus` | Card.css |
| `--pds-shadow-sm` | `--p-shadow-sm` | Card.css, Column.css |
| `--pds-shadow-md` | `--p-shadow-md` | KanbanBoard.css |
| `--pds-radius-sm` | `--p-radius-sm` | Card.css, Column.css, Shell.css |
| `--pds-radius-md` | `--p-radius-md` | Column.css, KanbanBoard.css |
| `--pds-spacing-xs` | `--p-spacing-static-xs` | Card.css, Column.css |
| `--pds-spacing-sm` | `--p-spacing-static-sm` | Card.css, Column.css |
| `--pds-spacing-md` | `--p-spacing-static-md` | FilterPanel.css, KanbanBoard.tsx |
| `--pds-border-default` (alias) | `--p-color-contrast-low` | Shell.css, FilterPanel.css, SessionRows.css |
| `--pds-text-default` (alias) | `--p-color-primary` | Shell.css |
| `--pds-border-subtle` (undeclared) | `--p-color-contrast-low` | Card.css |
| `--pds-text-subtle` (undeclared) | `--p-color-contrast-medium` | Card.css |
| `--pds-grid-gap` (undeclared, fallback 8px) | `--p-spacing-static-sm` | Shell.css |
| `--pds-grid-margin` (undeclared, fallback 16px) | `--p-spacing-static-md` | Shell.css |

All PDS mappings value-verified against `node_modules/@porsche-design-system/components-react/global-styles/`.

### 3b. Tailwind Utility (0 tokens)

No `--pds-*` token maps to a Tailwind utility class. All consumed tokens have direct PDS `--p-*` equivalents.

### 3c. Custom-Keep (1 token)

| Token | Rationale | Replacement |
|---|---|---|
| `--pds-signal-claimed` | No PDS purple token exists. Used for "claimed" card signal. | Move to `custom-tokens.css` as `--custom-signal-claimed` with `light-dark()` |

### 3d. Dead-Delete (11 tokens — removed with tokens.css)

| Token | Rationale |
|---|---|
| `--pds-contrast-high` | Defined, never consumed in any CSS/TSX |
| `--pds-notification-info` | Defined, never consumed |
| `--pds-notification-info-soft` | Defined, never consumed |
| `--pds-state-active` | Defined, never consumed (value = hover) |
| `--pds-state-disabled` | Defined, never consumed |
| `--pds-shadow-lg` | Defined, never consumed |
| `--pds-radius-lg` | Defined, never consumed |
| `--pds-radius-xl` | Defined, never consumed |
| `--pds-spacing-lg` | Defined, never consumed |
| `--pds-spacing-xl` | Defined, never consumed |
| `--pds-spacing-2xl` | Defined, never consumed |

### 3e. Summary

| Classification | Count | Action |
|---|---|---|
| PDS equivalent | 27 (21 direct + 2 aliases + 4 undeclared) | `--pds-*` → `--p-*` at each usage site |
| Tailwind utility | 0 | — |
| Custom-keep | 1 | Move to `custom-tokens.css` |
| Dead-delete | 11 | Deleted with `tokens.css` |
| **Total classified** | **39** | |

## 4. Grep-Verified Coverage

Source files containing `--pds-*` (non-test): `tokens.css`, `Shell.css`, `Card.css`, `Column.css`, `FilterPanel.css`, `SessionRows.css`, `KanbanBoard.css`, `KanbanBoard.tsx`, `ErrorBoundary.tsx`. Zero unclassified references — every `var(--pds-*)` call maps to a row in §3.

## 5. Affected Test Files

| Test File | `--pds-*` Refs | Action | Rationale |
|---|---|---|---|
| `TokenArchitecture_1535.test.ts` | 36 | **Retired** | Validated tokens.css structure (file deleted); test removed by downstream work |
| `TokenArchitecture_1543.test.ts` | 37 | **Retired** | Same — later iteration; test removed |
| `BoardVisualDesign.test.tsx` | 30+ | **Update** | Token name assertions `--pds-*` → `--p-*` |
| `Card.css.test.ts` | 12 | **Update** | Signal color assertions |
| `Card.css.supplemental.test.ts` | — | **Update** | Absorbed content from former CardCSS_1546 |
| `Column.css.test.ts` | 12 | **Update** | Layout token assertions (formerly ColumnCSS_1547) |
| `ShellSecondaryCSS.base.test.tsx` | 5 | **Update** | Consolidated Shell token + migration assertions (formerly _1542 + _1550) |
| `Shell.secondary-css.test.tsx` | 0 | **Keep** | FilterPanel + KanbanBoard token assertions; already uses `--p-*` equivalents (formerly part of Shell secondary CSS family) |
| `PDSHexScan.test.ts` | 16 | **Update** | Scanner exclusion regex `--pds-` references (formerly PDSHexScan_1395) |
| `PdsMigration.test.tsx` | 0 | **Keep** | Verifies element-to-PDS component migration; no CSS token references |
| `CardSignalModel.test.tsx` | 1 | **Keep** | Comment-only reference (formerly CardSignalModel_1544) |
| `ThemeLightTokenScan.test.ts` | 3 | **Keep** | Checks `--pds-theme-light-*` legacy pattern guard (formerly ThemeLightTokenScan_1552) |
| `PdsColorSchemeBridge.test.ts` | 0 | **Keep** | Validates custom-tokens.css exists (successor to deleted tokens.css); no `--pds-*` refs (formerly PdsColorSchemeBridge_1555) |

## 6. Recommendation (confidence: 0.90)

No new follow-up tasks needed. The downstream tasks already exist: #1600 (tests for migration) and #1603 (atomic migration implementation). This provenance map is the input artifact both tasks consume.

Challenge: FALLBACK — challenger subagent not invoked (info-only classification, no contested recommendation).

## 7. Follow-up Tasks

None created — #1600 and #1603 already exist in pipeline at `research` status.
