# owlbear-cockpit — Steering Cockpit Package

Cockpit combines a FastAPI backend (`src/owlbear_cockpit/`) with a React frontend (`web/`),
served as built static assets from `dist/`. The backend wraps `KanbanEngine` with read and
mutation APIs, and the frontend provides the steering viewport used to view, edit, move,
archive, inspect activity, and resolve decisions.

→ Parent: [README.md](../../README.md)

---

## Launch / Usage

Build frontend assets (developer/source workflow):

```bash
cd serve/cockpit/web
npm run build
cd -
```

Sync Porsche Design System runtime assets from CDN (run once after PDS version bumps):

```bash
cd serve/cockpit/web
npm run sync:pds
cd -
```

This downloads the core chunk, 58 component chunks, and 290 icon SVGs from
`cdn.ui.porsche.com` into `public/porsche-design-system/` and commits them for offline
use. Assets are version-pinned to the installed `@porsche-design-system/components-js`
version; re-run after any PDS upgrade.

Launch Cockpit backend + static frontend:

```bash
uv run cockpit
```

`uv run cockpit` serves `serve/cockpit/dist/`, starts on `127.0.0.1:8420` by default,
and opens a browser unless disabled with `COCKPIT_NO_OPEN=1`.

## Frontend Surface

Frontend source is under `serve/cockpit/web/` and is the only Node/npm package in this
repository.

| Attribute | Value |
|-----------|-------|
| Node requirement | `>=24.15.0` (`web/package.json`) |
| Stack | React `^19.2.5`, Vite `^8.0.10`, TypeScript `^6.0.3`, React Router `^7.14.2`, Porsche Design System React `^4.0.0`, React Compiler (`babel-plugin-react-compiler` `^1.0.0`), Tailwind CSS `^4.3.0` (`@tailwindcss/vite` + `tailwindcss`) |
| Test runner | Vitest `^4.1.5` (`npm test`) |
| E2E runner | Playwright `^1.59.1` (`npm run test:e2e`) |
| CSS/HTML lint | Stylelint `^17.10.0` (`npm run lint:css`), HTMLHint `^1.9.2` (`npm run lint:html`) |
| Build output | `serve/cockpit/dist/` via `npm run build` |

Accessibility and responsive state after #1396:

- #1395 gate tests verify viewport and accessibility scans (including 320px, 768px,
  1024px, and 1440px checks).
- Focus-management behavior for decision and repair flows is verified by the #1396
  regression tests.
- #1565 adds card information density cues: task cards now render id, priority tag,
  tag preview with overflow indicator, update-recency metadata, and explicit text cues
  (`Blocked`, `Claimed`, `Dependencies blocked`, `Decision pending`) for all four state
  signals. State cues are perceivable without relying on rail color alone, verified by
  Playwright locator/text assertions in `serve/cockpit/web/e2e/card-density.spec.ts` (AC-2).
- #1562 adds shell/sidecar inspector semantic structure: `[data-region="sidecar-header"]`
  renders the selected task identity outside the tab content area; metadata fields render
  `Status:` and `Priority:` labels paired with their values; body, history, and actions
  regions are distinctly identified by `data-region`; decision queue items are `<article>`
  elements with separately labeled Agent/Request type/Age/Task fields; filter controls are
  grouped in `role="toolbar"`; the product-identity `<h1>` has non-zero visible dimensions
  (width > 50px, height > 10px); each named status-bar control carries an individually
  asserted accessible name. Verified in `serve/cockpit/web/e2e/shell-sidecar-inspector.spec.ts`
  (18 tests).
- #1564 adds filter and form control PDS compliance verification: 34 Playwright E2E
  tests in `serve/cockpit/web/e2e/filter-controls.spec.ts` cover the filter-panel workflow (toggle
  open via `p-button[data-testid="filter-toggle"]`, search, priority selection via
  `CustomEvent('change', { detail: { value } })`, tags selection via
  `CustomEvent('update', { detail: { value: [...] } })`, blocked toggle, badge and
  result-count updates, and clear-all via `p-button[data-testid="filter-reset"]`) and
  task-editor controls (priority `p-select-option` children, `p-tag` tag chips, and
  action buttons). Tests use PDS-host-scoped selectors and dual-render guards
  (native-element count-0 absence checks using `page.evaluate()` on `el.children`)
  per PDS policy §5 from #1560.
- #1566 extends the responsive contract: `[data-testid="column-body"]` receives
  `tabIndex="0"` when scrollable (axe `scrollable-region-focusable`), verified at
  320x800, 768x1024, and 1024x768 in `serve/cockpit/web/e2e/responsive-contract.spec.ts`. Mobile
  task detail renders in a `p-sheet` custom element at 320x800 (post-#1560 board-first
  contract) with click-dependent selection signals.
