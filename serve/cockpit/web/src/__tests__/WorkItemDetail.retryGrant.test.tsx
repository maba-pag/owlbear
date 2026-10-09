import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import { expect, it } from "vitest";
import {
  card,
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

const GRANT = { kind: "grant-attempt", label: "Grant one more attempt", command: null } as const;
const HEADLINE = "Automatic retries are used up; grant one more attempt or inspect the Change.";

function exhausted(attemptId: string) {
  return readiness({
    status: "blocked",
    reason_code: "retry-exhausted",
    next_actor: "you",
    attempts: 3,
    stop_reason: "retry-exhausted",
    grant_attempt_id: attemptId,
    prompt: null,
    progress: situation("your-decision", { headline: HEADLINE, waiting_on: "you" }),
  });
}

it("grants an exhausted Finalizer one more attempt as the publication card's one action", async () => {
  const blocked = exhausted("finalizer-attempt-3");
  fixtureState.currentDetail = detail({
    card: publicationCardForChecks({
      publication_phase: "ready-for-finalization",
      needs: "you",
      next_actor: "you",
      action: GRANT,
      readiness: blocked,
    }),
    readiness: blocked,
    publication: publicationForChecks("ready-for-finalization"),
  });
  renderPage("/delivery/change-alpha/publication");

  const inspector = await screen.findByTestId("work-item-detail");
  const grantSection = within(inspector).getByTestId("retry-grant");
  expect(grantSection).toHaveTextContent("Granting adds exactly one more Finalizer attempt.");
  expect(within(inspector).queryByTestId("readiness-prompt")).toBeNull();
  expect(within(inspector).queryByRole("button", { name: /^Copy/ })).toBeNull();
  fireEvent.click(within(grantSection).getByText("Grant one more attempt", { selector: "p-button" }));

  await waitFor(() =>
    expect(fixtureState.requests).toContainEqual({
      url: "/api/changes/change-alpha/retry-attempts/finalizer-attempt-3/grant",
      method: "POST",
      body: { expected_frontier_digest: "a".repeat(64) },
    }),
  );
  expect(await screen.findByText("One more attempt granted.")).toBeInTheDocument();
});

it("names the Planner for an exhausted Planning retry and shows no grant without an exhausted attempt", async () => {
  const blocked = exhausted("planner-attempt-3");
  fixtureState.currentDetail = detail({
    card: card({ stage: "planning", needs: "you", next_actor: "you", action: GRANT, readiness: blocked }),
    readiness: blocked,
  });
  const { unmount } = renderPage("/delivery/change-alpha/outcome%3AOUT-001");

  const grantSection = await screen.findByTestId("retry-grant");
  expect(grantSection).toHaveTextContent("Granting adds exactly one more Planner attempt.");
  unmount();

  const builderBlocked = readiness({ ...blocked, grant_attempt_id: null });
  fixtureState.currentDetail = detail({
    card: card({ needs: "you", next_actor: "you", action: GRANT, readiness: builderBlocked }),
    readiness: builderBlocked,
  });
  renderPage("/delivery/change-alpha/outcome%3AOUT-001");
  await screen.findByTestId("work-item-detail");
  expect(screen.queryByTestId("retry-grant")).toBeNull();
});
