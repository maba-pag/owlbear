# Cockpit Visual Audit Consolidated

> **Owning task:** #1534 - Board Visual Design / draft-board-visual-design  
> **Date:** 2026-05-14 **Status:** Complete audit, no implementation changes

## 1. Context And Question

The completed Board Visual Design task was supposed to make Cockpit feel like a finished dashboard. Live inspection shows it does not. The board columns/cards are somewhat styled, but the whole product still reads as raw HTML around a lightly styled kanban area.

Audit question: what is wrong visually and structurally, what can Porsche Design System (PDS) provide that Cockpit is not using, and what decisions must be made before Planner decomposes remediation?

## 2. Sources Studied

| Source | What It Proved | Confidence |
|---|---|---:|
| `.owlbear/briefs/draft-board-visual-design/brief.md` | Original scope was token/card/column/theme styling, not a full cockpit redesign | 0.95 |
| Live Cockpit at `http://127.0.0.1:8420` | Actual visual outcome across desktop, dark, tablet, mobile, selected detail, filters, context menu, DR, cleanup | 0.98 |
| Screenshots in `.owlbear/scratch/cockpit-visual-audit/*.png` | Persistent visual evidence for all major states inspected | 0.95 |
| `serve/cockpit/web/src/**/*.{tsx,css}` | Structural causes: missing CSS, raw controls, in-flow overlays, weak sidecar markup | 0.97 |
| PDS React export inventory | Available components include `PPopover`, `PModal`, `PSheet`, `PInputSearch`, `PSwitch`, `PTag`, `PTable`, `PSegmentedControl` | 0.92 |
| PDS docs: home, modal, popover, select, spacing | PDS is intended as a complete component/token/guideline system, not occasional button decoration | 0.86 |
| `npm run lint:css`, `npm run lint:html` | Static lint passes despite poor UI | 0.90 |
| Targeted Playwright E2E | Responsive/a11y still fails: 320px overflow and scrollable-region focusability | 0.94 |

Existing notes reviewed after the independent pass: `.owlbear/research/cockpit-visual-audit.md`. This file does not overwrite it; it consolidates and extends it.

## 3. Overall Verdict

**Not releasable as a polished dashboard.** This is not a color tweak problem. It is a product-composition problem: shell, sidecar, filters, overlays, dialogs, cards, and responsive behavior were not designed as one cockpit.

The earlier task delivered useful pieces: token aliases, dark values, card rails, column surfaces, and a sidecar collapse affordance. Those pieces are not enough. The implementation mixed PDS components, native controls, raw HTML, and thin custom CSS without a governing design policy.

Approximate quality by area: shell/status 2/10, nav 2/10, board columns 5/10, cards 4/10, filters 2/10, sidecar 0/10, overlays/dialogs 0/10, mobile 1/10, visual gates 2/10.

## 4. Runtime Findings

- Build succeeds and Cockpit runs.
- PDS assets load from `/porsche-design-system/components/...` and custom elements hydrate. This is important: the ugly result is mostly not because PDS is absent.
- `/theme-bootstrap.js` is served as `text/html` by the SPA catch-all even though `dist/theme-bootstrap.js` exists. Browser error: `Unexpected token '<'`. Theme still changes after React loads, but the no-flash bootstrap promise is broken.
- CSS and HTML lint pass, which proves current gates do not measure visual quality.
- Targeted E2E fails three checks: axe `scrollable-region-focusable`, shell horizontal overflow at 320px, and board reachability without document-level horizontal scroll at 320px.

### PDS Asset Delivery Finding

Cockpit does not use a Python/pip PDS package. It uses npm packages (`@porsche-design-system/components-js` and `components-react`) plus a sync script that downloads the PDS runtime chunks/icons once into `public/porsche-design-system/`. Vite copies those files into `dist/`; FastAPI serves `/porsche-design-system`; `main.tsx` traps `document.porscheDesignSystem.cdn.url` to `window.location.origin`; CSP tests require no runtime requests to `cdn.ui.porsche.com`.

This local asset mode is intentional and heavily tested (`pds-runtime-csp.spec.ts`, `main_pds_trap_1496.test.ts`, `test_sync_pds_assets_1511.py`). Switching to live CDN resources would not fix the current styling failures, because PDS components already hydrate locally. It would instead require changing CSP, removing/relaxing local-bundle tests, accepting runtime internet dependency, and revisiting the consumer-branch promise that Cockpit launches from prebuilt `dist/` without Node/npm. Live CDN can be considered, but it is an architecture/product packaging decision, not a design remediation shortcut.

## 5. Production UI Inventory

Production code only, excluding tests:

