# Cockpit Visual Audit — 2026-05-14

> Owning task graph: #1534 / draft-board-visual-design.  
> Mode: audit only. No implementation fixes were made during this pass.

## Executive Summary

The board visual-design work improved a few isolated surfaces, mainly task cards and columns, but it did not produce a professional dashboard. The visible result still reads as a raw web app: native buttons remain in primary workflows, the sidecar is almost unstyled, popovers expand the header instead of overlaying it, PDS controls are used inconsistently, and the mobile layout still overflows.

The strongest evidence is visual and structural: screenshots show a composed column/card area sitting inside an unfinished shell. Source review confirms that whole regions have no component CSS or use in-flow native HTML. PDS is loading and hydrated, so the main issue is not asset failure. The main issue is scope and composition: PDS was treated as tokens plus occasional components, not as the organizing UI system.

Overall dashboard quality: **not releasable as a polished Cockpit UI**.

## Evidence Collected

### Screenshots

All screenshots are under `.owlbear/scratch/` and were captured from the live Cockpit app at `http://127.0.0.1:8420`.

| File | View |
|------|------|
| `cockpit-visual-audit-20260514-desktop-home.png` | Desktop board, default state |
| `cockpit-visual-audit-20260514-desktop-detail.png` | Desktop task detail sidecar |
| `cockpit-visual-audit-20260514-desktop-filters.png` | Filter panel open |
| `cockpit-visual-audit-20260514-desktop-dr-popover.png` | Decision-request indicator open |
| `cockpit-visual-audit-20260514-desktop-health-popover.png` | Health indicator open |
| `cockpit-visual-audit-20260514-context-menu.png` | Board card context menu |
| `cockpit-visual-audit-20260514-dark-home.png` | Dark scheme board |
| `cockpit-visual-audit-20260514-tablet-home.png` | Tablet viewport |
| `cockpit-visual-audit-20260514-mobile-home.png` | Mobile viewport |
| `cockpit-visual-audit-20260514-metrics.json` | DOM/layout metrics snapshot |

### Runtime And Test Signals

- Backend health endpoint returned `{"status":"ok"}`.
- PDS local assets were requested from `/porsche-design-system/components/...` and returned 200 in focused probes.
- PDS custom elements such as `p-button`, `p-select`, `p-tabs`, `p-text`, and `p-multi-select` hydrate.
- Playwright `networkidle` is not a reliable load condition because Cockpit keeps SSE/EventSource open.
- Browser console/page evidence included repeated `Unexpected token '<'` errors; root cause was not isolated in this audit.
- PDS emitted select-value warnings for values such as `critical` and empty string not being present in the select options.

Targeted validation:

| Command | Result |
|---------|--------|
| `npm run lint:css` | Passed |
| `npm run test:e2e -- --reporter=list responsive-layout-1391.spec.ts pds-scheme-dark-1555.spec.ts accessibility-1395.spec.ts` | 43 passed, 3 failed |

Failing E2E cases:

1. `accessibility-1395.spec.ts:186` — axe `scrollable-region-focusable`; `.column-body` scrollable regions are not keyboard focusable.
2. `responsive-layout-1391.spec.ts:168` — document-level horizontal overflow at 320px.
3. `responsive-layout-1391.spec.ts:306` — board content requires document-level horizontal scrolling at 320px.

### Files Inspected

- `.owlbear/briefs/draft-board-visual-design/brief.md`
- `serve/cockpit/web/src/Shell.tsx`
- `serve/cockpit/web/src/Shell.css`
- `serve/cockpit/web/src/KanbanBoard.tsx`
- `serve/cockpit/web/src/KanbanBoard.css`
- `serve/cockpit/web/src/tokens.css`
- `serve/cockpit/web/src/main.tsx`
- `serve/cockpit/web/src/hooks/useTheme.ts`
- `serve/cockpit/web/src/components/Card.tsx`
- `serve/cockpit/web/src/components/Card.css`
- `serve/cockpit/web/src/components/Column.tsx`
- `serve/cockpit/web/src/components/Column.css`
- `serve/cockpit/web/src/components/FilterPanel.tsx`
- `serve/cockpit/web/src/components/FilterPanel.css`
- `serve/cockpit/web/src/components/DetailTab.tsx`
- `serve/cockpit/web/src/components/TaskFieldsEditor.tsx`
- `serve/cockpit/web/src/components/ActivityTab.tsx`
- `serve/cockpit/web/src/components/HistorySubtab.tsx`
- `serve/cockpit/web/src/components/DecisionViewport.tsx`
- `serve/cockpit/web/src/components/DRStatusIndicator.tsx`
- `serve/cockpit/web/src/components/HealthBadge.tsx`
- `serve/cockpit/web/src/components/ThemeToggle.tsx`

