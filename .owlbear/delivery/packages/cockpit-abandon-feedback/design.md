# Cockpit Abandon Feedback Design

> Status: candidate architecture; admission gates pending

## Current Ownership (observed)

- `serve/cockpit/web/src/components/WorkItemDetail.tsx` `ChangeDispositionSection` collects the reason, opens the confirmation `PModal`, and calls `onAbandonChange`; it closes the dialog on success and shows `ActionFeedback` on failure.
- `serve/cockpit/web/src/hooks/useWorkItems.ts` `useWorkItemDetail.abandonChange` calls `abandonWorkItemChange` through `mutate`, which sets `actionResult` to "Change abandoned.", refetches the detail, and calls `onChanged` (portfolio refetch). It returns `null` on success without awaiting the refreshes.
- `serve/cockpit/web/src/pages/WorkPortfolioPage.tsx` effect: when the selected Change was present and its group disappears, it sets workspace to `history`, sets focus destination `history-view`, and navigates to `/delivery/history`, unmounting `SelectedWorkItemDetail` and its action result.
- Live detail and history routes render the same `WorkPortfolioPage` instance (no route-dependent key), so page state survives that navigation (challenger-observed in `routes.ts` and `CockpitShell.tsx`).
- `PToast` is mounted app-wide but auto-dismisses.

## Proposed Architecture

`WorkPortfolioPage` owns one piece of state: `abandonedNotice: { changeId: string; title: string } | null`.

- `SelectedWorkItemDetail` receives a new `onAbandoned(changeId, title)` prop from the page. It wraps `selectedDetail.abandonChange`: before awaiting the request it captures the title from the narrowed available detail (`detail.item.change_title`; `WorkItemDetailResponse` also includes unavailable responses without `item`, and `WorkItemDetail` is only rendered for available detail), then, when the returned error is `null`, calls `onAbandoned(identity.changeId, capturedTitle)`. `WorkItemDetail`'s `onAbandonChange` contract (`(reason) => Promise<Error | null>`) is unchanged; `ChangeDispositionSection` needs no change.
- The page renders the notice at page level above the workspace content and outside the `PFlyout` (both Current delivery and Change history views), so it survives the detail unmount and the automatic navigation. Text: "<title> was abandoned and is now in Change history." with `role="status"`, success styling consistent with existing success feedback (`border-l-4 border-success bg-surface`), and a dismiss button (Porsche Design System button, icon close, accessible label "Dismiss abandonment confirmation") that sets the state to `null`.
- A later successful abandonment replaces the notice. Failure paths never call `onAbandoned`.
- The existing selected-Change-left-portfolio effect, focus restoration, and navigation are untouched.

## Interfaces

- New internal prop `onAbandoned: (changeId: string, title: string) => void` on `SelectedWorkItemDetail` / `SelectedDetail` in `WorkPortfolioPage.tsx`. No public API, backend, or `WorkItemDetail` prop changes.

## Alternatives And Tradeoffs

- Keep detail open (B) and shell-wide banner (C) rejected by user decision A.
- Rendering the notice only in Change history would hide it if the Change somehow stays in the portfolio; page-level rendering covers both views at negligible cost.

## Known Weaknesses

- The notice is in-memory page state; reload or leaving the Delivery page clears it (accepted exclusion).
- The in-detail "Change abandoned." action result remains and is redundant when the detail does stay open; harmless.
- Porsche Design System keyboard operation and real-browser focus are proven only through jsdom Vitest, not a real browser.
- Baseline (2026-10-06, main checkout): full `npm run lint:biome` fails because local runtime directories under `.owlbear/controller/releases/` contain nested root `biome.json` files; this is environmental and unrelated. Proof therefore uses Biome scoped to changed files from the repository root.

## Proof Approach

- Extend `serve/cockpit/web/src/__tests__/WorkPortfolio.part3.test.tsx` (existing abandonment tests and harness): after confirm, make the fixture portfolio drop the Change, assert navigation to Change history, focus on the Change history view control (`[data-workspace-view="history"]`), and the notice text with the title; trigger further refreshes and a view switch, assert it remains; activate dismiss, assert removal. Assert the failure test shows no notice.
- In `serve/cockpit/web/`: `npx vitest run src/__tests__/WorkPortfolio.part` (all `WorkPortfolio.part*.test.tsx` files), `npx tsc -b`, and `node scripts/run-biome-check.mjs check <changed files as repository-root-relative paths>`.
