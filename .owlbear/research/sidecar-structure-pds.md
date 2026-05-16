# Sidecar Structure — Padding, Sections, Typography

> **Owning task:** #1607 — P1-11: Sidecar structure — padding, sections, typography
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

The cockpit sidecar panel (`Shell.tsx` `<aside class="shell__sidecar">`) has zero internal padding, no section dividers, and no PDS typography hierarchy. The AC requires:

1. Sidecar content uses `--p-spacing-md` or greater padding on all sides
2. At least 3 visually distinct sections with PDS typography scale differentiation
3. Visible section dividers between content blocks

The sidecar currently contains: `sidecar-header` (h2 title), `DecisionViewport`, `p-tabs` wrapping `DetailTab` (history, metadata, body/editor, actions sections) and `ActivityTab`. Raw `<h2>`/`<h3>` tags with no PDS sizing.

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | PDS v4 Spacing docs (designsystem.porsche.com/v3/styles/spacing) | 0.9 | Token names: `--p-spacing-static-md` (16px), `--p-spacing-fluid-md` (clamp 16–36px). "Use m as default since it corresponds to grid-gap." |
| 2 | PDS v4 Typography docs (designsystem.porsche.com/v3/styles/typography) | 0.9 | Heading scale: xx-large → small. "Pair heading with text one or two steps below." |
| 3 | PDS PHeading API (designsystem.porsche.com/v3/components/heading/api) | 0.9 | Props: `size` (small/medium/large/x-large/xx-large), `tag` (h1–h6). Default size: xx-large. |
| 4 | PDS PDivider API (designsystem.porsche.com/v3/components/divider/api) | 0.8 | Self-closing `<PDivider />`. Orientation: horizontal (default) or vertical. Color inherits from theme. |
| 5 | Codebase: Shell.tsx + Shell.css + DetailTab.tsx | 1.0 | Current sidecar structure, existing data-region attributes, section layout |
| 6 | PDS v4 global-styles/index.css (node_modules) | 0.9 | Confirmed token definitions: `--p-spacing-static-md: 16px`, typescale tokens |

## 3. Analysis

### AC1: Padding Token Selection

| Token | Value | Type | Fit |
|-------|-------|------|-----|
| `--p-spacing-static-md` | 16px | Fixed | Best — sidecar is fixed-width (360px), no viewport scaling needed |
| `--p-spacing-fluid-md` | clamp(16px, 1.25vw+12px, 36px) | Responsive | Overkill — sidecar width doesn't change with viewport |
| `--p-spacing-static-lg` | 32px | Fixed | Too generous for 360px panel — wastes 18% of width |

**Recommendation:** `--p-spacing-static-md` (16px) for sidecar content padding. Applied to `#shell-sidecar-content` via CSS.

**Note on AC text:** AC says `--p-spacing-md` which doesn't exist as a token. PDS v4 has `--p-spacing-static-md` (fixed) and `--p-spacing-fluid-md` (responsive). Both satisfy "md or greater." Recommend `--p-spacing-static-md`.

### AC2: Typography Hierarchy

Three approaches compared:

| Approach | Mechanism | Test Complexity | DOM Nodes | PDS Alignment |
|----------|-----------|-----------------|-----------|---------------|
| A: `PHeading` React components | `<PHeading size="..." tag="...">` | Medium — query `p-heading` custom elements | More (shadow DOM) | Highest — PDS-recommended |
| B: CSS typography style imports | `headingMediumStyle` etc. as inline styles | Low | Fewer | High — PDS docs list as alternative |
| C: Tailwind typography utilities | `text-heading-md` class | Low | Fewest | Medium — PDS Tailwind integration |

**Recommendation:** Option A (`PHeading`/`PText`) — already imported pattern in codebase (`PButton`, `PBanner`, `PText` all used). PDS docs explicitly recommend components over style imports "for heading styling and hierarchy."

**Proposed hierarchy (3 distinct PHeading sizes for AC2):**

