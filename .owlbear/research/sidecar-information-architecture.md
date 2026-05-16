# Sidecar Information Architecture

> **Owning task:** #1616 — P2-07: Sidecar information architecture
> **Date:** 2026-05-16 **Status:** Complete

## 1. Context and Question

The cockpit sidecar panel renders task details in an unoptimized order: History button → Metadata → Editor → Actions. Action controls are buried below the fold. No sections are collapsible. Section headings use raw `<h3>` with no PDS typography scale differentiation. The task requires reordering by usage frequency, adding accordion/collapsible patterns for low-frequency content, and applying PDS typography hierarchy.

**Current sidecar structure (top to bottom):**
- Shell level: sidecar-header (h2 title) → DecisionViewport → p-tabs (Detail | Activity)
- Detail tab: History button → Metadata (7 read-only fields) → Editor (TaskFieldsEditor) → Actions (conditional buttons) → HistorySubtab (conditional) → ConflictBanner

## 2. Sources Studied

| # | Source | Relevance | What was taken |
|---|--------|-----------|----------------|
| 1 | PDS Accordion API (designsystem.porsche.com/v3/components/accordion/api) | 0.9 | Props: heading, heading-tag (h1-h6), open, size (small\|medium), compact, update event |
| 2 | PDS Accordion Usage (designsystem.porsche.com/v3/components/accordion/usage) | 0.9 | "Use for large amounts of content." "Don't use for essential content." "Don't add divider on top of first item." |
| 3 | PDS PHeading API (designsystem.porsche.com/v3/components/heading/api) | 0.8 | Heading sizes: small → xx-large. Already documented in #1607 research. |
| 4 | Codebase: DetailTab.tsx, Shell.tsx, Shell.css | 1.0 | Current section order, data-region attributes, initialSubtab routing, dual render paths |
| 5 | Codebase: test suites (DetailTab.test.tsx, SidecarUX.test.tsx, TaskDetailModel.test.tsx) | 1.0 | DOM contract: field-* selectors, history routing, detail-loaded sentinel (field-id) |
| 6 | Jira Cloud docs: Configure work item details | 0.7 | Actions/transitions prominent, description middle, activity bottom. Configurable field layout. |
| 7 | PDS React package: PAccordion export | 0.9 | Confirmed available via runtime check. Not yet used in codebase. |

## 3. Analysis

### AC1: Section Reordering by Usage Frequency

| Section | Usage Frequency | Rationale | Position |
|---------|----------------|-----------|----------|
| Editor (TaskFieldsEditor) | **Highest** | Every task interaction involves viewing/editing fields. Always-present surface. | 1st |
| Actions (move/unclaim/unblock) | **High** | Primary workflow operations. State-dependent — some tasks show no actions. | 2nd |
| Metadata (read-only fields) | **Low** | Reference-only (ID, status, created, claimed, dep_status). Rarely needed after initial glance. | 3rd |
| History | **Low** | Navigation destination via initialSubtab, but used infrequently during normal task work. | 4th |

**Editor before Actions rationale:** Actions is conditional (empty when no backward target, task unclaimed, and unblocked). Editor is always present with editable fields. Placing an empty Actions section at position 1 wastes prominent space. Jira/Linear both put description/fields above actions.

**DecisionViewport scope:** DecisionViewport sits at Shell level (above p-tabs), not inside DetailTab. Its placement is correct — pending decisions are urgent and belong above tab content. No IA change needed at Shell level. The AC scopes to "section ordering" within the sidecar's Detail tab.

### AC2: Accordion for Low-Frequency Content

| Approach | Mechanism | Sections Wrapped | Risk |
|----------|-----------|-----------------|------|
| A: PAccordion for Metadata only | `PAccordion compact heading="Metadata" heading-tag="h3"` | Metadata | Low — clear low-frequency reference data |
| B: PAccordion for Metadata + History | Both in accordions | Metadata, History | **Medium** — History has initialSubtab routing; accordion must auto-open on route |
| C: PAccordion for all sections | Every section collapsible | All | **High** — violates PDS guideline ("Don't use for essential content") |
| D: CSS-only collapse (no PAccordion) | `details/summary` or custom toggle | Any | Medium — not PDS-native, no theme integration |