## Root Causes

1. **The brief solved component cosmetics, not dashboard design.** Card rails, column surfaces, tokens, and dark mode were implemented, but the app shell, sidecar information hierarchy, overlays, filters, and responsive composition were not redesigned as one product surface.

2. **PDS adoption is partial and inconsistent.** PDS is installed, loaded, and sometimes used, but native buttons, inputs, checkboxes, raw lists, raw tabs, and custom icon buttons still appear in core UI. Components are often chosen by availability rather than semantic fit.

3. **The sidecar was effectively left as structural HTML.** The worst visual surface is not the board. It is the right panel: decision requests, detail text, activity, tabs, collapse control, and empty states lack layout and hierarchy.

4. **Overlay behavior is structurally wrong.** Health and DR popovers are in-flow divs. Opening them increases the header height and pushes the application layout around. Cleanup states have the same inline-dialog risk.

5. **Tests accepted reachability as design quality.** Current E2E tests check that regions exist, have positive dimensions, or are keyboard-reachable. They do not fail on raw native controls, poor hierarchy, weak spacing, or professional visual regression.

6. **Mobile was treated as reachable, not usable.** Some tests pass because controls are present at 320px, but the shell and board still overflow horizontally and screenshots show cramped composition.

## Severity-Ranked Findings

### Critical: Sidecar Is The Main Visual Failure

Observed: the sidecar has no coherent internal layout. Decision requests render as a visible bullet list plus native buttons. The collapse control is a text button. The detail tab shows raw metadata spans and markdown without a typographic system. The activity tab is sparse and weakly organized.

Why it matters: this is the primary inspector area for selected tasks and pending decisions. It should feel like a dense operational panel. Instead it looks like unstyled debug output beside the board.

Evidence: `DecisionViewport.tsx` returns `ul`, `li`, and native `button` elements with no companion CSS. `DetailTab.tsx` has no dedicated CSS. `Shell.css` styles the sidecar container border but not its content architecture.

Needed direction: redesign the sidecar as an inspector with explicit sections, spacing, headers, metadata rows, tab styling, and deliberate empty states. Decide whether pending decision requests belong in the same rail or deserve a separate queue/sheet.

### Critical: Popovers And Dialogs Are In-Flow

Observed: opening Health or DR details expands the status bar instead of showing a floating layer. The health view can make the header hundreds of pixels tall.

Why it matters: this breaks dashboard stability. Header controls should not reflow the board and sidecar when opened.

Evidence: `HealthBadge.tsx` and `DRStatusIndicator.tsx` create plain `div role="dialog"` popovers without overlay positioning or PDS `PPopover`. Cleanup confirmation/result states also render inline in the status-bar area.

Needed direction: replace in-flow popovers with PDS `PPopover`, `PModal`, `PSheet`, or an intentionally positioned local overlay. The decision should be consistent across Health, DR, Cleanup, archival, and edit confirmations.

### High: Filters And Dropdowns Are Under-Designed And Misusing PDS

Observed: the visible filter toggle is a native button. The filter panel has minimal container styling, large blank space, weak labels, a raw text input, a raw checkbox/switch, and select warnings.

Why it matters: this is a direct match for the user-visible complaint that dropdowns have no design. Filtering is a core board workflow and currently looks bolted on.

Evidence: `KanbanBoard.tsx` uses native `<button data-testid="filter-toggle">`. `FilterPanel.tsx` uses a raw `<input type="text">`, raw `<input type="checkbox">`, `PSelect` with native `<option>` children, and only a thin `.filter-panel` CSS wrapper. `TaskFieldsEditor.tsx` repeats the `PSelect` plus native `<option>` pattern.

Needed direction: use `PInputSearch` or `PInputText`, `PSwitch` or a proper checkbox pattern, `PSelectOption` rather than native `option`, and a real filter-toolbar/panel layout.