| Metric | Count | Meaning |
|---|---:|---|
| TS/TSX files | 44 | Significant UI surface area |
| CSS files | 7 | Many components have no visual layer |
| PDS import files | 17 | PDS is present but partial |
| Native `<button>` | 6 | Still in core visible flows |
| Native `<input>` | 5 | Filters and DR radios remain native |
| Raw `role="dialog"` containers | 7 | Overlay semantics without overlay composition |
| Raw menu | 1 | Context menu only partially styled |
| Inline style blocks | 11 | Layout remains scattered in JSX |
| `tabIndex={-1}` | 8 | Several controls are removed from normal tab flow |
| Raw `ul/li` nodes | 14 | Lists render like document HTML, especially sidecar/health/DR |

## 6. Severity-Ranked Problems

### P0 - Sidecar Is Unstyled Debug Output

The right panel is the worst surface. It contains collapse control, pending decisions, tabs, detail metadata, markdown body, tags, actions, and activity, but has almost no internal layout or hierarchy. Decision requests render as bullets plus native buttons. Detail fields run together. Labels, values, timestamps, tags, dependencies, and task body do not form an inspector.

Needed direction: redesign the sidecar as a real inspector with sections, spacing, metadata rows, headers, tabs, DR cards, empty states, and consistent action placement. Decide whether DR queue belongs in the sidecar, a sheet, or a route.

### P0 - Popovers And Dialogs Reflow The App

Health and DR "popovers" are plain in-flow dialogs inside the status bar. Opening them expands the header and pushes the board. Cleanup confirm/result states also render inline. Resolve and archival dialogs are raw `div role="dialog"` containers rather than PDS modal/sheet surfaces.

Needed direction: adopt one overlay policy. Likely use `PPopover` for compact status disclosures, `PModal` for blocking decisions, and `PSheet` or a side panel for dense task/decision workflows.

### P0 - Design-System Adoption Is Not Systemic

PDS is loaded, but Cockpit uses it like a component grab bag. Native buttons, native inputs, raw radios, raw lists, custom `.icon-button`, raw web components, and PDS components appear side by side. Some PDS components are semantically wrong: status indicators are buttons; nav is a button; tabs are raw-looking; selects use native `option` children.

Needed direction: establish a PDS-first visible-control policy with explicit exceptions. Choose components by semantics: `PButtonPure` for icon actions, `PPopover` for disclosures, `PInputSearch` for search, `PSwitch`/`PCheckbox` for binary filters, `PSelectOption` for selects, `PTag` for metadata, `PTable`/structured rows for activity, `PSegmentedControl` for activity filters.

### P1 - Filter Workflow Looks Bolted On

The filter toggle is a browser-default button. The panel is an inline block with minimal styling, a raw search input, weak labels, raw checkbox, and large blank regions. Opening the panel pushes the board down. Dropdown/select styling is not integrated enough to feel deliberate.

Needed direction: design a filter toolbar and panel. Use PDS form controls, active filter chips/count, clear action placement, compact field grouping, and decide inline vs popover/sheet behavior.

### P1 - Mobile Contract Is Undefined And Failing

Mobile screenshots show compressed desktop UI, horizontal overflow, and a sidecar that becomes a raw long document. Current tests fail at 320px. Tablet is reachable but still not composed.

Needed direction: decide the product contract: fully supported mobile, board-only mobile with sidecar as sheet, or explicit desktop-first with a controlled small-screen message. Then test that contract.

### P1 - Cards Are Operationally Too Thin

Cards now have rail/surface/shadow, but visible content is essentially only the title. No task ID, priority, tags, claimed/blocked label, age, or non-color signal. The rail alone is not enough for scanning.

Needed direction: add compact metadata without making cards noisy: task ID, title, priority/status tag, first tags with overflow, blocked/claimed icon/text, accessible non-color signal.

### P1 - Visual Gates Are False-Green

Lint passes. Many E2E tests verify existence, reachability, or dimensions, not quality. Existing tests allowed an obviously unfinished dashboard to ship as complete.

Needed direction: add screenshot approval/regression gates for desktop home, selected sidecar, filters, context menu, DR/health overlays, cleanup/resolve modal, dark mode, tablet, and mobile. Add structural tests that reject in-flow overlays and document-level horizontal overflow.

### P2 - Columns Are Only Half Finished

Columns are one of the better surfaces, but empty states are plain text, status names expose internal strings (`in-progress`), and scrollable bodies fail axe focusability. Empty columns should feel intentionally quiet, not abandoned.

Needed direction: focusable scroll regions, polished status labels, restrained empty states, and possibly subtle state-specific treatment for done/review/blocking conditions.

### P2 - Navigation And Status Bar Lack Product Identity

The app name is visually hidden. The nav rail has one item and the text/icon composition is awkward. Status bar controls look like unrelated buttons. Health/DR/Cleanup/Theme have no clear visual roles.

