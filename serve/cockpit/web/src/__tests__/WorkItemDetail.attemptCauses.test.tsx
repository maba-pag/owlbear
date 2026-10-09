import { screen, within } from "@testing-library/react";
import { expect, it } from "vitest";
import {
  detail,
  fixtureState,
  installWorkPortfolioHarness,
  publicationCardForChecks,
  publicationForChecks,
  readiness,
  renderPage,
  situation,
} from "./workPortfolioHarness";

installWorkPortfolioHarness();

it("states each exhausted attempt's recorded cause in plain language without reconstructing it", async () => {
  const blocked = readiness({
    status: "blocked",
    reason_code: "retry-exhausted",
    next_actor: "you",
    attempts: 4,
    stop_reason: "retry-exhausted",
    grant_attempt_id: "finalizer-attempt-4",
    progress: situation("your-decision", { waiting_on: "you" }),
    retry_history: [
      { ordinal: 1, kind: "original", status: "failed", failure_code: null, observed_at: null },
      {
        ordinal: 2,
        kind: "repair",
        status: "failed",
        failure_code: "finalizer-ended-without-report",
        observed_at: "2026-10-08T10:00:00Z",
      },
      { ordinal: 3, kind: "repair", status: "failed", failure_code: "maintained-check-failed", observed_at: null },
      { ordinal: 4, kind: "repair", status: "failed", failure_code: "agent-specific-code", observed_at: null },
    ],
  });
  fixtureState.currentDetail = detail({
    card: publicationCardForChecks({ publication_phase: "ready-for-finalization", readiness: blocked }),
    readiness: blocked,
    publication: publicationForChecks("ready-for-finalization"),
  });
  renderPage("/delivery/change-alpha/publication");

  const causes = await screen.findByTestId("readiness-attempt-causes");
  expect(
    within(causes)
      .getAllByRole("listitem")
      .map((item) => item.textContent),
  ).toEqual([
    "Failed; no cause was recorded.",
    "The Finalizer ended without a report; no result was recorded.",
    "A verification check failed.",
    "Failed with code agent-specific-code.",
  ]);
  // The recorded codes stay available in the technical history.
  expect(screen.getByTestId("readiness-retry-history")).toHaveTextContent("finalizer-ended-without-report");
});