### High: PDS Is Present But Not Governing The Interface

Observed: PDS custom elements hydrate and tokens exist, but the page still shows native controls and raw HTML in key places.

Why it matters: using a design system as occasional decoration does not create a system. It also creates mixed interaction patterns: PDS buttons beside native buttons, PDS text inside native buttons, raw tabs beside PDS selects.

Evidence: native controls remain in `ThemeToggle.tsx`, `KanbanBoard.tsx`, `DecisionViewport.tsx`, `FilterPanel.tsx`, and sidecar collapse in `Shell.tsx`. PDS buttons are also overused for status indicators and nav, where tags, badges, pure buttons, popovers, tabs, or sheets would be more appropriate.

Needed direction: adopt a PDS-first component policy with explicit exceptions. Pick components by semantic role, not by visual convenience.

### High: Mobile And Tablet Composition Are Not Acceptable

Observed: 320px tests fail for document-level overflow. Screenshots show a cramped shell and board. Tablet layout passes some width assertions but still feels like desktop squeezed into a smaller frame.

Why it matters: the dashboard does not need to be a mobile-first consumer app, but it must not horizontally overflow or hide critical controls at common small widths.

Evidence: targeted E2E failures at `responsive-layout-1391.spec.ts:168` and `responsive-layout-1391.spec.ts:306`.

Needed direction: define supported breakpoints and behavior. Likely options: board-first mobile with sidecar as sheet, horizontally scrollable columns inside a contained board region, or explicit desktop-only support with a dignified small-screen message.

### High: Visual Test Gates Are Too Weak

Observed: CSS lint passes while the UI remains poor. Many E2E tests assert that surfaces exist, not that they are visually acceptable. Some tests may preserve current weak patterns, such as native controls or reachability-only mobile behavior.

Why it matters: the project can repeatedly ship false-green visual work. This is exactly what happened here.

Evidence: targeted run had 43 passing E2E tests despite obvious design failures in the screenshot set.

Needed direction: add screenshot regression or visual approval gates for desktop home, selected detail, filter panel, DR/health overlays, dark mode, tablet, and mobile. Add tests that reject in-flow popovers and document overflow.

### Medium-High: Cards Are Better, But Still Too Thin For Operations

Observed: cards now have surface, shadow, selected state, and a left signal rail. But they render almost only the title.

Why it matters: a kanban dashboard card needs enough metadata to scan work without opening every detail: ID, priority, blocked/claimed state, tags, and age/session signals where relevant.

Evidence: `Card.tsx` renders the task title as the only visible content. Priority is present as `data-priority` but not rendered. Tags and blocked/claimed states are mostly color-only or absent.

Needed direction: add compact metadata hierarchy, not a busy card. PDS tags/badges/icons are available.

### Medium: Column Work Is Partial

Observed: columns are one of the better areas, but empty states are plain text, status labels expose internal names, and scrollable bodies trigger axe failures.

Why it matters: columns frame the board. Unstyled empty states and keyboard-inaccessible scroll regions undercut the improved surfaces.

Evidence: `.column-body` axe failure in decision-resolution view. Empty state text such as `No in-progress tasks` remains data-driven rather than polished.

Needed direction: make column bodies keyboard-accessible, improve empty-state copy and layout, and decide whether completed/status-specific columns need differentiated treatment.

### Medium: Context Menu Is Only Barely Styled

Observed: the context menu has a surface, border, padding, and shadow, but item hierarchy, hover/focus states, destructive/action differentiation, and z-index policy are weak.

Why it matters: context menus are frequent operational controls. They should feel native to the product, not just less raw than before.

Evidence: `KanbanBoard.css` contains only `.kanban-context-menu` container styling.

Needed direction: style menu items, keyboard focus, hover, disabled/destructive states, and layering.

### Medium: Dark Mode Technically Works But Does Not Solve Composition

Observed: dark mode applies color scheme and PDS custom elements respond, but the same layout and hierarchy flaws remain.

Why it matters: theme support can make an unfinished layout look even more like a prototype because contrast and hierarchy problems become more visible.

Evidence: dark screenshot plus PDS scheme test pass.

Needed direction: verify dark mode after structural redesign, not before. Add visual dark baselines.

