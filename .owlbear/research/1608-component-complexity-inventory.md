# Component Complexity Inventory — PDS v4 Migration

> **Owning task:** #1608 — P2-01: Component complexity inventory
> **Date:** 2026-05-17 **Status:** Complete

## 1. Context and Question

Which raw HTML elements remain in `serve/cockpit/web/src/` after Batch 0–1, and how should each be classified for Phase 2 migration? Must categorize every interactive/display element (per AC-3: buttons, headings, selects, lists, web-component elements, modals, form controls) as simple swap, complex integration, or intentional native.

**Scope definition:** "Interactive/display elements" = elements from the AC-3 list: buttons, headings, selects, lists, web-component elements, modals, and form controls. Generic containers (`div`, `span`, `section`, `main`, `nav`), semantic inline text (`strong`, `em`, `code`), and presentational SVG (`svg`/`path` inline icons inside intentional-native buttons) are structural HTML with no PDS component equivalent — excluded from classification scope.

## 2. Sources Studied

| # | Source | Type | Relevance |
|---|--------|------|-----------|
| 1 | Codebase grep — all `.tsx` in `src/` (excl. tests) | local scan | 1.0 |
| 2 | PDS v4 React wrapper exports (`node_modules/@porsche-design-system/components-react/`) | local package | 1.0 |
| 3 | #1614 research (`.owlbear/research/1614-simple-component-swaps.md`) | prior inventory | 0.9 |
| 4 | PDS v4 component docs (`designsystem.porsche.com/v4/`) | web | 0.8 |
| 5 | Test files asserting DOM contracts (`PdsSimpleSwaps`, `PdsMigration`, `SidecarCollapse`, `BoardVisualDesign`, `PModal.coverage`) | local tests | 1.0 |
| 6 | Existing Phase 2 task ACs (#1616, #1617, #1618) | kanban archive | 0.9 |

## 3. Analysis

### 3.1 Buttons (7 raw `<button>`, 0 remaining swaps)

All three migrateable buttons (ActivityTab session-row, DRStatusIndicator resolve-button, ErrorBoundary retry) were migrated to PButton in #1614. Seven remaining buttons carry explicit `data-pds-exception` markers or have test-asserted native tag identity:

| File | Element | Classification | Evidence |
|------|---------|---------------|----------|
| Shell.tsx:266 | sidecar-collapse | **Intentional native** | `SidecarCollapse.behavior.test.tsx` asserts `tagName === 'BUTTON'` + `aria-expanded`/`aria-controls` contract |
| Shell.tsx:267 | nav-kanban | **Intentional native** | `data-pds-exception="nav-kanban"`; `PdsMigration.test.tsx` asserts marker; contains inline SVG icon |
| KanbanBoard.tsx:278 | filter-toggle | **Intentional native** | `data-pds-exception="filter-toggle"`; `aria-expanded`/`aria-controls` contract |
| ThemeToggle.tsx:23 | theme-toggle | **Intentional native** | `data-pds-exception="theme-toggle"`; `BoardVisualDesign.test.tsx` asserts raw `<button>` tagName |
| HealthBadge.tsx:75 | health-badge | **Intentional native** | `data-pds-exception="status-bar-control"`; popover trigger pattern |
| CleanupPanel.tsx:179 | cleanup-button | **Intentional native** | `data-pds-exception="status-bar-control"` |
| DRStatusIndicator.tsx:76 | dr-indicator | **Intentional native** | `data-pds-exception="status-bar-control"`; popover trigger |

*Note:* Challenger flagged that filter-toggle, health-badge, and cleanup-button tests only assert behavior, not tag identity. However, all carry explicit `data-pds-exception` markers — the PdsSimpleSwaps test exempts any button with this attribute. The marker IS the engineering decision to keep them native (status-bar compact controls where PButton's shadow DOM overhead is undesirable).

### 3.2 Headings — **Fully migrated.** Zero raw `<h1>`–`<h6>` remain. All replaced with PHeading in #1614.

### 3.3 Selects and Options

| File | Element | Classification | Owner | Notes |
|------|---------|---------------|-------|-------|
| FilterPanel.tsx | `PSelect` + `PSelectOption` | **Already migrated** | #1617 (done) | Established migration pattern |
| ArchivalModal.tsx:361,368 | `<option>` inside `<PSelect>` | **Simple swap** | #1618 | → `PSelectOption`; follows #1617 pattern |
| TaskFieldsEditor.tsx:233 | `<option>` inside `<PSelect>` | **Simple swap** | **Unowned** | → `PSelectOption`; needs follow-up task |

### 3.4 Lists (8 `<ul>` + 9 `<li>`, 5 files)

| File | Context | Classification | Rationale |
|------|---------|---------------|-----------|
| DecisionViewport.tsx | DR item list | **Intentional native** | No PDS list component exported |
| DRStatusIndicator.tsx | Popover DR list | **Intentional native** | No PDS list component exported |
| HealthBadge.tsx | Popover issue list | **Intentional native** | No PDS list component exported |
| CleanupPanel.tsx | Skipped items list | **Intentional native** | No PDS list component exported |
| RepairPanel.tsx | Outcome rows (3 lists) | **Intentional native** | No PDS list component exported |

PDS v4 exports no `PList`/`PListItem` component. Lists may benefit from PDS token-based styling (spacing, typography) in Phase 3 polish but cannot be component-migrated.

### 3.5 Web-Component Elements (9 raw `<p-*>` tags)

| File | Element | Classification | Owner | Migration Notes |
|------|---------|---------------|-------|----------------|
| Shell.tsx:314 | `<p-sheet>` | **Complex integration** | #1616 | PSheet React wrapper available |
| Shell.tsx:342,440 | `<p-tabs>` ×2 | **Complex integration** | #1616 | Uses deprecated `tabChange` event (v3); must migrate to PTabs `onUpdate` prop |
| Shell.tsx:343,408,441,506 | `<p-tabs-item>` ×4 | **Complex integration** | #1616 | Uses `ref` + `setAttribute('label')` pattern → PTabs/PTabsItem React wrappers |
| DetailTab.tsx:196 | `<p-accordion>` | **Already migrated** | #1616 (done) | Web-component tag used correctly; PAccordion import available but current usage works |
| Card.tsx:143 | `<p-icon>` | **Simple swap** | #1615 (done) | PIcon React wrapper available |

**Key risk:** Shell `tabChange` → PTabs `onUpdate` migration requires updating 5+ test files that dispatch `tabChange` custom events.

### 3.6 Modals and Dialog Surfaces (7 total surfaces)

| File | Element | Classification | Owner | Notes |
|------|---------|---------------|-------|-------|
| ConfirmDialog.tsx | `<PModal>` | **Already migrated** | #1618 (done) | Wrapper modal with dialog semantics enforced via `aria` |
| ResolveModal.tsx | `<PModal>` | **Already migrated** | #1618 (done) | Decision-request modal flow migrated |
| ArchivalModal.tsx | `<PModal>` | **Already migrated** | #1618 (done) | Archival workflow modal migrated |
| CleanupPanel.tsx:92 | `<div role="dialog" aria-modal="true">` | **Complex integration** | **Unowned** | Confirm overlay uses custom focus trap/keyboard handling; candidate for migration to a shared modal wrapper |
| RepairPanel.tsx:72 | `<div role="dialog" aria-modal="true">` | **Complex integration** | **Unowned** | Confirm overlay includes file-preview list + ESC handling; same migration class as CleanupPanel |
| DRStatusIndicator.tsx:92 | `<div role="dialog">` | **Intentional native** | — | Anchored status-bar popover behavior with explicit focus/position management; not part of modal migration scope |
| HealthBadge.tsx:91 | `<div role="dialog">` | **Intentional native** | — | Anchored status-bar popover behavior with explicit focus/position management; mirrors DRStatusIndicator |

### 3.7 Form Controls

| File | Element | Classification | Owner | Notes |
|------|---------|---------------|-------|-------|
| ResolveModal.tsx:241 | `<fieldset>` | **Complex integration** | #1618 | Part of radio→PRadioGroup migration |
| ResolveModal.tsx:242 | `<legend>` | **Complex integration** | #1618 | Absorbed into PRadioGroup `label` prop |
| ResolveModal.tsx:245,258,271 | `<input type="radio">` ×3 | **Complex integration** | #1618 | → PRadioGroup + PRadioGroupOption; group-based API |
| ResolveModal.tsx:244,257,270 | `<label>` ×3 | **Complex integration** | #1618 | Absorbed into PRadioGroupOption `label` prop |
| ArchivalModal.tsx:351,377 | `<label>` ×2 | **Intentional native** | — | Wrapping `<PSelect>` (already PDS); HTML label association preserved |

### 3.8 Other Elements (anchor)

| File | Element | Classification | Owner | Notes |
|------|---------|---------------|-------|-------|
| DecisionViewport.tsx:52 | `<a>` task reference link | **Simple swap** | **Unowned** | PLinkPure available; uses `preventDefault` + `onClick` pattern; test accepts `button` or `a` |

## 4. Recommendation

**Confidence: 0.82**

The inventory is complete for the AC-3 scope. Four unowned migration targets were identified:
1. TaskFieldsEditor `<option>` → `PSelectOption` (simple swap, ~5 LOC)
2. DecisionViewport `<a>` → `PLinkPure` (simple swap, ~10 LOC)
3. CleanupPanel confirm overlay `div[role="dialog"]` → shared modal pattern (complex integration)
4. RepairPanel confirm overlay `div[role="dialog"]` → shared modal pattern (complex integration)

The two simple swaps are already routed via follow-up #1634. The two confirm-overlay dialogs require one additional follow-up task.

Challenge: proceed — confidence in original revised from 0.85 to 0.82 after challenger identified: (1) missing `<legend>` element (added to §3.7), (2) misclassified `<option>` elements in ArchivalModal/TaskFieldsEditor (reclassified as simple swap), (3) incorrect DecisionViewport `<a>` routing to #1616 (corrected to unowned), (4) uneven intentional-native rationale (added marker-as-decision reasoning in §3.1 note). Accepted all four challenges; adjusted classifications and routing.

## 5. Dependency Graph and Parallelism

All Phase 2 test tasks depend only on this inventory (#1608) and can proceed in parallel:

```
#1608 (this inventory)
  ├─→ #1609 (tests: simple swaps) → #1614 (impl) ✅ DONE
  ├─→ #1610 (tests: card visual) → #1615 (impl) ✅ DONE
  ├─→ #1611 (tests: sidecar IA) → #1616 (impl) ✅ DONE
  ├─→ #1612 (tests: filter panel) → #1617 (impl) ✅ DONE
  └─→ #1613 (tests: modals) → #1618 (impl) ✅ DONE
```

No inter-task dependencies within Phase 2 — all five streams are independent. Consolidation test #1629 depends on all Phase 2+3 impl tasks completing.

## 6. Follow-Up Tasks

1. **Created:** #1634 — Migrate TaskFieldsEditor `<option>` → `PSelectOption` + DecisionViewport `<a>` → `PLinkPure` (unowned simple swaps discovered by inventory)
2. **New task needed:** Migrate CleanupPanel + RepairPanel confirm overlays from raw `div[role="dialog"]` to a shared modal implementation path (unowned complex integration)