| Section | Component | Size | Tag | Visible in |
|---------|-----------|------|-----|------------|
| Task title (sidecar-header) | `PHeading` | `large` | `h2` | Shell.tsx |
| Primary section labels (Metadata, Editor) | `PHeading` | `medium` | `h3` | DetailTab.tsx |
| Secondary section labels (Actions, History) | `PHeading` | `small` | `h3` | DetailTab.tsx |

Three distinct PHeading sizes (large, medium, small) satisfy "at least 3 visually distinct sections with heading sizes that differ." Body text uses `PText size="small"` for metadata fields but this doesn't count toward the AC — the 3 tiers are all heading-level.

**Existing PHeading precedent:** `PHeading` is already imported and used in `ArchivalModal.tsx` and `ResolveModal.tsx` (dialog titles), confirming the component works in the project.

### AC3: Section Dividers

| Approach | Mechanism | Theme-aware | Semantic |
|----------|-----------|-------------|----------|
| A: `<PDivider />` component | PDS custom element | Yes (auto) | Yes (renders `<hr>`) |
| B: CSS `border-bottom` with `--p-color-*` | Manual border | Manual | No |

**Recommendation:** Option A (`<PDivider />`) — self-closing, theme-aware, renders semantic `<hr>`. Zero configuration needed.

**Placement (all content blocks, including DecisionViewport):**
1. Between sidecar-header and DecisionViewport (Shell.tsx)
2. Between DecisionViewport and p-tabs (Shell.tsx)
3. Between metadata and editor sections (DetailTab.tsx)
4. Between editor and actions sections (DetailTab.tsx)

**Dual render-path:** Shell.tsx has two content branches — mobile (`p-sheet`) and desktop. Both render identical section structure (`sidecar-header`, `DecisionViewport`, `p-tabs`). All structural changes (padding, dividers, headings) must be applied to BOTH branches. Builder must verify parity.

### Token Migration Dependency

The codebase currently uses `--pds-*` prefix (custom `tokens.css`). PDS v4 ships `--p-*`. Token migration is task #1603 (separate, also in research).

This task should use `--p-*` tokens because:
1. AC text explicitly says `--p-spacing-md`
2. PDS global-styles import (#1594, Batch 0) already completed — `--p-*` tokens are available on `:root`
3. PDS React components (`PHeading`, `PDivider`) use `--p-*` internally
4. Using `--pds-*` would couple this task to a token alias layer that #1603 will delete

### Risk: Test-Task Dependency (#1602 Archived)

Task #1602 (test-first for sidecar structure) was archived/deprecated with ref to #1607. This means test-writing is folded into the implementation task. Builder must write both tests and implementation.

## 4. Recommendation

**Use PDS React components (`PHeading`, `PDivider`) + `--p-spacing-static-md` token for padding. (Confidence: 0.85)**

This is the PDS-documented approach for heading hierarchy and dividers. Low risk — all components already available in the installed package (v4.1.0), and the pattern (`PButton`, `PText`, `PBanner`) is already established in the codebase.

Challenge: reconsider → revised — confidence after revision: 0.82.

Challenger raised valid concerns: (1) AC-2 required 3 heading sizes, not 2+body-text — fixed to large/medium/small PHeading. (2) DecisionViewport omitted from divider plan — added. (3) Dual render-path in Shell.tsx not addressed — noted for builder. (4) PHeading already used in modals (corrected evidence). Core recommendation (PDS components + --p-spacing-static-md) unchanged.

## 5. Testing Strategy

- **Vitest unit tests (test-first, since #1602 archived into #1607):**
  - Assert `#shell-sidecar-content` has CSS padding using `--p-spacing-static-md` or equivalent ≥16px
  - Assert 3+ `p-heading` elements with different `size` attributes in sidecar DOM
  - Assert `p-divider` elements between content blocks
  - Assert both mobile and desktop render paths have matching structure
- **Regression:** Existing Shell.test.tsx, SidecarCollapse_1541/1549 tests must pass unchanged
- **proof_bundle:** behavioral — Vitest assertions on DOM structure

## 6. Follow-up Tasks

- #1607 moves to backlog for test-writing + implementation (combined since #1602 was archived)
- No new follow-up tasks needed — T1 (autonomous): CSS + component swap, no new capability