- #1568 restores sequential keyboard reachability for the nav-rail: the `<PButton
  data-surface="kanban">` in `Shell.tsx` no longer carries `tabIndex={-1}`, so the
  persistent nav control is reachable via Tab. Modal/popover containers
  (`role="dialog"`) retain their `tabIndex={-1}` for focus-management; only the
  persistent nav control was changed. Verified in
  `serve/cockpit/web/e2e/nav-rail-taborder.spec.ts` (2 E2E assertions) and
  `tests/test_cockpit_shell_sidecar.py` (source inspection).
- #1569 converts in-flow disclosure and confirmation surfaces to out-of-flow overlay
  containers across seven components. `HealthBadge` and `DRStatusIndicator` disclosures
  become trigger-anchored fixed-position popovers (coordinates derived from
  `getBoundingClientRect()`, not hard-coded viewport values). `CleanupPanel`,
  `ConfirmDialog`, `ResolveModal`, and `ArchivalModal` confirmations become
  fixed-position modal containers with `role="dialog"`, `aria-modal="true"`,
  Tab/Shift+Tab focus-trap cycling between first and last focusable elements, and
  focus-return to the triggering element on close. `RepairPanel` is extracted from the
  `HealthBadge` disclosure and mounted as an independent sibling control in `Shell.tsx`.
  The context-menu overlay contract (`position:fixed`, `role="menu"`, arrow-key
  navigation, Escape focus-return to the originating task card) is preserved unchanged.
  Verified by `serve/cockpit/web/e2e/overlay-behavior.spec.ts` (19 E2E tests, all
  pass) and `serve/cockpit/web/src/__tests__/OverlayAnchoring.test.tsx` (13 unit
  tests covering trigger-anchored positioning and CleanupPanel modal-equivalence
  semantics).
- #1572 completes the cockpit responsive contract: `Shell.css` eliminates 320px
  document-level horizontal overflow via `overflow-x: clip` on `.shell`, wrapping on
  `.shell__status-bar` with compact vertical padding, and `min-width: 0` /
  `overflow-wrap: anywhere` on the product-identity text. `Column.tsx` makes
  `tabIndex="0"` conditional on `scrollHeight > clientHeight` via `ResizeObserver`,
  `window.resize`, and `MutationObserver`-based re-sync, removing the attribute when
  the column body is not scrollable. Responsive proof coverage now lives in
  `serve/cockpit/web/e2e/responsive-contract.spec.ts`, which proves the conditional
  `tabIndex` both-branch contract and mobile `p-sheet` heading identity after task
  selection at 320x800. The older responsive layout proof suite was retired during test
  curation.
- #1573 added cross-cutting visual-remediation proof coverage for phase 2. The archived
  screenshot-baseline suite was retired during test curation; durable structural coverage
  remains in `serve/cockpit/web/e2e/overlay-behavior.spec.ts`,
  `serve/cockpit/web/e2e/responsive-contract.spec.ts`, and
  `serve/cockpit/web/e2e/filter-controls.spec.ts`.
- #1596 fixes board horizontal scroll: `KanbanBoard.tsx` changes the board grid's
  `gridTemplateColumns` from `repeat(auto-fit, minmax(200px, 1fr))` to
  `repeat(${board.statuses.length}, minmax(200px, 1fr))`, producing a fixed N-column
  track layout that overflows the board container horizontally instead of wrapping
  columns to a second row. Board container `overflowX: 'auto'` (already present from
  #1572) handles internal horizontal scroll. Shell-level `overflow-x: clip` is
  unaffected. Verified by `serve/cockpit/web/e2e/board-scroll.spec.ts` (scrollWidth >
  clientWidth at 1280x720, all 7 columns identical `offsetTop`).
- #1603 performs the atomic PDS token migration: `serve/cockpit/web/src/tokens.css` is
  deleted and replaced with `serve/cockpit/web/src/custom-tokens.css`, which declares
  `--custom-signal-claimed` — the sole non-PDS-equivalent signal color at migration time
  (a second bundled token, `--p-color-contrast-low`, was added by #1625). All `--pds-*`
  token references in authored CSS and production TypeScript
  are migrated to PDS v4 `--p-*` equivalents. Manual dark-mode override blocks
  (`[data-theme="dark"]` and `@media (prefers-color-scheme: dark)`) are removed from
  authored CSS; dark mode is handled natively by PDS via `.scheme-dark`/`.scheme-light`
  class switching. `main.tsx` import updated from `tokens.css` to `custom-tokens.css`.
  Verified by `serve/cockpit/web/src/__tests__/TokenMigration.test.ts` (17 tests
  covering AC-1 through AC-4) and durable suites `PdsColorSchemeBridge.test.ts`,
  `BoardVisualDesign.test.tsx`, `Card.css.supplemental.test.ts`, `Shell.secondary-css.test.tsx`,
  and `ShellSecondaryCSS.base.test.tsx` (90 tests total, all passing).
- #1606 applies sticky header and responsive sidecar layout via Tailwind utilities.
  `[data-region="status-bar"]` in `Shell.tsx` gains `sticky top-0 z-10` classes, ensuring
  the header remains visible after the workspace element is scrolled past viewport height.
  At 768–1023px (tablet, without manual collapse), `--shell-columns` resolves to `48px`
  for the sidecar column; at ≥1024px it resolves to `360px`. `Shell.css` is stripped of
  10 banned layout property families (`display`, `width`, `height`, `overflow`, `padding`,
  `gap`, `position`, `z-index`, `grid-template-columns`, `grid-template-rows`); only
  `grid-template-areas` declarations and `--shell-*` custom-property aliases are retained
  in CSS. Verified by `serve/cockpit/web/e2e/shell-layout-1606.spec.ts` (21 Playwright
  E2E tests — AC1 behavioral workspace-scroll guard plus `sticky`/`top-0`/`z-10` class
  checks; AC2 sidecar `boundingBox()` width at 1023px and 1024px; AC3 file-content
  negatives for all 10 banned property families and DOM no-inline-style regression guard
  for `.shell` and `[data-region]` children).
- #1614 performs PDS simple component swaps across five cockpit components.
  `ActivityTab.tsx` session-row button, `DRStatusIndicator.tsx` resolve-button, and
  `ErrorBoundary.tsx` retry button are replaced with `PButton` controls with preserved
  `data-testid` attributes and `onClick` handlers. `Shell.tsx` status-bar `<h1>`, both
  sidecar-section `<h2>` elements, `DetailTab.tsx` actions `<h3>`, and `ErrorBoundary.tsx`
  error-state `<h3>` are replaced with `PHeading` with explicit `tag` props. Remaining
  native `<button>` elements carry `data-pds-exception` attributes or are the
  sidecar-collapse toggle (`aria-expanded` pattern); zero raw `<select>` elements exist
  in source. Verified by `serve/cockpit/web/src/__tests__/PdsSimpleSwaps.test.tsx`
  (29 tests covering AC-1 through AC-4) and `serve/cockpit/web/src/__tests__/PdsMigration.test.tsx`
  (durable regression, 78 passing).
- #1615 migrates `Card.tsx` visual chips and tags to PDS React wrappers and introduces a
  mapping utility. Status and priority chips are replaced with `<PTag compact variant={...}>`
  using `statusToVariant()` and `priorityToVariant()` from `utils/cardVariants.ts`; both
  utilities return only valid PDS `TagVariant` values (`primary`, `secondary`, `info`,
  `warning`, `success`, `error`, and frosted variants) with a `secondary` fallback for
  unrecognized strings. Signal icon renders as `<p-icon size="xs" aria-label={signal}>` for
  `dr-pending`, `blocked`, `claimed`, and `deps-unmet` states; no icon is rendered for
  `ready`. Each visible tag (up to `TAG_PREVIEW_LIMIT=3`) renders as an individual
  `<PTag compact variant="secondary">` pill with overflow count indicator preserved. Existing
  state cue text spans (`Blocked`, `Claimed`, `Dependencies blocked`, `Decision pending`) are
  unchanged. `Card.tsx` carries no `no-restricted-syntax` eslint-disable. Verified by
  `serve/cockpit/web/src/__tests__/CardVariants.test.ts` and
  `serve/cockpit/web/src/__tests__/Card.visual-treatment.test.tsx` (48 tests covering
  AC-1 through AC-6) and `serve/cockpit/web/src/__tests__/Card.signal.test.tsx` (durable
  regression, 27 passing).
- #1616 establishes the `DetailTab` sidecar information architecture: `DetailTab.tsx` root renders four `data-region` direct children in DOM order `sidecar-body` -> `actions` -> `sidecar-metadata` -> `history` (asserted via `:scope > [data-region]` direct-child selector). The `sidecar-metadata` region is the `p-accordion` host element (`p-accordion[data-region='sidecar-metadata'][compact][heading="Metadata"]`), closed by default (no `open` attribute); accordion subtree remains in DOM when closed via CSS height animation, not conditional render. `SidecarStructure_1607.test.tsx` divider assertion updated to be order-agnostic. Verified by `serve/cockpit/web/src/__tests__/DetailTab.information-architecture.test.tsx` (9 tests covering AC1 DOM order and AC2 accordion host attributes and closed-state DOM visibility).
- #1607 applies sidecar structural PDS components to `Shell.tsx`, `Shell.css`, and `DetailTab.tsx`. Both `#shell-sidecar-content` elements (mobile `p-sheet` and desktop branches) carry the Tailwind arbitrary-value class `p-[var(--p-spacing-static-md)]`; no directional `pt-/pb-/pl-/pr-` overrides are present; token is PDS-native (not deprecated `--pds-*`). `[data-region="sidecar-header"]` renders `PHeading size="large"` (no raw `h2`) in both Shell viewport branches; `[data-region="sidecar-body"]` in `DetailTab` renders `PHeading size="medium"`; `[data-region="actions"]` renders `PHeading size="small"` (no raw `h3`). A `syncHeadingAttrs` ref helper mirrors both `tag` and `size` props to the host element for DOM querying. `PDivider` separates `sidecar-header` from `DecisionViewport` and `DecisionViewport` from `p-tabs` in both Shell branches; a `PDivider` immediately follows the `sidecar-metadata` region in `DetailTab`. Verified by `serve/cockpit/web/src/__tests__/SidecarStructure_1607.test.tsx` (23 tests — AC-1 source+DOM padding with four-direction directional-override guard; AC-2 desktop+mobile dual-branch Shell heading proof using `p-sheet` ancestor discriminators and DetailTab region-scoped heading assertions; AC-3 desktop+mobile dual-branch Shell divider proof and DetailTab metadata-divider proof).
- #1617 migrates the remaining filter panel controls to PDS React wrappers: the blocked
  checkbox replaces raw `<p-checkbox>` + `onClick` toggle with a controlled `PCheckbox`
  wrapper using `checked={filter.blocked}` and `onChange` reading `event.detail.checked`;
  the priority `PSelect` replaces native `<option>` children with `PSelectOption`; and
  `.filter-panel` gains a flex layout (`display:flex`, `flex-wrap:wrap`,
  `gap:var(--p-spacing-static-sm)`, `align-items:flex-end`). Verified by
  `serve/cockpit/web/src/__tests__/FilterPanel.pds-controls.test.tsx` (13 tests covering
  `PCheckbox` checked-state reflection, `onChange` true/false paths, `PSelectOption` presence,
  native-option absence, and CSS flex declarations) and
  `serve/cockpit/web/src/__tests__/FilterPanel.test.tsx` (durable regression, 40 passing).