**Recommendation: Option A** — Metadata-only accordion. (Confidence: 0.80)

History should remain a **conditional render** (current pattern) because:
1. `initialSubtab === 'history'` from ActivityTab handoff requires History to be visible on mount — accordion doesn't satisfy this without additional open-state syncing logic
2. History button already serves as the toggle; wrapping in accordion adds a redundant affordance
3. SidecarUX tests assert the ActivityTab → History handoff path

PAccordion renders slot content in DOM regardless of `open` state (uses CSS height/opacity animation, not conditional mounting) — verified from PDS source. This means `field-*` test selectors inside a closed Metadata accordion remain queryable. However, Vitest's `getByTestId` on hidden content may need `{ hidden: true }` option depending on testing-library configuration.

**PDS bootstrap impact:** Adding `p-accordion` to the page requires updating `componentsReady` call in `main.tsx` if it's element-specific, or confirming the existing call covers dynamically added elements.

### AC3: Typography Hierarchy

Three visually distinct heading levels required. Without depending on #1607 (still backlog):

| Level | Component | Visual Weight | Used For |
|-------|-----------|--------------|----------|
| 1 (largest) | `PHeading size="large" tag="h2"` | Bold, ~24px | Task title in sidecar-header (Shell.tsx) |
| 2 (medium) | `PHeading size="medium" tag="h3"` | Semi-bold, ~18px | Always-visible sections: Editor, Actions |
| 3 (smallest) | `PAccordion heading-tag="h3" size="small"` | PDS accordion heading style, ~14px | Metadata accordion heading |

PAccordion's built-in heading is visually distinct from PHeading sizes — the chevron icon and border treatment create clear differentiation even at the same semantic level (h3).

**Overlap with #1607:** Task #1607 researched PHeading/PDivider/padding. Task #1616 is IA — section ordering and accordion. Typography is a shared concern. The builder for #1616 should implement PHeading for section headings even though #1607 also plans to. If #1607 ships first, #1616 adjusts. If #1616 ships first, it establishes the heading pattern.

### Width and Dual-Path Considerations

| Surface | Width | Notes |
|---------|-------|-------|
| Desktop aside | 360px | PAccordion compact fits well |
| Tablet aside | 240px | Tight — PAccordion compact uses minimal padding. Verify chevron and heading don't clip. |
| Mobile p-sheet | max 70vh × 100vw | PAccordion works at any width. Verify touch target size (PDS accordion button ≥ 44px). |

Both Shell.tsx render paths (desktop aside and mobile p-sheet) contain identical content structure. All IA changes (section order, accordion) must apply to **both branches**. The sidecar-structure-pds.md (#1607) already flagged this dual-path parity requirement.

## 4. Recommendation

**Reorder Detail tab sections (Editor → Actions → Metadata accordion → History) and wrap Metadata in PAccordion compact.** (Confidence: 0.78)

This is the simplest approach that satisfies all three AC without breaking existing History routing or DOM contracts.

Challenge: `reconsider` — confidence in original: 0.58. Key revisions made:
- Removed History from accordion (initialSubtab routing conflict)
- Added DecisionViewport scope analysis (no change needed — Shell-level)
- Added DOM contract analysis for collapsed accordion content
- Added tablet (240px) and mobile width evidence
- Decoupled from #1607 — typography recommendations are self-contained
- Clarified Actions placement (2nd not 1st) given conditional content

## 5. Follow-up Tasks

No additional follow-up tasks needed. Task #1616 itself covers the full implementation scope. The test-first task (#1611) was archived with ref to #1616 — builder writes both tests and implementation.

Testing approach for builder:
- Verify DOM order of `data-region` attributes matches new sequence
- Verify `p-accordion` present wrapping metadata content
- Verify `field-*` selectors accessible inside closed accordion
- Verify PHeading/PAccordion heading sizes create ≥3 distinct hierarchy levels
- Verify both desktop and mobile render paths have identical section order
