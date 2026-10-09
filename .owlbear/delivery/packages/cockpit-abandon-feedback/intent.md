# Cockpit Abandon Feedback

> Status: candidate Design authority; admission gates pending

## Problem

In Cockpit's Change detail, after "Confirm abandon Change" the success message ("Change abandoned.") is visible for about a second. The abandoned Change then leaves the current portfolio, and `WorkPortfolioPage` closes the detail and navigates to `/delivery/history`. The success message lives in `useWorkItemDetail` state, which unmounts with the detail. The user cannot read whether abandonment worked or where the Change went (user-observed 2026-10-06 with `frontier-serialization-contract`; mechanism observed in source).

## Product Promise

- After a successful abandonment, the user sees a confirmation that stays visible until they dismiss it.
- The confirmation names the abandoned Change by its title and states that it is now in Change history.
- The user still lands on Change history automatically, where the abandoned record is retained.

## Normal Workflow

1. The user opens a Change's publication detail, enters a reason, selects "Abandon Change", then "Confirm abandon Change".
2. Abandonment succeeds; the Change leaves the current portfolio; Cockpit closes the detail and shows Change history (existing behavior).
3. A dismissible success notice reads that the named Change was abandoned and is now in Change history.
4. The notice stays through polling refreshes and view switches until the user dismisses it.

## Operating Context (inferred)

- Actors and trust: one trusted local user operating Cockpit on `127.0.0.1`.
- Exposure: none added; presentation-only over existing Cockpit API responses.
- Stakes: low and reversible; feedback-only. Abandonment itself is unchanged.
- Guarded: lost or misleading success feedback after the detail closes. Not guarded: persistence of the notice across page reload, browser tabs, or leaving the Delivery page; the notice is in-page state.

## Scope

- Page-level abandonment notice owned by `WorkPortfolioPage`, fed by the successful abandon action in the Change detail.
- Focused Vitest coverage in the existing Work Portfolio test suite.

## Accepted Exclusions

- No `PToast` (auto-dismisses) and no shell-wide notification mechanism (user decision A).
- No persistence of the notice across reload or leaving the Delivery page.
- No change to abandonment API, backend, confirmation dialog, history records, or the auto-navigation rule.

## Preserved Behavior

- Abandon request body, reason requirement, confirmation dialog, and failure handling (dialog stays open with the error; no success feedback) are unchanged.
- Automatic close and navigation to Change history when a selected Change leaves the portfolio is unchanged, including focus moving to the Change history view control.
- Abandoned Changes remain in Change history as abandoned records.

## Decisions

- User-confirmed (2026-10-06): Option A — show a dismissible notice on the Delivery portfolio page and keep auto-navigation to Change history. Rejected: keeping the detail open (B); a shell-wide banner (C).
- Source-observed: `PToast` auto-dismisses and cannot satisfy "stays until dismissed".

## Success

After confirming abandonment of a Change titled T, the user lands on Change history and reads a notice naming T and stating it is now in Change history; the notice remains until the user dismisses it.

## Technically Done But Wrong

- Lengthening a timeout or using a toast that still disappears on its own.
- A notice that names only the internal Change ID when a title is available, or omits where the Change went.
- A notice that appears on abandonment failure.
- Suppressing or changing the existing auto-navigation or focus behavior.
- Notice state kept inside the detail component so it still unmounts with the detail.

```yaml target-contract
kind: commitment
id: COM-001
class: dealbreaker
provenance: user-reported problem and requested outcome
statement: After a successful Change abandonment from Cockpit, a confirmation naming the Change and stating that it is now in Change history remains visible until the user dismisses it, independent of the Change detail closing.
```

```yaml target-contract
kind: commitment
id: COM-002
class: agreed-path
provenance: user decision A (2026-10-06)
statement: The confirmation is a dismissible notice owned by the Delivery portfolio page; the existing automatic navigation to Change history is kept; no auto-dismissing toast or shell-wide notification mechanism is introduced.
```

```yaml target-contract
kind: commitment
id: COM-003
class: protected-request
provenance: source-observed existing behavior
statement: The abandonment request, reason requirement, confirmation dialog, failure handling, auto-navigation focus behavior, and Change history retention of abandoned records are unchanged.
```

```yaml target-contract
kind: outcome
id: OUT-001
title: Persistent abandonment confirmation
promise: After abandoning a Change, the user reads a confirmation naming the Change and stating it is in Change history, and it stays until they dismiss it.
dependencies: []
commitments: [COM-001, COM-002, COM-003]
acceptance:
  - "AC-001: Given an open Change publication detail whose abandonment succeeds and whose Change then leaves the current portfolio, Cockpit shows Change history and a notice containing the Change title and stating that the Change is now in Change history."
  - "AC-002: Given the abandonment notice is shown, it remains visible across subsequent portfolio refreshes and switches between Current delivery and Change history until the user activates its dismiss control, after which it is no longer rendered."
  - "AC-003: Given the abandonment request fails, no abandonment notice is shown and the confirmation dialog stays open with the error, as before."
  - "AC-004: Given the abandonment notice is shown, it is exposed with role status and has a keyboard-operable dismiss button with an accessible name referencing the abandonment confirmation."
  - "AC-005: Given the changed Cockpit frontend, in serve/cockpit/web the WorkPortfolio Vitest files, npx tsc -b, and Biome check scoped to the changed files through scripts/run-biome-check.mjs pass."
```
