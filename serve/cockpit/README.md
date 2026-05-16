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
  Playwright locator/text assertions in `e2e/card-density-1565.spec.ts` (AC-2).
- #1562 adds shell/sidecar inspector semantic structure: `[data-region="sidecar-header"]`
  renders the selected task identity outside the tab content area; metadata fields render
  `Status:` and `Priority:` labels paired with their values; body, history, and actions
  regions are distinctly identified by `data-region`; decision queue items are `<article>`
  elements with separately labeled Agent/Request type/Age/Task fields; filter controls are
  grouped in `role="toolbar"`; the product-identity `<h1>` has non-zero visible dimensions
  (width > 50px, height > 10px); each named status-bar control carries an individually
  asserted accessible name. Verified in `e2e/shell-sidecar-inspector-1562.spec.ts`
  (18 tests).
- #1564 adds filter and form control PDS compliance verification: 34 Playwright E2E
  tests in `e2e/filter-controls-1564.spec.ts` cover the filter-panel workflow (toggle
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
  320x800, 768x1024, and 1024x768 in `e2e/responsive-contract-1566.spec.ts`. Mobile
  task detail renders in a `p-sheet` custom element at 320x800 (post-#1560 board-first
  contract) with click-dependent selection signals.
- #1568 restores sequential keyboard reachability for the nav-rail: the `<PButton
  data-surface="kanban">` in `Shell.tsx` no longer carries `tabIndex={-1}`, so the
  persistent nav control is reachable via Tab. Modal/popover containers
  (`role="dialog"`) retain their `tabIndex={-1}` for focus-management; only the
  persistent nav control was changed. Verified in
  `e2e/nav-rail-taborder-1568.spec.ts` (2 E2E assertions) and
  `tests/test_cockpit_shell_sidecar_1568.py` (source inspection).
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
  Verified by `serve/cockpit/web/e2e/overlay-behavior-1563.spec.ts` (19 E2E tests, all
  pass) and `serve/cockpit/web/src/__tests__/OverlayAnchoring_1569.test.tsx` (13 unit
  tests covering trigger-anchored positioning and CleanupPanel modal-equivalence
  semantics).
- #1572 completes the cockpit responsive contract: `Shell.css` eliminates 320px
  document-level horizontal overflow via `overflow-x: clip` on `.shell`, wrapping on
  `.shell__status-bar` with compact vertical padding, and `min-width: 0` /
  `overflow-wrap: anywhere` on the product-identity text. `Column.tsx` makes
  `tabIndex="0"` conditional on `scrollHeight > clientHeight` via `ResizeObserver`,
  `window.resize`, and `MutationObserver`-based re-sync, removing the attribute when
  the column body is not scrollable. Responsive proof coverage:
  `e2e/responsive-layout-1391.spec.ts` (42 tests) proves 320px overflow elimination
  and last-column reachability via board-container `scrollIntoView`, 768px tablet
  workspace/sidecar sizing, and 1024px/1440px desktop layout with exactly 7 visible
  columns and no board-container vertical overflow; `e2e/responsive-contract-1566.spec.ts`
  (39 tests) proves the conditional `tabIndex` both-branch contract (scrollable column
  bodies gain the attribute; non-scrollable column bodies lack it) and mobile `p-sheet`
  heading identity (exact selected task title) after task selection at 320×800.
- #1573 adds cross-cutting visual-regression and structural consolidation coverage for
  the phase-2 visual remediation lane: 19 screenshot baselines committed across desktop
  board, selected-task sidecar, filter panel, context menu, Health popover, DR popover,
  Cleanup dialog, Resolve modal, Archive modal, Repair confirm, dark mode, tablet 768px,
  and mobile 320px states (`e2e/visual-remediation-1573.spec.ts`). Structural gates
  include non-reflow proof (overlay surfaces do not expand parent containers), 320px
  horizontal-overflow guard, and a non-circular PDS native-control gate
  (`ac2c_v2_native_controls_match_documented_exception_set`) that enumerates all native
  `<button>` elements in the rendered board view and fails if any fall outside the
  six-item documented exception set. Keyboard reachability gates (AC-7-v2) verify Tab
  traversal reaches the status bar, nav-rail, workspace, filter-toggle, sidecar-collapse,
  and sidecar-content controls in base state and filter-panel-open state; DOM audit covers
  both states and PDS custom-element hosts. `DecisionViewport` task-reference links were
  converted from native `<button>` to anchor elements to keep the native-control count
  within the documented exception ceiling.
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