- #1618 migrates the three complex modal roots (`ConfirmDialog`, `ResolveModal`, and
  `ArchivalModal`) from hand-rolled `div[role="dialog"]` overlays to PModal host elements.
  Legacy `position:fixed` overlay styles, Tab/Shift+Tab keyboard handlers, and focus-trap
  cycling code are removed from all three components. Per-modal dismiss policy: `ConfirmDialog`
  uses `aria.role='alertdialog'`, `disableBackdropClick=true`, and `dismissButton=false`
  (Escape and in-body Cancel/Confirm only); `ResolveModal` and `ArchivalModal` allow backdrop
  click, Escape, dismiss button (X), and in-body Cancel/Close. Existing action callback
  contracts (`onCancel`, `onConfirm`, `onClose`, `onResolved`, `onRefresh`) are preserved
  unchanged. Three PDS-workaround categories are permitted under documented PModal
  limitations: a Tab-cycling shim for slotted light-DOM focus trapping (native `<dialog>`
  does not trap slotted controls in Chromium), focus-state capture/restore for close-path
  variants, and host attribute normalization (`role`, `aria-modal`) via `MutationObserver`.
  Focus return: `ResolveModal` returns focus to the DR trigger button on close;
  `ArchivalModal` returns focus to the originating task card via `onDismiss` plus an
  explicit fallback target (context-menu opener is destroyed before close); `ConfirmDialog`
  returns focus to the action button that opened it. Verified by
  `serve/cockpit/web/src/__tests__/PModal.migration.test.tsx` (30 tests — AC-1 PModal
  roots and no legacy wrapper/overlay/z-index, AC-3/AC-4 dismiss policy wiring and focus
  fallback for all three modals),
  `serve/cockpit/web/src/__tests__/PModal.coverage.test.tsx` (53 tests — branch coverage
  for `ConfirmDialog.tsx` at 98.57% and `ResolveModal.tsx` at 92.75%), and
  `serve/cockpit/web/e2e/overlay-behavior.spec.ts` (19 E2E tests — host-attribute
  checks, Tab-cycle containment, and exact focus-return for all three modals).
