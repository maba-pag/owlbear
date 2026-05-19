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
- Frontend decision UX is centered on the decision viewport and resolution modal;
  it is not limited to a small status popover.

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
| `GET /api/decisions/pending` | Reads `decisions/pending/*.md`, parses YAML frontmatter, returns `{count, items[{id, task_id, agent, request_type, created, title, body, body_preview}]}`. Only items with frontmatter `response == "pending"` are included. Returns `{count: 0, items: []}` when the directory is empty or missing. |
| `POST /api/decisions/{id}/resolve` | Accepts `{response: "approved"\|"needs-info"\|"rejected", notes?: string}`. Immediately: appends the canonical `## Decision Request` summary to the linked task, unblocks the task for `approved`/`rejected` responses, and moves the DR file from `pending/` to `resolved/`. Returns `{id, response}` on success. Returns 404 (`{detail}`) for unknown or already-cockpit-resolved ids. Returns 409 (`{code, message}`) for DRs resolved by another agent (still in `resolved/`). Returns 422 (`{detail}`) for malformed ids. |

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
| `ruamel.yaml` | Round-trip YAML parsing for the Decisions API |