## PDS Capability Comparison

| UI Need | PDS Can Provide | Cockpit Currently Does |
|---------|-----------------|------------------------|
| Primary/secondary actions | `PButton`, `PButtonPure` | Mixes PDS buttons with native buttons and custom `.icon-button` |
| Compact status/count | `PTag`, badges/count patterns | Uses buttons or raw text for Health/DR/status |
| Floating disclosure | `PPopover` | Plain in-flow `div role="dialog"` |
| Modal/sheet workflow | `PModal`, `PSheet` | Inline confirm/result panels in header contexts |
| Search input | `PInputSearch` | Raw text input in filters |
| Text input/editing | `PInputText`, `PTextarea` | PDS in editor areas, raw elsewhere |
| Select options | `PSelect` + `PSelectOption` | `PSelect` with native `option`, causing warnings |
| Multi-select | `PMultiSelect` | Used, but panel composition around it is weak |
| Binary setting | `PSwitch` / checkbox pattern | Raw checkbox for blocked filter |
| Tabs | `PTabs`, `PTabsItem` or hydrated web components | Raw-looking `p-tabs` in sidecar |
| Text hierarchy | `PHeading`, `PText` props | PText often used without size/weight; many spans/divs |
| Task/status chips | `PTag`, icon components | Not rendered on cards; color-only rail signal |
| Tables/lists | `PTable`, text/list patterns | Activity/DR/detail areas use raw or minimal rows |

## Remediation Tracks For Planner

These are not implementation tasks yet. They are planning lanes that should become scoped kanban tasks after the user adds their own findings and the product decisions are resolved.

1. **Shell and sidecar redesign.** Treat the sidecar as a real inspector. Include decision queue, detail, activity, collapse behavior, tabs, empty states, typography, and spacing.
2. **Overlay system.** Replace in-flow popovers/dialogs with a consistent PDS overlay strategy for Health, DR, Cleanup, archival, and edit flows.
3. **Filter and form control system.** Fix filter toggle/panel, select options, search input, blocked switch, editor select/dropdowns, labels, and validation/empty states.
4. **Board card information density.** Add task ID, priority, tags, blocked/claimed/age metadata, and accessible non-color status cues.
5. **Responsive contract.** Decide whether Cockpit supports mobile as a usable interface, a board-only interface, a sheet-based layout, or a desktop-only warning. Then test that contract.
6. **Visual regression and quality gates.** Add screenshot baselines and reject tests for raw native controls in core surfaces, in-flow overlays, document overflow, and missing sidecar spacing.
7. **PDS usage policy.** Define when to use PDS components, when custom CSS is acceptable, and which native controls are prohibited in production UI.

## Decision Gates

Planner should not split implementation tasks until these are answered.

1. **Redesign scope.** Should the next round be a full Cockpit shell/sidecar/filter redesign, or incremental fixes inside the current structure?
2. **Design-system policy.** Should Cockpit adopt PDS-first controls for all visible UI, with explicit exceptions only, or continue mixing native and PDS controls?
3. **Sidecar information architecture.** Should decision requests remain in the sidecar above task detail, move to a dedicated queue/sheet, or become a separate route/panel?
4. **Mobile contract.** Should 320px be a fully supported layout, a constrained board-only layout, or an unsupported viewport with a controlled message?
5. **Visual gate.** Should screenshot regression become required for Cockpit UI work before future visual tasks are accepted?

## Immediate Known Defects

- Fix `.column-body` keyboard accessibility for scrollable regions.
- Fix 320px document horizontal overflow.
- Fix 320px board horizontal overflow or contain it inside an intentional board scroller.
- Replace or correctly implement `PSelect` option children to stop PDS value warnings.
- Investigate repeated `Unexpected token '<'` runtime errors.
- Stop Health/DR/Cleanup panels from expanding the status bar.

## Audit Conclusion

The implemented work should be treated as a foundation, not a finished design. Tokens, dark mode, card surfaces, and column surfaces are useful pieces. The product still needs a dashboard-level design pass that connects shell, sidecar, filters, cards, overlays, and responsive behavior into one coherent cockpit.

The highest-leverage next move is not to tweak colors. It is to make an explicit product decision that the next planning cycle is a Cockpit UI redesign cycle, then let Planner decompose that into bounded implementation tasks.