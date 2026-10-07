# Cockpit Abandon Without Publication Design

> Status: candidate architecture; admission gates pending

## Current Ownership (observed)

- `serve/cockpit/web/src/components/WorkItemDetail.tsx` `ChangeDispositionSection` gates on `card.scope === "change-publication"` and hides when `publication.phase === "abandoned"`; it collects the reason, opens the confirmation `PModal`, and calls `onAbandonChange(reason)`. It is rendered once, last, in `WorkItemDetail`.
- `serve/cockpit/web/src/hooks/useWorkItems.ts` `abandonChange` posts with the detail's `snapshot_version` as the expected frontier digest; it is Change-level and works for any card detail.
- `serve/cockpit/src/owlbear_cockpit/routes/target_work.py` passes Delivery's `WorkItemDetailView` through unchanged (`target_models.py` `item: WorkItemDetailView`) and routes abandon to `set_change_intent(ABANDON)`. No Cockpit backend change is needed.
- `serve/delivery/src/owlbear_delivery/work_items.py` `WorkItemProjector.show_view` builds `WorkItemDetailView` in two branches (publication and outcome); only the publication branch carries `publication`. `application_readiness.py` updates views through `model_copy`, which preserves added fields (challenger-observed). Delivery MCP serializes the model unfiltered (challenger-observed in `target_server.py`).
- `serve/delivery/src/owlbear_delivery/delivery_runtime.py` `abandon_change` refuses completed Changes and any active outcome or Integration repair claim, and returns the existing receipt for an already-abandoned Change; `_require_change_mutable` explicitly permits `abandon_change` for paused and attention Changes.
- `tests/test_cockpit_boundary.py` `test_work_item_detail_view_typescript_parity` requires every `WorkItemDetailView` field to be mirrored in the Cockpit TypeScript interface.

## Proposed Architecture

### Delivery projection

- Add `abandon_available: bool = False` to `WorkItemDetailView` beside `pause_available`. Default `False` keeps unconstructed views fail-closed.
- In `WorkItemProjector`, compute once from the captured frontier: `change_completion is None and change_abandonment is None`, and pass it in both `show_view` branches.
- The flag mirrors Delivery's terminal checks, not transient claim refusals; those stay with the runtime and surface as the existing error.

### Cockpit frontend

- `serve/cockpit/web/src/api/workItems.ts`: add `abandon_available?: boolean` to `WorkItemDetailView` (keeps the TypeScript parity test green).
- `ChangeDispositionSection`: replace the scope and abandoned-phase guards with `if (props.detail.item.abandon_available !== true) return null;`. Keep hooks before the guard. Change the paused note condition to `item.change_progress === "paused" || phase === "deferred"` so it also appears on outcome details of paused Changes. All other markup, reason handling, confirmation, and failure feedback stay unchanged.
- No placement change: the section stays last in `WorkItemDetail`, so each detail renders at most one control.

## Interfaces

- `WorkItemDetailView.abandon_available: bool` (Delivery model, Delivery MCP `show_work_item_view`, Cockpit `GET` detail JSON). Additive read field; no request or route change.

## Alternatives And Tradeoffs

- B (frontend inference from `change_progress == null` and `pause_unavailable_reason == "change-inactive"`) rejected by D1: couples Cockpit to an incidental field combination.
- C (project `publication` on outcome details) rejected by D1: publication-scoped UI would start rendering on outcome details.

## Known Weaknesses

- A merged-but-not-completed Change (merged pull-request latch, no completion record) still projects `abandon_available` true, because Delivery's runtime accepts abandonment there; this matches today's publication-detail behavior and is preserved.
- Active-claim refusals are not pre-hidden; the user sees the existing failure feedback in the confirmation dialog.
- Delivery MCP serialization of the new field is not separately tested; it relies on unfiltered model serialization (source-observed).
- Sibling package `cockpit-abandon-feedback` edits `WorkPortfolioPage.tsx` and `WorkPortfolio.part3.test.tsx` around abandonment success feedback and wraps the same callback without changing its contract; no semantic conflict, but shared part3 tests may need textual reconciliation.
- Real-browser behavior is proven only through jsdom Vitest.

## Proof Approach

- Delivery: in `serve/delivery/tests/test_work_items.py`, assert `abandon_available` for outcome and publication details across in-delivery, paused (existing deferral test), abandoned (existing abandonment test), and completed (existing merged/completion test) projectors.
- HTTP pass-through: in `tests/test_cockpit_work_items.py`, assert an outcome detail response for an in-delivery Change carries `item.abandon_available` true; check the two additional fixture constructors (around the `WorkItemDetailView` fixtures near line 402) still express their intended state with the new default.
- Parity: `tests/test_cockpit_boundary.py::test_work_item_detail_view_typescript_parity` passes with the mirrored field.
- Cockpit Vitest: `workPortfolioHarness.tsx` default `detail()` fixture projects `abandon_available: true`; abandoned-Change fixtures project `false`. Replace the `WorkPortfolio.part3.test.tsx` test "does not show Change disposition controls on an Outcome detail" with (a) an outcome-detail abandonment test for an in-delivery group without a publication card asserting exactly one "Abandon Change" control and the POST body, and (b) an outcome-detail test with `abandon_available: false` asserting no control (keep its "Defer Change" absence assertion). Update the `WorkPortfolio.part5.test.tsx` test "shows a recorded Pause request on an outcome detail with Resume" so its abandon assertion follows the projected flag.
- Commands: `uv run pytest serve/delivery/tests/test_work_items.py tests/test_cockpit_work_items.py tests/test_cockpit_boundary.py`; in `serve/cockpit/web/`: `npx vitest run src/__tests__/WorkPortfolio.part`, `npx tsc -b`, `node scripts/run-biome-check.mjs check <changed files>`.