Needed direction: define Cockpit chrome: visible product identity, compact status indicators, clear nav affordance, and differentiated alert/action/theme controls.

## 7. PDS Capability Gap

| Need | PDS Capability | Cockpit Today |
|---|---|---|
| Floating disclosure | `PPopover`, `PFlyout` | In-flow raw `div role="dialog"` |
| Blocking dialog | `PModal` | Raw dialog divs |
| Dense side workflow | `PSheet` | Fixed aside with raw content |
| Search | `PInputSearch` | Raw `<input type="text">` |
| Binary setting | `PSwitch`, `PCheckbox` | Raw checkbox/radios |
| Select options | `PSelect`, `PSelectOption` | `PSelect` with native options |
| Status/meta chips | `PTag`, `PTagDismissible` | Mostly absent or raw spans |
| Activity filters | `PSegmentedControl` | Row of secondary buttons |
| Structured history/activity | `PTable`, `PTextList` | Raw clickable div/list rows |
| Typographic hierarchy | `PHeading`, `PText`, `PDisplay` | Raw spans/divs, PText with little hierarchy |
| Separators | `PDivider` | Borders and raw whitespace |
| Icons/actions | `PButtonPure`, PDS icons | Manual SVG / custom icon button |

## 8. Planner-Ready Remediation Lanes

1. **Cockpit shell and sidecar redesign** - inspector layout, decision queue placement, detail hierarchy, activity/history styling, collapse affordance, visible app identity.
2. **Overlay system** - Health, DR, Cleanup, ConfirmDialog, ResolveModal, ArchivalModal, RepairPanel using a consistent PDS popover/modal/sheet strategy.
3. **Filter and form control system** - filter toggle/panel, search input, selects/options, blocked switch, active filter chips, editor field grouping.
4. **Card information density** - task ID, title hierarchy, tags, priority/status indicators, blocked/claimed/accessibility cues.
5. **Responsive contract** - decide and implement mobile/tablet behavior; fix 320px overflow; sidecar as sheet or controlled unsupported state.
6. **Visual quality gates** - screenshot baselines plus structural tests for no in-flow overlays, no raw core controls, no document overflow.
7. **PDS policy and exceptions** - document component selection rules and exceptions for jsdom/test constraints.

## 9. Decision Requests

Existing pending DR `.owlbear/kanban/decisions/pending/1534-decision.md` already asks whether the next Cockpit UI cycle should be a coordinated redesign. Do not create a duplicate unless the existing DR is rejected or split.

The current DR should be resolved or amended around these choices:

| Decision | Recommended Option | Confidence | Risk If Deferred |
|---|---|---:|---|
| Remediation scope | Full coordinated Cockpit dashboard redesign, not incremental polish | 0.88 | Local fixes preserve incoherent product feel |
| PDS policy | PDS-first for all visible production controls; explicit exceptions only | 0.84 | Continued native/PDS mix and inconsistent UX |
| Sidecar IA | Redesign sidecar as inspector; decide DR queue location before implementation | 0.82 | Worst surface remains cluttered and unscannable |
| Overlay strategy | `PPopover` for compact disclosures, `PModal` for blocking decisions, `PSheet` for dense side workflows | 0.80 | Header/app reflow bugs continue |
| Mobile contract | Keep 320px no-overflow as a hard gate, but choose full/mobile-sheet/unsupported contract | 0.78 | Tests and design keep disagreeing |
| Visual gate | Require screenshot review/regression for future Cockpit UI tasks | 0.86 | Another false-green visual implementation ships |
| PDS asset mode | Keep local pinned assets unless product explicitly abandons offline-after-build/CSP constraints | 0.81 | CDN switch breaks tested packaging without improving composition |

## 10. Immediate Defect List

- Serve `/theme-bootstrap.js` as a static asset; it currently falls through to HTML.
- Fix `.column-body` keyboard focusability for scrollable regions.
- Fix 320px document-level horizontal overflow.
- Stop Health/DR/Cleanup disclosures from expanding the status bar.
- Replace raw filter toggle/search/checkbox/radios or document explicit exceptions.
- Replace native select-option usage in PDS selects where it causes warnings.
- Add CSS/layout for `DecisionViewport`, `DetailTab`, `ActivityTab`, `HealthBadge`, `DRStatusIndicator`, `CleanupPanel`, and modal/dialog surfaces.

## 11. Recommendation

Approve the existing #1534 redesign DR as a full coordinated redesign cycle. Planner should not create small isolated polish tasks first; the failure is contextual. The first implementation wave should be shell/sidecar/overlay architecture and visual gates, because those set the standard for filters/cards/responsive work.

Challenge: proceed - confidence in original recommendation 0.86. The main counterargument is scope size, but the screenshot evidence shows incremental fixes would mostly move the rawness around rather than remove it.
