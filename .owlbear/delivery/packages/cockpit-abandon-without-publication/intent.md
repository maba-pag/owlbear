# Cockpit Abandon Without Publication

> Status: candidate Design authority; admission gates pending

## Problem

Cockpit offers "Abandon Change" only in the Change publication detail: `ChangeDispositionSection` in `serve/cockpit/web/src/components/WorkItemDetail.tsx` returns `null` unless `card.scope` is `change-publication` (observed). Delivery projects the publication card only when every outcome is completed, a checkpoint is pending, or the Change has a disposition, deferral, or abandonment (`serve/delivery/src/owlbear_delivery/work_items.py` `_project_cards`, observed). An in-delivery Change therefore has no abandon control in Cockpit, although Delivery accepts the abandon intent for it and Pause is shown on every card detail. Observed 2026-10-06: `delivery-action-readiness` had to be abandoned through the agent tool (user-reported).

## Product Promise

- Every unfinished, not yet abandoned Change offers "Abandon Change" in Cockpit, whichever of its card details (outcome or publication) the user opens.
- The control keeps the same reason field, confirmation dialog, request, and failure feedback as today.
- Completed and abandoned Changes show no abandon control on any card detail.
- Delivery, not Cockpit, decides whether a Change is still abandonable; Cockpit only maps the projected flag.

## Normal Workflow

1. The user opens any outcome detail of an in-delivery Change (no publication card exists yet).
2. In the "Change lifecycle" section the user enters a reason, selects "Abandon Change", then "Confirm abandon Change".
3. Delivery records the abandonment through the existing `POST /api/changes/{change_id}/abandon` route; the Change becomes abandoned exactly as it does today from the publication detail.

## Operating Context (inferred)

- Actors and trust: one trusted local user operating Cockpit on `127.0.0.1`; Delivery MCP agents read the same projection and are trusted but fallible.
- Exposure: none added; the existing abandon route and Delivery intent are reused; one boolean is added to an existing read projection.
- Stakes: abandonment is permanent for the Change (retained as an abandoned record); local only.
- Guarded: accidental abandonment (reason plus confirmation dialog, unchanged); offering abandonment on completed or abandoned Changes. Not guarded: a transient Delivery refusal (for example an active claim) is surfaced through the existing failure feedback rather than pre-hidden, as on the publication detail today.

## Scope

- Delivery `WorkItemDetailView` gains a projected `abandon_available` boolean, true unless the Change has a completion or abandonment record, on both outcome and publication details.
- Cockpit `ChangeDispositionSection` renders on every available card detail where `abandon_available` is true, replacing the publication-scope and abandoned-phase checks.
- Cockpit TypeScript detail type gains the optional field.
- Focused Delivery pytest, Cockpit HTTP and schema-parity pytest, and Cockpit Vitest coverage.

## Accepted Exclusions

- No abandon control on the portfolio group row or table; the control lives in the card detail (user request names `WorkItemDetail.tsx`).
- No pre-hiding for transient Delivery refusals (active claims); existing failure feedback covers them.
- No change to Delivery's abandonment rules, the abandon route, the request body, or the Cockpit backend route code.

## Preserved Behavior

- Abandon request body (`confirmed_abandonment`, `reason`, `expected_frontier_digest` from the detail's `snapshot_version`), reason requirement, confirmation dialog, and failure handling are unchanged.
- Publication-detail abandonment remains available whenever it is today for unfinished Changes, including paused Changes ("This Change is paused and retains its worktree." note).
- Pause and Resume controls and their availability are unchanged.
- The Cockpit backend passes Delivery's `WorkItemDetailView` through unchanged.

## Decisions

- D1 user-confirmed (2026-10-06): Option A — Delivery projects an explicit `abandon_available` flag on `WorkItemDetailView`; Cockpit gates on it. Rejected: frontend inference from `change_progress` and `pause_unavailable_reason` (B); projecting `publication` on outcome details (C).

## Success

From an outcome detail of an in-delivery Change with no publication card, the user abandons the Change with a reason and confirmation in Cockpit, without agent tools; outcome and publication details of completed or abandoned Changes show no abandon control.

## Technically Done But Wrong

- The control appears on an outcome detail of an abandoned or completed Change.
- Two abandon controls appear in one detail view.
- A different reason or confirmation flow than the publication detail.
- Hiding the control whenever Pause is unavailable (paused Changes can still be abandoned).
- Cockpit infers terminal state from other fields instead of the Delivery flag.
- The flag is set only on publication details, so outcome details still lack the control.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: user-reported problem and requested outcome (2026-10-06)
statement: Every Change without a completion or abandonment record offers Abandon Change in each of its Cockpit card details, outcome or publication, and completed or abandoned Changes offer it in none.
```

```yaml target-contract
kind: commitment
id: COM-002
class: agreed-path
provenance: user decision D1 option A (2026-10-06)
statement: Delivery projects abandonment eligibility as an explicit abandon_available boolean on WorkItemDetailView, true exactly when the Change has neither a completion nor an abandonment record, and Cockpit gates the control only on that flag.
```

```yaml target-contract
kind: commitment
id: COM-003
class: protected-request
provenance: user request and source-observed existing behavior
statement: The reason field, confirmation dialog, abandon request body, failure feedback, Delivery abandonment rules, Pause and Resume controls, and Cockpit backend pass-through are unchanged.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Abandon from any Change detail
promise: The user can abandon any unfinished, not yet abandoned Change from any of its Cockpit card details with the same reason and confirmation flow, and never sees the control on completed or abandoned Changes.
dependencies: []
commitments: [COM-001, COM-002, COM-003]
acceptance:
  - "AC-001: Given a Delivery Change with no completion or abandonment record, WorkItemProjector.show_view returns abandon_available true for every outcome detail and, when present, the publication detail, including for a paused Change."
  - "AC-002: Given a Delivery Change with an abandonment record or a completion record, WorkItemProjector.show_view returns abandon_available false for every outcome detail and the publication detail."
  - "AC-003: Given a Cockpit outcome detail whose abandon_available is true, the detail shows exactly one Abandon Change control; entering a reason and confirming sends POST /api/changes/{change_id}/abandon with confirmed_abandonment true, the trimmed reason, and the detail snapshot_version as expected_frontier_digest."
  - "AC-004: Given a Cockpit outcome or publication detail whose abandon_available is false or absent, no Abandon Change control is rendered."
  - "AC-005: Given the existing publication-detail abandonment tests, including the failure case that keeps the confirmation dialog open with the error, they pass with fixtures that project abandon_available true."
  - "AC-006: Given the changed sources, uv run pytest serve/delivery/tests/test_work_items.py passes, and in serve/cockpit/web the WorkPortfolio Vitest files, npx tsc -b, and Biome check scoped to the changed files through scripts/run-biome-check.mjs pass."
  - "AC-007: Given the Cockpit HTTP detail route for an outcome of an in-delivery Change, the response item carries abandon_available true, and tests/test_cockpit_work_items.py and tests/test_cockpit_boundary.py pass with the field mirrored in the Cockpit WorkItemDetailView TypeScript interface."
```