- #1624 adds success feedback via PDS `PToast` for move operations and an inline
  save-confirmed indicator for edit saves. `Shell.tsx` mounts a `<PToast />` singleton
  and calls `useToastManager().addMessage({ state: 'success', text })` from
  `onMutationSuccess`; `KanbanBoard.tsx` passes the target status name in the success
  message on drag-drop and context-menu moves. `TaskFieldsEditor.tsx` shows
  `[data-testid="save-confirmed"]` for 2000ms after a successful dirty-field edit and
  actively clears it (with timer cancellation) when a handled failure returns `false`.
  `CockpitProvider.tsx` guards `setSelectedTask(null)` to fire only on true task
  switches (`isTaskSwitch`), not nonce-driven same-task refetches, so the indicator
  survives the post-edit data refresh. `TaskFieldsEditor.tsx` mirrors this with a
  `prevTaskIdRef` guard that resets the indicator immediately only on `task.id` change.
  Existing `PBanner` error/warning surfaces are unchanged. Verified by
  `serve/cockpit/web/src/__tests__/PToastSuccess_1624.test.tsx` (AC1 wiring: KanbanBoard
  message, Shell addMessage, PToast in tree) and
  `serve/cockpit/web/src/__tests__/SaveConfirmed_1624.test.tsx` (AC2 indicator lifecycle:
  appears on success, survives same-task refetch, resets on task-switch; AC3 failure
  contract: indicator absent on initial false-return and cleared from prior success;
  `TestFromAC_SaveConfirmedRefetchSurvival`, `TestFromAC_SaveConfirmedTaskSwitch`,
  `TestFromAC_SaveConfirmedFailure`) and
  `serve/cockpit/web/src/__tests__/CockpitRefetch_1624.test.tsx` (provider-level
  same-task refetch guard). (Literal `p-toast-item` shadow-DOM timing proof confirmed via
  #1629 consolidation gate — `npm run test:e2e:all` and `npm test` both exit 0.)
- #1625 extends `custom-tokens.css` with a second bundled token: `--p-color-contrast-low`
  declared via `light-dark()` for runtime border contrast without CDN dependency. `Shell.css`
  gains `border-right: 1px solid var(--p-color-contrast-low, currentColor)` on
  `.shell__nav-rail`, completing the structural border set alongside existing sidecar, column,
  and filter-panel declarations (all using `--p-color-contrast-low` via #1614–#1618 token
  migration). Contract tests (`TokenMigration.test.ts`, `PdsColorSchemeBridge.test.ts`)
  updated to expect 2 custom declarations. Verified by
  `serve/cockpit/web/e2e/dark-mode-border-1625.spec.ts` (9 Playwright E2E tests — AC-1
  runtime guard + 4 border-width + contrast-ratio assertions for sidecar, nav-rail, column,
  and filter-panel; AC-3 runtime no-injection scheme-color comparison on sidecar + nav-rail;
  AC-4 no-injection card-chip border-width in both schemes) and updated Vitest contract
  tests (40 passing, 0 failed).
- #1626 applies PDS focus-visible ring styling to all native interactive elements.
  `custom-tokens.css` adds a global `:focus-visible` rule for `button`, `[role="button"]`,
  `[role="menuitem"]`, `input`, and `a` — the elements PDS Shadow DOM does not reach — using
  `outline: 2px solid var(--color-focus)` and `outline-offset: 2px`. `Card.css`
  `.card:focus-visible` migrates from the legacy `var(--p-color-focus)` token to
  `var(--color-focus)` and aligns its offset from 1px to 2px. No `:focus` fallback is
  present; styling is strictly focus-visible-only. Verified by
  `serve/cockpit/web/src/__tests__/FocusVisibleCssSource_1626.test.ts` (Vitest — grouped-rule
  source-contract proving the five-part selector list in a single rule block, legacy-token
  prohibition, and hardcoded-color regex scan) and
  `serve/cockpit/web/e2e/focus-visible-pds-1626.spec.ts` (Playwright — keyboard-traversal
  behavioral proof under Tab/arrow-key for each selector bucket).
- #1627 migrates CSS-file transition declarations to PDS v4 duration and easing tokens.
  `.shell` (`grid-template-columns`), `.icon-button` (`background`, `border-color`), and
  `.card` (`box-shadow`) transitions in `Shell.css` and `Card.css` replace hardcoded
  `250ms ease` values with `var(--p-duration-sm)` and `var(--p-ease-in-out)`. Collapsed-state
  sidecar declarations (`.shell[data-sidecar-collapsed]` for desktop and tablet) and
  `.shell__sidecar { overflow: hidden; }` are added to complete the sidecar collapse
  contract. No `transition: all` declarations are introduced (AC-2 regression guard).
  Verified by `serve/cockpit/web/src/__tests__/PdsMotionTokens_1627.test.tsx` (10 tests —
  token presence, no-hardcoded-ms, and property-level exact-match assertions using
  space-delimited matching for all 3 migrated declarations).
- #1628 completes the WCAG 2.1 AA accessibility sweep: invalid host-level ARIA attributes
  (`aria-expanded`, `aria-controls`) on `p-button` host controls are replaced with native
  `<button>` elements in `KanbanBoard.tsx` (filter toggle) and `Shell.tsx` (nav rail
  control); prohibited `aria-current`/`aria-label` on the nav `p-button` host is removed.

> **TODO:** unverified — heading semantics claim below ("Shell.tsx adds the page-level `<h1>` product identity and `<h2>` headings for sidecar sections; `DetailTab.tsx` adds `<h3>` section headings") may duplicate #1614 work; the `PHeading` additions in `Shell.tsx`/`DetailTab.tsx` were implemented by #1614. Verify which aspects of heading structure #1628 actually introduced vs. inherited. [#1628]

  Heading semantics are corrected: `Shell.tsx` adds the page-level `<h1>` product identity
  and `<h2>` headings for sidecar sections; `DetailTab.tsx` adds `<h3>` section headings
  for accordion content. `RepairPanel.tsx` moves the confirm action from a non-interactive
  `<span onClick>` wrapper to the `<PButton>` element; `DecisionViewport.tsx` removes
  `role="button"` misuse from non-interactive `<article>` decision cards. `vite-env.d.ts`
  adds `p-accordion` IntrinsicElements typing. Verified by
  `serve/cockpit/web/e2e/accessibility-sweep.spec.ts` (10 E2E tests — WCAG 2.1 AA `.withTags()` axe
  scans on board view, sidecar detail view, DRStatusIndicator popover, HealthBadge popover,
  FilterPanel open state, ResolveModal, ArchivalModal, ConfirmDialog, CleanupPanel confirm
  dialog, and RepairPanel confirm dialog, all zero violations).

- #1634 migrates two unowned raw HTML elements discovered by #1608 to PDS React wrappers.
  `TaskFieldsEditor.tsx` replaces native `<option>` children inside `<PSelect>` with
  `PSelectOption`, following the established FilterPanel pattern from #1617.
  `DecisionViewport.tsx` replaces the task reference `<a>` with `<PLinkPure href="..." icon="none">`
  using the host-href pattern; `data-testid` and click callback are preserved; `href` and `icon`
  host attributes are normalized via `ref` for deterministic jsdom assertions. Existing
  `DecisionViewport.test.tsx` clickable-element and keyboard-reachability assertions are updated
  to accept `p-link-pure` with host `href` preserved. Verified by
  `serve/cockpit/web/src/__tests__/PdsSimpleSwaps_1634.test.tsx` (3 tests — AC1 `p-select-option`
  presence and zero native `OPTION` guard; AC2 `PLinkPure` host `href`, `icon="none"`,
  `data-testid`, and click callback; AC3 keyboard-reachability host-`href`) and updated
  `serve/cockpit/web/src/__tests__/DecisionViewport.test.tsx` (durable regression suite,
  35 passing).

- #1636 migrates the confirming-phase overlays in `CleanupPanel.tsx` and `RepairPanel.tsx`
  from raw `div[role="dialog"]` overlays to `PModal`, completing the PModal migration
  across all confirm surfaces (following #1618 for `ConfirmDialog`, `ResolveModal`, and
  `ArchivalModal`). Both confirm modals pass `open`, `disableBackdropClick`, and
  `dismissButton={false}`; `role="dialog"` is retained (PModal default — no `alertdialog`
  override). Inline `position:fixed` and `z-index` styles are removed from both confirm
  phases. Focus management is retained: `previousFocusRef` restore on close, modal-container
  focus on open, and Tab/Shift+Tab wrapping including the modal-host-active Shift+Tab path
  (`active === event.currentTarget`), matching the `ConfirmDialog` focus-trap pattern.
  Escape cancel is wired via both `onDismiss` and `onKeyDown` for belt-and-suspenders
  coverage. Verified by `serve/cockpit/web/src/__tests__/PModal.migration.test.tsx`
  (56 tests — extended with CleanupPanel and RepairPanel AC1–AC6 including modal-host-active
  Shift+Tab path), `serve/cockpit/web/src/__tests__/CleanupPanel.test.tsx`,
  `serve/cockpit/web/src/__tests__/CleanupPanel.integration.test.tsx`,
  `serve/cockpit/web/src/__tests__/RepairPanel.test.tsx`,
  `serve/cockpit/web/src/__tests__/RepairPanelFocusMgmt.test.tsx`,
  `serve/cockpit/web/src/__tests__/OverlayAnchoring.test.tsx`,
  `serve/cockpit/web/src/__tests__/HealthBadgeRepair.test.tsx`, and
  `serve/cockpit/web/src/__tests__/SidecarUX.test.tsx` (206 passed, 0 failed, ESLint clean;
  coverage `CleanupPanel.tsx` 97.59%, `RepairPanel.tsx` 98.98%).

- #1637 unblocks the full Playwright e2e:all gate. `TaskFieldsEditor.tsx` removes the
  hidden `p-select[name="priority"]` shim and assigns `name="priority"` directly to the
  visible editable `PSelect` with `PSelectOption` children; every tag chip now renders as
  `PTag data-testid="tag-chip"` (no mixed wrapper-`div`/`PTag` host pattern). Additional
  component-level fixes resolve PDS filter-toggle event-wiring mismatches, sidecar metadata
  visibility contracts, focus-visible token runtime gaps, mobile-sheet selection signals at
  320px, and repair-confirm overlay status-bar reflow. `filter-controls.spec.ts` assertions
  are updated to non-strict multi-element locators for priority-option counts and multi-chip
  tag rendering, removing false-green paths from the prior hidden-shim state. Verified by
  `serve/cockpit/web/e2e/filter-controls.spec.ts` (assertions at `:425–476` cover editable
  priority control, `PSelectOption` children, visible `p-select[name="priority"]`,
  `p-tag[data-testid="tag-chip"]` chip equality, and no legacy span chips) and full
  proof bundle (`npm run test:e2e:all`, `npm test`, `npm run build` all exit 0;
  2324 passed, 0 failed, 11 skipped).

- #1629 is the full-surface consolidation gate for the visual redesign (all 4 batches).
  JSX inline-style attributes reduced from 14 to 4 across `KanbanBoard.tsx`,
  `ErrorBoundary.tsx`, `HistorySubtab.tsx`, `DRStatusIndicator.tsx`, `HealthBadge.tsx`,
  `RepairPanel.tsx`, and `ActivityTab.tsx`; static styles (error-boundary layout,
  RepairPanel confirm container, and `cursor:pointer` for session rows) moved to CSS.
  The 4 retained `style={…}` sites — `KanbanBoard.tsx` context-menu and grid-column
  positioning, `DRStatusIndicator.tsx` popover, and `HealthBadge.tsx` popover — are
  runtime-positioned and each carry an adjacent `// inline-justified: {reason}` comment.
  `accessibility-dual-theme.spec.ts` extended from 4 to all 10 accessibility-sweep
  surfaces (board view, sidecar detail, DRStatusIndicator popover, HealthBadge popover,
  FilterPanel, ResolveModal, ArchivalModal, ConfirmDialog, CleanupPanel, RepairPanel)
  under both `.scheme-light` and `.scheme-dark` — 20 Playwright tests, all green.
  Durable consolidation gate added in `serve/cockpit/tests/test_visual_redesign.py`
  (6 tests: `test_vitest_passes`, `test_playwright_e2e_all_passes`,
  `test_production_build_passes`, `test_inline_style_count_at_most_four`,
  `test_each_inline_style_has_justification_comment`, `test_dual_theme_axe_spec_passes`).

- Documentation here does not treat cache/SSE invalidation work from #1346 as part of
  this delivery bundle.

- #1639 introduces declarative tab-routing infrastructure. `routes.ts` exports a
  module-level `routeConfig: RouteConfigEntry[]` array typed `{ path, label, icon,
  component: ComponentType<KanbanBoardProps> }` with two entries: kanban at `/` and
  decisions at `/decisions`. `Shell.tsx` replaces its prior single inline `<Route>` with
  a `routeConfig.map()` render loop inside `<Routes>`, so registering a new tab requires
  only a new array entry without modifying `Shell.tsx`. `pages/DecisionsPage.tsx` is
  initially a skeleton component (`<section data-testid="decisions-page" />`) that
  validates end-to-end routing (replaced with the full list view by #1645). Verified by
  `serve/cockpit/web/src/__tests__/routes_1639.test.tsx` (12 tests — config shape,
  extensibility, and lazy/eager split contract updated by #1644),
  `serve/cockpit/web/src/__tests__/Shell.tab-routing_1639.test.tsx`
  (12 tests — Shell routing behavior, KanbanBoard props preserved, AC3 extensibility),
  `serve/cockpit/web/src/__tests__/DecisionsPage_1639.test.tsx` (3 tests — skeleton
  testid), and `serve/cockpit/web/src/__tests__/Shell.decisions-integration_1639.test.tsx`
  (3 integration tests — renders real `routeConfig` at `/decisions` and asserts
  `data-testid="decisions-page"` from the real `DecisionsPage`, updated by #1644 to
  await Suspense resolution via `act(async)` + `waitFor`).

- #1644 adds lazy loading for the `/decisions` route. In `routes.ts`, the
  `DecisionsPage` import is replaced with `const DecisionsPage = lazy(() =>
  import('./pages/DecisionsPage'))`, while `/` (`KanbanBoard`) remains an eager import.
  `Shell.tsx` wraps the `<Routes>` block in `<Suspense fallback={<div
  data-testid="route-loading" />}>`, providing a visible fallback during async chunk
  load. Vite auto-splits `DecisionsPage` into a separate JS chunk (`DecisionsPage-*.js`
  alongside `index-*.js` in `dist/assets/`). Verified by
  `serve/cockpit/web/src/__tests__/routes.lazy-loading_1644.test.tsx` (2 tests —
  `$$typeof === Symbol.for('react.lazy')` proof for `/decisions`, and ≥2 JS chunk
  count assertion after `npm run build`) and
  `serve/cockpit/web/src/__tests__/Shell.suspense-boundary_1644.test.tsx` (1 test —
  `data-testid="route-loading"` fallback renders while the route suspends).

- #1642 wires the nav-rail to `routeConfig`. The `<nav>` element gains an explicit
  `role="navigation"` landmark; the prior single hardcoded kanban `<button>` is replaced
  with `routeConfig.map(...)` rendering each config entry as a native `<button>` with
  `data-surface={route.icon}` (preserving existing test selectors),
  `onClick={() => navigate(route.path)}` via `useNavigate()`, and
  `aria-current={isActive ? 'page' : undefined}`. Active state is derived from
  `normalizedPathname === normalizeRoutePath(route.path)` — the same normalization as
  Shell's `matchedRoute` logic at `Shell.tsx:275–277` — so slash-normalized configured
  paths (e.g. `/foo/` active at location `/foo`) mark the correct button current.
  Verified by `serve/cockpit/web/src/__tests__/NavRailButtons_1642.test.tsx` (27 tests
  — explicit `role`, per-entry button count, click navigation, active/inactive
  `aria-current` toggling, route-switch updates, unknown-route behavior, and 4
  falsifiability gate tests proving button count and identity track `routeConfig`
  entries rather than any hardcoded set).

- #1643 adds route-conditional sidecar suppression. `RouteConfigEntry` in `routes.ts`
  gains an optional `hasSidecar?: boolean` field; when `false`, the
  `<aside data-region="sidecar">` element is omitted from the DOM entirely on that
  route. Shell uses `useLocation()` and a `routeConfig` lookup to derive `hasSidecar`
  at render time; unknown routes default to sidecar-present (no `hasSidecar` key or
  `hasSidecar: true`). The `/decisions` entry sets `hasSidecar: false`; the `/`
  (kanban) entry keeps the default. When sidecar is absent, Shell applies
  `data-no-sidecar` on `.shell`, which reduces `--shell-columns` to
  `var(--shell-rail-width) minmax(0, 1fr)` (2-column, no sidecar column) so
  `[data-region="workspace"]` fills the remaining horizontal space. `isSidecarCollapsed`
  state is preserved across navigation — returning to `/` restores the prior collapsed
  state. Canonical `React.lazy(() => import('./pages/DecisionsPage'))` loading is
  preserved; AC2 tests use `async`/`waitFor` to account for React Router v7
  `startTransition`-deferred commit timing when a lazy route suspends. Verified by
  `serve/cockpit/web/src/__tests__/Shell.sidecar-conditional_1643.test.tsx` (8 tests
  — AC1 sidecar-absent DOM, AC2 navigate-remove/restore/collapsed-state-preservation,
  AC3 `data-no-sidecar` attribute, CSS 2-column grid-column contract, CSS grid-area
  sidecar exclusion, and preload-hack source-inspection guard).

- #1645 replaces the `DecisionsPage.tsx` skeleton with the full decisions list view.
  `useDRState().items` drives the render: each `PendingDR` is displayed as a clickable
  `<div data-testid="dr-item-{id}">` containing an `<article>` with agent, request
  type, relative age (d/h/m format), task id, and body preview truncated to 200 chars.
  Items are arranged in a `display:flex` / `flexDirection:column` / `gap:1rem`
  container; the root `<section data-testid="decisions-page">` carries `width:100%`.
  When `items` is empty and neither `isLoading` nor `error` is set, a
  `data-testid="decisions-empty-state"` element with a "nothing to decide" message is
  rendered instead. Loading and error states are handled separately. Item click calls
  `setSelectedDRId(item.id)`. The page uses the `try/catch`-guarded `useDRState()`
  access pattern to preserve standalone mount stability for the `#1639` legacy tests.
  Verified by `serve/cockpit/web/src/__tests__/DecisionsPage_1645.test.tsx` (29 tests
  — AC1 item rendering, field display, 200-char truncation, and d/h/m age format;
  AC2 empty-state presence only under empty/non-loading/non-error preconditions;
  AC3 `dr-item-{id}` testids, click wiring, `gap >= 16px`, and effective
  `display:flex|grid` layout mechanism; AC4 discriminating root `width:100%` and
  list `flexDirection:column` assertions).

- #1646 adds a pending-count badge to the nav-rail decisions button. Inside the
  `routeConfig.map()` render loop in `Shell.tsx`, the decisions entry (`route.icon ===
  'decisions'`) conditionally renders a child `<span class="shell__nav-badge"
  data-testid="nav-badge" aria-hidden="true">` displaying `pendingDRCount` when the
  count is greater than zero; the span is absent from the DOM when the count is zero.
  `Shell.tsx` also switches the button `aria-label` between `Decisions (N pending)` and
  `Decisions` to carry the count for assistive technology. Badge overlay styles in
  `Shell.css` position the span absolutely (top-right corner of its `position:relative`
  nav button) using PDS notification tokens (`--p-color-notification-error`,
  `--p-radius-full`, `--p-font-weight-semibold`). `pendingDRCount` is sourced from
  `useDRState().count` via `CockpitProvider` — no new data-fetching or provider changes.
  Verified by `serve/cockpit/web/src/__tests__/NavBadge_1646.test.tsx` (15 tests —
  AC1 badge presence, numeric text, decisions-button scoping, no-kanban-badge guard;
  AC2 rerender transitions count→0 on both `/` and `/decisions`; AC3 exact aria-label
  format with count and reversion to `Decisions` on count=0) and durable
  `serve/cockpit/web/src/__tests__/Shell.test.tsx` (18 tests, all passing).

- #1647 wires `DecisionsPage` click/keyboard activation to the Shell-level `ResolveModal`
  and adds a snapshot guard to `ResolveModal`. In `DecisionsPage.tsx`, each DR list item's
  click and `keydown` handlers call `drState.setSelectedDRId(item.id)`, opening the same
  Shell-level `ResolveModal` used by `DRStatusIndicator` — no second modal instance is
  created. In `ResolveModal.tsx`, `const [snapshotDR] = useState(() => dr)` copies the
  `dr` prop into component-local state on mount; all subsequent renders read from
  `snapshotDR` rather than the live prop, so SSE-triggered `useDRState()` refetches do not
  overwrite the title, body, or id visible in the open modal. Closing and reopening the
  modal creates a fresh mount and a new snapshot, so a second open always reflects current
  data. Verified by `serve/cockpit/web/src/__tests__/ResolveModalSnapshot_1647.test.tsx`
  (7 tests — AC1 DecisionsPage click opens Shell modal with DR data; AC2 same-id rerenders
  do not overwrite the open modal title/body; AC3 reopened modal picks up newer DR data).

- #1648 removes `DecisionViewport` from the Shell sidecar. The `DecisionViewport` import is removed from `Shell.tsx` and the component is no longer rendered inside the sidecar `<aside>` in either the mobile `p-sheet` or desktop branch; the canvas carries `data-no-sidecar`. `DRStatusIndicator` in the status bar and `ResolveModal` gated on `selectedDR` state are retained — both render outside the `<Routes>` outlet and are route-independent by construction. The obsolete `Shell.decision-viewport.test.tsx` legacy proof suite is deleted. Verified by `serve/cockpit/web/src/__tests__/Shell.remove-decision-viewport_1648.test.tsx` (15 tests — AC-1 no-sidecar DOM and zero `DecisionViewport` calls across default, loading, pending, and error states; AC-2 `DRStatusIndicator` presence, count wiring, and click-to-modal at `/`, `/decisions`, and `/memories`; AC-3 render smoke with and without pending DRs).

- #1662 adds the Ideas tab at `/ideas`. `src/api/ideas.ts` provides `fetchIdeas()` (GET `/api/ideas`, returns `{ content: string }`) and `saveIdeas(content)` (PUT `/api/ideas`, void return) using the existing `ApiError` + `getResponseErrorMessage` pattern. `pages/IdeasPage.tsx` (default export, lazy-loaded in `routeConfig` with icon `ideas`) manages 100% local page state: initial loading indicator (`data-testid="ideas-loading"`) while GET is in flight; focused textarea populated with fetched content after load; dirty indicator (`data-testid="ideas-dirty"`) while `content !== lastSavedContent`; save button (`data-testid="ideas-save"`) disabled when content matches the last-saved baseline or while a save is in progress; placeholder `Capture ideas here...` when content is empty; Cmd+S/Ctrl+S keyboard shortcut sends PUT when dirty and no-ops when clean; GET failure renders an error state; PUT failure preserves textarea content, re-enables the save button, and allows immediate retry by button or Cmd/Ctrl+S without requiring an intermediate edit. No `CockpitProvider` extension is needed. `routes.ts` gains a `/ideas` entry: `{ path: '/ideas', label: 'Ideas', icon: 'ideas', component: IdeasPage }`. Verified by `serve/cockpit/web/src/__tests__/IdeasPage_1662.test.tsx` (31 tests — loading/loaded/error states, exact GET and PUT endpoint assertions, dirty indicator lifecycle, keyboard shortcut, route-binding render proof, and retry-after-failed-save assertions).

- #1663 adds a markdown preview toggle to `IdeasPage`. A toggle button (`data-testid="ideas-preview-toggle"`) switches between edit and preview modes; default mode is edit. In preview mode, a `<div data-testid="ideas-preview">` renders textarea content via `ReactMarkdown` + `remark-gfm` + `rehype-sanitize` (default schema, following the `TaskFieldsEditor.tsx` pattern); in edit mode, the textarea is visible and focused. The preview label is "Preview" in edit mode and "Edit" in preview mode. Textarea content is preserved across mode switches via shared `content` state. Focus auto-moves to the textarea only when not in preview mode. GFM extensions (tables, strikethrough, task lists) are active; raw HTML in the source (e.g. `<script>`, `<img onerror=...>`) is stripped by the default `rehype-sanitize` schema. Verified by `serve/cockpit/web/src/__tests__/IdeasPage_1663.test.tsx` (15 tests — toggle default/enter/return mode exclusivity, GFM table/strikethrough/task-list rendering, unsafe DOM stripping, content round-trip for baseline/edited/empty/multiline inputs).

- #1664 adds an unsaved-changes navigation guard to `IdeasPage`. When the page content is dirty (`content !== lastSavedContent`), route navigation is intercepted via `UNSAFE_NavigationContext`: if the navigator exposes `block` (React Router v5 API), it is used directly; otherwise `navigator.push`, `navigator.replace`, and `navigator.go` are patched to intercept navigation calls (the path used by `useNavigate` under `BrowserRouter` in production). On interception a `div[role="alertdialog"]` renders with the text "You have unsaved changes. Leave anyway?" and "Leave" / "Cancel" buttons; clicking "Leave" completes the pending transition, clicking "Cancel" dismisses the dialog and keeps the user on IdeasPage. When dirty, a `beforeunload` event handler calls `event.preventDefault()` to trigger the browser's native leave-page prompt on tab/window close. When content is clean, no blocking is applied and no `beforeunload` handler is registered. All patches and event listeners are removed on component unmount. Verified by `serve/cockpit/web/src/__tests__/IdeasPage_1664.test.tsx` (17 tests — alertdialog render, required text, proceed/cancel actions, beforeunload dirty/clean contract, cleanup on unmount and dirty→clean transition, and 5 `BrowserRouter`-surface tests proving the production router path).

- #1665 adds external-edit awareness and conflict resolution to `IdeasPage`. A `visibilitychange` listener calls GET `/api/ideas` when `document.visibilityState` becomes `'visible'`; route activation (existing component mount) satisfies the re-fetch requirement on navigation return. When the page is clean both at trigger and resolve time and the last-saved baseline has not changed since trigger, fetched content silently replaces the textarea value and baseline without a loading indicator. When a clean-start refetch is in flight and the page becomes dirty before the GET resolves, or the last-saved baseline changes (mid-flight save), the refetch result is discarded — textarea content, baseline, dirty indicator, save-button enablement, and conflict state are all left unchanged. When the page is dirty at trigger time and fetched content differs from the trigger-time last-saved baseline, a conflict notice appears with Overwrite (`data-testid="ideas-conflict-overwrite"`) and Discard & Reload (`data-testid="ideas-conflict-discard"`) buttons; Save and Cmd/Ctrl+S are blocked while the notice is showing. Overwrite dismisses the notice and updates the last-saved baseline to fetched content; dirty indicator visibility and Save enablement then reflect whether textarea content differs from the updated baseline. Discard & Reload dismisses the notice and sets both textarea value and baseline to fetched content (page becomes clean). Background refetch failures are silent — no error or conflict notice is shown. Conflict determination always compares fetched content against the trigger-time last-saved baseline, even when a save completes mid-flight. Transient edits that are reverted before the GET resolves do not latch: the apply branch still fires and fetched content is applied. Verified by `serve/cockpit/web/src/__tests__/IdeasPage_1665.test.tsx` (41 tests — AC1–AC10 coverage: listener registration and cleanup, silent clean-path update, clean-start discard guards for dirty-at-resolve and save-before-resolve interleavings, transient-edit-revert regression guard, conflict notice render, Save/keyboard blocking, Overwrite both-branch end states, Discard & Reload, and silent failure handling).

- #1671 adds the Memory tab list view at `/memories`. `pages/MemoryTab.tsx` (default
  export, lazy-loaded in `routeConfig` with `hasSidecar: false`) fetches `GET
  /api/memories` on mount and on `document.visibilitychange` to visible (no SSE in V1).
  Client-side intersection filtering supports state `p-multi-select[name="state-filter"]`
  (initial: `[pending, curated, approved]`), category `p-multi-select[name="category-filter"]`
  (initial: `[]`; AND logic within dimension), agent `p-select[name="agent-filter"]`
  (initial: `""`; empty `scope_agents` passes unconditionally), and
  `p-input-search[name="memory-search"]` (title + content case-insensitive substring).
  Entries are sorted by state priority (`pending=0`, `curated=1`, `approved=2`,
  `deleted=3`) then `created_at` asc. State badge is `p-tag[data-testid="memory-entry-state"]`
  with `.variant` property (`pending="warning"`, `curated="info"`, `approved="success"`,
  `deleted="secondary"`); no synthetic `setAttribute` calls — `variant` prop drives the
  DOM property. `data-testid="clear-filters"` resets all controls to initial values.
  `data-testid="parse-errors-warning"` appears when `parse_errors > 0`. Verified by
  `serve/cockpit/web/src/__tests__/MemoryTab_1671.test.tsx` (74 tests — route mount,
  fetch, sort, filter intersection, PDS option dual-render guard, state variant proof,
  empty states, clear-filters per-control reset, and parse-error warning).

- #1672 adds interactive accordion detail and mutation actions to the Memory tab.
  Each entry expands via `PAccordion` to show sanitized markdown content (rehype-sanitize
  custom schema allowing p, br, ul, ol, li, strong, em, code, a with href restricted to
  http/https/mailto protocols; stripped: script, style, img, iframe; no
  `dangerouslySetInnerHTML`) and all metadata fields (id, source_agent, scope_agents,
  categories, confidence, state, timestamps). State-dependent action buttons are gated
  within the accordion: Approve (curated only), Edit (all non-deleted; inline approved-entry
  warning), and Delete (all non-deleted; confirmation dialog distinguishing hard-delete for
  pending vs soft-delete for curated/approved). The inline edit form covers title,
  categories, confidence, scope_agents, and content with a 1024-char counter; save sends
  `POST /api/memories/{id}/edit` with `expected_updated_at` from the loaded entry. Error
  UX: 409 OCC conflict shows an inline banner (`Entry was modified — refreshing`) and
  auto-refetches; 404 removes the entry from the local list; 422 renders field-level
  validation messages inside the edit form, parsed from FastAPI structured detail
  (`{detail: [{loc, msg}]}`). On mutation success, the entry is replaced from the response
  payload (approve/edit) or removed/soft-marked deleted (delete) without a list-level
  loading spinner; on failure, local state is unchanged. When an edit auto-promotes a
  pending entry to curated via scope_agents assignment, an inline promotion note is shown
  immediately. `hooks/usePendingMemoryCount.ts` dispatches a pending-count delta event on
  successful pending-state mutations; `Shell.tsx` consumes this event and updates the
  nav-rail memory badge immediately (hidden at zero, aria-label includes count) without
  waiting for the next 60s poll. Verified by
  `serve/cockpit/web/src/__tests__/MemoryTab_1672.test.tsx` (74 tests — accordion detail
  and sanitization schema, state-dependent button visibility, OCC/404/422 error UX,
  response-driven local updates without list spinner, state promotion feedback, immediate
  nav-badge sync after pending-state mutations, approved-state delete confirmation
  (soft-delete dialog branch), and approved-entry edit downgrade to curated).

## Product Boundary

Cockpit steering owns viewing, editing, moving/archiving, user blocks, health/admin,
activity, and decision resolution. Task creation and agent lifecycle operations stay in
agent/planner/MCP flows.

## Engine Surface — Allowlist

The cockpit exposes a subset of `KanbanEngine`'s public API. Read routes call the engine or `CockpitView` directly; `adapter.py` retains only one method used by mutation routes.

### Via adapter

| Method | Purpose |
|--------|---------|
| `valid_transitions(status)` | Validates move targets; called by the `move_task` mutation route |

### Mutation routes

All mutation routes go through the `CockpitView` facade.

#### Via CockpitView facade

| Method | Route | Notes |
|--------|-------|-------|
| `view.show_task()` + `view.move_task()` | `POST /tasks/{id}/move` | OCC token precheck, then `valid_transitions` check (bypassed for `archived`), then move through CockpitView with `expected_updated`; archival moves validated by `CockpitView.move_task` before the engine call (`ValidationError` → 422); `ConcurrencyError` → 409 |
| `view.show_task()` + `view.release_task()` | `POST /tasks/{id}/release` | Claimed check (409 if unclaimed), release through CockpitView with `expected_updated`; `ConcurrencyError` → 409 |
| `view.show_task()` + `view.edit_task()` | `POST /tasks/{id}/edit` | Pre-fetches task when `tags`, `depends_on`, or `block_reason` is set (for diff and D21 block:user lifecycle); diffs tags/deps, restores block:user; tri-state field semantics: `body: ""` clears body, `body: null`/omitted = no change; `parent: null` clears parent, negative → 422; `block_reason: ""`/`null` unblocks; edit with `expected_updated`; `ConcurrencyError` → 409 |
| `view.sweep()` | `POST /tasks/sweep` | Releases expired claims; returns list of released task IDs |
| `view.scan_corruption()` | `POST /tasks/scan` | Scans all task files for corruption; returns list of `{code, detail, file_path}` items |
| `view.repair_storage()` | `POST /tasks/repair` | Repairs corrupted task files; returns list of `RepairOutcome` items |
| `view.compact_activity()` | `POST /tasks/compact-activity` | Compacts the activity log; returns `ActivityCompactionResult` |
| `view.cleanup()` | `POST /tasks/cleanup` | Releases expired claims, archives done tasks, and prunes orphan lock files; returns `CleanupResult` with `released_claim_ids`, `archived_task_ids`, `pruned_lock_paths`, and `skipped_items` |

> **TODO:** stale — `view.cleanup()` row claims `pruned_lock_paths` return field and "prunes orphan lock files" behavior; both were removed by the flock-infrastructure removal. `CleanupResult` now returns `released_claim_ids`, `archived_task_ids`, `duplicate_removed_ids`, `skipped_items`. [#1571]

### Excluded methods — why

| Method | Reason excluded |
|--------|----------------|
| `create_task()` | Pipeline agents create tasks, not the UI |
| `claim_task()` / `start_work()` / `end_work()` | Agent lifecycle operations |
| `refresh_config()` | Managed internally by the engine |

Any route exposing excluded lifecycle methods requires an explicit product brief before implementation.

Decision behavior after #1385 and #1389:

- Backend decision lifecycle is canonical: resolution appends the task summary,
  moves decision files to `resolved/`, and applies unblock semantics per response.
- Frontend decision UX after #1645 and #1648: the `/decisions` tab (`DecisionsPage`) is the primary path; `DRStatusIndicator` in the status bar → `ResolveModal` is the secondary (route-independent Shell-level) path. `DecisionViewport` is no longer rendered in the sidecar.

## Error Envelope

Most cockpit routes use a stable JSON error envelope with no `detail` or `guidance` fields:

```json
{"code": "<STABLE_CODE>", "message": "<user-facing text>"}
```

Decisions API resolve routes are the explicit exception for malformed/unknown
IDs and duplicate cockpit-resolved IDs; those responses use FastAPI's
`{"detail": "..."}` envelope for 404/422 cases.

| Domain error | HTTP status | `code` example |
|---|---|---|
| `NotFoundError` | 404 | `ERR_NOT_FOUND` |
| `ConcurrencyError` | 409 | `ERR_STALE` |
| `ValidationError` | 422 | `ERR_INVALID_STATUS` |
| `ConfigError` | 500 | *(varies by config context)* |
| Unexpected exception | 500 | `COCKPIT_INTERNAL_ERROR` |

Handled by centralized `@app.exception_handler` registrations in `main.py`; route code raises domain errors directly and lets the handlers serialize them.

## Decisions API

Two endpoints handle Decision Request (DR) lifecycle. These routes use `get_decisions_dir` (a separate DI callable in `deps.py`) — not the CockpitView facade.

| Route | Behaviour |
|-------|----------|
| `GET /api/decisions/pending` | Reads `decisions/pending/*.md`, parses YAML frontmatter, returns `{count, items[{id, task_id (int), agent, request_type, created, title, body, body_preview}]}`. Only items with frontmatter `response == "pending"` are included. Items that fail schema validation (e.g. missing or non-coercible `task_id`) are silently excluded; `count` reflects only successfully validated items. Returns `{count: 0, items: []}` when the directory is empty or missing. |
| `POST /api/decisions/{id}/resolve` | Accepts `{response: "approved"\|"needs-info"\|"rejected", notes?: string (max 10,000 chars)}`. Immediately: appends the canonical `## Decision Request` summary to the linked task, unblocks the task for `approved`/`rejected` responses, and moves the DR file from `pending/` to `resolved/`. Returns `{id, response}` on success. Returns 404 (`{detail}`) for unknown or already-cockpit-resolved ids. Returns 409 (`{code, message}`) for DRs resolved by another agent (still in `resolved/`). Returns 422 (`{detail}`) for malformed ids or `notes` exceeding 10,000 characters. |

## Memory API

Four endpoints expose `MemoryEngine` read and OCC mutation operations. These routes use `get_memory_engine` (a separate DI callable in `deps.py`) — not the CockpitView facade.

| Route | Behaviour |
|-------|----------|
| `GET /api/memories` | Returns `{ entries: [...], parse_errors: int }`. Each entry carries all 11 `MemoryEntryResponse` fields: `id`, `title`, `content`, `categories`, `confidence`, `state`, `scope_agents`, `source_agent`, `created_at`, `updated_at`, `approved_at`. Entries in all four states (`pending`, `curated`, `approved`, `deleted`) are included. `parse_errors` is the count of files that failed to parse. |
| `POST /api/memories/{id}/approve` | Accepts `{ expected_updated_at: str }` body. Approves one entry in `curated` state; returns `{ entry: MemoryEntryResponse }` on success. Errors: 404 `MEM_NOT_FOUND`, 409 `MEM_CONFLICT` (OCC mismatch), 422 `MEM_INVALID_TRANSITION` (entry not curated). |
| `POST /api/memories/{id}/edit` | Accepts `{ expected_updated_at: str, title?, content?, categories?, confidence?, scope_agents? }` with extra fields forbidden. Editable fields are validated at the cockpit boundary (title: non-empty; content: max 1 024 chars; categories: non-empty list; confidence: 0.7–1.0). Editing an `approved` entry transitions it back to `curated`. Returns `{ entry: MemoryEntryResponse }`. Errors: 404 `MEM_NOT_FOUND`, 409 `MEM_CONFLICT`, 422 `MEM_INVALID_TRANSITION` (entry is `deleted`). |
| `POST /api/memories/{id}/delete` | Accepts `{ expected_updated_at: str }` body. `pending` entries are hard-deleted from disk; `curated`/`approved` entries are soft-deleted (state → `deleted`). Deleting an already-`deleted` entry returns 422. Returns `{ success: true }` on success. Errors: 404 `MEM_NOT_FOUND`, 409 `MEM_CONFLICT`, 422 `MEM_INVALID_TRANSITION`. |

Memory error handlers are registered in `main.py` separately from the kanban error handler, using qualified imports from `owlbear_memory.errors`:

| Memory error | HTTP status | `code` |
|---|---|---|
| `NotFoundError` | 404 | `MEM_NOT_FOUND` |
| `ConcurrencyError` | 409 | `MEM_CONFLICT` |
| `TransitionError` | 422 | `MEM_INVALID_TRANSITION` |

## Ideas API

Two endpoints expose a single shared markdown file for collaborative ideation. These routes use `get_ideas_path` (a DI callable in `deps.py`) — not the CockpitView facade.

| Route | Behaviour |
|-------|----------|
| `GET /api/ideas` | Returns `{"content": "..."}` with the full contents of `.owlbear/ideas.md` when the file exists; returns `{"content": ""}` when the file is absent. |
| `PUT /api/ideas` | Accepts `{"content": "..."}` body (extra fields forbidden — 422 on violation). Writes via `atomic_write` from `owlbear_kanban.storage_io`, creating the file on first write if absent. Returns HTTP 204 with no response body. |

`get_ideas_path` resolves to `kanban_dir.parent / "ideas.md"` (`.owlbear/ideas.md`); override via `app.dependency_overrides` for test isolation.

## Work Sessions Model

`GET /api/sessions` returns derived `SessionRecord` objects built from `activity.jsonl` at read time — there is no separate sessions store.

### Derived states

| State | Derivation condition |
|-------|---------------------|
| `running` | Open claim; last activity within `claim_timeout` |
| `stuck` | Open claim; last activity exceeds `claim_timeout` |
| `completed` | `end_work` with `detail` starting `"success:"` |
| `rejected` | `end_work` with `detail` starting `"reject:"` |
| `blocked` | Any other `end_work` outcome |
| `released` | `release` action in the log |
| `expired` | `sweep-release` action in the log (expired claim auto-released) |

### Filter vocabulary

| Filter value | Included states |
|-------------|-----------------|
| `active` | `running`, `stuck` |
| `all` | all states |
| `blocked-or-rejected` | `blocked`, `rejected` |
| `failed-or-rejected` | `blocked`, `rejected` (legacy alias for `blocked-or-rejected`) |
| `released` | `released` |

Usage: `GET /api/sessions?filter=active`

## Audit Trail — source Attribution Contract

Every mutation written to `activity.jsonl` carries a `source` field. Use `source="cockpit"` for UI-initiated mutations, `source="agent"` for agent-initiated mutations, and `source="engine"` for internal engine operations. `CockpitView` passes `source="cockpit"` explicitly on each mutation call — no constructor-level identity is set.

## Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `COCKPIT_PORT` | `8420` | Override listen port (1-65535) |
| `COCKPIT_NO_OPEN` | unset | Set to `1` to suppress browser auto-open |
| `KANBAN_DIR` | `.owlbear/kanban/` | Override kanban directory path |
| `MEMORY_DIR` | `.owlbear/memory/` | Override memory directory path used by `MemoryEngine` |

## Delivery Packaging

- Developer branch (`dev`): frontend source (`serve/cockpit/web/`) is present and used for
  build/test/lint workflows.
- Consumer branch (`main`): sync-to-main builds and stages prebuilt
  `serve/cockpit/dist/` artifacts; consumers launch Cockpit without Node/npm.

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | HTTP framework |
| `uvicorn` | ASGI server |
| `pydantic` | Request/response model validation |
| `sse-starlette` | SSE streaming for the `GET /api/events` invalidation endpoint |
| `watchfiles` | File-system watcher used by the events endpoint |
| `owlbear-kanban` | Kanban engine (workspace package) |
| `owlbear-memory` | Memory engine (workspace package) |
| `ruamel.yaml` | Round-trip YAML parsing for the Decisions API |
